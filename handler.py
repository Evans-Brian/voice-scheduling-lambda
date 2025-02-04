from typing import Any, Dict
import json
from handlers import HANDLERS

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for calendar operations.
    
    Args:
        event: Dict containing:
            - operation: String operation name ('book_appointment', 'get_next_open', 
              'get_appointments', 'cancel_appointment', or 'reschedule_appointment')
            - platform: String platform name (required)
            - Additional operation-specific parameters (see individual handlers for details)
        context: AWS Lambda context
    
    Returns:
        dict: Response with statusCode and body
    """
    try:
        # Check for required operation
        operation = event.get('operation')
        if not operation:
            return {
                'statusCode': 400,
                'body': json.dumps('Operation is required')
            }
        
        # Check for required platform
        platform = event.get('platform')
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