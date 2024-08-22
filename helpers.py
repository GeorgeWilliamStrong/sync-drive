import os
import json
import base64
from datetime import datetime
import requests
from config import TOKEN, TIME_FILE_PATH


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
        'Authorization': f'Bearer {TOKEN}'
    }
    response = requests.request(method, url, headers=headers, json=data)
    response.raise_for_status()  # Raises HTTPError for bad responses
    return response.json()


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
    with open(TIME_FILE_PATH, 'w') as file:
        file.write(modified_time)


def read_modified_time_from_file():
    """
    Read the modified time from a file if it exists.

    Returns:
        str or None: The modified time read from the file, or None if the file does not exist.
    """
    if os.path.exists(TIME_FILE_PATH):
        with open(TIME_FILE_PATH, 'r') as file:
            return file.read().strip()
    return None


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
