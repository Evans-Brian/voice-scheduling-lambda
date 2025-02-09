from typing import Any, Dict
import json
from handlers import HANDLERS, PLATFORMS
import shutil
import os
import traceback
import logging

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Handle both direct Lambda invocations and API Gateway events"""
    try:
        logger.info("Received event: %s", event)
        
        # Copy token to /tmp if it exists in the package
        if os.path.exists('token.pickle') and not os.path.exists('/tmp/token.pickle'):
            logger.info("Copying token.pickle to /tmp")
            shutil.copy2('token.pickle', '/tmp/token.pickle')
        if os.path.exists('credentials.json') and not os.path.exists('/tmp/credentials.json'):
            logger.info("Copying credentials.json to /tmp")
            shutil.copy2('credentials.json', '/tmp/credentials.json')
        
        # Check if this is an API Gateway event
        if 'body' in event:
            body = json.loads(event['body'])
            logger.info("Parsed API Gateway body: %s", body)
            event = body['args']
            logger.info("Extracted args: %s", event)

        # Find platform and handler
        platform = None
        handler = None
        
        # First check for platform
        for key in event.keys():
            if key.lower() in PLATFORMS:
                platform = key
                logger.info("Found platform: %s", platform)
                break
                
        if not platform:
            logger.error("No platform found in event")
            return {
                'statusCode': 400,
                'body': json.dumps('Platform is required')
            }
            
        event['platform_name'] = platform
        event.pop(platform)
        
        # Then check for operation
        operation = None
        for key in event.keys():
            if key in HANDLERS:
                handler = HANDLERS[key]
                operation = key
                logger.info("Found operation: %s", operation)
                break
        
        if not operation:
            logger.error("No operation found in event")
            return {
                'statusCode': 400,
                'body': json.dumps('Operation is required')
            }
        
        if not handler:
            logger.error("No handler found for operation: %s", operation)
            return {
                'statusCode': 400,
                'body': json.dumps(f'Unknown operation: {operation}')
            }

        # Execute the handler and return result directly
        logger.info("Executing handler for operation: %s", operation)
        result = handler(event, platform)
        logger.info("Handler result: %s", result)
        
        # Ensure body is JSON serialized
        if isinstance(result.get('body'), (dict, list)):
            result['body'] = json.dumps(result['body'])
            
        logger.info("Final formatted result: %s", result)
        return result
        
    except ValueError as e:
        logger.error("ValueError: %s", str(e))
        return {
            'statusCode': 400,
            'body': json.dumps(str(e))
        }
    except Exception as e:
        logger.error("Error details: %s", str(e))
        logger.error("Error type: %s", type(e))
        logger.error("Traceback: %s", traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

