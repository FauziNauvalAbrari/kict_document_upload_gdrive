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
    contract_number = fields.Char(string="Nomor Kontrak")
    engine_number = fields.Char(string="Nomor Mesin",related='fleet_id.engine_number')
    license_plate = fields.Char(string="Nomor Polisi",related='fleet_id.license_plate')
    file = fields.Binary(string="File", required=True)
    filename = fields.Char(string="Nama File") 
    url = fields.Char(string="Google Drive URL", readonly=True)
    drive_file_id = fields.Char(string="Google Drive File ID", readonly=True)
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

    def unlink(self):
        """Override unlink untuk hapus file di Google Drive sebelum hapus record"""
        drive_service = self.env['gdrive.service']
        
        for record in self:
            if record.drive_file_id:
                try:
                    drive_service.delete_file(record.drive_file_id)
                except Exception:
                    pass  # Lanjut hapus record meskipun gagal hapus file
        
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
            