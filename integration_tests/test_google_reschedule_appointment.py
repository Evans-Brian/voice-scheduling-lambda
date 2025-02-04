import sys
import os
# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
import logging
from platforms.google_calendar import GoogleCalendarPlatform
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
    """Integration test for rescheduling an appointment"""
    platform = GoogleCalendarPlatform()
    
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
    result = platform.book_appointment(
        name="Integration Test Appointment",
        timestamp=original_timestamp,
        phone_number="+1234567890",
        duration=30
    )
    logger.info(f"Initial booking response: {result}")
    
    # Verify initial booking success
    assert result['success'] == True, f"Initial booking failed: {result.get('message', 'No error message')}"
    
    try:
        # Now reschedule the appointment
        reschedule_result = platform.reschedule_appointment(
            name="Integration Test Appointment",
            phone_number="+1234567890",
            old_timestamp=original_timestamp,
            new_timestamp=new_timestamp
        )
        logger.info(f"Reschedule response: {reschedule_result}")
        
        # Verify rescheduling success
        assert reschedule_result['success'] == True, f"Rescheduling failed: {reschedule_result.get('message', 'No error message')}"
        
        # Verify the original appointment was cancelled
        original_appointment = platform.get_customer_appointments("+1234567890")
        logger.info(f"Final appointments: {original_appointment}")
        
        # Should only find one appointment at the new time
        assert original_appointment['success'] == True, "Failed to get appointments"
        assert len(original_appointment['appointments']) == 1, "Wrong number of appointments found"
        assert original_appointment['appointments'][0]['start'].startswith(new_timestamp), \
            f"Appointment not rescheduled correctly. Expected {new_timestamp}, got {original_appointment['appointments'][0]['start']}"
        
    finally:
        # Clean up: Cancel the appointment (try both times just in case)
        try:
            platform.cancel_appointment(timestamp=original_timestamp, phone_number="+1234567890")
        except Exception as e:
            logger.warning(f"Failed to clean up original appointment: {str(e)}")
            
        try:
            platform.cancel_appointment(timestamp=new_timestamp, phone_number="+1234567890")
        except Exception as e:
            logger.warning(f"Failed to clean up rescheduled appointment: {str(e)}")
            
    logger.info("=== End Debug Info ===\n")

if __name__ == '__main__':
    test_reschedule_appointment_integration() 