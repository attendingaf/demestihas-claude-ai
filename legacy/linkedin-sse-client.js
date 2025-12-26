#!/usr/bin/env node

const readline = require('readline');

const RPC_URL = 'http://178.156.170.161:3001/rpc';

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

function log(msg) {
    console.error(`[LinkedIn MCP] ${msg}`);
}

rl.on('line', async (line) => {
    if (!line.trim()) return;

    try {
        const jsonrpc = JSON.parse(line);
        log(`Received JSONRPC: ${jsonrpc.method}`);

        const response = await fetch(RPC_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(jsonrpc)
        });

        const data = await response.json();
        log(`Sending response for: ${jsonrpc.method}`);
        process.stdout.write(JSON.stringify(data) + '\n');

    } catch (err) {
        log(`Error: ${err.message}`);
        process.stderr.write(`[LinkedIn MCP] Error: ${err.message}\n`);
    }
});

process.on('SIGINT', () => {
    log('Shutting down gracefully...');
    rl.close();
    process.exit(0);
});

log('LinkedIn MCP client started');
