#!/usr/bin/env python3
import docker
client = docker.from_env()
container = client.containers.get('demestihas-yanay')

# Read yanay.py from container
exec_result = container.exec_run('cat /app/yanay.py')
content = exec_result.output.decode('utf-8')

# Check current status
print('Checking current status...')
has_evaluate = 'def evaluate_response_mode' in content
has_opus = 'def opus_conversation' in content
has_call = 'self.evaluate_response_mode(message_text)' in content

print(f'evaluate_response_mode defined: {has_evaluate}')
print(f'opus_conversation defined: {has_opus}')
print(f'Called in handle_message: {has_call}')

if has_evaluate and has_opus and not has_call:
    print('Methods exist but not called. Fixing...')
    
    # Find line with classify_intent and insert before it
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'intent = await self.classify_intent(message_text)' in line:
            print(f'Found classify_intent at line {i}')
            # Insert enhancement before this
            indent = '        '
            new_lines = [
                f'{indent}# Try enhancement first',
                f'{indent}try:',
                f'{indent}    mode = self.evaluate_response_mode(message_text)',
                f'{indent}    logger.info(f"Response mode: {{mode}}")',
                f'{indent}    if mode == "conversational":',
                f'{indent}        response = await self.opus_conversation(message_text, user_id)',
                f'{indent}        await self.send_message(chat_id, response)',
                f'{indent}        return',
                f'{indent}except Exception as e:',
                f'{indent}    logger.error(f"Enhancement error: {{e}}")',
                f'{indent}',
            ]
            lines[i:i] = new_lines
            break
    
    # Write back to container
    new_content = '\n'.join(lines)
    container.exec_run(f"echo '{new_content}' > /app/yanay.py")
    print('Fixed! Restarting container...')
    container.restart()
else:
    print('Status does not match expected state for patching')
