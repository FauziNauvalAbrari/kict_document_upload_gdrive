from odoo import models, fields, api

class KictDocumentCategory(models.Model):
    _name = 'kict.document.category'
    _description = 'KICT Document Category'

    name = fields.Char(string="Nama Kategori", required=True)
    description = fields.Text(string="Deskripsi")
    drive_folder_id = fields.Char(string="Google Drive Folder ID", readonly=True)

    @api.model
    def create(self, vals):
        """Override create untuk membuat menu item otomatis ketika kategori baru dibuat"""
        category = super(KictDocumentCategory, self).create(vals)
        category.create_menu_item()
        return category

    def write(self, vals):
        """Override write untuk update menu item ketika nama kategori diubah"""
        res = super(KictDocumentCategory, self).write(vals)
        if 'name' in vals:
            for category in self:
                category.update_menu_item()
        return res

    def unlink(self):
        """Override unlink untuk hapus menu item ketika kategori dihapus"""
        for category in self:
            category.delete_menu_item()
        return super(KictDocumentCategory, self).unlink()

    def create_menu_item(self):
        """Buat menu item untuk kategori ini (PUBLIC METHOD)"""
        self.ensure_one()
        IrUiMenu = self.env['ir.ui.menu'].sudo()
        IrActWindow = self.env['ir.actions.act_window'].sudo()
        
        parent_menu = IrUiMenu.search([
            ('name', '=', 'Dokumen'),
            ('parent_id.name', '=', 'Dokumen')
        ], limit=1)
        
        if not parent_menu:
            return False
        
        existing_menu = IrUiMenu.search([
            ('name', '=', self.name),
            ('parent_id', '=', parent_menu.id),
        ], limit=1)
        
        if existing_menu:
            return True
        
        action = IrActWindow.create({
            'name': self.name,
            'res_model': 'kict.document',
            'view_mode': 'tree,form,kanban',
            'domain': [('category_id', '=', self.id)],
            'context': "{'default_category_id': %s}" % self.id,
        })
        
        submenu_count = IrUiMenu.search_count([('parent_id', '=', parent_menu.id)])
        
        IrUiMenu.create({
            'name': self.name,
            'parent_id': parent_menu.id,
            'action': 'ir.actions.act_window,%s' % action.id,
            'sequence': (submenu_count + 1) * 10,
        })
        
        return True

    def update_menu_item(self):
        """Update menu item ketika nama kategori berubah"""
        self.ensure_one()
        IrUiMenu = self.env['ir.ui.menu'].sudo()
        IrActWindow = self.env['ir.actions.act_window'].sudo()
        
        parent_menu = IrUiMenu.search([
            ('name', '=', 'Dokumen'),
            ('parent_id.name', '=', 'Dokumen')
        ], limit=1)
        
        if not parent_menu:
            return False
        
        actions = IrActWindow.search([
            ('res_model', '=', 'kict.document'),
            ('domain', 'like', str(self.id)),
        ])
        
        for action in actions:
            action.write({'name': self.name})
            menu = IrUiMenu.search([
                ('parent_id', '=', parent_menu.id),
                ('action', '=', 'ir.actions.act_window,%s' % action.id),
            ], limit=1)
            if menu:
                menu.write({'name': self.name})
                return True
        
        return False

    def delete_menu_item(self):
        self.ensure_one()
        IrUiMenu = self.env['ir.ui.menu'].sudo()

        menus = IrUiMenu.search([("name", "=", self.name)])

        if menus:
            menus.unlink()

        return True

    def action_regenerate_all_menus(self):
        """Regenerate menu untuk semua kategori yang ada"""
        categories = self.env['kict.document.category'].search([])
        success_count = 0
        for category in categories:
            if category.create_menu_item():
                success_count += 1
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success!',
                'message': f'{success_count} menu items berhasil dibuat',
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            }
        }

    def action_create_drive_folder(self):
        """Buat folder di Google Drive untuk kategori ini"""
        drive_service = self.env['gdrive.service']
        
        for record in self:
            if not record.drive_folder_id:
                main_folder_id = drive_service.create_folder("Dokumen")
                category_folder_id = drive_service.create_folder(record.name, parent_id=main_folder_id)
                record.drive_folder_id = category_folder_id
