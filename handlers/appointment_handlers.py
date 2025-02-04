from typing import Any, Dict
from platforms.platform_factory import PlatformFactory
import json

def handle_book_appointment(event: Dict[str, Any], platform_name: str) -> Dict[str, Any]:
    """
    Handle booking appointment operation.
    
    Args:
        event: Dict containing:
            - name: String, customer's name
            - timestamp: String in format 'YYYY-MM-DDTHH:MM:SS', desired appointment time
            - phone_number: String, customer's phone number
            - duration: Integer (optional), appointment duration in minutes, defaults to 30
        platform_name: String, name of the calendar platform to use
    
    Returns:
        Dict containing:
            - statusCode: Integer HTTP status code
            - body: Dict containing:
                - success: Boolean indicating if booking was successful
                - message: String description of result
                - event_id: String (if success), unique identifier for the appointment
                - event_link: String (if success), URL to the calendar event
                - available_slots: List (if booking failed), alternative available time slots
    """
    name = event.get('name')
    timestamp = event.get('timestamp')
    phone_number = event.get('phone_number')
    duration = event.get('duration', 30)
    
    if not all([name, timestamp, phone_number]):
        return {
            'statusCode': 400,
            'body': 'Name, timestamp, and phone number are required'
        }
    
    platform = PlatformFactory.get_platform(platform_name)
    result = platform.book_appointment(
        name=name,
        timestamp=timestamp,
        phone_number=phone_number,
        duration=duration
    )
    
    return {
        'statusCode': 200,
        'body': result
    }

def handle_get_availability(event: Dict[str, Any], platform_name: str) -> Dict[str, Any]:
    """
    Handle getting availability operation.
    
    Args:
        event: Dict containing:
            - timestamp: Optional string in format 'YYYY-MM-DDTHH:MM:SS'
            - date: Optional string in format 'YYYY-MM-DD'
            - duration: Optional integer, appointment duration in minutes
        platform_name: String, name of the calendar platform to use
    
    Returns:
        Dict containing:
            - statusCode: Integer HTTP status code
            - body: Dict containing availability information
    """
    platform = PlatformFactory.get_platform(platform_name)
    
    # Get optional parameters
    duration = event.get('duration', 30)
    date = event.get('date')
    timestamp = event.get('timestamp')
    
    if date:
        # If specific date is provided, use get_availability with date
        result = platform.get_availability(duration=duration, date=date)
    elif timestamp:
        # If timestamp is provided, use get_next_availability
        result = platform.get_next_availability(timestamp=timestamp, duration=duration)
    else:
        # If neither is provided, get next available day
        result = platform.get_availability(duration=duration)
    
    return {
        'statusCode': 200,
        'body': result
    }

def handle_get_appointments(event: Dict[str, Any], platform_name: str) -> Dict[str, Any]:
    """
    Handle retrieving all appointments for a specific phone number.
    
    Args:
        event: Dict containing:
            - phone_number: String, customer's phone number to look up appointments
        platform_name: String, name of the calendar platform to use
    
    Returns:
        Dict containing:
            - statusCode: Integer HTTP status code
            - body: Dict containing:
                - success: Boolean indicating if operation was successful
                - appointments: List of appointments, each containing:
                    - start: String, start time in format 'YYYY-MM-DDTHH:MM:SS'
                    - end: String, end time in format 'YYYY-MM-DDTHH:MM:SS'
                    - name: String, customer's name
                    - event_id: String, unique identifier for the appointment
    """
    phone_number = event.get('phone_number')
    
    if not phone_number:
        return {
            'statusCode': 400,
            'body': 'Phone number is required'
        }
    
    platform = PlatformFactory.get_platform(platform_name)
    result = platform.get_customer_appointments(phone_number=phone_number)
    
    return {
        'statusCode': 200,
        'body': result
    }

def handle_cancel_appointment(event, platform_type):
    """
    Handle canceling an appointment.
    
    Args:
        event: Dict containing:
            - timestamp: String in format 'YYYY-MM-DDTHH:MM:SS'
            - phone_number: String, customer's phone number
        platform_type: String, name of the calendar platform to use
    
    Returns:
        Dict containing:
            - statusCode: Integer HTTP status code
            - body: JSON string containing operation result
    """
    platform = PlatformFactory.get_platform(platform_type)
    result = platform.cancel_appointment(
        timestamp=event.get('timestamp'),
        phone_number=event.get('phone_number')
    )
    
    return {
        'statusCode': 200,  # Changed from 400 to 200
        'body': json.dumps(result)
    }

def handle_reschedule_appointment(event: Dict[str, Any], platform_name: str) -> Dict[str, Any]:
    """
    Handle rescheduling an existing appointment to a new time.
    
    Args:
        event: Dict containing:
            - name: String, customer's name
            - phone_number: String, customer's phone number
            - old_timestamp: String in format 'YYYY-MM-DDTHH:MM:SS', current appointment time
            - new_timestamp: String in format 'YYYY-MM-DDTHH:MM:SS', desired new appointment time
        platform_name: String, name of the calendar platform to use
    
    Returns:
        Dict containing:
            - statusCode: Integer HTTP status code
            - body: Dict containing:
                - success: Boolean indicating if rescheduling was successful
                - message: String description of result
                - event_id: String (if success), unique identifier for the new appointment
                - event_link: String (if success), URL to the new calendar event
                - available_slots: List (if new time unavailable), alternative available time slots
    """
    name = event.get('name')
    phone_number = event.get('phone_number')
    old_timestamp = event.get('old_timestamp')
    new_timestamp = event.get('new_timestamp')
    
    if not all([name, phone_number, old_timestamp, new_timestamp]):
        return {
            'statusCode': 400,
            'body': 'Name, phone number, old timestamp, and new timestamp are required'
        }
    
    platform = PlatformFactory.get_platform(platform_name)
    result = platform.reschedule_appointment(
        name=name,
        phone_number=phone_number,
        old_timestamp=old_timestamp,
        new_timestamp=new_timestamp
    )
    
    return {
        'statusCode': 200,
        'body': result
    } 