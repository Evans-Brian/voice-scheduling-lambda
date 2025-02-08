from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
from constants import GOOGLE_CALENDAR_SCOPES

def get_credentials():
    """Gets valid user credentials from storage.
    
    Returns:
        Credentials, the obtained credential.
    """
    # Use /tmp directory for Lambda
    token_path = '/tmp/token.pickle'
    creds = None
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # For local development, fall back to project directory
            creds_file = ('credentials.json' if os.path.exists('credentials.json') 
                         else '/tmp/credentials.json')
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_file, GOOGLE_CALENDAR_SCOPES)
            creds = flow.run_local_server(port=0)
        # Save to /tmp for Lambda
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds 