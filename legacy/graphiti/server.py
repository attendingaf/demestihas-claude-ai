import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Configure logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Graphiti Knowledge Graph API Server")

# In-memory knowledge graph storage for development
knowledge_graph: Dict[str, Any] = {"nodes": [], "edges": [], "entities": {}}


class QueryRequest(BaseModel):
    query: str
    user_id: Optional[str] = None
    limit: Optional[int] = 5


class AddNodeRequest(BaseModel):
    user_id: str
    entity_type: str
    entity_name: str
    properties: Optional[Dict[str, Any]] = {}


class KnowledgeTriple(BaseModel):
    subject: str
    predicate: str
    object: str
    confidence: Optional[float] = 1.0
    metadata: Optional[Dict[str, Any]] = {}


class AddKnowledgeRequest(BaseModel):
    user_id: str
    triples: List[KnowledgeTriple]
    context: Optional[str] = None


class QueryResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "graphiti",
        "timestamp": datetime.utcnow().isoformat(),
    }


@app.post("/query", response_model=QueryResponse)
async def query_knowledge_graph(request: QueryRequest):
    """Query the knowledge graph."""
    try:
        query_lower = request.query.lower()
        relevant_entities = []
        relevant_relationships = []

        for node in knowledge_graph["nodes"]:
            if (
                query_lower in node.get("name", "").lower()
                or query_lower in node.get("type", "").lower()
            ):
                relevant_entities.append(node)
                if len(relevant_entities) >= request.limit:
                    break

        for edge in knowledge_graph["edges"]:
            if query_lower in edge.get("relationship", "").lower():
                relevant_relationships.append(edge)

        logger.info(
            f"Query '{request.query}' returned {len(relevant_entities)} entities"
        )

        return QueryResponse(
            success=True,
            data={
                "entities": relevant_entities,
                "relationships": relevant_relationships[: request.limit],
                "relevant_nodes": relevant_entities,
                "query": request.query,
            },
        )

    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/node", response_model=QueryResponse)
async def add_node(request: AddNodeRequest):
    """Add a new node/entity to the knowledge graph."""
    try:
        node_id = f"{request.entity_type}_{len(knowledge_graph['nodes'])}"

        node = {
            "id": node_id,
            "type": request.entity_type,
            "name": request.entity_name,
            "properties": request.properties,
            "user_id": request.user_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        knowledge_graph["nodes"].append(node)

        if request.user_id not in knowledge_graph["entities"]:
            knowledge_graph["entities"][request.user_id] = []
        knowledge_graph["entities"][request.user_id].append(node_id)

        logger.info(f"Added node {node_id} for user {request.user_id}")

        return QueryResponse(
            success=True, data=node, message=f"Node {node_id} created successfully"
        )

    except Exception as e:
        logger.error(f"Failed to add node: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/knowledge/add", response_model=QueryResponse)
async def add_knowledge_triples(request: AddKnowledgeRequest):
    """
    Add knowledge triples (Subject-Predicate-Object) to the knowledge graph.

    This is the mandatory writeback endpoint for the LangGraph knowledge consolidation node.
    """
    try:
        added_triples = []

        for triple in request.triples:
            # Find or create subject node
            subject_node = next(
                (n for n in knowledge_graph["nodes"] if n["name"] == triple.subject),
                None,
            )
            if not subject_node:
                subject_id = f"entity_{len(knowledge_graph['nodes'])}"
                subject_node = {
                    "id": subject_id,
                    "type": "entity",
                    "name": triple.subject,
                    "properties": {},
                    "user_id": request.user_id,
                    "created_at": datetime.utcnow().isoformat(),
                }
                knowledge_graph["nodes"].append(subject_node)

            # Find or create object node
            object_node = next(
                (n for n in knowledge_graph["nodes"] if n["name"] == triple.object),
                None,
            )
            if not object_node:
                object_id = f"entity_{len(knowledge_graph['nodes'])}"
                object_node = {
                    "id": object_id,
                    "type": "entity",
                    "name": triple.object,
                    "properties": {},
                    "user_id": request.user_id,
                    "created_at": datetime.utcnow().isoformat(),
                }
                knowledge_graph["nodes"].append(object_node)

            # Create edge (relationship)
            edge_id = f"edge_{len(knowledge_graph['edges'])}"
            edge = {
                "id": edge_id,
                "source": subject_node["id"],
                "target": object_node["id"],
                "relationship": triple.predicate,
                "confidence": triple.confidence,
                "metadata": triple.metadata,
                "user_id": request.user_id,
                "context": request.context,
                "created_at": datetime.utcnow().isoformat(),
            }
            knowledge_graph["edges"].append(edge)

            added_triples.append(
                {
                    "subject": triple.subject,
                    "predicate": triple.predicate,
                    "object": triple.object,
                    "edge_id": edge_id,
                }
            )

        # Update user entity tracking
        if request.user_id not in knowledge_graph["entities"]:
            knowledge_graph["entities"][request.user_id] = []

        logger.info(
            f"✅ Added {len(added_triples)} knowledge triples for user {request.user_id}"
        )

        return QueryResponse(
            success=True,
            data={
                "triples_added": len(added_triples),
                "triples": added_triples,
            },
            message=f"Successfully added {len(added_triples)} knowledge triples",
        )

    except Exception as e:
        logger.error(f"Failed to add knowledge triples: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/knowledge/get")
async def get_knowledge(user_id: Optional[str] = None, entity: Optional[str] = None):
    """
    Retrieve knowledge triples from the graph.

    Args:
        user_id: Filter by user
        entity: Filter by entity name (subject or object)
    """
    try:
        filtered_edges = knowledge_graph["edges"]

        if user_id:
            filtered_edges = [e for e in filtered_edges if e.get("user_id") == user_id]

        if entity:
            # Find node with matching name
            matching_nodes = [
                n
                for n in knowledge_graph["nodes"]
                if entity.lower() in n["name"].lower()
            ]
            node_ids = [n["id"] for n in matching_nodes]

            filtered_edges = [
                e
                for e in filtered_edges
                if e["source"] in node_ids or e["target"] in node_ids
            ]

        # Reconstruct triples
        triples = []
        for edge in filtered_edges:
            source_node = next(
                (n for n in knowledge_graph["nodes"] if n["id"] == edge["source"]), None
            )
            target_node = next(
                (n for n in knowledge_graph["nodes"] if n["id"] == edge["target"]), None
            )

            if source_node and target_node:
                triples.append(
                    {
                        "subject": source_node["name"],
                        "predicate": edge["relationship"],
                        "object": target_node["name"],
                        "confidence": edge.get("confidence", 1.0),
                        "context": edge.get("context"),
                        "created_at": edge.get("created_at"),
                    }
                )

        logger.info(
            f"Retrieved {len(triples)} knowledge triples (user_id={user_id}, entity={entity})"
        )

        return {
            "success": True,
            "total_triples": len(triples),
            "triples": triples,
        }

    except Exception as e:
        logger.error(f"Failed to retrieve knowledge: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def status():
    """Service status."""
    return {
        "service": "graphiti",
        "status": "running",
        "total_nodes": len(knowledge_graph["nodes"]),
        "total_edges": len(knowledge_graph["edges"]),
        "total_users": len(knowledge_graph["entities"]),
        "storage": "in-memory (development mode)",
    }


if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=3000, log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
