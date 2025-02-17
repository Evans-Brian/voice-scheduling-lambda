from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict
from constants import DEFAULT_START_HOUR, DEFAULT_END_HOUR
import pytz

class BookingPlatform(ABC):
    """Base class for all booking platform integrations"""
    
    def __init__(self):
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
    
    @abstractmethod
    def book_appointment(self, name: str, timestamp: str, phone_number: str, duration: int = 30) -> dict:
        """
        Book appointment on the platform. If booking fails, returns available slots.
        
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
        pass
    
    @abstractmethod
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
                slots: List of available time slots in natural language
        """
        pass
    
    @abstractmethod
    def get_customer_appointments(self, phone_number: str) -> dict:
        """
        Get all appointments for a given phone number.
        
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
        pass
    
    @abstractmethod
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
        pass
    
    def _combine_events(self, slots: List[Dict[str, str]], date: str, duration: int = 30) -> str:
        """
        Combines 4 or more consecutive time slots and returns a natural language description.
        Single slots are shown as start time only, consecutive slots shown as range.
        
        Args:
            slots: List of dicts with 'start' and 'end' times in 'HH:MM' format
            date: String date in format 'YYYY-MM-DD'
            duration: Integer minutes for appointment duration (default 30)
        
        Returns:
            str: Natural language description of available times
        """
        if not slots:
            return "No available times found"
        
        # Format the date
        date_obj = datetime.strptime(date, '%Y-%m-%d')
        # Sort slots by start time
        sorted_slots = sorted(slots, key=lambda x: x['start'])
        

        # Convert time to 12-hour format
        def format_time(time_str: str) -> str:
            """
            Convert 24-hour time string to 12-hour format with minutes when needed.
            Examples:
                "14:30" -> "2:30PM"
                "09:00" -> "9AM"
                "15:45" -> "3:45PM"
                "12:00" -> "12PM"
            """
            time_obj = datetime.strptime(time_str, '%H:%M')
            hour = time_obj.strftime('%I').lstrip('0')  # Remove leading zero
            minutes = time_obj.strftime('%M')
            ampm = time_obj.strftime('%p')
            
            # Only include minutes if they're not zero
            if minutes == '00':
                return f"{hour}{ampm}"
            return f"{hour}:{minutes}{ampm}"
        
        # Group consecutive slots
        groups = []
        current_group = [sorted_slots[0]]
        
        for i in range(1, len(sorted_slots)):
            # Check if current slot starts when previous slot ends
            if sorted_slots[i]['start'] == current_group[-1]['end']:
                current_group.append(sorted_slots[i])
            else:
                groups.append(current_group)
                current_group = [sorted_slots[i]]
        groups.append(current_group)  # Add the last group
        
        # Format each group into a string
        time_strings = []
        for group in groups:
            if len(group) >= 3:
                # For 4 or more consecutive slots, show range
                start = format_time(group[0]['start'])
                # Get the start time of last slot
                end = format_time(group[-1]['start'])
                time_strings.append(f"from {start} to {end}")
            else:
                # For individual or small groups, show each slot's start time
                for slot in group:
                    time_strings.append(format_time(slot['start']))
        
        # Combine all times with commas
        times = ", ".join(time_strings)
        
        # Ternary operator: condition_if_true if condition else condition_if_false
        return times
    
    def get_available_times(self, timestamp: str, booking_result: dict, duration: int = 30) -> dict:
        """
        Find available time slots for a given day when original booking fails.
        
        Args:
            timestamp: String in format 'YYYY-MM-DDTHH:MM:SS'
            booking_result: Dict containing booking attempt result with bookedEvents
            duration: Integer minutes for appointment duration (default 30)
        
        Returns:
            dict with:
                slots: List of available time slots
                date: String date in format 'YYYY-MM-DD'
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
        
        # Get current time in platform's timezone (Eastern)
        now = datetime.now(self.timezone).replace(tzinfo=None)
        today = now.date()
        
        # If requested date is in the past, return early
        print('testt')
        print(requested_date.date())
        print(today)
        if requested_date.date() < today:
            return {
                'message': f"Requested date is before today. Can you please provide a date on or after today?",
                'date': requested_date.strftime('%Y-%m-%d'),
            }
        
        while current_time < end_of_day:
            # Skip slots that are in the past for today
            if requested_date.date() == today and current_time <= now:
                current_time += timedelta(minutes=30)
                continue
                
            slot_end = current_time + timedelta(minutes=duration)
            if slot_end <= end_of_day:
                # Check if this slot overlaps with any booked slots
                candidate_start = current_time.strftime('%H:%M')
                candidate_end = slot_end.strftime('%H:%M')
                slot_is_available = True
                
                for booked_start, booked_end in booked_slots:
                    # Check all possible overlap cases:
                    # 1. Candidate starts during booked slot
                    # 2. Candidate ends during booked slot
                    # 3. Candidate contains booked slot
                    # 4. Booked slot contains candidate
                    if (candidate_start >= booked_start and candidate_start < booked_end) or \
                       (candidate_end > booked_start and candidate_end <= booked_end) or \
                       (candidate_start <= booked_start and candidate_end >= booked_end) or \
                       (booked_start <= candidate_start and booked_end >= candidate_end):
                        slot_is_available = False
                        break
                
                if slot_is_available:
                    available_slots.append({
                        'start': candidate_start,
                        'end': candidate_end
                    })
            
            current_time += timedelta(minutes=30)  # Move to next slot
        
        stripped_date = requested_date.strftime('%Y-%m-%d')
        # Get available slots
        combined_slots = self._combine_events(
            available_slots, 
            stripped_date,
            duration
        )   
        # Convert string date back to datetime for formatting
        date_obj = datetime.strptime(stripped_date, '%Y-%m-%d')
        formatted_date = date_obj.strftime('%A, %B %d')  # e.g. "Monday, March 20"
        availability_found = False
        if available_slots:
            message = f"Available {formatted_date}: {combined_slots}"
            availability_found = True
        else:
            message = f"No available times found on {formatted_date}"
        
        return {
            'message': message,
            'date': requested_date.strftime('%Y-%m-%d'),
            'availability_found': availability_found
        }
    
    def reschedule_appointment(self, name: str, phone_number: str, old_timestamp: str, new_timestamp: str) -> dict:
        """
        Reschedule an existing appointment to a new time.
        
        Args:
            name: String, customer's name
            phone_number: String, customer's phone number
            old_timestamp: String in format 'YYYY-MM-DDTHH:MM:SS', current appointment time
            new_timestamp: String in format 'YYYY-MM-DDTHH:MM:SS', desired new appointment time
            
        Returns:
            dict with:
                success: bool
                message: str
                available_slots: List (if new time unavailable), alternative available time slots
        """
        # First try to book the new appointment
        booking_result = self.book_appointment(
            name=name + " (Rescheduled)",
            timestamp=new_timestamp,
            phone_number=phone_number
        )
        
        # If booking succeeded, cancel the old appointment
        if booking_result['success']:
            cancel_result = self.cancel_appointment(
                timestamp=old_timestamp,
                phone_number=phone_number
            )
            
            # If cancellation failed, we need to cancel the new booking
            if not cancel_result['success']:
                # Try to cancel the new booking
                self.cancel_appointment(
                    timestamp=new_timestamp,
                    phone_number=phone_number
                )
                return {
                    'success': False,
                    'message': f"Failed to cancel old appointment: {cancel_result['message']}"
                }
            
            # Both operations succeeded
            return {
                'success': True,
                'message': 'Appointment rescheduled successfully'
            }
        
        # If booking failed, return the failure result (which includes available slots)
        return booking_result 