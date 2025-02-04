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
    def __init__(self):
        """Initialize the Google Calendar service"""
        credentials = get_credentials()
        self.service = build('calendar', 'v3', credentials=credentials)
        self.timezone = pytz.timezone('America/New_York')  # EST/EDT timezone

    def _strip_timezone(self, dt_str: str) -> datetime:
        """Helper method to convert datetime string to naive datetime object in local time"""
        # Parse the UTC time
        dt_str = dt_str.replace('Z', '+00:00')
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
                event_id: str (if success)
                event_link: str (if success)
                available_slots: List[dict] (if failure)
                date: str (if failure) in format 'YYYY-MM-DD'
        """
        try:
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
                        'available_slots': available_times['slots'],
                        'date': available_times['date']
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
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error booking appointment: {str(e)}'
            }

    def get_availability(self, duration: int = 30, date: str = None) -> dict:
        """
        Get all available time slots for a specific date or the next available day.
        If date is not provided, will find the next day with available slots.
        
        Args:
            duration: Integer minutes for appointment duration (default 30)
            date: Optional string date in format 'YYYY-MM-DD'
                 If None, will find next available day
        
        Returns:
            dict with:
                success: bool
                message: str
                slots: List of available time slots (if success)
                    Each slot has:
                        start: String time in format 'HH:MM'
                        end: String time in format 'HH:MM'
                date: String date in format 'YYYY-MM-DD' (if success)
        """
        try:
            if date:
                # Use provided date
                check_date = datetime.strptime(date, '%Y-%m-%d')
            else:
                # Start with tomorrow
                check_date = datetime.now() + timedelta(days=1)
            
            max_days_to_check = 14  # Don't look more than 2 weeks ahead
            days_checked = 0
            
            while days_checked < max_days_to_check:
                # Get events for the day
                start_of_day = check_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end_of_day = check_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                events_result = self.service.events().list(
                    calendarId=CALENDAR_ID,
                    timeMin=self._format_datetime_for_google(start_of_day),
                    timeMax=self._format_datetime_for_google(end_of_day),
                    singleEvents=True,
                    orderBy='startTime'
                ).execute()
                
                # Get available times using base platform method
                timestamp = check_date.replace(
                    hour=DEFAULT_START_HOUR,
                    minute=0,
                    second=0
                ).strftime('%Y-%m-%dT%H:%M:%S')
                
                available_times = self.get_available_times(
                    timestamp,
                    {'bookedEvents': events_result},
                    duration
                )
                
                # If we found available slots or we were given a specific date, return the result
                if available_times['slots'] or date:
                    return {
                        'success': True,
                        'message': 'Available slots found',
                        'slots': available_times['slots'],
                        'date': available_times['date']
                    }
                
                # If no slots found and no specific date was given, check next day
                check_date += timedelta(days=1)
                days_checked += 1
            
            return {
                'success': False,
                'message': 'No available slots found in the next two weeks',
                'slots': [],
                'date': None
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting available slots: {str(e)}',
                'slots': [],
                'date': None
            }

    def get_next_availability(self, timestamp: str, duration: int = 30) -> dict:
        """
        Get all available time slots for the next available day, starting from the given timestamp.
        
        Args:
            timestamp: String in format 'YYYY-MM-DDTHH:MM:SS'
            duration: Integer minutes for appointment duration (default 30)
        
        Returns:
            dict with:
                success: bool
                message: str
                slots: List of available time slots (if success)
                    Each slot has:
                        start: String time in format 'HH:MM'
                        end: String time in format 'HH:MM'
                date: String date in format 'YYYY-MM-DD' (if success)
        """
        try:
            # Parse the timestamp to get the date
            start_date = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
            date_str = start_date.strftime('%Y-%m-%d')
            
            # Use the existing get_availability method
            return self.get_availability(duration=duration, date=date_str)
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting next availability: {str(e)}',
                'slots': [],
                'date': None
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
            for event in events_result.get('items', []):
                # Check if event description contains the phone number in the specific format
                if 'description' in event and f'Phone: {phone_number}' in event.get('description', ''):
                    appointments.append({
                        'start': event['start']['dateTime'].replace('Z', ''),
                        'end': event['end']['dateTime'].replace('Z', ''),
                        'name': event.get('summary', '')
                    })

            return {
                'success': True,
                'message': 'Appointments retrieved successfully',
                'appointments': appointments
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

    def get_available_times(self, timestamp: str, booking_result: dict, duration: int = 30) -> dict:
        """
        Find available time slots for a given day when original booking fails.
        """
        # Parse the requested date from timestamp
        requested_date = datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S')
        
        # Get all booked slots for the day
        booked_slots = []
        if booking_result.get('bookedEvents') and booking_result['bookedEvents'].get('items'):
            for event in booking_result['bookedEvents']['items']:
                if 'dateTime' in event['start']:  # Skip all-day events
                    start = self._strip_timezone(event['start']['dateTime'])
                    end = self._strip_timezone(event['end']['dateTime'])
                    booked_slots.append((start.strftime('%H:%M'), end.strftime('%H:%M')))
        
        # Generate all possible time slots between business hours
        available_slots = []
        current_time = requested_date.replace(
            hour=DEFAULT_START_HOUR, 
            minute=0, 
            second=0, 
            microsecond=0
        )
        end_of_day = requested_date.replace(
            hour=DEFAULT_END_HOUR, 
            minute=0, 
            second=0, 
            microsecond=0
        )
        
        while current_time < end_of_day:
            slot_end = current_time + timedelta(minutes=duration)
            if slot_end <= end_of_day:
                slot_start = current_time.strftime('%H:%M')
                slot_end_str = slot_end.strftime('%H:%M')
                slot_is_available = True
                
                for booked_start, booked_end in booked_slots:
                    if (slot_start >= booked_start and slot_start < booked_end) or \
                       (slot_end_str > booked_start and slot_end_str <= booked_end):
                        slot_is_available = False
                        break
                
                if slot_is_available:
                    available_slots.append({
                        'start': slot_start,
                        'end': slot_end_str
                    })
            
            current_time += timedelta(minutes=30)
        
        return {
            'slots': self._combine_events(available_slots, duration),
            'date': requested_date.strftime('%Y-%m-%d')
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