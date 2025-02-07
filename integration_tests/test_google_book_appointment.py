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

def test_book_appointment_integration(caplog):
    """Integration test for booking an appointment through the Lambda handler"""
    caplog.set_level(logging.INFO)
    
    # Get tomorrow's date during business hours
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    appointment_time = tomorrow.replace(
        hour=DEFAULT_START_HOUR + 1,  # 1 hour after opening
        minute=0,
        second=0,
        microsecond=0
    )
    timestamp = appointment_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    logger.info(f"Testing timestamp: {timestamp}")
    
    # First check availability
    availability_event = {
        'get_availability': 'get_slots',
        'google': '',
        'duration': 30,
        'date': tomorrow.strftime('%Y-%m-%d')
    }
    
    availability_response = lambda_handler(availability_event, None)
    logger.info(f"Raw availability response: {availability_response}")
    
    if availability_response['statusCode'] != 200:
        pytest.fail(f"Availability check failed: {availability_response['body']}")
        
    availability = json.loads(availability_response['body'])
    logger.info(f"Parsed availability response: {availability}")
    assert availability['success'] == True, f"Failed to get availability: {availability.get('message', 'No error message')}"
    
    # Book the appointment
    booking_event = {
        'book_appointment': 'create',
        'google': '',
        'name': "Integration Test Appointment",
        'timestamp': timestamp,
        'phone_number': "+1234567890",
        'duration': 30
    }
    
    booking_response = lambda_handler(booking_event, None)
    logger.info(f"Raw booking response: {booking_response}")
    
    if booking_response['statusCode'] != 200:
        pytest.fail(f"Booking failed with error: {booking_response['body']}")
        
    result = json.loads(booking_response['body'])
    logger.info(f"Parsed booking response: {result}")
    
    # Verify booking success
    assert result['success'] == True, f"Booking failed: {result.get('message', 'No error message')}"
    
    # Clean up
    try:
        cancel_event = {
            'cancel_appointment': 'delete',
            'google': '',
            'timestamp': timestamp,
            'phone_number': "+1234567890"
        }
        
        cancel_response = lambda_handler(cancel_event, None)
        logger.info(f"Cleanup response: {cancel_response}")
    except Exception as e:
        logger.error(f"Failed to clean up test appointment: {str(e)}")
    logger.info("=== End Debug Info ===\n")

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
        'book_appointment': 'create',
        'google': '',
        'name': "Integration Test Appointment 1",
        'timestamp': timestamp,
        'phone_number': "+1234567890",
        'duration': 30
    }
    
    booking_response1 = lambda_handler(booking_event1, None)
    logger.info(f"First booking raw response: {booking_response1}")
    
    if booking_response1['statusCode'] != 200:
        pytest.fail(f"First booking failed with error: {booking_response1['body']}")
        
    result1 = json.loads(booking_response1['body'])
    logger.info(f"First booking parsed response: {result1}")
    print(f"First booking response: {result1}")
    assert isinstance(result1, dict), f"Expected dictionary response, got {type(result1)}"
    assert result1['success'] == True, f"Failed to book first appointment: {result1.get('message', 'No error message')}"
    
    # Try to book second appointment at same time
    booking_event2 = {
        'book_appointment': 'create',
        'google': '',
        'name': "Integration Test Appointment 2",
        'timestamp': timestamp,
        'phone_number': "+0987654321",
        'duration': 30
    }
    
    booking_response2 = lambda_handler(booking_event2, None)
    logger.info(f"Second booking raw response: {booking_response2}")
    result2 = json.loads(booking_response2['body'])
    logger.info(f"Second booking parsed response: {result2}")
    
    # Verify conflict handling
    assert result2['success'] == False, "Second booking should have failed"
    assert 'available_slots' in result2, "No available_slots in conflict response"
    assert 'date' in result2, "No date in conflict response"
    
    # Clean up
    try:
        cancel_event = {
            'cancel_appointment': 'delete',
            'google': '',
            'timestamp': timestamp,
            'phone_number': "+1234567890"
        }
        
        cancel_response = lambda_handler(cancel_event, None)
        logger.info(f"Cleanup response: {cancel_response}")
    except Exception as e:
        logger.error(f"Failed to clean up test appointment: {str(e)}")
    logger.info("=== End Debug Info ===\n") 