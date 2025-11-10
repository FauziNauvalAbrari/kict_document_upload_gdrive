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
        """Upload file ke Google Drive dengan struktur:
           Dokumen KICT / Category / Tahun / File
        """
        for record in self:
            if not record.file:
                raise ValueError("❌ Tidak ada file untuk diupload.")

            drive_service = self.env['gdrive.service']

            # 1️⃣ Buat atau ambil folder utama
            main_folder_id = drive_service.create_folder("Dokumen KICT")

            # 2️⃣ Buat / ambil folder kategori di dalam folder utama
            category_name = record.category_id.name or "Tanpa Kategori"
            category_folder_id = drive_service.create_folder(category_name, parent_id=main_folder_id)

            # Simpan ID folder ke kategori (biar ga bikin ulang tiap kali)
            if not record.category_id.drive_folder_id:
                record.category_id.drive_folder_id = category_folder_id

            # 3️⃣ Buat folder per tahun di dalam folder kategori
            if record.date:
                year = record.date.year
            else:
                year = date.today().year  # fallback kalau field date kosong

            year_folder_id = drive_service.create_folder(str(year), parent_id=category_folder_id)

            # 4️⃣ Upload file ke folder tahun
            file_content = base64.b64decode(record.file)
            filename = record.filename or f"{record.name}.pdf"

            try:
                file_url = drive_service.upload_file(
                    filename=filename,
                    file_content=file_content,
                    parent_id=year_folder_id
                )
                record.url = file_url

            except Exception as e:
                raise ValueError(f"Gagal upload ke Google Drive: {e}")