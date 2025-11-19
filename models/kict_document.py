import base64
from odoo import api,models, fields
from odoo.exceptions import UserError, ValidationError
from datetime import date

class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    kict_document_ids = fields.One2many(
        'kict.document',
        'fleet_id',
        string="Dokumen KICT"
    )
    
class KictDocument(models.Model):
    _name = 'kict.document'
    _description = 'KICT Document Upload ke Google Drive (OAuth)'

    name = fields.Char(string="Nama Dokumen", required=True)
    date = fields.Date(string="Tanggal", default=fields.Date.today)
    category_id = fields.Many2one('kict.document.category', string="Kategori", required=True)
    category_name = fields.Char(related='category_id.name',store=True)
    fleet_id = fields.Many2one('fleet.vehicle', string="Fleet", required=True)
    vin_sn = fields.Char(string="No. Rangka", related='fleet_id.vin_sn', readonly=True)
    bpkb_number = fields.Char(string="Nomor BPKB", store=True)
    contract_number = fields.Char(string="Nomor Kontrak")
    engine_number = fields.Char(string="Nomor Mesin",related='fleet_id.engine_number')
    license_plate = fields.Char(string="Nomor Polisi",related='fleet_id.license_plate')
    file = fields.Binary(string="File", required=False)
    filename = fields.Char(string="Nama File") 
    url = fields.Char(string="Google Drive URL", readonly=True)
    drive_file_id = fields.Char(string="Google Drive File ID", readonly=True )
    preview_html = fields.Html(string="Preview", compute="_compute_preview_html", sanitize=False)

    @api.depends('drive_file_id')
    def _compute_preview_html(self):
        """Generate HTML iframe untuk preview"""
        for record in self:
            if record.drive_file_id:
                preview_url = f"https://drive.google.com/file/d/{record.drive_file_id}/preview"
                record.preview_html = f'''
                    <div style="width: 100%; height: 700px; position: relative;">
                        <iframe src="{preview_url}" 
                                style="width: 100%; height: 100%; border: 1px solid #ddd; border-radius: 4px;"
                                frameborder="0"
                                allowfullscreen="true">
                        </iframe>
                    </div>
                '''
            else:
                record.preview_html = '''
                    <div style="padding: 40px; text-align: center; background: #f8f9fa; border: 1px dashed #ccc; border-radius: 4px;">
                        <i class="fa fa-file-o" style="font-size: 48px; color: #999; margin-bottom: 20px;"></i>
                        <h4 style="color: #666;">Belum ada file</h4>
                        <p style="color: #999;">Upload file dan submit ke Google Drive untuk melihat preview</p>
                    </div>
                '''

    def action_upload_to_gdrive(self):
        """Upload file ke Google Drive dengan struktur:
           Dokumen KICT / Category / Tahun / File
        """
        for record in self:
            if not record.file:
                raise ValidationError("Tidak ada file untuk diupload. Silakan pilih file terlebih dahulu.")

            drive_service = self.env['gdrive.service']

            # Hapus file lama jika ada
            if record.drive_file_id:
                try:
                    drive_service.delete_file(record.drive_file_id)
                except Exception:
                    pass  # Lanjut meskipun gagal hapus file lama

            # Buat folder structure
            try:
                main_folder_id = drive_service.create_folder("Dokumen KICT")

                category_name = record.category_id.name or "Tanpa Kategori"
                category_folder_id = drive_service.create_folder(category_name, parent_id=main_folder_id)

                if not record.category_id.drive_folder_id:
                    record.category_id.drive_folder_id = category_folder_id

                year = record.date.year if record.date else date.today().year
                year_folder_id = drive_service.create_folder(str(year), parent_id=category_folder_id)

                file_content = base64.b64decode(record.file)
                filename = record.filename or f"{record.name}.pdf"
                
                result = drive_service.upload_file(
                    filename=filename,
                    file_content=file_content,
                    parent_id=year_folder_id
                )
                
                # Update record dan hapus file dari database
                record.write({
                    'url': result['url'],
                    'drive_file_id': result['file_id'],
                    'file': False,
                })
                
                self.env.cr.commit()

                # Show success notification
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Upload Berhasil!',
                        'message': f"File '{filename}' berhasil diupload ke Google Drive!",
                        'type': 'success',
                        'sticky': False,
                    }
                }

            except Exception as e:
                raise UserError(f"Gagal upload ke Google Drive: {str(e)}")
            
    def _delete_drive_file(self):
        """Hapus file di Google Drive"""
        drive_service = self.env['gdrive.service']
        if self.drive_file_id:
            try:
                drive_service.delete_file(self.drive_file_id)
            except Exception:
                pass

    def write(self, vals):
        """Hapus file lama jika user mengganti file"""
        for rec in self:
            # Hanya jika file barunya ada (berisi data binary)
            if 'file' in vals and vals['file']:
                if rec.drive_file_id:
                    rec._delete_drive_file()
                rec.drive_file_id = False
                rec.url = False

        return super().write(vals)


    def unlink(self):
        """Hapus file di Google Drive sebelum record dihapus"""
        for rec in self:
            rec._delete_drive_file()
        return super(KictDocument, self).unlink()
    
    @api.constrains('file')
    def _check_file_required(self):
        for rec in self:
            # Kalau new record: file wajib
            if not rec.id and not rec.file:
                raise ValidationError("File wajib diupload.")

    # def unlink(self):
    #     """Override unlink untuk hapus file di Google Drive sebelum hapus record"""
    #     drive_service = self.env['gdrive.service']
        
    #     for record in self:
    #         if record.drive_file_id:
    #             try:
    #                 drive_service.delete_file(record.drive_file_id)
    #             except Exception:
    #                 pass  # Lanjut hapus record meskipun gagal hapus file
        
    #     return super(KictDocument, self).unlink()
    
    def action_delete_record(self):
        """Aksi hapus record langsung dari kanban"""
        for record in self:
            try:
                record.unlink()
            except Exception as e:
                raise UserError(f"Gagal menghapus dokumen: {str(e)}")
        return True
    
    @api.constrains('file', 'filename')
    def _check_file_type(self):
        allowed = ['pdf']   # <--format yang diizinkan
        for rec in self:
            if rec.filename:
                ext = rec.filename.split('.')[-1].lower()
                if ext not in allowed:
                    raise ValidationError(
                        "Jenis file tidak diizinkan! Hanya boleh: PDF"
                    )
    
    @api.constrains('file', 'category_name')
    def _check_file_size(self):
        for rec in self:
            if not rec.file:
                continue

            # Hitung ukuran file (bytes)
            file_size = len(base64.b64decode(rec.file))

            # Batasan
            max_stnk = 150 * 1024             # 150 KB
            max_other = 10 * 1024 * 1024      # 10 MB

            # Kondisi khusus STNK
            if rec.category_name == "STNK":
                if file_size > max_stnk:
                    raise ValidationError(
                        "Ukuran file STNK maksimal **150 KB**.\n"
                        f"Ukuran saat ini: {round(file_size/1024, 2)} KB"
                    )

            # Kategori lainnya
            else:
                if file_size > max_other:
                    raise ValidationError(
                        "Ukuran file maksimal **10 MB** untuk kategori ini.\n"
                        f"Ukuran saat ini: {round(file_size/1024/1024, 2)} MB"
                    )
    # @api.constrains('bpkb_number', 'category_id')
    # def _check_bpkb_number_required(self):
    #     for record in self:
    #         if record.category_id.name == 'BPKB' and not record.bpkb_number:
    #             raise ValidationError ("Nomor BPKB wajib diisi untuk kategori BPKB.")
            