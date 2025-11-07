import base64
from odoo import models, fields, api
from datetime import date

class KictDocument(models.Model):
    _name = 'kict.document'
    _description = 'KICT Document Upload ke Google Drive'

    name = fields.Char(string="Nama Dokumen", required=True)
    date = fields.Date(string="Tanggal", default=fields.Date.today)
    category_id = fields.Many2one('kict.document.category', string="Kategori", required=True)
    fleet_id = fields.Many2one('fleet.vehicle', string="Fleet")
    vin_sn = fields.Char(string="No. Rangka", related='fleet_id.vin_sn', readonly=True)
    file = fields.Binary(string="File", required=True)
    url = fields.Char(string="Google Drive URL", readonly=True)

    def action_upload_to_gdrive(self):
        """Upload file ke Google Drive sesuai kategori."""
        for record in self:
            if not record.file:
                raise ValueError("❌ Tidak ada file yang diupload.")

            api_key = self.env['ir.config_parameter'].sudo().get_param('gdrive_api_key')
            if not api_key:
                raise ValueError("⚠️ API Key Google Drive belum diset di System Parameters.")

            drive_service = self.env['gdrive.service']
            file_content = base64.b64decode(record.file)
            filename = f"{record.category_id.name or 'Dokumen'}_{record.name}.pdf"

            # --- Pastikan folder kategori sudah ada ---
            folder_id = record.category_id.drive_folder_id
            if not folder_id:
                folder_id = drive_service.create_folder(api_key, record.category_id.name)
                record.category_id.drive_folder_id = folder_id

            # --- (Optional) Buat folder per tahun ---
            current_year = str(date.today().year)
            year_folder_id = drive_service.create_folder(api_key, current_year, parent_id=folder_id)

            # --- Upload file ke folder kategori/tahun ---
            try:
                file_id = drive_service.upload_file(api_key, filename, file_content, parent_id=year_folder_id)
                record.url = f"https://drive.google.com/file/d/{file_id}/view"
            except Exception as e:
                raise ValueError(f"Gagal upload file ke Google Drive:\n{e}")
