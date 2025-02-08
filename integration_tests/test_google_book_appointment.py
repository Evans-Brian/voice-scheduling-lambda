import sys
import os
import pytest
import logging
# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from lambda_function import lambda_handler
from constants import DEFAULT_START_HOUR
import json

# Set up logging
logger = logging.getLogger(__name__)


def test_book_appointment_conflict_integration(caplog):
    """Integration test for booking conflicting appointments through the Lambda handler"""
    caplog.set_level(logging.INFO)
    
    # Get tomorrow's date during business hours
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    appointment_time = tomorrow.replace(
        hour=DEFAULT_START_HOUR + 2,  # 2 hours after open
        minute=0,
        second=0,
        microsecond=0
    )
    timestamp = appointment_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    logger.info(f"Testing timestamp: {timestamp}")
    
    # Book first appointment
    booking_event1 = {
        'body': json.dumps({
            'args': {
                'book_appointment': 'create',
                'google': '',
                'name': 'Integration Test Appointment',
                'timestamp': timestamp,
                'phone_number': '+1234567890',
                'duration': 30
            }
        })
    }
    
    booking_response1 = lambda_handler(booking_event1, None)
    logger.info(f"First booking raw response: {booking_response1}")
    
    if booking_response1['statusCode'] != 200:
        pytest.fail(f"First booking failed with error: {booking_response1['body']}")
        
    result1 = booking_response1['body']
    logger.info(f"First booking parsed response: {result1}")
    assert isinstance(result1, dict), f"Expected dictionary response, got {type(result1)}"
    assert result1['success'] == True, f"Failed to book first appointment: {result1.get('message', 'No error message')}"
    assert result1['message'] == 'Appointment booked successfully', f"Expected message to be 'Appointment booked successfully', got {result1['message']}"
    

    # Try to book second appointment at same time
    booking_event2 = {
        'body': json.dumps({
            'args': {
                'book_appointment': 'create',
                'google': '',
                'name': 'Integration Test Appointment 2',
                'timestamp': timestamp,
                'phone_number': '+0987654321',
                'duration': 30
            }
        })
    }
    
    booking_response2 = lambda_handler(booking_event2, None)
    logger.info(f"Second booking raw response: {booking_response2}")
    result2 = booking_response2['body']
    logger.info(f"Second booking parsed response: {result2}")
    
    # Verify conflict handling
    assert result2['success'] == False, "Second booking should have failed"
    assert 'available_slots' in result2, "No available_slots in conflict response"
    
    # Clean up
    try:
        cancel_event = {
            'cancel_appointment': '',
            'google': '',
            'timestamp': timestamp,
            'phone_number': "+1234567890"
        }
        
        cancel_response = lambda_handler(cancel_event, None)
        logger.info(f"Cleanup response: {cancel_response}")
    except Exception as e:
        logger.error(f"Failed to clean up test appointment: {str(e)}")
    logger.info("=== End Debug Info ===\n") 