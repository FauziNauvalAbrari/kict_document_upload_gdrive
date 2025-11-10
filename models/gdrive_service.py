import base64
import json
import logging
from io import BytesIO

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

from odoo import models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveService(models.AbstractModel):
    _name = 'gdrive.service'
    _description = 'Google Drive Service (OAuth version)'

    def _get_google_credentials(self):
        """Load credentials from system parameters and refresh if needed."""
        params = self.env['ir.config_parameter'].sudo()
        
        access_token = params.get_param('google_drive_access_token', '')
        refresh_token = params.get_param('google_drive_refresh_token', '')
        client_id = params.get_param('google_drive_client_id', '')
        client_secret = params.get_param('google_drive_client_secret', '')
        
        if not all([client_id, client_secret, refresh_token]):
            raise UserError(_(
                "Google Drive credentials tidak lengkap. "
                "Silakan konfigurasi di Settings > Technical > System Parameters:\n"
                "- google_drive_client_id\n"
                "- google_drive_client_secret\n"
                "- google_drive_refresh_token\n"
                "- google_drive_access_token (opsional, akan di-generate otomatis)"
            ))
        
        info_token = {
            "token": access_token,
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        try:
            creds = Credentials.from_authorized_user_info(info_token, SCOPES)
            
            # Refresh token jika expired
            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    _logger.info("Refreshing Google Drive access token...")
                    creds.refresh(Request())
                    
                    # Simpan token baru ke system parameters
                    params.set_param('google_drive_access_token', creds.token)
                    _logger.info("Access token berhasil di-refresh")
                else:
                    raise UserError(_("Credentials tidak valid dan tidak bisa di-refresh"))
                    
            return creds
            
        except Exception as e:
            _logger.error(f"Error getting Google credentials: {str(e)}")
            raise UserError(_(f"Gagal mendapatkan credentials Google Drive: {str(e)}"))

    def _get_drive_service(self):
        """Get authenticated Google Drive service."""
        try:
            creds = self._get_google_credentials()
            service = build('drive', 'v3', credentials=creds)
            return service
        except Exception as e:
            _logger.error(f"Error building Drive service: {str(e)}")
            raise UserError(_(f"Gagal membuat koneksi ke Google Drive: {str(e)}"))

    def upload_file(self, filename, file_content, parent_id=None, mimetype='application/pdf'):
        """Upload file to Google Drive folder"""
        try:
            service = self._get_drive_service()

            metadata = {'name': filename}
            if parent_id:
                metadata['parents'] = [parent_id]

            # File content in memory
            media = MediaIoBaseUpload(
                BytesIO(file_content), 
                mimetype=mimetype,
                resumable=True
            )

            _logger.info(f"Uploading file: {filename} to folder: {parent_id}")
            file = service.files().create(
                body=metadata, 
                media_body=media, 
                fields='id, name, webViewLink'
            ).execute()
            
            file_id = file.get('id')
            _logger.info(f"File uploaded successfully with ID: {file_id}")

            # Set sharing permissions (public read)
            try:
                service.permissions().create(
                    fileId=file_id,
                    body={'type': 'anyone', 'role': 'reader'},
                ).execute()
                _logger.info(f"File {file_id} set to public")
            except HttpError as e:
                _logger.warning(f"Could not set public permission: {str(e)}")

            return f"https://drive.google.com/file/d/{file_id}/view"

        except HttpError as e:
            _logger.error(f"Google Drive API error: {str(e)}")
            raise UserError(_(f"Gagal upload ke Google Drive: {str(e)}"))
        except Exception as e:
            _logger.error(f"Upload error: {str(e)}")
            raise UserError(_(f"Error saat upload file: {str(e)}"))

    def create_folder(self, folder_name, parent_id=None):
        """Create folder in Drive if not exists.
       Otomatis buat folder utama 'Dokumen_KICT' kalau belum ada.
        """
        try:
            service = self._get_drive_service()

            # 1️⃣ Buat / ambil folder utama "Dokumen_KICT"
            main_folder_name = 'Dokumen_KICT'
            main_query = (
                f"name='{main_folder_name}' and "
                f"mimeType='application/vnd.google-apps.folder' and trashed=false"
            )
            _logger.info(f"Checking for main folder: {main_folder_name}")
            main_results = service.files().list(
                q=main_query,
                fields="files(id, name)",
                spaces='drive'
            ).execute()
            main_folders = main_results.get('files', [])

            if main_folders:
                main_folder_id = main_folders[0]['id']
                _logger.info(f"Main folder already exists: {main_folder_id}")
            else:
                _logger.info(f"Main folder not found. Creating new one...")
                main_metadata = {
                    'name': main_folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                main_folder = service.files().create(
                    body=main_metadata,
                    fields='id'
                ).execute()
                main_folder_id = main_folder.get('id')
                _logger.info(f"Main folder created successfully: {main_folder_id}")

            # 2️⃣ Pastikan folder kategori dibuat di dalam folder utama
            if not parent_id:
                parent_id = main_folder_id

            # 3️⃣ Cek apakah folder kategori sudah ada di dalam folder utama
            query = (
                f"name='{folder_name}' and "
                f"mimeType='application/vnd.google-apps.folder' and "
                f"'{parent_id}' in parents and trashed=false"
            )

            _logger.info(f"Checking for existing category folder: {folder_name}")
            results = service.files().list(
                q=query,
                fields="files(id, name)",
                spaces='drive'
            ).execute()

            folders = results.get('files', [])
            if folders:
                _logger.info(f"Category folder already exists: {folders[0]['id']}")
                return folders[0]['id']

            # 4️⃣ Jika belum ada, buat folder kategori
            metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            _logger.info(f"Creating new category folder: {folder_name}")
            folder = service.files().create(body=metadata, fields='id').execute()

            folder_id = folder.get('id')
            _logger.info(f"Category folder created successfully: {folder_id}")
            return folder_id

        except HttpError as e:
            _logger.error(f"Google Drive API error: {str(e)}")
            raise UserError(_(f"Gagal membuat folder di Google Drive: {str(e)}"))
        except Exception as e:
            _logger.error(f"Create folder error: {str(e)}")
            raise UserError(_(f"Error saat membuat folder: {str(e)}"))


    def test_connection(self):
        """Test Google Drive connection."""
        try:
            service = self._get_drive_service()
            # Try to list files (limit to 1 to save quota)
            results = service.files().list(pageSize=1, fields="files(id, name)").execute()
            return True, _("Koneksi ke Google Drive berhasil!")
        except Exception as e:
            return False, str(e)