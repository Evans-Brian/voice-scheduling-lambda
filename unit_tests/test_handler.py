import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from unittest.mock import Mock, patch
from lambda_function import lambda_handler

def test_missing_operation():
    """Test handler returns 400 when operation is missing"""
    event = {
        'platform': 'google',
        'name': 'John Doe'
    }
    
    result = lambda_handler(event, None)
    assert result['statusCode'] == 400
    body = json.loads(result['body'])
    assert 'Operation is required' in body, f"Expected error message not found in response: {body}"

def test_missing_platform():
    """Test handler returns 400 when platform is missing"""
    event = {
        'operation': 'book_appointment',
        'name': 'John Doe'
    }
    
    result = lambda_handler(event, None)
    assert result['statusCode'] == 400
    body = json.loads(result['body'])
    assert 'Platform is required' in body, f"Expected error message not found in response: {body}"

def test_unknown_operation():
    """Test handler returns 400 for unknown operation"""
    event = {
        'operation': 'invalid_operation',
        'platform': 'google'
    }
    
    result = lambda_handler(event, None)
    assert result['statusCode'] == 400
    body = json.loads(result['body'])
    assert 'Unknown operation' in body, f"Expected error message not found in response: {body}"

def test_successful_booking():
    """Test successful booking operation"""
    event = {
        'operation': 'book_appointment',
        'platform': 'google',
        'name': 'John Doe',
        'timestamp': '2024-03-20T09:00:00',
        'phone_number': '+1234567890'
    }
    
    mock_response = {
        'statusCode': 200,
        'body': json.dumps({
            'success': True,
            'message': 'Appointment booked successfully',
            'event_id': 'mock_event_123',
            'event_link': 'http://calendar/event123',
            'timestamp': '2024-03-20T09:00:00',
            'bookedEvents': {
                'items': []
            }
        })
    }
    
    # Create a mock handler that returns our success response
    mock_handler = Mock(name='mock_book_appointment')
    mock_handler.return_value = mock_response
    
    mock_handlers = {
        'book_appointment': mock_handler
    }
    
    # Stack multiple patches to catch all possible import paths
    with patch('handlers.HANDLERS', mock_handlers), \
         patch('lambda_function.HANDLERS', mock_handlers), \
         patch('handlers.appointment_handlers.handle_book_appointment', mock_handler):
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 200, "Status code should be 200"
        body = json.loads(result['body'])
        assert isinstance(body, dict), "Body should be a dictionary after parsing"
        assert body.get('success') is True, f"Booking should be successful, got: {body}"
        assert 'event_id' in body, "Should include event_id"
        assert 'event_link' in body, "Should include event_link"
        assert 'timestamp' in body, "Should include timestamp"
        mock_handler.assert_called_once_with(event, 'google')

def test_general_error_handling():
    """Test handler returns 500 for unexpected errors"""
    event = {
        'operation': 'book_appointment',
        'platform': 'google',
        'name': 'John Doe',
        'timestamp': '2024-03-20T09:00:00',
        'phone_number': '+1234567890'
    }
    
    # Create a mock with side_effect
    mock_handler = Mock(name='mock_book_appointment')
    mock_handler.side_effect = Exception("Test error")
    
    mock_handlers = {
        'book_appointment': mock_handler
    }
    
    # Stack multiple patches to catch all possible import paths
    with patch('handlers.HANDLERS', mock_handlers), \
         patch('lambda_function.HANDLERS', mock_handlers), \
         patch('handlers.appointment_handlers.handle_book_appointment', mock_handler):
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 500, "General exception should return 500 status code"
        body = json.loads(result['body'])
        assert 'Error' in body, f"Expected error message not found in response: {body}"

def test_value_error_handling():
    """Test handler returns 400 for ValueError"""
    event = {
        'operation': 'book_appointment',
        'platform': 'google'
    }
    
    # Create a mock with ValueError side_effect
    mock_handler = Mock(name='mock_book_appointment')
    mock_handler.side_effect = ValueError('Invalid input')
    
    mock_handlers = {
        'book_appointment': mock_handler
    }
    
    # Stack multiple patches to catch all possible import paths
    with patch('handlers.HANDLERS', mock_handlers), \
         patch('lambda_function.HANDLERS', mock_handlers), \
         patch('handlers.appointment_handlers.handle_book_appointment', mock_handler):
        
        result = lambda_handler(event, None)
        
        assert result['statusCode'] == 400, "ValueError should return 400 status code"
        body = json.loads(result['body'])
        assert 'Invalid input' in body, f"Expected error message not found in response: {body}"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s']) 