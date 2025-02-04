import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import Mock, patch
import json
from handlers.appointment_handlers import (
    handle_book_appointment,
    handle_get_availability,
    handle_get_appointments,
    handle_cancel_appointment,
    handle_reschedule_appointment
)

@pytest.fixture
def mock_platform():
    platform = Mock()
    return platform

def test_book_appointment_success(mock_platform):
    """Test successful appointment booking"""
    # Setup
    mock_response = {
        'success': True,
        'message': 'Appointment booked successfully',
        'event_id': 'mock_event_123',
        'event_link': 'http://calendar/event123'
    }
    mock_platform.book_appointment.return_value = mock_response
    
    with patch('handlers.appointment_handlers.PlatformFactory') as mock_factory:
        mock_factory.get_platform.return_value = mock_platform
        
        event = {
            'name': 'John Doe',
            'timestamp': '2024-03-20T09:00:00',
            'phone_number': '+1234567890',
            'duration': 30
        }
        
        # Execute
        result = handle_book_appointment(event, 'google')
        
        # Assert
        assert isinstance(result, dict)
        assert result.get('statusCode') == 200
        body = result.get('body', {})
        assert body.get('success') is True
        assert 'event_id' in body
        assert 'event_link' in body
        mock_platform.book_appointment.assert_called_once_with(
            name='John Doe',
            timestamp='2024-03-20T09:00:00',
            phone_number='+1234567890',
            duration=30
        )

def test_book_appointment_slot_unavailable(mock_platform):
    """Test booking when slot is unavailable"""
    # Setup
    mock_response = {
        'success': False,
        'message': 'Time slot is already booked',
        'available_slots': [
            {'start': '09:30', 'end': '10:00'},
            {'start': '10:30', 'end': '11:00'}
        ],
        'date': '2024-03-20'
    }
    mock_platform.book_appointment.return_value = mock_response
    
    with patch('handlers.appointment_handlers.PlatformFactory') as mock_factory:
        mock_factory.get_platform.return_value = mock_platform
        
        event = {
            'name': 'John Doe',
            'timestamp': '2024-03-20T09:00:00',
            'phone_number': '+1234567890'
        }
        
        # Execute
        result = handle_book_appointment(event, 'google')
        
        # Assert
        assert isinstance(result, dict)
        assert result.get('statusCode') == 200
        body = result.get('body', {})
        assert body.get('success') is False
        assert 'available_slots' in body
        assert len(body['available_slots']) == 2
        assert body.get('date') == '2024-03-20'

def test_get_availability_slots(mock_platform):
    """Test getting next available slots"""
    # Setup
    mock_response = {
        'success': True,
        'message': 'Available slots found',
        'slots': [
            {'start': '09:00', 'end': '09:30'},
            {'start': '10:00', 'end': '10:30'}
        ],
        'date': '2024-03-20'
    }
    mock_platform.get_availability.return_value = mock_response
    
    with patch('handlers.appointment_handlers.PlatformFactory') as mock_factory:
        mock_factory.get_platform.return_value = mock_platform
        
        # Execute
        result = handle_get_availability({}, 'google')
        
        # Assert
        assert isinstance(result, dict)
        assert result.get('statusCode') == 200
        assert isinstance(result.get('body'), str)  # Verify body is a string
        body = json.loads(result.get('body'))  # Parse JSON string
        assert body['success'] is True
        assert 'slots' in body
        assert len(body['slots']) == 2
        assert body['date'] == '2024-03-20'
        mock_platform.get_availability.assert_called_once_with(duration=30)

def test_get_appointments(mock_platform):
    """Test getting user appointments"""
    # Setup
    mock_response = {
        'success': True,
        'appointments': [
            {
                'start': '2024-03-20T09:00:00',
                'end': '2024-03-20T09:30:00',
                'name': 'John Doe',
                'event_id': 'mock_event_123'
            }
        ]
    }
    mock_platform.get_customer_appointments.return_value = mock_response
    
    with patch('handlers.appointment_handlers.PlatformFactory') as mock_factory:
        mock_factory.get_platform.return_value = mock_platform
        
        event = {
            'phone_number': '+1234567890'
        }
        
        # Execute
        result = handle_get_appointments(event, 'google')
        
        # Assert
        assert isinstance(result, dict)
        assert result.get('statusCode') == 200
        body = result.get('body', {})
        assert body.get('success') is True
        assert 'appointments' in body
        assert len(body['appointments']) == 1
        mock_platform.get_customer_appointments.assert_called_once_with(phone_number='+1234567890')

def test_cancel_appointment(mock_platform):
    """Test canceling an appointment"""
    # Setup
    mock_response = {
        'success': True,
        'message': 'Appointment cancelled successfully'
    }
    mock_platform.cancel_appointment.return_value = mock_response
    
    with patch('handlers.appointment_handlers.PlatformFactory') as mock_factory:
        mock_factory.get_platform.return_value = mock_platform
        
        event = {
            'event_id': 'mock_event_123'
        }
        
        # Execute
        result = handle_cancel_appointment(event, 'google')
        
        # Assert
        assert isinstance(result, dict)
        assert result.get('statusCode') == 400
        assert isinstance(result.get('body'), str)  # Verify body is a string
        body = json.loads(result.get('body'))  # Parse JSON string
        assert body['success'] is True
        assert 'message' in body
        mock_platform.cancel_appointment.assert_called_once_with(event_id='mock_event_123')
