# LinkedIn MCP Server

This is a Model Context Protocol (MCP) server that exposes LinkedIn posting capabilities via HTTP. It supports OAuth 2.0 authentication and provides tools for posting text, articles, and images.

## Features

- **OAuth 2.0 Authentication**: Securely authenticate with LinkedIn using the `w_member_social` scope.
- **Token Persistence**: Tokens are stored locally in `tokens.json` and persist across restarts.
- **MCP Support**: Implements the MCP protocol over SSE (Server-Sent Events) at `/sse`.
- **REST API**: Exposes tools as standard REST endpoints at `/api/...`.
- **Tools**:
  - `post_text`: Post a simple text update.
  - `post_article`: Share an article with a URL and commentary.
  - `post_image`: Upload and share an image with commentary.

## Setup

1. **Install Dependencies**:

    ```bash
    npm install
    ```

2. **Configuration**:
    Copy `.env.example` to `.env` and fill in your LinkedIn App credentials.

    ```bash
    cp .env.example .env
    ```

    - `LINKEDIN_CLIENT_ID`: Your App Client ID.
    - `LINKEDIN_CLIENT_SECRET`: Your App Client Secret.
    - `LINKEDIN_REDIRECT_URI`: The callback URL (e.g., `http://your-vps-ip:3000/auth/linkedin/callback`).
    - `PORT`: The port to run on (default 3000).

    **Note**: Ensure your LinkedIn App has the `w_member_social`, `profile`, `email`, and `openid` scopes enabled.

3. **Run Locally**:

    ```bash
    node src/index.js
    ```

## Authentication

1. Navigate to `http://your-vps-ip:3000/auth/linkedin` in your browser.
2. Log in to LinkedIn and authorize the app.
3. You will be redirected to the callback URL and see a success message.

## Usage

### MCP (Claude Desktop)

Configure Claude Desktop to connect to the SSE endpoint:

- **URL**: `http://your-vps-ip:3000/sse`

### REST API

You can also use the tools via standard HTTP POST requests.

#### Post Text

```bash
curl -X POST http://localhost:3000/api/post_text \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello LinkedIn! Posting from my MCP server."}'
```

#### Post Article

```bash
curl -X POST http://localhost:3000/api/post_article \
  -H "Content-Type: application/json" \
  -d '{"text": "Check out this cool library!", "url": "https://modelcontextprotocol.io"}'
```

#### Post Image

**Note**: The image must exist on the server at `image_path`.

```bash
curl -X POST http://localhost:3000/api/post_image \
  -H "Content-Type: application/json" \
  -d '{"text": "A nice picture", "image_path": "/path/to/image.jpg"}'
```

## Deployment (Systemd)

To run this server as a background service on Linux:

1. Create a service file: `/etc/systemd/system/linkedin-mcp.service`

    ```ini
    [Unit]
    Description=LinkedIn MCP Server
    After=network.target

    [Service]
    Type=simple
    User=root
    WorkingDirectory=/path/to/linkedin-mcp-server
    ExecStart=/usr/bin/node src/index.js
    Restart=on-failure
    EnvironmentFile=/path/to/linkedin-mcp-server/.env

    [Install]
    WantedBy=multi-user.target
    ```

2. Reload systemd and start the service:

    ```bash
    sudo systemctl daemon-reload
    sudo systemctl enable linkedin-mcp
    sudo systemctl start linkedin-mcp
    ```

3. Check status:

    ```bash
    sudo systemctl status linkedin-mcp
    ```
