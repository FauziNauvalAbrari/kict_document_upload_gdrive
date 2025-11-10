from odoo import models, fields, api

class KictDocumentCategory(models.Model):
    _name = 'kict.document.category'
    _description = 'Kategori Dokumen KICT'

    name = fields.Char(string="Nama Kategori", required=True)
    description = fields.Text(string="Deskripsi")
    drive_folder_id = fields.Char(string="Google Drive Folder ID", readonly=True)

    def action_create_drive_folder(self):
     """Buat folder di Google Drive untuk kategori ini menggunakan OAuth."""
     gdrive_service = self.env['gdrive.service']
     for category in self:
          if not category.drive_folder_id:
            folder_id = gdrive_service.create_folder(category.name)
            category.drive_folder_id = folder_id

