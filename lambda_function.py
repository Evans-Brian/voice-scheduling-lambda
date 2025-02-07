from typing import Any, Dict
import json
from handlers import HANDLERS

def lambda_handler(event, context):
    """Handle both direct Lambda invocations and API Gateway events"""
    try:
        # Check if this is an API Gateway event
        if event.get('httpMethod'):
            # Parse the body from API Gateway
            body = json.loads(event.get('body', '{}'))
            # Use body as the event
            event = body
        
        # Find the operation from the keys in the event
        operation = None
        for key in HANDLERS.keys():
            if key in event:
                operation = key
                break
        
        if not operation:
            return {
                'statusCode': 400,
                'body': json.dumps('Operation is required')
            }
        
        # Find platform from keys
        platform = None
        for key in event.keys():
            if key in ['google']:  # Add other platforms as needed
                platform = key
                break
        
        if not platform:
            return {
                'statusCode': 400,
                'body': json.dumps('Platform is required')
            }
        
        # Get the appropriate handler
        handler = HANDLERS.get(operation)
        if not handler:
            return {
                'statusCode': 400,
                'body': json.dumps(f'Unknown operation: {operation}')
            }
        
        # Execute the handler
        result = handler(event, platform)
        
        # Ensure the response body is JSON serialized
        if isinstance(result.get('body'), (dict, list)):
            result['body'] = json.dumps(result['body'])
        elif not isinstance(result.get('body'), str):
            result['body'] = json.dumps(str(result.get('body')))
            
        return result
        
    except ValueError as e:
        return {
            'statusCode': 400,
            'body': json.dumps(str(e))
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f'Error: {str(e)}')
        }