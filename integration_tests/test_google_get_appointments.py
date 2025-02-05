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

def test_get_appointments():
    """Integration test for getting all appointments for a phone number"""
    
    # Get tomorrow's date during business hours
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    timestamp = tomorrow.replace(
        hour=DEFAULT_START_HOUR + 1,  # 1 hour after opening
        minute=0,
        second=0,
        microsecond=0
    ).strftime('%Y-%m-%dT%H:%M:%S')
    
    phone_number = "+1234567890"
    
    logger.info("\n=== Testing Get Appointments ===")
    logger.info(f"Setting up test appointment at: {timestamp}")
    
    try:
        # First create a test appointment
        book_event = {
            'operation': 'book_appointment',
            'platform': 'google',
            'name': "Get Appointments Test",
            'timestamp': timestamp,
            'phone_number': phone_number,
            'duration': 30
        }
        
        book_result = lambda_handler(book_event, None)
        logger.info(f"Booking response: {book_result}")
        
        # Verify booking success
        assert book_result['statusCode'] == 200, "Booking request failed"
        book_body = json.loads(book_result['body']) if isinstance(book_result['body'], str) else book_result['body']
        assert book_body['success'] == True, f"Booking failed: {book_body.get('message', 'No error message')}"
        
        # Get all appointments
        get_event = {
            'operation': 'get_appointments',
            'platform': 'google',
            'phone_number': phone_number
        }
        
        result = lambda_handler(get_event, None)
        logger.info(f"Get appointments response: {result}")
        
        # Verify response
        assert result['statusCode'] == 200, "Request failed"
        body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
        assert body['success'] == True, f"Getting appointments failed: {body.get('message', 'No error message')}"
        assert 'appointments' in body, "No appointments field in response"
        
        # Verify we can find our test appointment
        appointments = body['appointments']
        assert len(appointments) > 0, "No appointments found"
        
        found_appointment = False
        for appt in appointments:
            if appt['start'].startswith(timestamp):
                found_appointment = True
                assert appt['name'] == "Get Appointments Test", "Wrong appointment name"
                break
        
        assert found_appointment, f"Could not find test appointment scheduled for {timestamp}"
        
        logger.info("=== Get Appointments Test Passed ===\n")
        
    finally:
        # Clean up: Cancel the test appointment
        logger.info("Cleaning up test appointment...")
        cancel_event = {
            'operation': 'cancel_appointment',
            'platform': 'google',
            'timestamp': timestamp,
            'phone_number': phone_number
        }
        
        try:
            cancel_result = lambda_handler(cancel_event, None)
            cancel_body = json.loads(cancel_result['body']) if isinstance(cancel_result['body'], str) else cancel_result['body']
            if cancel_body.get('success'):
                logger.info("Successfully cleaned up test appointment")
            else:
                logger.warning(f"Test appointment cleanup failed: {cancel_body.get('message')}")
        except Exception as e:
            logger.warning(f"Failed to clean up test appointment: {str(e)}")

if __name__ == '__main__':
    test_get_appointments() 