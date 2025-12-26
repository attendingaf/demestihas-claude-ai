from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import asyncio
import json
import redis
from datetime import datetime
import logging
from typing import Dict, Any
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Email Webhook Service", version="1.0.0")

# Redis connection
redis_client = redis.Redis(
    host="lyco-redis",  # Use container name in docker network
    port=6379,
    decode_responses=True,
    socket_connect_timeout=5,
    socket_timeout=5
)

@app.on_event("startup")
async def startup_event():
    """Test Redis connection on startup"""
    try:
        redis_client.ping()
        logger.info("✅ Redis connection established")
    except Exception as e:
        logger.error(f"❌ Redis connection failed: {e}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        redis_client.ping()
        return {"status": "healthy", "service": "email-webhook", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.post("/email/webhook")
async def handle_email_webhook(request: Request):
    """Handle incoming email webhook from SendGrid"""
    try:
        # Get webhook data
        if request.headers.get("content-type", "").startswith("application/json"):
            email_data = await request.json()
        else:
            # SendGrid sends form data
            form_data = await request.form()
            email_data = dict(form_data)
        
        sender = email_data.get('from', 'unknown')
        logger.info(f"📧 Email webhook received from: {sender}")
        
        # Extract key email components
        processed_email = {
            'sender': email_data.get('from', ''),
            'subject': email_data.get('subject', ''),
            'body': email_data.get('text', email_data.get('html', '')),
            'to': email_data.get('to', ''),
            'timestamp': datetime.now().isoformat(),
            'attachments': email_data.get('attachments', 0),
            'raw_data': json.dumps(email_data)  # Preserve full context
        }
        
        # Validate required fields
        if not processed_email['sender'] or not processed_email['subject']:
            logger.warning(f"⚠️ Incomplete email data: {processed_email}")
            return {"status": "warning", "message": "Incomplete email data"}
        
        # Queue for processing
        queue_key = "email_queue"
        redis_client.lpush(queue_key, json.dumps(processed_email))
        logger.info(f"📥 Email queued for processing: {processed_email['subject'][:50]}")
        
        # Trigger email processing (async)
        asyncio.create_task(process_email_queue())
        
        return {"status": "queued", "message": "Email queued for processing"}
        
    except Exception as e:
        logger.error(f"❌ Webhook processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook processing failed: {str(e)}")

async def process_email_queue():
    """Process queued emails (background task)"""
    try:
        queue_key = "email_queue"
        email_raw = redis_client.rpop(queue_key)
        
        if not email_raw:
            return
        
        email_data = json.loads(email_raw)
        logger.info(f"🔄 Processing email: {email_data['subject'][:50]}")
        
        # Import email parser
        from email_parser import parse_email_to_tasks
        
        # Parse email into tasks
        tasks = await parse_email_to_tasks(email_data)
        
        if not tasks:
            logger.warning(f"⚠️ No tasks extracted from email: {email_data['subject']}")
            return
        
        # Import Lyco integration
        from lyco_api import create_task
        
        # Create tasks in Notion via Lyco
        for task in tasks:
            try:
                # Add email context to task
                task['email_context'] = {
                    'sender': email_data['sender'],
                    'subject': email_data['subject'], 
                    'timestamp': email_data['timestamp']
                }
                
                # Create task via existing Lyco agent
                result = await create_task(task)
                logger.info(f"✅ Task created: {task['title'][:30]}")
                
            except Exception as e:
                logger.error(f"❌ Task creation failed: {e}")
        
        logger.info(f"📧 Email processing complete: {len(tasks)} tasks created")
        
    except Exception as e:
        logger.error(f"❌ Email processing error: {e}")

@app.get("/queue/status")
async def queue_status():
    """Check email processing queue status"""
    try:
        queue_length = redis_client.llen("email_queue")
        return {
            "queue_length": queue_length,
            "status": "active" if queue_length > 0 else "idle"
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8090))
    uvicorn.run(app, host="0.0.0.0", port=port)
