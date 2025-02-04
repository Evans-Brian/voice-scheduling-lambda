import sys
import os
# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from platforms.google_calendar import GoogleCalendarPlatform
from constants import DEFAULT_START_HOUR

def test_book_appointment_integration():
    """Integration test for booking an appointment"""
    platform = GoogleCalendarPlatform()
    
    # Get tomorrow's date during business hours
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    appointment_time = tomorrow.replace(
        hour=DEFAULT_START_HOUR + 1,  # 1 hour after opening
        minute=0,
        second=0,
        microsecond=0
    )
    timestamp = appointment_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    print("\n=== Debug Info ===")
    print(f"Testing timestamp: {timestamp}")
    
    # First check availability
    availability = platform.get_availability(
        duration=30,
        date=tomorrow.strftime('%Y-%m-%d')
    )
    print(f"Availability response: {availability}")
    assert availability['success'] == True, f"Failed to get availability: {availability.get('message', 'No error message')}"
    
    # Book the appointment
    result = platform.book_appointment(
        name="Integration Test Appointment",
        timestamp=timestamp,
        phone_number="+1234567890",
        duration=30
    )
    print(f"Booking response: {result}")
    
    # Verify booking success
    assert result['success'] == True, f"Booking failed: {result.get('message', 'No error message')}"
    
    try:
        # Clean up: Cancel the test appointment
        cancel_result = platform.cancel_appointment(
            timestamp=timestamp,
            phone_number="+1234567890"
        )
        print(f"Cleanup result: {cancel_result}")
    except Exception as e:
        print(f"Warning: Failed to clean up test appointment: {str(e)}")
    print("=== End Debug Info ===\n")

def test_book_appointment_conflict_integration():
    """Integration test for booking conflicting appointments"""
    platform = GoogleCalendarPlatform()
    
    # Get tomorrow's date during business hours
    tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    appointment_time = tomorrow.replace(
        hour=DEFAULT_START_HOUR + 2,  # 2 hours after open
        minute=0,
        second=0,
        microsecond=0
    )
    timestamp = appointment_time.strftime('%Y-%m-%dT%H:%M:%S')
    
    print("\n=== Debug Info ===")
    print(f"Testing timestamp: {timestamp}")
    
    # Book first appointment
    result1 = platform.book_appointment(
        name="Integration Test Appointment 1",
        timestamp=timestamp,
        phone_number="+1234567890",
        duration=30
    )
    print(f"First booking response: {result1}")
    assert result1['success'] == True, f"Failed to book first appointment: {result1.get('message', 'No error message')}"
    
    # Try to book second appointment at same time
    result2 = platform.book_appointment(
        name="Integration Test Appointment 2",
        timestamp=timestamp,
        phone_number="+0987654321",
        duration=30
    )
    print(f"Second booking response: {result2}")
    
    # Verify conflict handling
    assert result2['success'] == False, "Second booking should have failed"
    assert 'available_slots' in result2, "No available_slots in conflict response"
    assert 'date' in result2, "No date in conflict response"
    
    try:
        # Clean up: Cancel the test appointment
        cancel_result = platform.cancel_appointment(
            timestamp=timestamp,
            phone_number="+1234567890"
        )
        print(f"Cleanup result: {cancel_result}")
    except Exception as e:
        print(f"Warning: Failed to clean up test appointment: {str(e)}")
    print("=== End Debug Info ===\n") 