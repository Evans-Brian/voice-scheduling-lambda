import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from datetime import datetime, timedelta
from platforms.base_platform import BookingPlatform
from constants import DEFAULT_START_HOUR, DEFAULT_END_HOUR
from unittest.mock import patch, Mock
import pytz

class MockPlatform(BookingPlatform):
    """Mock platform for testing base class functionality"""
    def book_appointment(self, name: str, timestamp: str, phone_number: str, duration: int = 30) -> dict:
        """Mock implementation that validates inputs and business hours"""
        if not all([name, timestamp, phone_number]):
            raise ValueError('Missing required fields')
            
        # Validate timestamp format - let ValueError propagate up
        appointment_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
        start_hour = appointment_time.hour
        start_minute = appointment_time.minute
        
        # Calculate end time
        end_time = appointment_time + timedelta(minutes=duration)
        end_hour = end_time.hour
        end_minute = end_time.minute
        
        # Check business hours for both start and end times
        if (start_hour < DEFAULT_START_HOUR or 
            start_hour >= DEFAULT_END_HOUR or
            end_hour >= DEFAULT_END_HOUR or
            (end_hour == DEFAULT_END_HOUR and end_minute > 0)):
            return {
                'success': False,
                'message': 'Outside business hours',
                'available_slots': [],
                'date': appointment_time.strftime('%Y-%m-%d')
            }
            
        return {
            'success': True,
            'message': 'Appointment booked successfully'
        }
        
    def get_availability(self, duration: int = 30, date: str = None) -> dict:
        """Mock implementation for getting available slots"""
        return {
            'success': True,
            'message': 'Available slots found',
            'slots': [{'start': '09:00', 'end': '09:30'}],
            'date': '2024-03-20'
        }
        
    def get_next_availability(self, timestamp: str, duration: int = 30) -> dict:
        """Mock implementation for getting next available day slots"""
        return {
            'success': True,
            'message': 'Available slots found',
            'slots': [{'start': '09:00', 'end': '09:30'}],
            'date': '2024-03-20'
        }
        
    def get_customer_appointments(self, phone_number: str) -> dict:
        """Mock implementation for getting customer appointments"""
        return {
            'success': True,
            'appointments': []
        }
        
    def get_appointments(self, phone_number: str) -> dict:
        """Mock implementation for getting appointments"""
        return {
            'success': True,
            'appointments': []
        }
        
    def cancel_appointment(self, timestamp: str, phone_number: str) -> dict:
        """Mock implementation for canceling appointment"""
        return {
            'success': True,
            'message': 'Appointment cancelled'
        }
        
    def reschedule_appointment(self, name: str, phone_number: str, old_timestamp: str, new_timestamp: str) -> dict:
        """Mock implementation for rescheduling appointment"""
        return {
            'success': True,
            'message': 'Appointment rescheduled'
        }

def test_book_appointment_success():
    """Test successful booking attempt"""
    platform = MockPlatform()
    result = platform.book_appointment(
        name="Test Success",
        timestamp="2024-03-20T10:00:00",
        phone_number="+1234567890"
    )
    
    assert result['success'] == True
    assert 'message' in result

def test_book_appointment_outside_hours():
    """Test booking outside business hours"""
    platform = MockPlatform()
    result = platform.book_appointment(
        name="Test Early",
        timestamp="2024-03-20T07:00:00",
        phone_number="+1234567890"
    )
    
    assert result['success'] == False
    assert result['message'] == 'Outside business hours'
    assert 'available_slots' in result
    assert isinstance(result['available_slots'], list)

def test_book_appointment_end_after_hours():
    """Test booking that would end after business hours"""
    platform = MockPlatform()
    result = platform.book_appointment(
        name="Test Late End",
        timestamp=f"2024-03-20T{DEFAULT_END_HOUR-1}:45:00",
        phone_number="+1234567890"
    )
    
    assert result['success'] == False
    assert result['message'] == 'Outside business hours'
    assert 'available_slots' in result
    assert isinstance(result['available_slots'], list)

def test_book_appointment_invalid_timestamp():
    """Test booking with invalid timestamp format"""
    platform = MockPlatform()
    with pytest.raises(ValueError):
        platform.book_appointment(
            name="Test Invalid",
            timestamp="invalid_timestamp",
            phone_number="+1234567890"
        )

def test_book_appointment_missing_fields():
    """Test booking with missing required fields"""
    platform = MockPlatform()
    with pytest.raises(ValueError):
        platform.book_appointment(
            name=None,
            timestamp=None,
            phone_number=None
        )

def test_get_availability():
    """Test getting availability"""
    platform = MockPlatform()
    result = platform.get_availability()

    assert result['success'] == True
    assert 'slots' in result
    assert isinstance(result['slots'], list)
    assert 'date' in result

def test_get_appointments():
    """Test getting appointments"""
    platform = MockPlatform()
    result = platform.get_appointments(phone_number="+1234567890")
    
    assert result['success'] == True
    assert 'appointments' in result
    assert isinstance(result['appointments'], list)

def test_cancel_appointment():
    """Test canceling appointment"""
    platform = MockPlatform()
    result = platform.cancel_appointment(
        timestamp="2024-03-20T10:00:00",
        phone_number="+1234567890"
    )
    
    assert result['success'] == True
    assert 'message' in result

def test_reschedule_appointment():
    """Test rescheduling appointment"""
    platform = MockPlatform()
    result = platform.reschedule_appointment(
        name="Test Reschedule",
        phone_number="+1234567890",
        old_timestamp="2024-03-20T10:00:00",
        new_timestamp="2024-03-20T11:00:00"
    )
    
    assert result['success'] == True
    assert 'message' in result

def test_combine_events_empty():
    """Test combining empty slot list"""
    platform = MockPlatform()
    result = platform._combine_events([], "2099-03-20")
    assert result == "No available times found"

def test_combine_events_single_slot():
    """Test combining single slot"""
    platform = MockPlatform()
    slots = [
        {'start': '09:00', 'end': '09:30'}
    ]
    result = platform._combine_events(slots, "2099-03-20")
    assert result == "9AM"

def test_combine_events_non_consecutive():
    """Test combining non-consecutive slots"""
    platform = MockPlatform()
    slots = [
        {'start': '09:00', 'end': '09:30'},
        {'start': '10:00', 'end': '10:30'},
        {'start': '11:00', 'end': '11:30'}
    ]
    result = platform._combine_events(slots, "2099-03-20")
    assert result == "9AM, 10AM, 11AM"

def test_combine_events_consecutive():
    """Test combining consecutive slots"""
    platform = MockPlatform()
    slots = [
        {'start': '10:00', 'end': '10:30'},
        {'start': '10:30', 'end': '11:00'},
        {'start': '11:00', 'end': '11:30'},
        {'start': '11:30', 'end': '12:00'}
    ]
    result = platform._combine_events(slots, "2099-03-20")
    assert result == "10AM to 11:30AM"

def test_combine_events_mixed():
    """Test combining mix of consecutive and non-consecutive slots"""
    platform = MockPlatform()
    slots = [
        {'start': '09:00', 'end': '09:30'},
        {'start': '09:30', 'end': '10:00'},
        {'start': '10:30', 'end': '11:00'},
        {'start': '11:00', 'end': '11:30'},
        {'start': '11:30', 'end': '12:00'},
        {'start': '12:00', 'end': '12:30'},
        {'start': '14:00', 'end': '14:30'}
    ]
    result = platform._combine_events(slots, "2099-03-20")
    assert result == "9AM, 9:30AM, 10:30AM to 12PM, 2PM"

def test_combine_events_pm_times():
    """Test combining slots in PM time"""
    platform = MockPlatform()
    slots = [
        {'start': '13:00', 'end': '13:30'},
        {'start': '13:30', 'end': '14:00'},
        {'start': '14:00', 'end': '14:30'},
        {'start': '14:30', 'end': '15:00'},
        {'start': '16:00', 'end': '16:30'}
    ]
    result = platform._combine_events(slots, "2099-03-20")
    assert result == "1PM to 2:30PM, 4PM"

def test_get_available_times_filters_past_dates():
    """Test that get_available_times shows no slots for past dates"""
    platform = MockPlatform()
    with patch('platforms.base_platform.datetime') as mock_dt:
        real_now = datetime(2024, 3, 20, 10, 0)
        mock_now = Mock(wraps=real_now)
        mock_now.date.return_value = real_now.date()
        mock_now.replace.return_value = real_now
        mock_dt.now.return_value = mock_now
        mock_dt.strptime = datetime.strptime
        
        past_result = platform.get_available_times(
            "2024-03-19T10:00:00",  # Yesterday
            {'bookedEvents': {'items': []}}
        )
        assert past_result['message'] == "Requested date is before today. Can you please provide a date on or after today?"

def test_get_available_times_filters_past_hours_today():
    """Test that get_available_times only shows future times for today"""
    platform = MockPlatform()
    
    fixed_date = datetime(2024, 3, 20, 10, 0)
    fixed_date_eastern = pytz.timezone('America/New_York').localize(fixed_date)
    
    with patch('datetime.datetime') as mock_datetime, \
         patch('platforms.base_platform.datetime') as mock_platform_dt, \
         patch('platforms.google_calendar.datetime') as mock_google_dt:
        
        # Configure all the mocks to return the same fixed date
        mock_datetime.now.return_value = fixed_date_eastern
        mock_datetime.strptime.side_effect = datetime.strptime
        
        mock_platform_dt.now.return_value = fixed_date_eastern
        mock_platform_dt.strptime.side_effect = datetime.strptime
        
        mock_google_dt.now.return_value = fixed_date_eastern
        mock_google_dt.strptime.side_effect = datetime.strptime
        
        today_result = platform.get_available_times(
            "2024-03-20T10:00:00",
            {'bookedEvents': {'items': []}}
        )
        assert today_result['message'] == "Available Wednesday, March 20: 10:30AM to 4:30PM"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])