import sys
import os
# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import logging
import json
from lambda_function import lambda_handler
from constants import DEFAULT_START_HOUR

# Force logging to stdout
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
logger.propagate = False  # Prevent duplicate logs

def test_get_availability():
    """Integration test for getting next available appointment slots"""
    
    # Get tomorrow's date during business hours
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    timestamp = tomorrow.replace(
        hour=DEFAULT_START_HOUR + 1,  # 1 hour after opening
        minute=0,
        second=0,
        microsecond=0
    ).strftime('%Y-%m-%dT%H:%M:%S')
    
    logger.info("\n=== Testing Next Availability ===")
    logger.info(f"Checking availability from: {timestamp}")
    
    # Get next availability
    event = {
        'get_availability': 'next',
        'google': '', 
        'timestamp': timestamp
    }
    
    result = lambda_handler(event, None)
    logger.info(f"Next availability response: {result}")
    
    # Verify response
    assert result['statusCode'] == 200, "Request failed"
    body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
    assert body['success'] == True, f"Getting availability failed: {body.get('message', 'No error message')}"
    assert 'slots' in body, "No slots in response"
    assert 'date' in body, "No date in response"
    assert body['slots'] == 'Available February 08: 9AM to 4:30PM'
    
    
    logger.info("=== Next Availability Test Passed ===\n")

def test_get_availability_specific_date():
    """Integration test for getting availability on a specific date"""
    
    # Get date 2 days from now
    target_date = (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d')
    
    logger.info("\n=== Testing Specific Date Availability ===")
    logger.info(f"Checking availability for date: {target_date}")
    
    # Get availability for specific date
    event = {
        'get_availability': 'date',
        'google': '', 
        'date': target_date
    }
    
    result = lambda_handler(event, None)
    logger.info(f"Specific date availability response: {result}")
    
    # Verify response
    assert result['statusCode'] == 200, "Request failed"
    body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
    assert body['success'] == True, f"Getting availability failed: {body.get('message', 'No error message')}"
    assert 'slots' in body, "No slots in response"
    assert 'date' in body, "No date in response"
    assert body['date'] == target_date, f"Wrong date returned. Expected {target_date}, got {body['date']}"
    
    # Verify slot format if any slots are available
    print('aaaa')
    print(body['slots'])
    assert body['slots'] == 'Available February 09: 9AM to 4:30PM'
    
    logger.info("=== Specific Date Availability Test Passed ===\n")

if __name__ == '__main__':
    test_get_availability()
    test_get_specific_date_availability() 