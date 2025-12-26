from google_auth_oauthlib.flow import InstalledAppFlow
import os
import json

SCOPES = ['https://www.googleapis.com/auth/drive.file']
ROOT = os.path.dirname(os.path.dirname(__file__))
CREDENTIALS_PATH = os.path.join(ROOT, "config", "credentials.json") # Rename/Download your OAuth 2.0 Client ID json to this
TOKEN_PATH = os.path.join(ROOT, "config", "token.json")

def main():
    if not os.path.exists(CREDENTIALS_PATH):
        print(f"[ERROR] Please download your OAuth 2.0 Client ID JSON and save it as: {CREDENTIALS_PATH}")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        CREDENTIALS_PATH, SCOPES
    )
    creds = flow.run_local_server(port=0)
    
    # Save the credentials for the next run
    with open(TOKEN_PATH, 'w') as token:
        token.write(creds.to_json())
        
    print(f"[SUCCESS] Token saved to: {TOKEN_PATH}")
    print("Now copy the CONTENT of this token.json to your GitHub Secret as 'GDRIVE_TOKEN'.")

if __name__ == '__main__':
    main()
