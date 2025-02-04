# constants.py

# Calendar Settings
CALENDAR_ID = 'fb2a6f4673e36a5dbba5c1540d3ad0ae5c9860cd891e53bb277dbab29bbc6b84@group.calendar.google.com'  
# Use 'primary' for the user's primary calendar
# Or replace with specific calendar ID

# Time Settings
DEFAULT_START_HOUR = 9  # 9 AM
DEFAULT_END_HOUR = 17   # 5 PM

# API Scopes
GOOGLE_CALENDAR_SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

# File Paths
CREDENTIALS_FILE = 'credentials.json'