from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List, Dict
from constants import DEFAULT_START_HOUR, DEFAULT_END_HOUR

class BookingPlatform(ABC):
    """Base class for all booking platform integrations"""
    
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
                date: str (if failure) in format 'YYYY-MM-DD'
        """
        pass
    
    @abstractmethod
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
                slots: List of available time slots (if success)
                    Each slot has:
                        start: String time in format 'HH:MM'
                        end: String time in format 'HH:MM'
                date: String date in format 'YYYY-MM-DD' (if success)
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
    
    def _combine_events(self, slots: List[Dict[str, str]], duration: int = 30) -> List[Dict[str, str]]:
        """
        Combines 4 or more consecutive time slots into single slots.
        Subtracts duration from end time of combined slots.
        
        Args:
            slots: List of dicts with 'start' and 'end' times in 'HH:MM' format
            duration: Integer minutes for appointment duration (default 30)
        
        Returns:
            list: Combined time slots with adjusted end times
        """
        if not slots:
            return []
        
        # Sort slots by start time
        sorted_slots = sorted(slots, key=lambda x: x['start'])
        
        combined_slots = []
        current_group = [sorted_slots[0]]
        
        for i in range(1, len(sorted_slots)):
            # Check if current slot starts when previous slot ends
            if sorted_slots[i]['start'] == current_group[-1]['end']:
                current_group.append(sorted_slots[i])
            else:
                # Process the current group if it exists
                if len(current_group) >= 4:
                    # Calculate end time minus duration
                    end_time = datetime.strptime(current_group[-1]['end'], '%H:%M')
                    adjusted_end = (end_time - timedelta(minutes=duration)).strftime('%H:%M')
                    
                    combined_slots.append({
                        'start': current_group[0]['start'],
                        'end': adjusted_end
                    })
                else:
                    combined_slots.extend(current_group)
                current_group = [sorted_slots[i]]
        
        # Process the last group
        if len(current_group) >= 4:
            # Calculate end time minus duration
            end_time = datetime.strptime(current_group[-1]['end'], '%H:%M')
            adjusted_end = (end_time - timedelta(minutes=duration)).strftime('%H:%M')
            
            combined_slots.append({
                'start': current_group[0]['start'],
                'end': adjusted_end
            })
        else:
            combined_slots.extend(current_group)
        
        return combined_slots
    
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
                    start = datetime.strptime(event['start']['dateTime'].replace('-05:00', ''), '%Y-%m-%dT%H:%M:%S')
                    end = datetime.strptime(event['end']['dateTime'].replace('-05:00', ''), '%Y-%m-%dT%H:%M:%S')
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
                # Check if this slot overlaps with any booked slots
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
            
            current_time += timedelta(minutes=30)  # Move to next slot
        
        # Combine consecutive slots
        combined_slots = self._combine_events(available_slots, duration)
        
        return {
            'slots': combined_slots,
            'date': requested_date.strftime('%Y-%m-%d')
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