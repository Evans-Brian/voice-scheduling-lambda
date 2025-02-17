import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from platforms.google_calendar import GoogleCalendarPlatform
from constants import CALENDAR_ID, DEFAULT_START_HOUR, DEFAULT_END_HOUR
import pytz

@pytest.fixture
def mock_service():
    """Create a mock Google Calendar service"""
    service = Mock()
    
    # Mock the events().list().execute() chain
    events_list = Mock()
    events_list.execute.return_value = {
        'items': [
            {
                'summary': 'Test Appointment',
                'description': 'Phone: +1234567890',
                'start': {'dateTime': '2024-03-20T09:00:00Z'},
                'end': {'dateTime': '2024-03-20T09:30:00Z'}
            }
        ]
    }
    events = Mock()
    events.list.return_value = events_list
    service.events.return_value = events
    
    return service

@pytest.fixture
def platform(mock_service):
    """Create a GoogleCalendarPlatform instance with mocked service"""
    platform = GoogleCalendarPlatform(test_mode=True)
    platform.service = mock_service
    return platform

def test_book_appointment_success(platform, mock_service):
    """Test successful appointment booking"""
    # Mock the events().insert().execute() chain
    insert_result = Mock()
    insert_result.execute.return_value = {}
    events = Mock()
    events.insert.return_value = insert_result
    events.list.return_value.execute.return_value = {'items': []}  # No conflicts
    mock_service.events.return_value = events
    
    result = platform.book_appointment(
        name="John Doe",
        timestamp="2024-03-20T10:00:00",
        phone_number="+1234567890",
        duration=30
    )
    
    assert result['success'] == True
    assert 'message' in result

def test_book_appointment_conflict(platform, mock_service):
    """Test booking when time slot is already taken"""
    # Mock current time to be March 20th, 2024
    real_datetime = datetime
    fixed_date = real_datetime(2024, 3, 20, 8, 0)  # 8 AM
    fixed_date_eastern = pytz.timezone('America/New_York').localize(fixed_date)
    
    # Mock the events().list().execute() chain to show a conflict
    events_list = Mock()
    events_list.execute.return_value = {
        'items': [
            {
                'summary': 'Existing Appointment',
                'start': {'dateTime': '2024-03-20T10:00:00-04:00'},  # Use EST timezone
                'end': {'dateTime': '2024-03-20T10:30:00-04:00'}
            }
        ],
        'timeZone': 'America/New_York'
    }
    events = Mock()
    events.list.return_value = events_list
    mock_service.events.return_value = events
    
    # Create a class to mock datetime
    class MockDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_date_eastern if tz is None else fixed_date_eastern.astimezone(tz)

    with patch('datetime.datetime', MockDateTime), \
         patch('platforms.base_platform.datetime', MockDateTime), \
         patch('platforms.google_calendar.datetime', MockDateTime):
        
        result = platform.book_appointment(
            name="John Doe",
            timestamp="2024-03-20T10:00:00",
            phone_number="+1234567890",
            duration=30
        )
    assert result['success'] == False
    assert result['message'] == 'Time slot is already booked'
    assert result['otherAvailableTimes'] == 'Available Wednesday, March 20: 9AM, 9:30AM, from 10:30AM to 4:30PM'

def test_book_appointment_conflict_entire_day(platform, mock_service):
    """Test booking when time slot is already taken"""
    # Mock current time to be March 20th, 2024
    real_datetime = datetime
    fixed_date = real_datetime(2024, 3, 20, 8, 0)  # 8 AM
    fixed_date_eastern = pytz.timezone('America/New_York').localize(fixed_date)
    
    # Create two different return values
    first_response = {
        'items': [
            {
                'summary': 'Existing Appointment',
                'start': {'dateTime': '2024-03-20T08:00:00-04:00'},  # Use EST timezone
                'end': {'dateTime': '2024-03-20T20:30:00-04:00'}
            }
        ],
        'timeZone': 'America/New_York'
    }

    second_response = {
        'items': [
            {
                'summary': 'Existing Appointment',
                'start': {'dateTime': '2024-03-20T08:00:00-04:00'},  # Use EST timezone
                'end': {'dateTime': '2024-03-20T20:30:00-04:00'}
            }
        ],
        'timeZone': 'America/New_York'
    }
    third_response = {
        'items': [],  # Empty list for subsequent calls
        'timeZone': 'America/New_York'
    }
    
    # Mock the events().list().execute() chain with different responses
    events_list = Mock()
    events_list.execute.side_effect = [first_response, second_response, third_response]
    events = Mock()
    events.list.return_value = events_list
    mock_service.events.return_value = events
    
    # Create a class to mock datetime
    class MockDateTime(real_datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_date_eastern if tz is None else fixed_date_eastern.astimezone(tz)

    with patch('datetime.datetime', MockDateTime), \
         patch('platforms.base_platform.datetime', MockDateTime), \
         patch('platforms.google_calendar.datetime', MockDateTime):
        
        result = platform.book_appointment(
            name="John Doe",
            timestamp="2024-03-20T10:00:00",
            phone_number="+1234567890",
            duration=30
        )
    assert result['success'] == False
    assert result['message'] == 'Time slot is already booked'
    assert result['otherAvailableTimes'] == 'Requested date unavailable, but there is availability on: Available Thursday, March 21: from 9AM to 4:30PM'


def test_get_customer_appointments(platform, mock_service):
    """Test getting customer appointments"""
    events = Mock()
    events.list.return_value.execute.return_value = {
        'items': [
            {
                'summary': 'Test Appointment',
                'description': 'Phone: +1234567890',
                'start': {'dateTime': '2024-03-20T09:00:00+00:00'},
                'end': {'dateTime': '2024-03-20T09:30:00+00:00'}
            }
        ]
    }
    mock_service.events.return_value = events
    
    result = platform.get_customer_appointments(phone_number="+1234567890")
    
    assert result['success'] == True
    assert 'appointments' in result
    appointments = result['appointments']
    assert appointments == 'The caller has appointments booked for March 20 at 09:00AM'


def test_cancel_appointment_success(platform, mock_service):
    """Test successful appointment cancellation"""
    # Mock the events().list().execute() chain for phone verification
    list_result = Mock()
    list_result.execute.return_value = {
        'items': [
            {
                'id': 'test_event_id',
                'description': 'Phone: +1234567890',
                'start': {'dateTime': '2024-03-20T10:00:00-04:00'},  # EST timezone
                'end': {'dateTime': '2024-03-20T10:30:00-04:00'}
            }
        ]
    }
    events = Mock()
    events.list.return_value = list_result
    
    # Mock the delete operation
    delete_result = Mock()
    delete_result.execute.return_value = {}
    events.delete.return_value = delete_result
    
    mock_service.events.return_value = events
    
    result = platform.cancel_appointment(
        "2024-03-20T10:00:00",  # Local time that matches the event's start time
        "+1234567890"
    )
    
    assert result['success'] == True, "Cancellation should succeed"
    assert 'cancelled successfully' in result['message'].lower()

def test_cancel_appointment_not_found(platform, mock_service):
    """Test canceling a non-existent appointment"""
    # Mock the events().list().execute() chain to return no matching appointments
    events_list = Mock()
    events_list.execute.return_value = {'items': []}  # No appointments found
    events = Mock()
    events.list.return_value = events_list
    mock_service.events.return_value = events
    
    result = platform.cancel_appointment(
        timestamp="2024-03-20T10:00:00",
        phone_number="+1234567890"
    )
    
    assert result['success'] == False
    assert 'no matching appointment' in result['message'].lower()

def test_get_availability_no_conflicts(platform, mock_service):
    """Test getting available slots for a day with no conflicts"""
    events = Mock()
    events.list.return_value.execute.return_value = {'items': []}
    mock_service.events.return_value = events
    
    result = platform.get_availability(duration=30, date="2099-03-20")
    assert result['success'] == True
    assert result['message'] == "Available Friday, March 20: from 9AM to 4:30PM"

def test_get_availability_with_conflicts(platform, mock_service):
    """Test getting available slots with existing appointments"""
    # Mock multiple existing events
    events = Mock()
    events.list.return_value.execute.return_value = {
        'items': [
            {
                'start': {'dateTime': '2024-03-20T09:00:00-04:00'},  # EST timezone
                'end': {'dateTime': '2024-03-20T10:00:00-04:00'}
            },
            {
                'start': {'dateTime': '2024-03-20T14:00:00-04:00'},  # EST timezone
                'end': {'dateTime': '2024-03-20T15:00:00-04:00'}
            }
        ]
    }
    mock_service.events.return_value = events
    
    result = platform.get_availability(duration=30, date="2099-03-20")
    
    assert result['success'] == True
    assert isinstance(result['message'], str)
    
    # Check that conflicting times are not mentioned in the string
    conflicting_times = ['9AM', '9:30AM', '2PM', '2:30PM']
    for conflict_time in conflicting_times:
        assert conflict_time not in result['message'], \
            f"Found conflicting time {conflict_time} in available slots: {result['slots']}"
    
    # Check that the string contains expected format
    assert result['message'] == "Available Friday, March 20: from 10AM to 1:30PM, from 3PM to 4:30PM"

def test_outside_business_hours(platform):
    """Test booking outside business hours"""
    result = platform.book_appointment(
        name="John Doe",
        timestamp=f"2024-03-20T{DEFAULT_END_HOUR}:00:00",
        phone_number="+1234567890"
    )
    
    assert result['success'] == False
    assert 'between 9:00 and 17:00' in result['message'].lower()

def test_get_availability_today_filters_past_times(platform, mock_service):
    """Test getting available slots for today filters out past times"""
    # Mock current time to be 2:30 PM
    with patch('platforms.base_platform.datetime') as mock_dt:
        real_now = datetime(2024, 3, 20, 14, 30)  # 2:30 PM
        mock_now = Mock(wraps=real_now)
        mock_now.date.return_value = real_now.date()
        mock_now.replace.return_value = real_now
        mock_dt.now.return_value = mock_now
        mock_dt.strptime = datetime.strptime
        
        # Mock no existing appointments
        events = Mock()
        events.list.return_value.execute.return_value = {'items': []}
        mock_service.events.return_value = events
        
        result = platform.get_availability(duration=30, date="2024-03-20")
        
        assert result['success'] == True
        # Should only show times from 3:00 PM to 4:30 PM
        assert result['message'] == "Available Wednesday, March 20: from 3PM to 4:30PM"

def test_get_availability_no_date_provided(platform, mock_service):
    """Test getting available slots when no date is provided (should default to today)"""
    # Mock current time to be 9:30 AM on March 20, 2024
    fixed_date = datetime(2024, 3, 20, 9, 30)
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
        
        # Mock no existing appointments
        events = Mock()
        events.list.return_value.execute.return_value = {'items': []}
        mock_service.events.return_value = events
        
        result = platform.get_availability(duration=30)  # No date provided
        
        assert result['success'] == True
        # Should show times from 10:00 AM onwards (since current time is 9:30 AM)
        assert result['message'] == "Available Wednesday, March 20: from 10AM to 4:30PM" 

def test_get_availability_today_given_as_date(platform, mock_service):
    """Test getting available slots when no date is provided (should default to today)"""
    # Mock current time to be 9:30 AM on March 20, 2024
    fixed_date = datetime(2024, 3, 20, 9, 30)
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
        
        # Mock no existing appointments
        events = Mock()
        events.list.return_value.execute.return_value = {'items': []}
        mock_service.events.return_value = events
        
        result = platform.get_availability(duration=30, date="2024-03-20")  # No date provided
        
        assert result['success'] == True
        # Should show times from 10:00 AM onwards (since current time is 9:30 AM)
        assert result['message'] == "Available Wednesday, March 20: from 10AM to 4:30PM" 