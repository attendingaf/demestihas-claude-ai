# FalkorDB MCP Server

A Model Context Protocol (MCP) server for FalkorDB with semantic memory search capabilities using OpenAI embeddings.

## Project Status

### ✅ FULLY IMPLEMENTED & TESTED - Production Ready

**All bugs fixed and verified working!** See `BUG-FIXES-APPLIED.md` and `FINAL-STATUS.md` for details.

**Core Infrastructure:**

- ✅ Project initialization with Node.js and TypeScript
- ✅ All dependencies installed
- ✅ Database connection manager with pooling (`src/db/connection.ts`)
- ✅ Server entry point with MCP integration (`src/index.ts`)
- ✅ Environment configuration

**Utilities:**

- ✅ OpenAI embedding generation (`src/embeddings/openai.ts`)
- ✅ Cypher query templates (`src/db/queries.ts`)
- ✅ Memory classifier with keyword detection (`src/utils/memory-classifier.ts`)
- ✅ Zod input validators (`src/utils/validators.ts`)

**MCP Tools:**

- ✅ save-memory tool - Store memories with embeddings (`src/tools/save-memory.ts`)
- ✅ search-memories tool - Semantic search with similarity (`src/tools/search-memories.ts`)
- ✅ get-all-memories tool - Retrieve all user memories (`src/tools/get-all-memories.ts`)

## REST API Endpoints

The server exposes REST endpoints for direct graph interaction. These endpoints require an API key.

### Authentication

All endpoints except `/health` require the `Authorization` header:
`Authorization: Bearer <FALKOR_API_KEY>`

The API key is configured in the `.env` file as `FALKOR_API_KEY`.

### Endpoints

#### 1. Execute Cypher Query

- **URL:** `POST /graph/query`
- **Body:**

  ```json
  {
    "cypher": "MATCH (n) RETURN n LIMIT 10",
    "params": {}
  }
  ```

#### 2. Create Nodes

- **URL:** `POST /graph/nodes`
- **Body:**

  ```json
  {
    "label": "Framework",
    "properties": {
      "name": "Litvak_Smoothing",
      "description": "Method for reducing artificial variability"
    }
  }
  ```

#### 3. Create Relationships

- **URL:** `POST /graph/relationships`
- **Body:**

  ```json
  {
    "from_label": "Framework",
    "from_match": { "name": "Litvak_Smoothing" },
    "to_label": "Metric",
    "to_match": { "name": "LOS" },
    "relationship_type": "REDUCES",
    "properties": { "certainty": "high" }
  }
  ```

#### 4. Search Nodes

- **URL:** `GET /graph/search`
- **Query Params:** `label`, `property`, `value`
- **Example:** `/graph/search?label=Framework&property=name&value=Litvak_Smoothing`

#### 5. Get Node with Relationships

- **URL:** `GET /graph/node/:label/:property/:value/relationships`
- **Example:** `/graph/node/Framework/name/Litvak_Smoothing/relationships`

#### 6. Bulk Import

- **URL:** `POST /graph/bulk`
- **Body:**

  ```json
  {
    "nodes": [
      { "label": "Person", "properties": { "name": "Alice" } },
      { "label": "Person", "properties": { "name": "Bob" } }
    ],
    "relationships": [
      {
        "from": { "label": "Person", "match": { "name": "Alice" } },
        "to": { "label": "Person", "match": { "name": "Bob" } },
        "type": "KNOWS",
        "properties": { "since": "2023" }
      }
    ]
  }
  ```

## Prerequisites

- Node.js 20.x or later
- FalkorDB instance running (default: localhost:6379)
- OpenAI API key

## Installation

```bash
npm install
```

## Configuration

Edit the `.env` file with your configuration:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# FalkorDB Configuration
FALKORDB_HOST=localhost
FALKORDB_PORT=6379
FALKORDB_USERNAME=
FALKORDB_PASSWORD=
FALKORDB_GRAPH_NAME=memory_graph

# Embedding Configuration
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSIONS=1536

# MCP Server Configuration
MCP_SERVER_NAME=falkordb-mcp-server
MCP_SERVER_VERSION=1.0.0
FALKORDB_MAX_CONNECTIONS=10
```

## Development

Run the server in development mode with auto-reload:

```bash
npm run dev:watch
```

Or run once:

```bash
npm run dev
```

## Build

Compile TypeScript to JavaScript:

```bash
npm run build
```

## Production

Run the compiled server:

```bash
npm start
```

## License

ISC
