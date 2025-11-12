import base64
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date

class KictDocument(models.Model):
    _name = 'kict.document'
    _description = 'KICT Document Upload ke Google Drive (OAuth)'

    name = fields.Char(string="Nama Dokumen", required=True)
    date = fields.Date(string="Tanggal", default=fields.Date.today)
    category_id = fields.Many2one('kict.document.category', string="Kategori", required=True)
    fleet_id = fields.Many2one('fleet.vehicle', string="Fleet", required=True)
    vin_sn = fields.Char(string="No. Rangka", related='fleet_id.vin_sn', readonly=True)
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
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'Error!',
                        'message': 'Tidak ada file untuk diupload.',
                        'type': 'danger',
                        'sticky': True,
                    }
                }

            drive_service = self.env['gdrive.service']

            # ✅ Cek dan hapus file lama sebelum upload file baru
            old_file_id = record.drive_file_id
            if old_file_id:
                try:
                    drive_service.delete_file(old_file_id)
                except Exception:
                    pass

            # Buat folder structure
            try:
                main_folder_id = drive_service.create_folder("Dokumen KICT")

                category_name = record.category_id.name or "Tanpa Kategori"
                category_folder_id = drive_service.create_folder(category_name, parent_id=main_folder_id)

                if not record.category_id.drive_folder_id:
                    record.category_id.drive_folder_id = category_folder_id

                if record.date:
                    year = record.date.year
                else:
                    year = date.today().year

                year_folder_id = drive_service.create_folder(str(year), parent_id=category_folder_id)

                file_content = base64.b64decode(record.file)
                filename = record.filename or f"{record.name}.pdf"

                result = drive_service.upload_file(
                    filename=filename,
                    file_content=file_content,
                    parent_id=year_folder_id
                )

                new_file_id = result['file_id']
                new_url = result['url']

                record.write({
                    'url': new_url,
                    'drive_file_id': new_file_id
                })

                self.env.cr.commit()

                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': '✅ Upload Berhasil!',
                        'message': f'File "{filename}" berhasil diupload ke Google Drive.',
                        'type': 'success',
                        'sticky': False,
                        'next': {'type': 'ir.actions.act_window_close'},
                    }
                }

            except Exception as e:
                error_msg = str(e)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': '❌ Upload Gagal!',
                        'message': f'Gagal upload ke Google Drive: {error_msg}',
                        'type': 'danger',
                        'sticky': True,
                    }
                }

    def unlink(self):
        """Override unlink untuk hapus file di Google Drive sebelum hapus record"""
        drive_service = self.env['gdrive.service']

        for record in self:
            if record.drive_file_id:
                try:
                    drive_service.delete_file(record.drive_file_id)
                except Exception:
                    pass

        return super(KictDocument, self).unlink()
