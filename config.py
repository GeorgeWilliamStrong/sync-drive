import os

# Configuration Constants
NAMESPACE_ID = "george_strong"
TOKEN = os.environ.get("INSTILL_API_TOKEN")
KB_ID = "google-test"
DOMAIN = "api.instill.tech"
LIST_FILES_URL = f"https://{DOMAIN}/v1alpha/namespaces/{NAMESPACE_ID}/catalogs/{KB_ID}/files"
UPLOAD_FILES_URL = f"https://{DOMAIN}/v1alpha/namespaces/{NAMESPACE_ID}/catalogs/{KB_ID}/files"
PROCESS_FILES_URL = f"https://{DOMAIN}/v1alpha/catalogs/files/processAsync"
TIME_FILE_PATH = 'modified_time.txt'
UPLOADED_FILE_PATH = 'uploaded_files.json'
FAILED_FILE_PATH = 'failure_files.json'
UNSUPPORTED_FILE_PATH = 'unsupported_type_files.json'
SAVE_LOG_FILE = False
SCOPES = ["https://www.googleapis.com/auth/drive"]
