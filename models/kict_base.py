from odoo import models, fields, api
from datetime import date

class KictBaseMixin(models.AbstractModel):
    """Mixin untuk fitur umum semua dokumen KICT (STNK, SIO, KEUR, IAK)"""
    _name = 'kict.base.mixin'
    _description = 'KICT Base Mixin'

    # Informasi Kendaraan
    fleet_id = fields.Many2one('fleet.vehicle', string="Fleet", required=True, ondelete='cascade')
    license_plate = fields.Char(string="No. Polisi", related='fleet_id.license_plate', readonly=True)
    vin_sn = fields.Char(string="No. Rangka", related='fleet_id.vin_sn', readonly=True)
    engine_number = fields.Char(string="No. Mesin", related='fleet_id.engine_number')
    vehicle_type = fields.Char(string="Tipe Kendaraan", compute='_compute_vehicle_type', store=True)
    color = fields.Char(string="Warna", related='fleet_id.color', readonly=True)

    # Tanggal & Status
    date_terima = fields.Date(string="Tgl. Terima", required=True)
    date_ditetapkan = fields.Date(string="Tanggal Ditetapkan", required=True)
    date_berlaku = fields.Date(string="Tanggal Berlaku", required=True)
    
    # Computed Fields untuk Status
    umur_days = fields.Integer(string="Umur (Hari)", compute='_compute_umur', store=True)
    umur_display = fields.Char(string="Umur", compute='_compute_umur', store=True)
    keterangan = fields.Char(string="Keterangan", compute='_compute_keterangan', store=True)
    status_color = fields.Integer(string="Status Color", compute='_compute_keterangan', store=True)

    # Biaya
    pkb = fields.Float(string="PKB", default=0.0)
    swdkllj = fields.Float(string="SWDKLLJ", default=0.0)
    jasa = fields.Float(string="JASA", default=0.0)
    admin_plat = fields.Float(string="ADMIN PLAT", default=0.0)
    denda = fields.Float(string="DENDA", default=0.0)
    materai = fields.Float(string="MATERAI", default=0.0)
    total = fields.Float(string="Total", compute='_compute_total', store=True)

    # SPK Info
    no_spk = fields.Char(string="No. SPK", readonly=True)
    tanggal_spk = fields.Date(string="Tanggal SPK")
    status_perpanjangan = fields.Selection([
        ('draft', 'Draft'),
        ('butuh_approval', 'Butuh Approval'),
        ('pending', 'Pending'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft')
    notes = fields.Text(string='Catatan')

    @api.depends('fleet_id')
    def _compute_vehicle_type(self):
        for rec in self:
            rec.vehicle_type = rec.fleet_id.model_id.name if rec.fleet_id and rec.fleet_id.model_id else '-'

    @api.depends('pkb', 'swdkllj', 'jasa', 'admin_plat', 'denda', 'materai')
    def _compute_total(self):
        for rec in self:
            rec.total = rec.pkb + rec.swdkllj + rec.jasa + rec.admin_plat + rec.denda + rec.materai

    @api.depends('date_berlaku')
    def _compute_umur(self):
        today = date.today()
        for rec in self:
            if rec.date_berlaku:
                delta = rec.date_berlaku - today
                rec.umur_days = delta.days
                if delta.days < 0:
                    rec.umur_display = f"Lewat {abs(delta.days)} Hari"
                elif delta.days == 0:
                    rec.umur_display = "Hari Ini!"
                else:
                    rec.umur_display = f"Sisa {delta.days} Hari"
            else:
                rec.umur_days = 0
                rec.umur_display = "-"

    @api.depends('umur_days')
    def _compute_keterangan(self):
        for rec in self:
            if rec.umur_days < 0:
                rec.keterangan = "DENDA!!"
                rec.status_color = 1
            elif rec.umur_days <= 30:
                rec.keterangan = "Segera Perpanjang"
                rec.status_color = 3
            elif rec.umur_days <= 60:
                rec.keterangan = "Perhatian"
                rec.status_color = 4
            else:
                rec.keterangan = "Normal"
                rec.status_color = 10

    def _generate_spk_number(self, doc_type):
        """Generate No. SPK dengan format: SPK-001/TYPE/MonYYYY"""
        today = self.tanggal_spk or date.today()
        month_year = today.strftime('%b%Y')
        
        # Cari sequence terakhir
        prefix = f'SPK-'
        existing = self.search([('no_spk', 'like', f'{prefix}%/{doc_type}/')], order='no_spk desc', limit=1)
        
        if existing and existing.no_spk:
            try:
                last_num = int(existing.no_spk.split('-')[1].split('/')[0])
                new_num = last_num + 1
            except:
                new_num = 1
        else:
            new_num = 1
        
        return f"SPK-{str(new_num).zfill(3)}/{doc_type}/{month_year}"


class KictSpkMixin(models.AbstractModel):
    """Mixin untuk model SPK (History Perpanjangan)"""
    _name = 'kict.spk.mixin'
    _description = 'KICT SPK Mixin'

    tanggal_spk = fields.Date(string='Tanggal SPK', required=True)
    no_spk = fields.Char(string='No. SPK', required=True, readonly=True)
    date_ditetapkan = fields.Date(string='Tanggal Ditetapkan', required=True)
    date_berlaku = fields.Date(string='Tanggal Berlaku', required=True)
    
    pkb = fields.Float(string='PKB', default=0.0)
    swdkllj = fields.Float(string='SWDKLLJ', default=0.0)
    jasa = fields.Float(string='JASA', default=0.0)
    admin_plat = fields.Float(string='ADMIN PLAT', default=0.0)
    denda = fields.Float(string='DENDA', default=0.0)
    materai = fields.Float(string='MATERAI', default=0.0)
    total_biaya = fields.Float(string='Total Biaya', compute='_compute_total_biaya', store=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('butuh_approval', 'Butuh Approval'),
        ('pending', 'Pending'),
        ('closed', 'Closed'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft')
    notes = fields.Text(string='Catatan')

    @api.depends('pkb', 'swdkllj', 'jasa', 'admin_plat', 'denda', 'materai')
    def _compute_total_biaya(self):
        for rec in self:
            rec.total_biaya = rec.pkb + rec.swdkllj + rec.jasa + rec.admin_plat + rec.denda + rec.materai