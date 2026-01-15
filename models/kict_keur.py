from odoo import models, fields, api
from datetime import date

class KictKeur(models.Model):
    _name = 'kict.keur'
    _inherit = ['kict.base.mixin']
    _description = 'KICT KEUR Kendaraan'
    _order = 'date_berlaku desc'

    # Field khusus KEUR
    no_keur = fields.Char(string="No. KEUR", required=True)
    jenis_uji = fields.Selection([
        ('berkala', 'Uji Berkala'),
        ('pertama', 'Uji Pertama'),
        ('khusus', 'Uji Khusus')
    ], string="Jenis Uji", default='berkala')
    hasil_uji = fields.Selection([
        ('lulus', 'Lulus'),
        ('tidak_lulus', 'Tidak Lulus'),
        ('pending', 'Pending')
    ], string="Hasil Uji", default='pending')
    
    # Relasi ke SPK
    spk_ids = fields.One2many('kict.keur.spk', 'keur_id', string='History SPK')
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
                rec.no_spk = rec._generate_spk_number('KEUR')
                self.env['kict.keur.spk'].create({
                    'keur_id': rec.id,
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
            'name': 'History SPK KEUR',
            'type': 'ir.actions.act_window',
            'res_model': 'kict.keur.spk',
            'view_mode': 'tree,form',
            'domain': [('keur_id', '=', self.id)],
            'context': {'default_keur_id': self.id},
        }


class KictKeurSpk(models.Model):
    _name = 'kict.keur.spk'
    _inherit = ['kict.spk.mixin']
    _description = 'SPK Perpanjangan KEUR'
    _order = 'tanggal_spk desc'

    keur_id = fields.Many2one('kict.keur', string='KEUR Reference', required=True, ondelete='cascade')
    
    fleet_id = fields.Many2one(related='keur_id.fleet_id', store=True)
    license_plate = fields.Char(related='keur_id.license_plate', store=True)
    no_keur = fields.Char(related='keur_id.no_keur', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('no_spk') and vals.get('tanggal_spk'):
                tanggal = fields.Date.from_string(vals['tanggal_spk'])
                month_year = tanggal.strftime('%b%Y')
                
                existing = self.search([('no_spk', 'like', 'SPK-%/KEUR/')], order='id desc', limit=1)
                if existing and existing.no_spk:
                    try:
                        last_num = int(existing.no_spk.split('-')[1].split('/')[0])
                        new_num = last_num + 1
                    except:
                        new_num = 1
                else:
                    new_num = 1
                
                vals['no_spk'] = f"SPK-{str(new_num).zfill(3)}/KEUR/{month_year}"
        
        records = super().create(vals_list)
        
        for rec in records:
            if rec.keur_id:
                rec.keur_id.write({
                    'date_ditetapkan': rec.date_ditetapkan,
                    'date_berlaku': rec.date_berlaku,
                    'no_spk': rec.no_spk,
                    'tanggal_spk': rec.tanggal_spk,
                })
        
        return records