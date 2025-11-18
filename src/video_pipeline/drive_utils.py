# import os
# import io
# from datetime import datetime
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaIoBaseUpload
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.oauth2.credentials import Credentials
# from google.oauth2 import service_account
# from google.auth.transport.requests import Request
# from logger import pipeline_logger
# from pathlib import Path


# SCOPES = ["https://www.googleapis.com/auth/drive.file"]


# def get_drive_service(auth_mode: str, credentials_path: str, token_path: str = None):
#     """Authenticate Google Drive client using OAuth token or service account."""
#     creds = None
#     try:
#         if auth_mode == "token":
#             if token_path and os.path.exists(token_path):
#                 creds = Credentials.from_authorized_user_file(token_path, SCOPES)

#             if not creds or not creds.valid:
#                 if creds and creds.expired and creds.refresh_token:
#                     creds.refresh(Request())
#                     pipeline_logger.info("🔄 Google Drive token refreshed.")
#                 else:
#                     pipeline_logger.info("🌐 Starting new OAuth flow...")
#                     flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
#                     creds = flow.run_local_server(port=0)
#                 if token_path:
#                     os.makedirs(os.path.dirname(token_path), exist_ok=True)
#                     with open(token_path, "w") as token_file:
#                         token_file.write(creds.to_json())
#                     pipeline_logger.info(f"💾 Token saved at {token_path}")

#         elif auth_mode == "service":
#             creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
#         else:
#             raise ValueError("Unsupported auth_mode. Use 'token' or 'service'.")

#         pipeline_logger.info("✅ Google Drive authentication successful.")
#         return build("drive", "v3", credentials=creds)

#     except Exception as e:
#         pipeline_logger.exception("❌ Google Drive authentication failed.")
#         raise


# def find_or_create_folder(service, name, parent_id=None):
#     """Find or create folder in Drive."""
#     query = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
#     if parent_id:
#         query += f" and '{parent_id}' in parents"

#     results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
#     folders = results.get("files", [])
#     if folders:
#         return folders[0]["id"]

#     metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
#     if parent_id:
#         metadata["parents"] = [parent_id]

#     folder = service.files().create(body=metadata, fields="id").execute()
#     pipeline_logger.info(f"📁 Created Drive folder: {name}")
#     return folder["id"]


# def upload_folder_to_drive(folder_path: str, drive_credentials: str, token_path: str, auth_mode: str = "token"):
#     """Upload an entire folder (recursively) to Google Drive."""
#     pipeline_logger.info(f"🔍 [Drive Upload Debug] Entered upload_folder_to_drive() with folder_path={folder_path}")

#     if not folder_path or not Path(folder_path).exists():
#         pipeline_logger.error(f"❌ Invalid TRANSACTION_FOLDER: {folder_path}")
#         return


#     try:

#         pipeline_logger.info(f"🚀 Starting Drive upload for folder: {folder_path}")


#         if not os.path.exists(folder_path):
#             raise FileNotFoundError(f"Folder not found: {folder_path}")

#         service = get_drive_service(auth_mode, drive_credentials, token_path)

#         # Root-level folder (example: "Video_Data" on Drive)
#         root_folder_id = find_or_create_folder(service, "Video_Data")

#         # Folder name on Drive (same as local)
#         folder_name = os.path.basename(folder_path.rstrip("\\/"))
#         session_folder_id = find_or_create_folder(service, folder_name, root_folder_id)

#         # Recursively upload all files
#         for root, dirs, files in os.walk(folder_path):
#             rel_path = os.path.relpath(root, folder_path)
#             current_parent_id = session_folder_id

#             if rel_path != ".":
#                 # nested folder structure inside Drive
#                 for part in rel_path.split(os.sep):
#                     current_parent_id = find_or_create_folder(service, part, current_parent_id)

#             for file_name in files:
#                 file_path = os.path.join(root, file_name)
#                 mime_type = "application/octet-stream"
#                 if file_name.endswith(".json"):
#                     mime_type = "application/json"
#                 elif file_name.endswith(".mp4"):
#                     mime_type = "video/mp4"
#                 elif file_name.endswith(".txt") or file_name.endswith(".py"):
#                     mime_type = "text/plain"

#                 with open(file_path, "rb") as f:
#                     file_bytes = io.BytesIO(f.read())
#                 media = MediaIoBaseUpload(file_bytes, mimetype=mime_type)
#                 file_metadata = {"name": file_name, "parents": [current_parent_id]}

#                 uploaded = service.files().create(
#                     body=file_metadata,
#                     media_body=media,
#                     fields="id, name, webViewLink"
#                 ).execute()

#                 pipeline_logger.info(f"✅ Uploaded '{file_name}' → {uploaded['webViewLink']}")

#         pipeline_logger.info(f"🎉 All contents from '{folder_path}' uploaded successfully.")
#         return {"status": "success", "uploaded_folder": folder_name}

#     except Exception as e:
#         pipeline_logger.exception("❌ Folder upload failed.")
#         raise

# video_pipeline/drive_utils.py
import os
import io
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
from logger import pipeline_logger
from config import Settings

SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]


# --------------------
# Authentication
# --------------------
def get_drive_service(auth_mode: str):
    """
    Returns an authenticated googleapiclient service
    auth_mode: "token" or "service"
    Credentials and token paths are read from Settings.
    """
    creds = None
    try:
        if auth_mode == "token":
            credentials_path = str(Settings.DRIVE_CREDENTIALS_PATH)
            token_path = str(Settings.TOKEN_PATH) if Settings.TOKEN_PATH else None

            if token_path and os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    pipeline_logger.info("🔄 Google Drive token refreshed.")
                else:
                    pipeline_logger.info("🌐 Starting local OAuth flow for Drive token...")
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                if token_path:
                    os.makedirs(os.path.dirname(token_path), exist_ok=True)
                    with open(token_path, "w") as f:
                        f.write(creds.to_json())
                    pipeline_logger.info(f"💾 Token saved at {token_path}")

        elif auth_mode == "service":
            service_account_path = str(Settings.SERVICE_ACCOUNT_PATH)
            creds = service_account.Credentials.from_service_account_file(service_account_path, scopes=SCOPES)

        else:
            raise ValueError("Unsupported auth_mode. Use 'token' or 'service'.")

        pipeline_logger.info(f"✅ Drive auth successful (mode={auth_mode})")
        return build("drive", "v3", credentials=creds)

    except Exception:
        pipeline_logger.exception("❌ Drive authentication failed.")
        raise


# --------------------
# Token-mode helpers (search/create)
# --------------------
def find_or_create_folder(service, name, parent_id=None):
    """
    Find a folder by name under parent_id; if not found, create it.
    Only used for token (user OAuth) mode.
    """
    try:
        q = f"name='{name}' and mimeType='application/vnd.google-apps.folder'"
        if parent_id:
            q += f" and '{parent_id}' in parents"

        res = service.files().list(q=q, spaces="drive", fields="files(id, name)").execute()
        folders = res.get("files", [])
        if folders:
            return folders[0]["id"]

        metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
        if parent_id:
            metadata["parents"] = [parent_id]

        folder = service.files().create(body=metadata, fields="id").execute()
        pipeline_logger.info(f"📁 Created folder (token-mode): {name}")
        return folder["id"]

    except Exception:
        pipeline_logger.exception("❌ find_or_create_folder failed.")
        raise


# --------------------
# Service-mode helper (create subfolder directly under known parent)
# --------------------
def create_subfolder_under_parent(service, subfolder_name: str, parent_id: str):
    """
    Create a folder named subfolder_name directly under parent_id.
    For service mode we DO NOT search; we create the subfolder (as requested).
    Returns created folder id and webViewLink.
    """
    try:
        metadata = {
            "name": subfolder_name,
            "mimeType": "application/vnd.google-apps.folder",
            "parents": [parent_id],
        }
        folder = service.files().create(body=metadata, fields="id, webViewLink", supportsAllDrives=True).execute()
        fid = folder.get("id")
        link = folder.get("webViewLink")
        pipeline_logger.info(f"📁 Created Drive subfolder '{subfolder_name}' under parent {parent_id} -> id={fid}")
        return fid, link
    except HttpError as e:
        pipeline_logger.exception(f"❌ create_subfolder_under_parent failed: {e}")
        raise


# --------------------
# Main function
# --------------------
def upload_folder_to_drive(folder_path: str, auth_mode: str = None):
    print("drive started")
    print("drive_folder_path",folder_path)
    """
    Upload a local folder recursively to Drive.

    Behavior:
    - token mode: replicate the local folder under Drive root 'Video_Data' (find/create folders).
    - service mode: create a single subfolder under Settings.DRIVE_FOLDER_ID
                   using the local transaction folder name, then replicate the entire
                   local hierarchy inside that subfolder. (No searching of other Drive
                   folders; only create subfolders beneath the given parent.)
    """
    pipeline_logger.info(f"🔍 upload_folder_to_drive called with: {folder_path}")

    if not folder_path or not Path(folder_path).exists():
        pipeline_logger.error(f"❌ Invalid folder_path: {folder_path}")
        return {"status": "error", "reason": "folder_not_found"}

    auth_mode = auth_mode or Settings.DRIVE_AUTH_MODE
    service = get_drive_service(auth_mode)
    local_root = Path(folder_path)
    session_name = local_root.name

    try:
        if auth_mode == "service":
            parent_id = Settings.DRIVE_FOLDER_ID
            if not parent_id:
                raise ValueError("DRIVE_FOLDER_ID is not set in Settings for service mode.")

            pipeline_logger.info(f"📁 Service-mode: uploading '{session_name}' under Drive parent ID {parent_id}")

            # create subfolder under the provided parent (no searching)
            session_folder_id, session_folder_link = create_subfolder_under_parent(service, session_name, parent_id)

            # We'll map local path -> created drive folder id for recursion
            folder_id_map = {str(local_root): session_folder_id}

            # Walk local directory, create subfolders under session_folder_id, upload files
            for root, dirs, files in os.walk(str(local_root)):

                dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]

                root = str(root)
                current_parent_id = folder_id_map[root]

                # create subfolders for this level
                for d in dirs:
                    local_sub = os.path.join(root, d)
                    # create subfolder under current_parent_id
                    sub_id, _ = create_subfolder_under_parent(service, d, current_parent_id)
                    folder_id_map[local_sub] = sub_id

                # upload files in this root
                for filename in files:
                    local_file = os.path.join(root, filename)
                    mime_type = (
                        "application/json" if filename.endswith(".json")
                        else "video/mp4" if filename.endswith(".mp4")
                        else "text/plain" if filename.endswith((".txt", ".py"))
                        else "application/octet-stream"
                    )
                    with open(local_file, "rb") as f:
                        file_bytes = io.BytesIO(f.read())
                    media = MediaIoBaseUpload(file_bytes, mimetype=mime_type)
                    metadata = {"name": filename, "parents": [current_parent_id]}
                    uploaded = service.files().create(
                        body=metadata,
                        media_body=media,
                        fields="id, name, webViewLink",
                        supportsAllDrives=True
                    ).execute()
                    pipeline_logger.info(f"✅ Uploaded (service): {filename} → {uploaded.get('webViewLink')}")

            pipeline_logger.info(f"🎉 Service-mode upload complete. Session folder link: {session_folder_link}")
            return {"status": "success", "uploaded_folder": session_name, "drive_folder_id": session_folder_id, "drive_link": session_folder_link}

        else:
            # token mode: create/find Video_Data then create/find session folder and mirror structure
            pipeline_logger.info("📁 Token-mode upload (creating/finding folders under 'Video_Data').")
            root_folder_id = find_or_create_folder(service, "Video_Data")
            session_folder_id = find_or_create_folder(service, session_name, root_folder_id)

            # map local path to drive folder id
            folder_id_map = {str(local_root): session_folder_id}

            for root, dirs, files in os.walk(str(local_root)):
                root = str(root)
                current_parent_id = folder_id_map[root]

                # find/create subfolders by name (token mode)
                for d in dirs:
                    local_sub = os.path.join(root, d)
                    sub_id = find_or_create_folder(service, d, current_parent_id)
                    folder_id_map[local_sub] = sub_id

                # upload files
                for filename in files:
                    local_file = os.path.join(root, filename)
                    mime_type = (
                        "application/json" if filename.endswith(".json")
                        else "video/mp4" if filename.endswith(".mp4")
                        else "text/plain" if filename.endswith((".txt", ".py"))
                        else "application/octet-stream"
                    )
                    with open(local_file, "rb") as f:
                        file_bytes = io.BytesIO(f.read())
                    media = MediaIoBaseUpload(file_bytes, mimetype=mime_type)
                    metadata = {"name": filename, "parents": [current_parent_id]}
                    uploaded = service.files().create(
                        body=metadata,
                        media_body=media,
                        fields="id, name, webViewLink"
                    ).execute()
                    pipeline_logger.info(f"✅ Uploaded (token): {filename} → {uploaded.get('webViewLink')}")

            pipeline_logger.info(f"🎉 Token-mode upload complete. Session folder id: {session_folder_id}")
            print("drive completed")
            return {"status": "success", "uploaded_folder": session_name, "drive_folder_id": session_folder_id}

    except Exception:
        pipeline_logger.exception("❌ Folder upload failed.")
        raise


