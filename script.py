import os
import logging
import io
import json
import base64
from datetime import datetime
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Configuration
namespace_id = "george_strong"
token = os.environ.get("INSTILL_API_TOKEN")
kbID = "google-test"
save_log_file = False

domain = "api.instill.tech"
list_files_url = f"https://{domain}/v1alpha/namespaces/{namespace_id}/catalogs/{kbID}/files"
upload_files_url = f"https://{domain}/v1alpha/namespaces/{namespace_id}/catalogs/{kbID}/files"
process_files_url = f"https://{domain}/v1alpha/catalogs/files/processAsync"

# Set up logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"app_time_{timestamp}.log"
handlers = [logging.FileHandler(log_filename), logging.StreamHandler()] if save_log_file else [logging.StreamHandler()]
logging.basicConfig(
    level=logging.INFO,  # Set the logging level
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=handlers
)

# OAuth Scopes
SCOPES = ["https://www.googleapis.com/auth/drive"]


def call_catalog_api(url, method, data=None, name=""):
    """
    Call the Instill Catalog API.

    Args:
        url (str): The URL of the API endpoint.
        method (str): The HTTP method to use ('GET', 'POST', 'PUT', 'DELETE').
        data (dict, optional): The data to send with the request.
        name (str, optional): The name of the API call for logging purposes.

    Returns:
        dict: The JSON response from the API.
    """
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }

    if method == 'GET':
        response = requests.get(url, headers=headers)
    elif method == 'POST':
        response = requests.post(url, headers=headers, json=data)
    elif method == 'PUT':
        response = requests.put(url, headers=headers, json=data)
    elif method == 'DELETE':
        response = requests.delete(url, headers=headers)

    response_json = response.json()
    return response_json


def get_file_type(mime_type):
    """
    Get the file type based on the MIME type.

    Args:
        mime_type (str): The MIME type of the file.

    Returns:
        str: The corresponding file type or 'none' if unsupported.
    """
    mime_type_to_file_type = {
        "application/pdf": "FILE_TYPE_PDF",
        "text/plain": "FILE_TYPE_TEXT",
        "text/markdown": "FILE_TYPE_MARKDOWN",
        "image/png": "FILE_TYPE_PNG",
        "image/jpeg": "FILE_TYPE_JPEG",
        "image/jpg": "FILE_TYPE_JPG",
        "text/html": "FILE_TYPE_HTML",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "FILE_TYPE_DOCX",
        "application/msword": "FILE_TYPE_DOC",
        "application/vnd.ms-powerpoint": "FILE_TYPE_PPT",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "FILE_TYPE_PPTX",
        "application/vnd.ms-excel": "FILE_TYPE_XLS",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "FILE_TYPE_XLSX",
    }
    return mime_type_to_file_type.get(mime_type, "none")


def process_file_data(file_path, file_type):
    """
    Process file data for upload.

    Args:
        file_path (str): The path to the file.
        file_type (str): The type of the file.

    Returns:
        dict: The file data in a format suitable for uploading.
    """
    with open(file_path, "rb") as file:
        base64_file = base64.b64encode(file.read())

    data = {
        "name": file_path,
        "type": file_type,
        "content": base64_file.decode('utf-8')
    }
    return data


time_file_path = 'modified_time.txt'


def get_current_time_formatted():
    """
    Get the current time formatted as an ISO 8601 string.

    Returns:
        str: The current time in ISO 8601 format.
    """
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def save_modified_time_to_file(modified_time):
    """
    Save the modified time to a file.

    Args:
        modified_time (str): The time to save.
    """
    with open(time_file_path, 'w') as file:
        file.write(modified_time)


def read_modified_time_from_file():
    """
    Read the modified time from a file if it exists.

    Returns:
        str or None: The modified time read from the file, or None if the file does not exist.
    """
    if os.path.exists(time_file_path):
        with open(time_file_path, 'r') as file:
            return file.read().strip()
    return None


uploaded_file_path = 'uploaded_files.json'
failed_file_path = 'failure_files.json'
unsupported_file_path = 'unsupported_type_files.json'


def load_uploaded_files(file_path):
    """
    Load the list of uploaded file IDs from a local file.

    Args:
        file_path (str): The path to the file containing the list of uploaded file IDs.

    Returns:
        list: A list of uploaded file IDs.
    """
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get("data", [])
    return []


def save_uploaded_files(uploaded_files, file_path):
    """
    Save the list of uploaded file IDs to a local file.

    Args:
        uploaded_files (list): A list of uploaded file IDs.
        file_path (str): The path to the file to save the list.
    """
    with open(file_path, 'w') as file:
        json.dump({"data": uploaded_files}, file, indent=4)


def append_file_id(file_id, file_path):
    """
    Append a new file ID to the list and save it.

    Args:
        file_id (str): The file ID to append.
        file_path (str): The path to the file containing the list of file IDs.
    """
    uploaded_files = load_uploaded_files(file_path)

    if file_id not in uploaded_files:  # Avoid duplicates
        uploaded_files.append(file_id)

    save_uploaded_files(uploaded_files, file_path)


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

                if file_id in load_uploaded_files(uploaded_file_path):
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
                    append_file_id(file_id, unsupported_file_path)
                    continue

                # Create a file stream to write the downloaded content
                with io.FileIO(local_file_name, 'wb') as fh:
                    downloader = MediaIoBaseDownload(fh, request)

                    done = False
                    while not done:
                        status, done = downloader.next_chunk()

                file_data = process_file_data(local_file_name, file_type)

                uploaded_file = call_catalog_api(upload_files_url, 'POST', file_data, 'Upload Files')
                file_uid = uploaded_file.get("file", {}).get("fileUid", None)

                if not file_uid:
                    logging.warning("API failure: ", uploaded_file)
                    logging.warning(f"Failed to upload file '{file_name}' with ID '{file_id}'.")
                    append_file_id(file_id, failed_file_path)
                    os.remove(local_file_name)
                    continue

                process_data = call_catalog_api(process_files_url, 'POST', {"fileUids": [file_uid]}, 'Process Files')
                process_status = process_data.get("files", [{}])[0].get("processStatus", None)

                if not process_status:
                    logging.warning(f"Failed to process file '{file_name}' with ID '{file_id}'.")
                    append_file_id(file_id, failed_file_path)
                    os.remove(local_file_name)
                    continue

                os.remove(local_file_name)
                append_file_id(file_id, uploaded_file_path)

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
