from datetime import datetime, timedelta
import pytz
from googleapiclient.discovery import build
from .base_platform import BookingPlatform
from constants import (
    CALENDAR_ID,
    DEFAULT_START_HOUR,
    DEFAULT_END_HOUR
)
from auth import get_credentials

class GoogleCalendarPlatform(BookingPlatform):
    def __init__(self, test_mode=False):
        """Initialize the platform
        
        Args:
            test_mode: If True, skip authentication (for unit tests)
        """
        if not test_mode:
            creds = get_credentials()
            self.service = build('calendar', 'v3', credentials=creds)
        self.timezone = pytz.timezone('America/New_York')  # EST/EDT timezone

    def _strip_timezone(self, dt_str: str) -> datetime:
        """
        Helper method to convert datetime string to naive datetime object in local time.
        Handles both UTC ('Z') and offset timezone formats (e.g., '-04:00')
        """
        # If the string ends with 'Z', convert to offset format
        if dt_str.endswith('Z'):
            dt_str = dt_str.replace('Z', '+00:00')
        
        # Parse with timezone info
        utc_dt = datetime.fromisoformat(dt_str)
        
        # Convert to EST
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        local_dt = utc_dt.astimezone(self.timezone)
        
        # Return naive datetime in local time
        return local_dt.replace(tzinfo=None)

    def _format_datetime_for_google(self, dt: datetime) -> str:
        """Helper method to format local datetime for Google Calendar API (in UTC)"""
        # Make datetime timezone-aware in EST
        local_dt = self.timezone.localize(dt)
        # Convert to UTC
        utc_dt = local_dt.astimezone(pytz.UTC)
        return utc_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')

    def book_appointment(self, name: str, timestamp: str, phone_number: str, duration: int = 30) -> dict:
        """
        Book appointment on Google Calendar. If booking fails, returns available slots.
        
        Args:
            name: String name for the calendar event
            timestamp: String in format 'YYYY-MM-DDTHH:MM:SS'
            phone_number: String phone number
            duration: Integer minutes for appointment duration (default 30)
            
        Returns:
            dict with:
                success: bool
                message: str
                available_slots: List[dict] (if failure)
        """
        # Parse the timestamp (assumed to be in local time)
        start_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
        end_time = start_time + timedelta(minutes=duration)
        # Check if time is within business hours
        if not (DEFAULT_START_HOUR <= start_time.hour < DEFAULT_END_HOUR):
            return {
                'success': False,
                'message': f'Appointments must be between {DEFAULT_START_HOUR}:00 and {DEFAULT_END_HOUR}:00'
            }
        
        # Get existing events for the day
        start_of_day = start_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_time.replace(hour=23, minute=59, second=59, microsecond=999999)
        events_result = self.service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=self._format_datetime_for_google(start_of_day),
            timeMax=self._format_datetime_for_google(end_of_day),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        # Check for conflicts
        for event in events_result.get('items', []):
            if 'dateTime' not in event['start'] or 'dateTime' not in event['end']:
                continue  # Skip all-day events
            event_start = self._strip_timezone(event['start']['dateTime'])
            event_end = self._strip_timezone(event['end']['dateTime'])
            if (start_time < event_end and end_time > event_start):
                # Time slot is taken, get available times
                available_times = self.get_available_times(timestamp, {'bookedEvents': events_result}, duration)
                return {
                    'success': False,
                    'message': 'Time slot is already booked',
                    'otherAvailableTimes': available_times['message'],
                }
        
        # Create the event
        event = {
            'summary': name,
            'description': f'Phone: {phone_number}',
            'start': {
                'dateTime': self._format_datetime_for_google(start_time),
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': self._format_datetime_for_google(end_time),
                'timeZone': 'America/New_York',
            },
        }
        
        self.service.events().insert(
            calendarId=CALENDAR_ID,
            body=event
        ).execute()
        
        return {
            'success': True,
            'message': 'Appointment booked successfully'
        }

    def get_availability(self, duration: int = 30, date: str = None) -> dict:
        """Get all available time slots for a specific date or next available day."""        
        if date:
            date_to_check = datetime.strptime(date, '%Y-%m-%d')
        else:
            est = pytz.timezone('America/New_York')
            now = datetime.now(est).replace(tzinfo=None)
            date_to_check = now
        
        max_days_to_check = 30  # Don't look more than 1 month ahead
        days_checked = 0
        
        while days_checked < max_days_to_check:
            # Get events for the day
            start_of_day = date_to_check.replace(hour=0, minute=0, second=0, microsecond=0)
            print(f"Getting availability for date {start_of_day}")
            end_of_day = date_to_check.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            events_result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=self._format_datetime_for_google(start_of_day),
                timeMax=self._format_datetime_for_google(end_of_day),
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            # Get available times using base platform method
            timestamp = date_to_check.replace(
                hour=DEFAULT_START_HOUR,
                minute=0,
                second=0
            ).strftime('%Y-%m-%dT%H:%M:%S')
            
            availability_object = self.get_available_times(
                timestamp,
                {'bookedEvents': events_result},
                duration
            )

            # If no slots found and no specific date was given, check next day
            date_to_check += timedelta(days=1)
            days_checked += 1

            # If we found available times
            if availability_object['message'] != "No available times found":
                # if requested date has times
                if days_checked == 1:
                    messsage = availability_object['message']
                else:
                    messsage = "Requested date unavailable, but there is availability on: " + availability_object['message']
                return {
                    'success': True,
                    'message': messsage,
                }
            
        
        return {
            'success': False,
            'message': 'No available times found in the next month',
            'slots': []
        }

    def get_customer_appointments(self, phone_number: str) -> dict:
        """
        Get all appointments for a given phone number from Google Calendar.
        
        Args:
            phone_number: String phone number to look up appointments
            
        Returns:
            dict with:
                success: bool
                message: str
                appointments: List[dict] (if success) containing:
                    - start: String time in format 'YYYY-MM-DDTHH:MM:SS'
                    - end: String time in format 'YYYY-MM-DDTHH:MM:SS'
                    - name: String, customer's name
        """
        try:
            # Get events from now onwards
            now = datetime.utcnow()
            
            events_result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=self._format_datetime_for_google(now),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            appointments = []
            message = "The caller has no appointments booked."
            for event in events_result.get('items', []):
                # Check if event description contains the phone number in the specific format
                if 'description' in event and f'Phone: {phone_number}' in event.get('description', ''):
                    # Parse and format the timestamp
                    dt = datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                    formatted_time = dt.strftime('%B %d at %I:%M%p')  # e.g. "March 20 at 9:00AM"
                    appointments.append(formatted_time)

            if appointments:
                message = "The caller has appointments booked for "
                for appointment in appointments:
                    message += f"{appointment}, "
                message = message.rstrip(', ')  # Remove trailing comma and space

            return {
                'success': True,
                'message': message,
                'appointments': message
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error retrieving appointments: {str(e)}',
                'appointments': []
            }

    def cancel_appointment(self, timestamp: str, phone_number: str) -> dict:
        """
        Cancel an appointment at the given time for the given phone number.
        
        Args:
            timestamp: String in format 'YYYY-MM-DDTHH:MM:SS', time of appointment to cancel
            phone_number: String phone number associated with the appointment
            
        Returns:
            dict with:
                success: bool
                message: str
        """
        try:
            # Parse the timestamp
            target_time = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
            
            # Get events for the day
            start_of_day = target_time.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day = target_time.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            events_result = self.service.events().list(
                calendarId=CALENDAR_ID,
                timeMin=self._format_datetime_for_google(start_of_day),
                timeMax=self._format_datetime_for_google(end_of_day),
                singleEvents=True,
                orderBy='startTime'
            ).execute()

            # Find the matching event
            for event in events_result.get('items', []):
                event_start = self._strip_timezone(event['start']['dateTime'])
                
                # Check if this is the right event (matching time and phone number)
                if (event_start == target_time and 
                    'description' in event and 
                    f'Phone: {phone_number}' in event.get('description', '')):
                    
                    # Delete the event
                    self.service.events().delete(
                        calendarId=CALENDAR_ID,
                        eventId=event['id']
                    ).execute()
                    
                    return {
                        'success': True,
                        'message': 'Appointment cancelled successfully'
                    }
            
            return {
                'success': False,
                'message': 'No matching appointment found'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error cancelling appointment: {str(e)}'
            }


    def reschedule_appointment(self, name: str, phone_number: str, old_timestamp: str, new_timestamp: str) -> dict:
        """
        Reschedule an existing appointment to a new time.
        
        Args:
            name: String name for the calendar event
            phone_number: String phone number
            old_timestamp: String in format 'YYYY-MM-DDTHH:MM:SS' of existing appointment
            new_timestamp: String in format 'YYYY-MM-DDTHH:MM:SS' for new appointment time
            
        Returns:
            dict with:
                success: bool
                message: str
        """
        try:
            # First try to book the new appointment
            booking_result = self.book_appointment(
                name=name,
                timestamp=new_timestamp,
                phone_number=phone_number
            )
            
            if not booking_result['success']:
                return booking_result
            
            # If new booking succeeds, cancel the old appointment
            cancel_result = self.cancel_appointment(
                timestamp=old_timestamp,
                phone_number=phone_number
            )
            
            if not cancel_result['success']:
                # If cancellation fails, try to cancel the new appointment to maintain consistency
                self.cancel_appointment(timestamp=new_timestamp, phone_number=phone_number)
                return {
                    'success': False,
                    'message': f"Failed to cancel old appointment: {cancel_result['message']}"
                }
            
            return {
                'success': True,
                'message': 'Appointment rescheduled successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error rescheduling appointment: {str(e)}'
            }

