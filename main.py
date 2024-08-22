import os
import logging
import io
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from config import SCOPES, UPLOAD_FILES_URL, PROCESS_FILES_URL, UPLOADED_FILE_PATH, FAILED_FILE_PATH, UNSUPPORTED_FILE_PATH, SAVE_LOG_FILE
from helpers import call_catalog_api, get_file_type, process_file_data, get_current_time_formatted, save_modified_time_to_file, read_modified_time_from_file, append_file_id, load_uploaded_files

# Set up logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"app_time_{timestamp}.log"
handlers = [logging.FileHandler(log_filename), logging.StreamHandler()] if SAVE_LOG_FILE else [logging.StreamHandler()]
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)


def main():
    """
    Main function to synchronize files from Google Drive to Instill Catalog.

    Authenticates with Google Drive, lists modified files, processes them,
    and uploads them to Instill Catalog. Handles errors and logging.
    """
    creds = None

    # Load existing credentials or initiate the OAuth flow
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)
        query_modified_time = read_modified_time_from_file()

        if not query_modified_time:
            query_modified_time = get_current_time_formatted()
            save_modified_time_to_file(query_modified_time)

        results = (
            service.files()
            .list(
                fields="nextPageToken, files(id, name, modifiedTime)",
                q=f"modifiedTime >= '{query_modified_time}'",
            )
            .execute()
        )
        items = results.get("files", [])

        if not items:
            logging.info("No files found.")
            return

        for item in items:
            try:
                logging.info(f"=== Processing file: {item['name']} ===")

                file_id = item['id']

                if file_id in load_uploaded_files(UPLOADED_FILE_PATH):
                    logging.info(f"File '{item['name']}' with ID '{file_id}' has already been uploaded.")
                    continue

                file_metadata = service.files().get(fileId=file_id, fields='mimeType, name').execute()
                mime_type = file_metadata['mimeType']
                file_name = file_metadata['name']
                local_file_name = f'{file_name}.pdf' if mime_type.startswith('application/vnd.google-apps.') else file_name

                if mime_type == "application/vnd.google-apps.folder":
                    logging.info(f"File '{file_name}' with ID '{file_id}' is a folder and will not be processed.")
                    continue

                if mime_type.startswith('application/vnd.google-apps.'):
                    # Export Google Docs Editors files
                    mime_type = 'application/pdf'  # Example export format
                    request = service.files().export_media(fileId=file_id, mimeType=mime_type)
                else:
                    # Download other file types directly
                    request = service.files().get_media(fileId=file_id)

                file_type = get_file_type(mime_type)
                if file_type == "none":
                    logging.info(f"File name: '{file_name}' with file type '{mime_type}' is not supported in Catalog.")
                    append_file_id(file_id, UNSUPPORTED_FILE_PATH)
                    continue

                # Create a file stream to write the downloaded content
                with io.FileIO(local_file_name, 'wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request)
                    done = False
                    while not done:
                        status, done = downloader.next_chunk()

                file_data = process_file_data(local_file_name, file_type)

                uploaded_file = call_catalog_api(UPLOAD_FILES_URL, 'POST', file_data, 'Upload Files')
                file_uid = uploaded_file.get("file", {}).get("fileUid", None)

                if not file_uid:
                    logging.warning("API failure: ", uploaded_file)
                    logging.warning(f"Failed to upload file '{file_name}' with ID '{file_id}'.")
                    append_file_id(file_id, FAILED_FILE_PATH)
                    os.remove(local_file_name)
                    continue

                process_data = call_catalog_api(PROCESS_FILES_URL, 'POST', {"fileUids": [file_uid]}, 'Process Files')
                process_status = process_data.get("files", [{}])[0].get("processStatus", None)

                if not process_status:
                    logging.warning(f"Failed to process file '{file_name}' with ID '{file_id}'.")
                    append_file_id(file_id, FAILED_FILE_PATH)
                    os.remove(local_file_name)
                    continue

                os.remove(local_file_name)
                append_file_id(file_id, UPLOADED_FILE_PATH)

            except Exception as error:
                logging.warning(f"Failed to download file '{file_name}' with ID '{file_id}'.")
                logging.warning(error)
                if os.path.exists(local_file_name):
                    os.remove(local_file_name)
                continue

    except Exception as error:
        logging.warning(error)
        # Retry on failure
        main()


if __name__ == "__main__":
    main()
    # Update the modified_time in the file
    modified_time = get_current_time_formatted()
    # TODO: Uncomment in production
    # save_modified_time_to_file(modified_time)
