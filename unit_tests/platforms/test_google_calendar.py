import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from platforms.google_calendar import GoogleCalendarPlatform
from constants import CALENDAR_ID, DEFAULT_START_HOUR, DEFAULT_END_HOUR

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
    with patch('platforms.google_calendar.build') as mock_build:
        mock_build.return_value = mock_service
        # Patch the abstract methods
        with patch('platforms.google_calendar.GoogleCalendarPlatform.__abstractmethods__', set()):
            platform = GoogleCalendarPlatform()
            platform.service = mock_service  # Set the service explicitly
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
    # Mock existing event at the same time
    events = Mock()
    events.list.return_value.execute.return_value = {
        'items': [
            {
                'start': {'dateTime': '2024-03-20T10:00:00-04:00'},  # EST timezone
                'end': {'dateTime': '2024-03-20T10:30:00-04:00'}
            }
        ]
    }
    mock_service.events.return_value = events
    
    # Try to book at the same time
    result = platform.book_appointment(
        name="John Doe",
        timestamp="2024-03-20T10:00:00",  # This should conflict with the existing event
        phone_number="+1234567890",
        duration=30
    )
    
    assert result['success'] == False, "Booking should fail due to conflict"
    assert 'time slot is already booked' in result['message'].lower()
    assert 'available_slots' in result, "Should provide alternative slots"

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
    assert len(appointments) == 1
    assert appointments[0]['start'] == '2024-03-20T09:00:00+00:00'

def test_get_next_availability(platform, mock_service):
    """Test getting next available day slots"""
    # Mock the events().list().execute() chain
    events = Mock()
    events.list.return_value.execute.return_value = {
        'items': []  # Empty list of events
    }
    mock_service.events.return_value = events
    
    result = platform.get_availability(
        duration=30,
        date=None  # This will make it look for next available day
    )
    
    assert result['success'] == True
    assert result['message'] == 'Available slots found'
    assert isinstance(result['slots'], list)
    assert len(result['slots']) > 0
    
    # Verify structure of slots
    for slot in result['slots']:
        assert isinstance(slot, dict)
        assert 'start' in slot
        assert 'end' in slot
        assert isinstance(slot['start'], str)
        assert isinstance(slot['end'], str)

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
    """Test cancelling non-existent appointment"""
    events = Mock()
    events.delete.side_effect = Exception('Event not found')
    mock_service.events.return_value = events
    
    result = platform.cancel_appointment("nonexistent", "+1234567890")
    
    assert result['success'] == False
    assert 'error' in result['message'].lower()

def test_get_availability_no_conflicts(platform, mock_service):
    """Test getting available slots for a day with no conflicts"""
    events = Mock()
    events.list.return_value.execute.return_value = {'items': []}
    mock_service.events.return_value = events
    
    result = platform.get_availability(duration=30, date="2024-03-20")
    
    assert result['success'] == True
    assert 'slots' in result
    assert len(result['slots']) > 0
    assert result['date'] == '2024-03-20'

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
    
    result = platform.get_availability(duration=30, date="2024-03-20")
    
    assert result['success'] == True
    assert 'slots' in result
    
    # Convert slots to a list of start times for easier checking
    slot_times = [slot['start'] for slot in result['slots']]
    
    # These times should not be in the available slots
    conflicting_times = ['09:00', '09:30', '14:00', '14:30']
    
    # Check each conflicting time is not in the available slots
    for conflict_time in conflicting_times:
        assert not any(conflict_time in slot_time for slot_time in slot_times), \
            f"Found conflicting time {conflict_time} in available slots: {slot_times}"

def test_outside_business_hours(platform):
    """Test booking outside business hours"""
    result = platform.book_appointment(
        name="John Doe",
        timestamp=f"2024-03-20T{DEFAULT_END_HOUR}:00:00",
        phone_number="+1234567890"
    )
    
    assert result['success'] == False
    assert 'between 9:00 and 17:00' in result['message'].lower() 