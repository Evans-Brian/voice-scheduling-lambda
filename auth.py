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
    creds = None
    token_path = 'token.pickle'
    
    # If running in Lambda, use /tmp directory
    if os.getenv('AWS_LAMBDA_FUNCTION_NAME'):
        token_path = '/tmp/token.pickle'
        # Copy token.pickle to /tmp if it exists in the package
        if os.path.exists('token.pickle') and not os.path.exists(token_path):
            with open('token.pickle', 'rb') as src, open(token_path, 'wb') as dst:
                dst.write(src.read())
    
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Save the refreshed credentials
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', GOOGLE_CALENDAR_SCOPES)
            creds = flow.run_local_server(port=0)
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
    
    return creds 