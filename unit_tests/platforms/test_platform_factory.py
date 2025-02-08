import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import pytest
from unittest.mock import Mock, patch
from platforms.platform_factory import PlatformFactory
from platforms.base_platform import BookingPlatform
from platforms.google_calendar import GoogleCalendarPlatform

@pytest.fixture(autouse=True)
def mock_service():
    """Mock Google Calendar dependencies"""
    with patch('platforms.google_calendar.get_credentials', return_value=None), \
         patch('platforms.google_calendar.build', return_value=Mock()):
        yield

def test_get_platform_google():
    """Test getting Google Calendar platform"""
    platform = PlatformFactory.get_platform('google')
    
    # Assert correct type
    assert isinstance(platform, BookingPlatform)
    assert isinstance(platform, GoogleCalendarPlatform)

def test_get_platform_case_insensitive(mock_service):
    """Test that platform name is case insensitive"""
    platform1 = PlatformFactory.get_platform('GOOGLE')
    platform2 = PlatformFactory.get_platform('Google')
    platform3 = PlatformFactory.get_platform('google')
    
    # Assert all variations work
    assert all(isinstance(p, GoogleCalendarPlatform) for p in [platform1, platform2, platform3])

def test_get_platform_unsupported():
    """Test error handling for unsupported platform"""
    with pytest.raises(ValueError) as exc_info:
        PlatformFactory.get_platform('unsupported')
    
    # Assert error message contains supported platforms
    error_msg = str(exc_info.value)
    assert 'Unsupported platform: unsupported' in error_msg
    assert 'Supported platforms are: google' in error_msg

def test_get_platform_empty_string():
    """Test error handling for empty platform name"""
    with pytest.raises(ValueError) as exc_info:
        PlatformFactory.get_platform('')
    
    # Assert error message
    error_msg = str(exc_info.value)
    assert 'Unsupported platform: ' in error_msg
    assert 'Supported platforms are: google' in error_msg

def test_get_platform_none():
    """Test error handling for None platform name"""
    with pytest.raises(ValueError) as exc_info:
        PlatformFactory.get_platform(None)
    
    # Assert error message
    error_msg = str(exc_info.value)
    assert 'Unsupported platform: None' in error_msg
    assert 'Supported platforms are: google' in error_msg

def test_platform_registration():
    """Test that platforms are properly registered"""
    # Get all registered platforms
    platforms = PlatformFactory._platforms
    
    # Assert Google Calendar is registered
    assert 'google' in platforms
    assert platforms['google'] == GoogleCalendarPlatform
    
    # Assert all registered platforms inherit from BookingPlatform
    assert all(issubclass(platform, BookingPlatform) for platform in platforms.values()) 