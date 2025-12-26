import os
import requests
import logging

logger = logging.getLogger(__name__)

def post_to_linkedin(content: str, confirmed: bool = False) -> str:
    """
    Posts content to LinkedIn via a Make.com webhook.
    
    Args:
        content (str): The text content of the LinkedIn post.
        confirmed (bool): Whether the user has explicitly confirmed the post.
        
    Returns:
        str: Result of the operation.
    """
    if not confirmed:
        return f"Please confirm you want to post the following to LinkedIn:\n\n'{content}'\n\nReply with 'yes' to proceed."
    
    webhook_url = os.getenv("MAKE_LINKEDIN_WEBHOOK")
    if not webhook_url:
        return "Error: MAKE_LINKEDIN_WEBHOOK environment variable is not set."
        
    try:
        # The user specified the content should be in "executionId"
        payload = {"executionId": content}
        
        response = requests.post(webhook_url, json=payload)
        
        if response.status_code == 200:
            return "Successfully sent post to LinkedIn via Make.com."
        else:
            return f"Failed to send post. Status code: {response.status_code}. Response: {response.text}"
            
    except Exception as e:
        logger.error(f"Error posting to LinkedIn: {str(e)}")
        return f"An error occurred while posting to LinkedIn: {str(e)}"
