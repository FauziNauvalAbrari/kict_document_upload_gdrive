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

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.tanggal_spk and rec.total > 0:
                rec.no_spk = rec._generate_spk_number('STNK')
                self.env['kict.stnk.spk'].create({
                    'stnk_id': rec.id,
                    'tanggal_spk': rec.tanggal_spk,
                    'no_spk': rec.no_spk,
                    'date_ditetapkan': rec.date_ditetapkan,
                    'date_berlaku': rec.date_berlaku,
                    'pkb': rec.pkb,
                    'swdkllj': rec.swdkllj,
                    'jasa': rec.jasa,
                    'admin_plat': rec.admin_plat,
                    'denda': rec.denda,
                    'materai': rec.materai,
                    'status': rec.status_perpanjangan,
                    'notes': rec.notes,
                })
        return records

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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('no_spk') and vals.get('tanggal_spk'):
                # Generate SPK number
                tanggal = fields.Date.from_string(vals['tanggal_spk'])
                month_year = tanggal.strftime('%b%Y')
                
                existing = self.search([('no_spk', 'like', 'SPK-%/STNK/')], order='id desc', limit=1)
                if existing and existing.no_spk:
                    try:
                        last_num = int(existing.no_spk.split('-')[1].split('/')[0])
                        new_num = last_num + 1
                    except:
                        new_num = 1
                else:
                    new_num = 1
                
                vals['no_spk'] = f"SPK-{str(new_num).zfill(3)}/STNK/{month_year}"
        
        records = super().create(vals_list)
        
        # Update parent STNK dengan data terbaru
        for rec in records:
            if rec.stnk_id:
                rec.stnk_id.write({
                    'date_ditetapkan': rec.date_ditetapkan,
                    'date_berlaku': rec.date_berlaku,
                    'no_spk': rec.no_spk,
                    'tanggal_spk': rec.tanggal_spk,
                })
        
        return records