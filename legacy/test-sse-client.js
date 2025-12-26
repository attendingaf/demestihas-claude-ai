#!/usr/bin/env node

/**
 * Proper SSE client test - keeps connection open while making requests
 */

const http = require("http");
const https = require("https");

async function testSSESession(baseUrl, useHttps = false) {
    const protocol = useHttps ? https : http;
    const urlObj = new URL(baseUrl);

    console.log(`\n🔗 Testing SSE session with ${baseUrl}\n`);

    return new Promise((resolve, reject) => {
        // Step 1: Open SSE connection
        const sseReq = protocol.get(
            `${baseUrl}/sse`,
            {
                headers: {
                    Accept: "text/event-stream",
                    Connection: "keep-alive",
                },
            },
            (sseRes) => {
                console.log(
                    `✓ SSE connection opened (status: ${sseRes.statusCode})`,
                );

                let sessionId = null;
                let buffer = "";

                sseRes.on("data", (chunk) => {
                    buffer += chunk.toString();

                    // Parse SSE messages
                    const lines = buffer.split("\n");
                    buffer = lines.pop(); // Keep incomplete line

                    for (const line of lines) {
                        if (line.startsWith("data: ")) {
                            const data = line.substring(6);
                            console.log(`📨 Received: ${data}`);

                            // Extract sessionId
                            const match = data.match(/sessionId=([a-f0-9-]+)/);
                            if (match) {
                                sessionId = match[1];
                                console.log(`✓ Session ID: ${sessionId}\n`);

                                // Step 2: Make POST request WHILE keeping SSE open
                                setTimeout(() => {
                                    testPostRequest(
                                        baseUrl,
                                        sessionId,
                                        useHttps,
                                    )
                                        .then(() => {
                                            console.log(
                                                "\n✅ Test completed successfully!",
                                            );
                                            sseReq.destroy(); // Close SSE now
                                            resolve();
                                        })
                                        .catch((err) => {
                                            console.error(
                                                "\n❌ POST request failed:",
                                                err.message,
                                            );
                                            sseReq.destroy();
                                            reject(err);
                                        });
                                }, 100);
                            }
                        }
                    }
                });

                sseRes.on("error", (err) => {
                    console.error("❌ SSE error:", err.message);
                    reject(err);
                });
            },
        );

        sseReq.on("error", (err) => {
            console.error("❌ SSE request error:", err.message);
            reject(err);
        });

        // Timeout if no session received
        setTimeout(() => {
            if (!sessionId) {
                console.error("❌ Timeout: No session ID received");
                sseReq.destroy();
                reject(new Error("Timeout waiting for session ID"));
            }
        }, 5000);
    });
}

async function testPostRequest(baseUrl, sessionId, useHttps = false) {
    const protocol = useHttps ? https : http;
    const urlObj = new URL(baseUrl);

    const postData = JSON.stringify({
        jsonrpc: "2.0",
        id: 1,
        method: "tools/list",
    });

    return new Promise((resolve, reject) => {
        const options = {
            hostname: urlObj.hostname,
            port: urlObj.port || (useHttps ? 443 : 80),
            path: `/message?sessionId=${sessionId}`,
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(postData),
            },
        };

        console.log(`📤 POST to /message?sessionId=${sessionId}`);

        const req = protocol.request(options, (res) => {
            let data = "";

            res.on("data", (chunk) => {
                data += chunk.toString();
            });

            res.on("end", () => {
                console.log(`📥 Response (${res.statusCode}): ${data}`);

                // 202 Accepted is the correct response for SSE transport
                // The actual response comes back over the SSE stream
                if (res.statusCode === 200 || res.statusCode === 202) {
                    console.log(
                        "✓ Request accepted - response will arrive via SSE",
                    );
                    resolve({ statusCode: res.statusCode, data });
                } else if (res.statusCode === 404) {
                    reject(new Error(`Session not found (${data})`));
                } else {
                    reject(new Error(`HTTP ${res.statusCode}: ${data}`));
                }
            });
        });

        req.on("error", (err) => {
            reject(err);
        });

        req.write(postData);
        req.end();
    });
}

// Main execution
const args = process.argv.slice(2);
const testUrl = args[0] || "http://localhost:8050";
const useHttps = testUrl.startsWith("https://");

testSSESession(testUrl, useHttps)
    .then(() => {
        console.log("\n✅ All tests passed!");
        process.exit(0);
    })
    .catch((err) => {
        console.error("\n❌ Test failed:", err.message);
        process.exit(1);
    });
