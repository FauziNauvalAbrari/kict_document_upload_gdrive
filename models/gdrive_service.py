import json
import requests
from odoo import models

class GoogleDriveService(models.AbstractModel):
    _name = 'gdrive.service'
    _description = 'Google Drive Service Helper'

    def upload_file(self, api_key, file_name, file_content, parent_id=None):
        """Upload file ke Google Drive."""
        headers = {"Authorization": f"Bearer {api_key}"}

        metadata = {"name": file_name}
        if parent_id:
            metadata["parents"] = [parent_id]

        files = {
            'data': ('metadata', json.dumps(metadata), 'application/json; charset=UTF-8'),
            'file': file_content
        }

        response = requests.post(
            "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart",
            headers=headers,
            files=files
        )

        if response.status_code in (200, 201):
            return response.json().get("id")
        else:
            raise ValueError(f"Gagal upload ke Google Drive: {response.text}")

    def create_folder(self, api_key, folder_name, parent_id=None):
        """Buat folder di Google Drive."""
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        body = {
            "name": folder_name,
            "mimeType": "application/vnd.google-apps.folder"
        }
        if parent_id:
            body["parents"] = [parent_id]

        response = requests.post(
            "https://www.googleapis.com/drive/v3/files",
            headers=headers,
            json=body
        )

        if response.status_code in (200, 201):
            return response.json().get("id")
        else:
            raise ValueError(f"Gagal membuat folder: {response.text}")
