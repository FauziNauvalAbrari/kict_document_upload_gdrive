from odoo import models, fields, api
from datetime import date

class KictIak(models.Model):
    _name = 'kict.iak'
    _inherit = ['kict.base.mixin']
    _description = 'KICT Izin Angkut Kendaraan'
    _order = 'date_berlaku desc'

    # Field khusus Izin Angkut
    no_iak = fields.Char(string="No. Izin Angkut", required=True)
    jenis_angkutan = fields.Selection([
        ('barang', 'Angkutan Barang'),
        ('orang', 'Angkutan Orang'),
        ('khusus', 'Angkutan Khusus')
    ], string="Jenis Angkutan", default='barang')
    kapasitas = fields.Float(string="Kapasitas Angkut")
    satuan_kapasitas = fields.Selection([
        ('kg', 'Kilogram'),
        ('ton', 'Ton'),
        ('orang', 'Orang')
    ], string="Satuan", default='kg')
    trayek = fields.Char(string="Trayek/Rute")
    
    # Relasi ke SPK
    spk_ids = fields.One2many('kict.iak.spk', 'iak_id', string='History SPK')
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
                rec.no_spk = rec._generate_spk_number('IAK')
                self.env['kict.iak.spk'].create({
                    'iak_id': rec.id,
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
            'name': 'History SPK Izin Angkut',
            'type': 'ir.actions.act_window',
            'res_model': 'kict.iak.spk',
            'view_mode': 'tree,form',
            'domain': [('iak_id', '=', self.id)],
            'context': {'default_iak_id': self.id},
        }


class KictIakSpk(models.Model):
    _name = 'kict.iak.spk'
    _inherit = ['kict.spk.mixin']
    _description = 'SPK Perpanjangan Izin Angkut'
    _order = 'tanggal_spk desc'

    iak_id = fields.Many2one('kict.iak', string='IAK Reference', required=True, ondelete='cascade')
    
    fleet_id = fields.Many2one(related='iak_id.fleet_id', store=True)
    license_plate = fields.Char(related='iak_id.license_plate', store=True)
    no_iak = fields.Char(related='iak_id.no_iak', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('no_spk') and vals.get('tanggal_spk'):
                tanggal = fields.Date.from_string(vals['tanggal_spk'])
                month_year = tanggal.strftime('%b%Y')
                
                existing = self.search([('no_spk', 'like', 'SPK-%/IAK/')], order='id desc', limit=1)
                if existing and existing.no_spk:
                    try:
                        last_num = int(existing.no_spk.split('-')[1].split('/')[0])
                        new_num = last_num + 1
                    except:
                        new_num = 1
                else:
                    new_num = 1
                
                vals['no_spk'] = f"SPK-{str(new_num).zfill(3)}/IAK/{month_year}"
        
        records = super().create(vals_list)
        
        for rec in records:
            if rec.iak_id:
                rec.iak_id.write({
                    'date_ditetapkan': rec.date_ditetapkan,
                    'date_berlaku': rec.date_berlaku,
                    'no_spk': rec.no_spk,
                    'tanggal_spk': rec.tanggal_spk,
                })
        
        return records