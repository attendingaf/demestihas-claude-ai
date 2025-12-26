"""
Document Processing Service for DemestiChat

Handles document upload, chunking, embedding, and storage in Qdrant for RAG.
Also extracts knowledge triples and stores them in FalkorDB.
Supports PDF, DOCX, and TXT file formats.
"""

import os
import logging
import uuid
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime

try:
    from langchain_community.document_loaders import (
        PyPDFLoader,
        Docx2txtLoader,
        TextLoader,
    )
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings
    import qdrant_client
    from qdrant_client.models import Distance, VectorParams, PointStruct

    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Processes and stores documents for RAG retrieval.

    Features:
    - Multi-format support (PDF, DOCX, TXT)
    - Intelligent chunking with overlap
    - OpenAI embeddings (text-embedding-3-small)
    - Qdrant vector storage
    """

    def __init__(self):
        """Initialize document processor with embeddings and vector store."""
        if not LANGCHAIN_AVAILABLE:
            raise ImportError(
                "Required packages not installed. Install with: "
                "pip install langchain langchain-community langchain-openai "
                "qdrant-client pypdf docx2txt"
            )

        # Initialize OpenAI embeddings
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Initialize Qdrant client
        qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
        qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

        self.qdrant = qdrant_client.QdrantClient(host=qdrant_host, port=qdrant_port)

        # Initialize text splitter
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        # Collection name for documents
        self.collection_name = "documents"

        # Ensure collection exists
        self._ensure_collection()

        logger.info(
            f"DocumentProcessor initialized: collection={self.collection_name}, "
            f"qdrant={qdrant_host}:{qdrant_port}"
        )

    def _ensure_collection(self):
        """Ensure the documents collection exists in Qdrant."""
        try:
            collections = self.qdrant.get_collections().collections
            collection_names = [col.name for col in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.qdrant.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=1536,  # text-embedding-3-small dimension
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Collection {self.collection_name} created successfully")
            else:
                logger.info(f"Collection {self.collection_name} already exists")

        except Exception as e:
            logger.error(f"Failed to ensure collection exists: {str(e)}")
            raise

    async def _extract_knowledge_triples(
        self, text: str, doc_name: str, user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract knowledge triples from document text using LLM.

        Args:
            text: Document text to extract knowledge from
            doc_name: Name of the document
            user_id: User who uploaded the document

        Returns:
            List of knowledge triples
        """
        import requests

        extraction_prompt = f"""You are a Fact Extraction Agent for a knowledge graph system.

Your task is to analyze the following document and extract ALL key facts, entities, and relationships as structured knowledge triples.

DOCUMENT SOURCE: {doc_name}
DOCUMENT CONTENT:
{text[:4000]}  # Limit to first 4000 chars to avoid token limits

EXTRACTION RULES:
1. Extract facts in the form: (Subject, Predicate, Object)
2. Focus on: People, Organizations, Projects, Deadlines, Budgets, Decisions, Actions Required, Key Concepts
3. Subject and Object must be specific entities (names, dates, amounts, projects, concepts)
4. Predicate must be a clear relationship (HAS_DEADLINE, APPROVES, REQUIRES, MANAGES, DEFINES, RELATES_TO, etc.)
5. Include temporal information (dates, quarters, timelines)
6. Include financial information (budgets, costs, approvals)
7. Include technical concepts and definitions
8. Use clear, normalized entity names

OUTPUT FORMAT (JSON):
You MUST respond with ONLY a valid JSON object in this exact format:
{{
  "triples": [
    {{"subject": "Entity1", "predicate": "RELATIONSHIP", "object": "Entity2", "confidence": 0.95}},
    {{"subject": "Entity2", "predicate": "RELATIONSHIP", "object": "Entity3", "confidence": 0.90}}
  ]
}}

CRITICAL: Output ONLY the JSON object. No explanation, no markdown, no additional text.

Extract NOW:"""

        try:
            openai_api_key = os.getenv("OPENAI_API_KEY")

            if not openai_api_key:
                logger.error(
                    "OPENAI_API_KEY not found - cannot perform fact extraction"
                )
                return []

            llm_response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a fact extraction system. Respond ONLY with valid JSON. No explanation.",
                        },
                        {"role": "user", "content": extraction_prompt},
                    ],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )

            if llm_response.status_code == 200:
                llm_result = llm_response.json()
                llm_content = (
                    llm_result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "{}")
                )

                extracted_data = json.loads(llm_content)
                triples = extracted_data.get("triples", [])

                logger.info(
                    f"✅ Extracted {len(triples)} knowledge triples from document {doc_name}"
                )
                return triples
            else:
                logger.error(
                    f"Knowledge extraction LLM failed with status {llm_response.status_code}"
                )
                return []

        except Exception as e:
            logger.error(f"Knowledge extraction failed: {str(e)}")
            return []

    async def _write_to_falkordb(
        self, triples: List[Dict[str, Any]], user_id: str, doc_name: str
    ) -> Dict[str, Any]:
        """
        Write extracted knowledge triples to FalkorDB.

        Args:
            triples: List of knowledge triples
            user_id: User who uploaded the document
            doc_name: Name of the document

        Returns:
            Writeback result
        """
        # Import the FalkorDB write function from main
        # This avoids circular imports
        from main import write_knowledge_to_falkordb

        try:
            result = await write_knowledge_to_falkordb(
                user_id=user_id,
                triples=triples,
                context=f"Document: {doc_name}",
            )
            return result
        except Exception as e:
            logger.error(f"Failed to write to FalkorDB: {str(e)}")
            return {"success": False, "error": str(e)}

    def process_document(
        self,
        file_path: str,
        doc_id: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
        extract_knowledge: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a document file and store in Qdrant.

        Args:
            file_path: Path to the document file
            doc_id: Unique identifier for this document
            user_id: User who uploaded the document
            metadata: Additional metadata to store with chunks

        Returns:
            Dictionary with processing results

        Raises:
            ValueError: If file format is not supported
            Exception: If processing fails
        """
        logger.info(f"Processing document: {file_path} (doc_id={doc_id})")

        # Determine file type and load document
        if file_path.endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        elif file_path.endswith(".docx"):
            loader = Docx2txtLoader(file_path)
        elif file_path.endswith(".txt"):
            loader = TextLoader(file_path)
        else:
            raise ValueError(
                f"Unsupported file format: {file_path}. "
                "Supported formats: PDF, DOCX, TXT"
            )

        try:
            # Load and split document
            documents = loader.load()
            chunks = self.splitter.split_documents(documents)

            logger.info(
                f"Document loaded: {len(documents)} pages, "
                f"split into {len(chunks)} chunks"
            )

            # Process and store chunks
            points = []
            chunk_texts = []

            for i, chunk in enumerate(chunks):
                # Generate embedding
                embedding = self.embeddings.embed_query(chunk.page_content)

                # Prepare metadata
                chunk_metadata = {
                    "text": chunk.page_content,
                    "doc_id": doc_id,
                    "user_id": user_id,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Add custom metadata if provided
                if metadata:
                    chunk_metadata.update(metadata)

                # Create point for Qdrant
                point = PointStruct(
                    id=str(uuid.uuid4()), vector=embedding, payload=chunk_metadata
                )

                points.append(point)
                chunk_texts.append(chunk.page_content)

            # Batch upsert to Qdrant
            self.qdrant.upsert(collection_name=self.collection_name, points=points)

            logger.info(
                f"Successfully stored {len(points)} chunks for document {doc_id}"
            )

            # PHASE 2: Extract knowledge and write to FalkorDB
            knowledge_result = {"extracted": False, "triples_written": 0}

            if extract_knowledge:
                try:
                    # Combine all chunk texts for extraction
                    full_text = "\n\n".join(chunk_texts)
                    doc_name = (
                        metadata.get("filename", "unknown") if metadata else "unknown"
                    )

                    # Extract knowledge triples (async operation)
                    # Use asyncio to run the async extraction
                    import concurrent.futures

                    # Check if we're in an async context
                    try:
                        loop = asyncio.get_running_loop()
                        # We're in async context - use ThreadPoolExecutor
                        logger.debug(
                            "Using ThreadPoolExecutor for knowledge extraction"
                        )

                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                lambda: asyncio.run(
                                    self._extract_knowledge_triples(
                                        full_text, doc_name, user_id
                                    )
                                )
                            )
                            triples = future.result(timeout=60)
                    except RuntimeError:
                        # No running loop, safe to use asyncio.run()
                        logger.debug("Using asyncio.run() for knowledge extraction")
                        triples = asyncio.run(
                            self._extract_knowledge_triples(
                                full_text, doc_name, user_id
                            )
                        )

                    if triples:
                        logger.info(
                            f"📊 Extracted {len(triples)} knowledge triples from {doc_name}"
                        )

                        # Write to FalkorDB
                        try:
                            loop = asyncio.get_running_loop()
                            # We're in async context - use ThreadPoolExecutor
                            with concurrent.futures.ThreadPoolExecutor() as executor:
                                future = executor.submit(
                                    lambda: asyncio.run(
                                        self._write_to_falkordb(
                                            triples, user_id, doc_name
                                        )
                                    )
                                )
                                write_result = future.result(timeout=60)
                        except RuntimeError:
                            # No running loop
                            write_result = asyncio.run(
                                self._write_to_falkordb(triples, user_id, doc_name)
                            )

                        if write_result.get("success"):
                            knowledge_result["extracted"] = True
                            knowledge_result["triples_written"] = write_result.get(
                                "triples_added", 0
                            )
                            logger.info(
                                f"✅ FALKORDB WRITEBACK: {knowledge_result['triples_written']}/{len(triples)} "
                                f"triples from document {doc_name} persisted to knowledge graph"
                            )
                        else:
                            logger.warning(
                                f"⚠️ FalkorDB writeback failed for {doc_name}: {write_result.get('error')}"
                            )
                    else:
                        logger.info(f"No knowledge triples extracted from {doc_name}")

                except Exception as e:
                    logger.error(f"Knowledge extraction/writeback failed: {str(e)}")

            return {
                "success": True,
                "doc_id": doc_id,
                "chunks_processed": len(chunks),
                "total_characters": sum(len(text) for text in chunk_texts),
                "chunk_texts": chunk_texts[:3],  # Return first 3 chunks as preview
                "knowledge_extracted": knowledge_result["extracted"],
                "knowledge_triples": knowledge_result["triples_written"],
            }

        except Exception as e:
            logger.error(f"Failed to process document {doc_id}: {str(e)}")
            raise

    def search_documents(
        self, query: str, user_id: Optional[str] = None, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks using semantic similarity.

        Args:
            query: Search query text
            user_id: Optional filter by user_id
            limit: Maximum number of results to return

        Returns:
            List of matching chunks with scores
        """
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)

            # Build filter
            query_filter = None
            if user_id:
                from qdrant_client.models import Filter, FieldCondition, MatchValue

                query_filter = Filter(
                    must=[
                        FieldCondition(key="user_id", match=MatchValue(value=user_id))
                    ]
                )

            # Search in Qdrant
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit,
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append(
                    {
                        "text": result.payload.get("text", ""),
                        "doc_id": result.payload.get("doc_id", ""),
                        "chunk_index": result.payload.get("chunk_index", 0),
                        "score": result.score,
                        "metadata": {
                            k: v
                            for k, v in result.payload.items()
                            if k not in ["text", "doc_id", "chunk_index"]
                        },
                    }
                )

            logger.info(
                f"Document search completed: query='{query[:50]}...', "
                f"found {len(formatted_results)} results"
            )

            return formatted_results

        except Exception as e:
            logger.error(f"Document search failed: {str(e)}")
            return []

    def delete_document(self, doc_id: str) -> bool:
        """
        Delete all chunks for a specific document.

        Args:
            doc_id: Document identifier

        Returns:
            True if deletion successful, False otherwise
        """
        try:
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            # Delete all points matching doc_id
            self.qdrant.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
                ),
            )

            logger.info(f"Deleted all chunks for document {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {str(e)}")
            return False


# Singleton instance
_document_processor = None


def get_document_processor() -> DocumentProcessor:
    """Get or create the global DocumentProcessor instance."""
    global _document_processor

    if _document_processor is None:
        _document_processor = DocumentProcessor()

    return _document_processor
