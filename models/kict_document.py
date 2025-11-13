import base64
from odoo import api,models, fields
from odoo.exceptions import UserError, ValidationError
from datetime import date

class KictDocument(models.Model):
    _name = 'kict.document'
    _description = 'KICT Document Upload ke Google Drive (OAuth)'

    name = fields.Char(string="Nama Dokumen", required=True)
    date = fields.Date(string="Tanggal", default=fields.Date.today)
    category_id = fields.Many2one('kict.document.category', string="Kategori", required=True)
    category_name = fields.Char(related='category_id.name',store=True)
    fleet_id = fields.Many2one('fleet.vehicle', string="Fleet", required=True)
    vin_sn = fields.Char(string="No. Rangka", related='fleet_id.vin_sn', readonly=True)
    bpkb_number = fields.Char(string="Nomor BPKB")
    engine_number = fields.Char(string="Nomor Mesin",related='fleet_id.engine_number')
    license_plate = fields.Char(string="Nomor Polisi",related='fleet_id.license_plate')
    file = fields.Binary(string="File", required=True)
    filename = fields.Char(string="Nama File") 
    url = fields.Char(string="Google Drive URL", readonly=True)
    drive_file_id = fields.Char(string="Google Drive File ID", readonly=True)

    def action_upload_to_gdrive(self):
        """Upload file ke Google Drive dengan struktur:
           Dokumen KICT / Category / Tahun / File
        """
        for record in self:
            if not record.file:
                raise UserError("❌ Tidak ada file untuk diupload.")

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
                # 👇 PERUBAHAN: Sekarang return dict dengan file_id dan url
                result = drive_service.upload_file(
                    filename=filename,
                    file_content=file_content,
                    parent_id=year_folder_id
                )
                
                # 👇 Simpan file_id dan url
                record.write({
                    'url': result['url'],
                    'drive_file_id': result['file_id']
                })

            except Exception as e:
                raise UserError(f"Gagal upload ke Google Drive: {e}")

    def unlink(self):
        """Override unlink untuk hapus file di Google Drive sebelum hapus record"""
        drive_service = self.env['gdrive.service']
        
        for record in self:
            # Hapus file di Google Drive jika ada file_id
            if record.drive_file_id:
                try:
                    drive_service.delete_file(record.drive_file_id)
                except Exception as e:
                    # Log error tapi tetap lanjut hapus record
                    # (supaya user tetap bisa hapus record meskipun gagal hapus di Drive)
                    import logging
                    _logger = logging.getLogger(__name__)
                    _logger.warning(f"Gagal hapus file di Google Drive: {e}")
        
        # Panggil parent unlink untuk hapus record di database
        return super(KictDocument, self).unlink()
    
    def action_delete_record(self):
        """Aksi hapus record langsung dari kanban"""
        for record in self:
            try:
                record.unlink()
            except Exception as e:
                raise UserError(f"Gagal menghapus dokumen: {str(e)}")
        return True
    
    @api.constrains('bpkb_number', 'category_id')
    def _check_bpkb_number_required(self):
        for record in self:
            if record.category_id.name == 'BPKB' and not record.bpkb_number:
                raise ValidationError ("Nomor BPKB wajib diisi untuk kategori BPKB.")