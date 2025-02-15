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
    """Generate new token with offline access."""
    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json',
        GOOGLE_CALENDAR_SCOPES
    )
    
    # Run local server with offline access and consent parameters
    creds = flow.run_local_server(
        port=0,
        access_type='offline',  # Enable offline access
        prompt='consent'  # Force consent screen to get refresh token
    )
    
    # Save the credentials
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)

if __name__ == '__main__':
    regenerate_token()