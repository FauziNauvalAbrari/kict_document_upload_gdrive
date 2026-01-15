# ============================================
# FILE: kict_stnk.py
# ============================================
from odoo import models, fields, api
from datetime import date

class KictStnk(models.Model):
    _name = 'kict.stnk'
    _inherit = ['kict.base.mixin']
    _description = 'KICT STNK Kendaraan'
    _order = 'date_berlaku desc'

    # Field khusus STNK
    no_stnk = fields.Char(string="No. STNK", required=True)
    fuel_type = fields.Selection([
        ('gasoline', 'Bensin'),
        ('diesel', 'Diesel'),
        ('electric', 'Listrik'),
        ('hybrid', 'Hybrid')
    ], string="Bahan Bakar", required=True)
    cylinder = fields.Integer(string="Cylinder", required=True)
    
    # Relasi ke SPK
    spk_ids = fields.One2many('kict.stnk.spk', 'stnk_id', string='History SPK')
    spk_count = fields.Integer(string='Jumlah SPK', compute='_compute_spk_count')

    @api.depends('spk_ids')
    def _compute_spk_count(self):
        for rec in self:
            rec.spk_count = len(rec.spk_ids)

    def action_view_spk(self):
        self.ensure_one()
        return {
            'name': 'History SPK STNK',
            'type': 'ir.actions.act_window',
            'res_model': 'kict.stnk.spk',
            'view_mode': 'tree,form',
            'domain': [('stnk_id', '=', self.id)],
            'context': {'default_stnk_id': self.id},
        }


class KictStnkSpk(models.Model):
    _name = 'kict.stnk.spk'
    _inherit = ['kict.spk.mixin']
    _description = 'SPK Perpanjangan STNK'
    _order = 'tanggal_spk desc'

    stnk_id = fields.Many2one('kict.stnk', string='STNK Reference', required=True, ondelete='cascade')
    
    # Related fields untuk info kendaraan
    fleet_id = fields.Many2one(related='stnk_id.fleet_id', store=True)
    license_plate = fields.Char(related='stnk_id.license_plate', store=True)
    no_stnk = fields.Char(related='stnk_id.no_stnk', store=True)

    @api.model
    def _generate_no_spk(self):
        """Generate No. SPK dengan format: SPK/YYYY/MM/XXXX"""
        today = date.today()
        year = today.strftime('%Y')
        month = today.strftime('%m')
        
        # Cari SPK terakhir di bulan ini
        last_spk = self.search([
            ('no_spk', 'like', f'SPK/{year}/{month}/%')
        ], order='no_spk desc', limit=1)
        
        if last_spk and last_spk.no_spk:
            try:
                last_number = int(last_spk.no_spk.split('/')[-1])
                new_number = last_number + 1
            except:
                new_number = 1
        else:
            new_number = 1
        
        return f"SPK/{year}/{month}/{new_number:04d}"
    
    @api.onchange('tanggal_spk')
    def _onchange_tanggal_spk(self):
        """Auto-generate no_spk ketika tanggal_spk diisi"""
        if self.tanggal_spk and not self.no_spk:
            self.no_spk = self._generate_no_spk()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Auto-generate no_spk jika belum ada
            if vals.get('tanggal_spk') and not vals.get('no_spk'):
                vals['no_spk'] = self._generate_no_spk()
        
        records = super().create(vals_list)
        
        # Update parent STNK dengan data terbaru jika status closed
        for rec in records:
            if rec.stnk_id and rec.status == 'closed':
                rec.stnk_id.write({
                    'date_ditetapkan': rec.date_ditetapkan,
                    'date_berlaku': rec.date_berlaku,
                })
        
        return records
    
    def write(self, vals):
        """Update STNK jika status jadi closed"""
        result = super().write(vals)
        
        for rec in self:
            if rec.status == 'closed' and rec.stnk_id:
                rec.stnk_id.write({
                    'date_ditetapkan': rec.date_ditetapkan,
                    'date_berlaku': rec.date_berlaku,
                })
        
        return result
