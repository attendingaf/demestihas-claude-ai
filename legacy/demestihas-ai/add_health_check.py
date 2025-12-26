import re

# Read yanay.py
with open('yanay.py', 'r') as f:
    content = f.read()

# Check if health check already exists
if 'aiohttp' in content and '8080' in content:
    print("✅ Health check already exists in yanay.py")
    exit(0)

# Add health check imports after existing imports
if 'from aiohttp import web' not in content:
    # Find the last import line
    imports_pattern = r'(import.*\n|from.*import.*\n)'
    imports = re.findall(imports_pattern, content)
    if imports:
        last_import = imports[-1]
        content = content.replace(last_import, last_import + 'from aiohttp import web\n')
    
# Add health check function before main()
health_function = '''
async def health_check(request):
    """Health check endpoint for Docker"""
    return web.json_response({
        'status': 'healthy',
        'service': 'yanay-bot',
        'timestamp': datetime.now().isoformat()
    })

async def start_health_server():
    """Start health check HTTP server"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("Health check server started on port 8080")

'''

# Insert before if __name__ == '__main__':
if "if __name__ == '__main__':" in content:
    content = content.replace("if __name__ == '__main__':", health_function + "if __name__ == '__main__':")
else:
    # Append at end
    content = content + '\n' + health_function

# Add health server start to main execution
if 'asyncio.run(' in content:
    # Find the asyncio.run line and add health server
    asyncio_pattern = r'asyncio\.run\(([^)]+)\)'
    match = re.search(asyncio_pattern, content)
    if match:
        old_run = match.group(0)
        main_func = match.group(1)
        
        new_main = f"""
async def main_with_health():
    await start_health_server()
    await {main_func}

asyncio.run(main_with_health())"""
        content = content.replace(old_run, new_main.strip())

print("✅ Health check added to yanay.py")

# Write modified content
with open('yanay.py', 'w') as f:
    f.write(content)
