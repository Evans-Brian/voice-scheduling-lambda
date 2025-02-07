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

def test_reschedule_appointment_integration():
    """Integration test for rescheduling an appointment through the Lambda handler"""
    
    # Get tomorrow's date during business hours
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    day_after_tomorrow = tomorrow + timedelta(days=1)  # Next day for rescheduling
    
    original_time = tomorrow.replace(
        hour=DEFAULT_START_HOUR + 1,  # 1 hour after opening
        minute=0,
        second=0,
        microsecond=0
    )
    new_time = day_after_tomorrow.replace(
        hour=DEFAULT_START_HOUR + 1,  # Same time, next day
        minute=0,
        second=0,
        microsecond=0
    )
    
    original_timestamp = original_time.strftime('%Y-%m-%dT%H:%M:%S')
    new_timestamp = new_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    logger.info("\n=== Debug Info ===")
    logger.info(f"Original timestamp: {original_timestamp}")
    logger.info(f"New timestamp: {new_timestamp}")
    
    # First book the appointment
    book_event = {
        'book_appointment': 'create',
        'google': '',  # Changed from platform
        'name': "Integration Test Appointment",
        'timestamp': original_timestamp,
        'phone_number': "+1234567890",
        'duration': 30
    }
    
    result = lambda_handler(book_event, None)
    logger.info(f"Initial booking response: {result}")
    
    # Verify initial booking success
    assert result['statusCode'] == 200, "Initial booking request failed"
    booking_body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
    assert booking_body['success'] == True, f"Initial booking failed: {booking_body.get('message', 'No error message')}"
    
    try:
        # Now reschedule the appointment using the handler
        reschedule_event = {
            'reschedule_appointment': 'update',
            'google': '',  # Changed from platform
            'name': "Integration Test Appointment",
            'phone_number': "+1234567890",
            'old_timestamp': original_timestamp,
            'new_timestamp': new_timestamp
        }
        
        reschedule_result = lambda_handler(reschedule_event, None)
        logger.info(f"Reschedule response: {reschedule_result}")
        
        # Verify rescheduling success
        assert reschedule_result['statusCode'] == 200, "Reschedule request failed"
        reschedule_body = json.loads(reschedule_result['body']) if isinstance(reschedule_result['body'], str) else reschedule_result['body']
        assert reschedule_body['success'] == True, f"Rescheduling failed: {reschedule_body.get('message', 'No error message')}"
        
        # Verify the appointment was rescheduled by getting current appointments
        get_appointments_event = {
            'get_appointments': 'list',
            'google': '',  # Changed from platform
            'phone_number': "+1234567890"
        }
        
        appointments_result = lambda_handler(get_appointments_event, None)
        logger.info(f"Final appointments: {appointments_result}")
        
        # Verify the appointments
        assert appointments_result['statusCode'] == 200, "Failed to get appointments"
        appointments_body = json.loads(appointments_result['body']) if isinstance(appointments_result['body'], str) else appointments_result['body']
        assert appointments_body['success'] == True, "Failed to get appointments"
        assert len(appointments_body['appointments']) == 1, "Wrong number of appointments found"
        assert appointments_body['appointments'][0]['start'].startswith(new_timestamp), \
            f"Appointment not rescheduled correctly. Expected {new_timestamp}, got {appointments_body['appointments'][0]['start']}"
        
    finally:
        logger.info("Cleaning up test appointments...")
        # Clean up: Cancel the appointment (try both times just in case)
        cancel_event = {
            'cancel_appointment': 'delete',
            'google': '',  # Changed from platform
            'timestamp': original_timestamp,
            'phone_number': "+1234567890"
        }
        
        # Try to cancel original appointment
        try:
            cancel_result = lambda_handler(cancel_event, None)
            cancel_body = json.loads(cancel_result['body']) if isinstance(cancel_result['body'], str) else cancel_result['body']
            if cancel_body.get('success'):
                logger.info("Successfully cleaned up original appointment")
            else:
                logger.warning(f"Original appointment cleanup failed: {cancel_body.get('message')}")
        except Exception as e:
            logger.warning(f"Failed to clean up original appointment: {str(e)}")
        
        # Try to cancel rescheduled appointment
        cancel_event['timestamp'] = new_timestamp
        try:
            cancel_result = lambda_handler(cancel_event, None)
            cancel_body = json.loads(cancel_result['body']) if isinstance(cancel_result['body'], str) else cancel_result['body']
            if cancel_body.get('success'):
                logger.info("Successfully cleaned up rescheduled appointment")
            else:
                logger.warning(f"Rescheduled appointment cleanup failed: {cancel_body.get('message')}")
        except Exception as e:
            logger.warning(f"Failed to clean up rescheduled appointment: {str(e)}")
    
            
    logger.info("=== End Debug Info ===\n")

if __name__ == '__main__':
    test_reschedule_appointment_integration() 