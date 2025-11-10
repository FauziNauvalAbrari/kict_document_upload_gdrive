import base64
from odoo import models, fields
from datetime import date

class KictDocument(models.Model):
    _name = 'kict.document'
    _description = 'KICT Document Upload ke Google Drive (OAuth)'

    name = fields.Char(string="Nama Dokumen", required=True)
    date = fields.Date(string="Tanggal", default=fields.Date.today)
    category_id = fields.Many2one('kict.document.category', string="Kategori", required=True)
    fleet_id = fields.Many2one('fleet.vehicle', string="Fleet")
    vin_sn = fields.Char(string="No. Rangka", related='fleet_id.vin_sn', readonly=True)
    file = fields.Binary(string="File", required=True)
    filename = fields.Char(string="Nama File") 
    url = fields.Char(string="Google Drive URL", readonly=True)     

    def action_upload_to_gdrive(self):
        """Upload file ke Google Drive menggunakan OAuth credentials."""
        for record in self:
            if not record.file:
                raise ValueError("❌ Tidak ada file untuk diupload.")

            drive_service = self.env['gdrive.service']

            # Pastikan folder kategori ada
            folder_id = record.category_id.drive_folder_id
            if not folder_id:
                folder_id = drive_service.create_folder(record.category_id.name)
                record.category_id.drive_folder_id = folder_id

            # Buat folder per tahun
            current_year = str(date.today().year)
            year_folder_id = drive_service.create_folder(current_year, parent_id=folder_id)

            # Upload file ke Drive
            file_content = base64.b64decode(record.file)
            filename = record.filename or f"{record.name}.pdf"
            

            try:
                file_url = drive_service.upload_file(filename, file_content, parent_id=year_folder_id)
                record.url = file_url
            except Exception as e:
                raise ValueError(f"Gagal upload ke Google Drive: {e}")
