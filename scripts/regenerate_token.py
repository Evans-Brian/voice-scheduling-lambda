import sys
import os
# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import pickle
from constants import GOOGLE_CALENDAR_SCOPES

def regenerate_token():
    """
    Get or refresh Google Calendar credentials.
    Will only request new credentials if:
    1. No token exists
    2. Token exists but is invalid and can't be refreshed
    """
    creds = None
    token_path = 'token.pickle'
    
    # If token exists but is expired/invalid, delete it
    if os.path.exists(token_path):
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            if not creds.valid and creds.expired:
                print("Token expired and can't be refreshed, deleting old token...")
                os.remove(token_path)
                creds = None
        except Exception as e:
            print(f"Error with existing token, deleting: {e}")
            os.remove(token_path)
            creds = None
    
    # If no valid credentials available, request new ones
    if not creds or not creds.valid:
        print("Requesting new credentials...")
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', 
            GOOGLE_CALENDAR_SCOPES,
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        
        # Request offline access for refresh token
        creds = flow.run_local_server(
            port=0,
            access_type='offline',
            prompt='consent'  # Force consent screen to get refresh token
        )
        
        # Save the credentials
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
        print("Successfully generated new token")
    else:
        print("Token is still valid")

if __name__ == '__main__':
    regenerate_token()