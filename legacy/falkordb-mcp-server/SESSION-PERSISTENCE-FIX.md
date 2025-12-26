# Session Persistence Fix - November 14, 2025

## Problem Summary

The FalkorDB MCP server was experiencing session persistence failures where all POST requests to established sessions returned `{"error":"Session not found"}` even though the SSE connection successfully created a session.

## Root Cause

**Primary Issue:** The `handlePostMessage()` call in `src/index-sse.ts:154` was not passing the pre-parsed request body as the third parameter.

When Express's `app.use(express.json())` middleware processes a request, it consumes the request stream and stores the parsed body in `req.body`. The MCP SDK's `SSEServerTransport.handlePostMessage()` method expects either:
1. An unparsed request (it will read the stream), OR
2. The parsed body as the third parameter

Without the third parameter, `handlePostMessage()` tried to read from an already-consumed stream, causing the error:
```
InternalServerError: stream is not readable
```

This error occurred in the `raw-body` package when `getRawBody()` attempted to read from a stream that had already been consumed by the Express JSON middleware.

## The Fix

**File:** `/root/falkordb-mcp-server/src/index-sse.ts`

**Line 154 - Before:**
```typescript
await transport.handlePostMessage(req, res);
```

**Line 154 - After:**
```typescript
// Pass req.body as third parameter since express.json() already parsed it
await transport.handlePostMessage(req, res, req.body);
```

**Additional improvement (lines 156-161):**
```typescript
} catch (error) {
    console.error("Error handling message:", error);
    // Only send error response if headers not already sent
    if (!res.headersSent) {
        res.status(500).json({ error: "Internal server error" });
    }
}
```

## How SSE Sessions Work

Understanding the MCP SSE protocol is crucial:

1. **Client opens SSE connection** → GET `/sse`
2. **Server creates session** → Returns `event: endpoint\ndata: /message?sessionId=XXX`
3. **Client KEEPS SSE connection OPEN** (critical!)
4. **Client sends POST requests** → POST `/message?sessionId=XXX`
5. **Server responds via SSE stream** (not via POST response)
6. **If SSE closes** → Session is deleted from Map → "Session not found"

### Why curl Tests Failed Initially

The curl command pattern failed because:
```bash
curl -N -H "Accept: text/event-stream" https://claude.beltlineconsulting.co/sse --max-time 2
# ↑ This closes the SSE connection after 2 seconds!

curl -X POST "https://claude.beltlineconsulting.co/message?sessionId=XXX" ...
# ↑ By this time, session is already deleted!
```

**This is correct behavior** - the SSE connection MUST remain open. curl is not suitable for testing SSE sessions because it closes the connection.

## Testing the Fix

### Proper Test Client

Use the provided Node.js test client that keeps the SSE connection open:

```bash
node /root/test-sse-client.js https://claude.beltlineconsulting.co
```

Expected output:
```
✓ SSE connection opened (status: 200)
✓ Session ID: <uuid>
✓ Request accepted - response will arrive via SSE
✅ All tests passed!
```

### Comprehensive Memory Test

Test full memory operations:

```bash
node /root/test-memory-operations.js https://claude.beltlineconsulting.co
```

This tests:
- ✅ Session persistence across multiple requests
- ✅ Tools list retrieval
- ✅ Save memory operation
- ✅ Search memories operation
- ✅ Get all memories operation

## Server Management

### Systemd Service

The server now runs as a systemd service for automatic startup on boot:

```bash
# Service commands
sudo systemctl status falkordb-mcp-server
sudo systemctl start falkordb-mcp-server
sudo systemctl stop falkordb-mcp-server
sudo systemctl restart falkordb-mcp-server

# View logs
sudo journalctl -u falkordb-mcp-server -f
tail -f /var/log/falkordb-mcp-server.log
```

### Service Configuration

**Location:** `/etc/systemd/system/falkordb-mcp-server.service`

**Auto-start:** Enabled (starts on boot)

**Restart policy:** Automatic restart on failure (10 second delay)

**Logs:** `/var/log/falkordb-mcp-server.log`

## Verification

### Health Check
```bash
curl https://claude.beltlineconsulting.co/health
```

Expected: `{"status":"ok","server":"falkordb-mcp-server","version":"1.0.0"}`

### Session Persistence Check
```bash
# Check server logs show sessions persisting
tail -20 /var/log/falkordb-mcp-server.log
```

Look for:
```
✓ Server connected to SSE transport (session: XXX)
Received message for session: XXX     ← Session found!
```

NOT:
```
✓ Server connected to SSE transport (session: XXX)
SSE connection closed for session: XXX
No transport found for session: XXX   ← Would indicate problem
```

## Architecture Notes

### Current Setup

- **Process:** Managed by systemd
- **Runtime:** Node.js via tsx (TypeScript executor)
- **Port:** 8050 (internal)
- **Proxy:** Caddy at port 443 (HTTPS)
- **Domain:** https://claude.beltlineconsulting.co
- **Database:** FalkorDB on localhost:6379 (Docker container)

### Session Storage

Sessions are stored in-memory in a JavaScript Map:
```typescript
const transports = new Map();
```

**Key point:** Sessions are ephemeral and tied to the SSE connection lifecycle. When the SSE connection closes, the session is deleted. This is by design in the MCP SSE protocol.

## Related Issues Found (Not Fixed)

During testing, a separate validation error was discovered:
```
keyValidator._parse is not a function
```

This error occurs in the tool handlers and is unrelated to session persistence. It appears to be a Zod validation schema issue in the tool input schemas. This should be addressed separately.

## Success Criteria Met

✅ Sessions persist across multiple POST requests  
✅ No more "Session not found" errors  
✅ Server responds with 202 Accepted for valid requests  
✅ Server auto-starts on boot via systemd  
✅ Health endpoint works  
✅ All three MCP tools are registered  

## Future Recommendations

1. **Session Persistence:** Consider implementing persistent session storage (Redis/FalkorDB) if sessions need to survive server restarts

2. **PM2 Alternative:** Could use PM2 instead of systemd for process management if you need more advanced features (clustering, monitoring dashboard)

3. **Tool Schema Fix:** Address the `keyValidator._parse` error in tool input schemas

4. **Monitoring:** Set up monitoring/alerting for service health

5. **Rate Limiting:** Consider adding rate limiting for the SSE endpoint

## Testing for Claude Desktop Integration

When integrating with Claude Desktop, ensure your MCP client:

1. **Keeps SSE connection open** during the entire conversation
2. **Handles 202 Accepted** responses (actual response comes via SSE)
3. **Listens for `event: message`** on the SSE stream for responses
4. **Implements reconnection logic** if SSE connection drops
5. **Uses proper HTTP headers** (Content-Type, Accept)

## Contact

For issues or questions about this fix, refer to:
- Server code: `/root/falkordb-mcp-server/`
- Test clients: `/root/test-sse-client.js`, `/root/test-memory-operations.js`
- Service config: `/etc/systemd/system/falkordb-mcp-server.service`
- Server logs: `/var/log/falkordb-mcp-server.log`

---

**Fix Applied:** November 14, 2025  
**Status:** ✅ RESOLVED  
**Verified:** Session persistence working correctly
