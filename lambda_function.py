from typing import Any, Dict
import json
from handlers import HANDLERS, PLATFORMS
import shutil
import os

def lambda_handler(event, context):
    """Handle both direct Lambda invocations and API Gateway events"""
    try:
        print("Received event:", event)
        # Copy token to /tmp if it exists in the package
        if os.path.exists('token.pickle') and not os.path.exists('/tmp/token.pickle'):
            shutil.copy2('token.pickle', '/tmp/token.pickle')
        if os.path.exists('credentials.json') and not os.path.exists('/tmp/credentials.json'):
            shutil.copy2('credentials.json', '/tmp/credentials.json')
        
        # Check if this is an API Gateway event
        if 'body' in event:
            body = json.loads(event['body'])
            print("Parsed body:", body)
            event = body['args']
            print("Parsed appointment request:", event)
            print(event.keys())

        # Find platform and handler
        platform = None
        handler = None
        
        # First check for platform
        for key in event.keys():
            if key.lower() in PLATFORMS:
                platform = key
                break
                
        if not platform:
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
                break
        
        if not operation:
            return {
                'statusCode': 400,
                'body': json.dumps('Operation is required')
            }
        
        if not handler:
            return {
                'statusCode': 400,
                'body': json.dumps(f'Unknown operation: {operation}')
            }

        # Execute the handler and return result directly
        return handler(event, platform)
        
    except ValueError as e:
        return {
            'statusCode': 400,
            'body': json.dumps(str(e))
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }

