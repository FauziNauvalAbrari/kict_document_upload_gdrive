from odoo import models, fields, api
from datetime import date

class KictSio(models.Model):
    _name = 'kict.sio'
    _inherit = ['kict.base.mixin']
    _description = 'KICT SIO Kendaraan'
    _order = 'date_berlaku desc'

    # Field khusus SIO untuk VERIFIKASI
    no_sio = fields.Char(string="No. SIO", required=True)
    
    # Override date_terima dari mixin jadi tidak required atau pakai field yang sama
    date_terima = fields.Date(string="Tgl. Terima SIO", required=True)  # Pakai field dari mixin
    jumlah_admin_sio = fields.Float(string="Jumlah Admin SIO", default=0.0)
    
    # Override fields dari mixin yang tidak dipakai di verifikasi
    pkb = fields.Float(string="PKB", default=0.0, readonly=True)
    swdkllj = fields.Float(string="SWDKLLJ", default=0.0, readonly=True)
    jasa = fields.Float(string="JASA", default=0.0, readonly=True)
    admin_plat = fields.Float(string="ADMIN PLAT", default=0.0, readonly=True)
    denda = fields.Float(string="DENDA", default=0.0, readonly=True)
    materai = fields.Float(string="MATERAI", default=0.0, readonly=True)
    
    # Relasi ke SPK
    spk_ids = fields.One2many('kict.sio.spk', 'sio_id', string='History SPK')
    spk_count = fields.Integer(string='Jumlah SPK', compute='_compute_spk_count')

    @api.depends('spk_ids')
    def _compute_spk_count(self):
        for rec in self:
            rec.spk_count = len(rec.spk_ids)

    def action_view_spk(self):
        self.ensure_one()
        return {
            'name': 'History SPK SIO',
            'type': 'ir.actions.act_window',
            'res_model': 'kict.sio.spk',
            'view_mode': 'tree,form',
            'domain': [('sio_id', '=', self.id)],
            'context': {
                'default_sio_id': self.id,
                'default_tgl_ditetapkan_lama': self.date_ditetapkan,
            },
        }


class KictSioSpk(models.Model):
    _name = 'kict.sio.spk'
    _description = 'SPK Perpanjangan SIO'
    _order = 'tanggal_spk desc'

    sio_id = fields.Many2one('kict.sio', string='SIO Reference', required=True, ondelete='cascade')
    
    # Related fields untuk info kendaraan
    fleet_id = fields.Many2one(related='sio_id.fleet_id', store=True)
    license_plate = fields.Char(related='sio_id.license_plate', store=True)
    no_sio = fields.Char(related='sio_id.no_sio', store=True)
    
    # Field SPK SIO
    tanggal_spk = fields.Date(string='Tanggal SPK', required=True, default=fields.Date.today)
    no_spk = fields.Char(string='No. SPK', readonly=True)
    
    # Tanggal dari Verifikasi terakhir (readonly)
    tgl_ditetapkan_lama = fields.Date(string='Tgl. Ditetapkan (Lama)', readonly=True)
    
    # Tanggal Perpanjangan Baru
    tgl_ditetapkan_baru = fields.Date(string='Tgl. Ditetapkan (Baru)', required=True)
    tgl_berlaku_baru = fields.Date(string='Tgl. Berlaku (Baru)', required=True)
    
    # Biaya khusus SIO
    nilai_sio = fields.Float(string='Nilai SIO', default=0.0)
    nilai_pengajuan = fields.Float(string='Nilai Pengajuan', default=0.0)
    total_biaya = fields.Float(string='Total Biaya', compute='_compute_total_biaya', store=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('butuh_approval', 'Butuh Approval'),
        ('pending', 'Pending'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft')
    notes = fields.Text(string='Catatan')

    @api.depends('nilai_sio', 'nilai_pengajuan')
    def _compute_total_biaya(self):
        for rec in self:
            rec.total_biaya = rec.nilai_sio + rec.nilai_pengajuan

    @api.onchange('sio_id')
    def _onchange_sio_id(self):
        """Auto-fill tanggal ditetapkan dari SIO terakhir"""
        if self.sio_id:
            self.tgl_ditetapkan_lama = self.sio_id.date_ditetapkan

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-fill tgl_ditetapkan_lama dari SIO
            if vals.get('sio_id') and not vals.get('tgl_ditetapkan_lama'):
                sio = self.env['kict.sio'].browse(vals['sio_id'])
                vals['tgl_ditetapkan_lama'] = sio.date_ditetapkan
            
            # Generate SPK number
            if not vals.get('no_spk') and vals.get('tanggal_spk'):
                tanggal = fields.Date.from_string(vals['tanggal_spk'])
                month_year = tanggal.strftime('%b%Y')
                
                existing = self.search([('no_spk', 'like', 'SPK-%/SIO/')], order='id desc', limit=1)
                if existing and existing.no_spk:
                    try:
                        last_num = int(existing.no_spk.split('-')[1].split('/')[0])
                        new_num = last_num + 1
                    except:
                        new_num = 1
                else:
                    new_num = 1
                
                vals['no_spk'] = f"SPK-{str(new_num).zfill(3)}/SIO/{month_year}"
        
        records = super().create(vals_list)
        
        # Update parent SIO dengan data terbaru
        for rec in records:
            if rec.sio_id and rec.status == 'closed':
                rec.sio_id.write({
                    'date_ditetapkan': rec.tgl_ditetapkan_baru,
                    'date_berlaku': rec.tgl_berlaku_baru,
                })
        
        return records
    
    def write(self, vals):
        """Update SIO jika status jadi closed"""
        result = super().write(vals)
        
        for rec in self:
            if rec.status == 'closed' and rec.sio_id:
                rec.sio_id.write({
                    'date_ditetapkan': rec.tgl_ditetapkan_baru,
                    'date_berlaku': rec.tgl_berlaku_baru,
                })
        
        return result