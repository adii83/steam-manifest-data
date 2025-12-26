import os
import json
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# =========================
# PATH SETUP
# =========================
ROOT = os.path.dirname(os.path.dirname(__file__))
ZIP_DIR = os.path.join(ROOT, "zips")
CONFIG_PATH = os.path.join(ROOT, "config", "gdrive_config.json")
# Service account removed, using token.json
TOKEN_PATH = os.path.join(ROOT, "config", "token.json")

# =========================
# SCOPES & RETRY CONFIG
# =========================
SCOPES = ['https://www.googleapis.com/auth/drive.file']
MAX_RETRIES = 3
RETRY_DELAY = 5

def authenticate():
    """Authenticates using the token.json file."""
    if not os.path.exists(TOKEN_PATH):
        print(f"[ERROR] Token file not found: {TOKEN_PATH}")
        return None
        
    try:
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"[ERROR] Auth failed: {e}")
        return None

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[ERROR] Config file not found: {CONFIG_PATH}")
        return None
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)


def check_file_exists(service, file_name, folder_id):
    """Checks if a file with the same name exists in the folder."""
    query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
    try:
        results = service.files().list(q=query, fields="files(id, name)").execute()
        files = results.get('files', [])
        if files:
            print(f"[SKIP] File {file_name} already exists in Drive (ID: {files[0]['id']})")
            return files[0]['id']
        return None
    except Exception as e:
        print(f"[WARN] Failed to check file existence: {e}")
        return None

def upload_file(service, file_path, folder_id):
    """Uploads a file to Google Drive and returns the file ID."""
    file_name = os.path.basename(file_path)
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    
    media = MediaFileUpload(
        file_path, 
        mimetype='application/zip',
        resumable=True
    )

    print(f"[UPLOAD] Starting upload: {file_name}")
    
    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"[SUCCESS] Uploaded {file_name} (ID: {file.get('id')})")
        return file.get('id')
        
    except Exception as e:
        print(f"[ERROR] Failed to upload {file_name}: {e}")
        with open("last_error.txt", "w") as f_err:
            f_err.write(str(e))
        return None

def main():
    config = load_config()
    if not config:
        return

    folder_id = config.get("gdrive_folder_id")
    if not folder_id or "PASTE_YOUR_GDRIVE_FOLDER_ID_HERE" in folder_id:
        print("[ERROR] Please configure 'gdrive_folder_id' in config/gdrive_config.json")
        exit(1)

    service = authenticate()
    if not service:
        exit(1)

    # Check if zips dir exists
    if not os.path.exists(ZIP_DIR):
        print(f"[INFO] No zips directory found at {ZIP_DIR}")
        return

    files = [f for f in os.listdir(ZIP_DIR) if f.endswith('.zip')]
    
    if not files:
        print("[INFO] No zip files to upload.")
        return

    print(f"[INFO] Found {len(files)} zip files to upload.")

    success_count = 0
    fail_count = 0

    for filename in files:
        file_path = os.path.join(ZIP_DIR, filename)
        
        # Check duplication
        existing_id = check_file_exists(service, filename, folder_id)
        
        if existing_id:
            # File exists, treat as success (for cleanup purposes)
            file_id = existing_id
        else:
            # Upload
            file_id = upload_file(service, file_path, folder_id)
        
        if file_id:
            # Delete local file only if upload successful
            try:
                os.remove(file_path)
                print(f"[CLEANUP] Deleted local file: {filename}")
                success_count += 1
            except Exception as e:
                print(f"[WARN] Failed to delete local file {filename}: {e}")
        else:
            fail_count += 1
            
        # Rate limit prevention
        time.sleep(1)

    print("====================================")
    print(f"[DONE] Upload finished. Success: {success_count}, Failed: {fail_count}")

if __name__ == '__main__':
    main()
