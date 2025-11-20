from odoo import models, fields, api
from datetime import date, timedelta

class KictNotice(models.Model):
    _name = 'kict.notice'
    _description = 'KICT Notice Kendaraan'
    _order = 'date_berlaku desc'

    # Informasi Kendaraan
    fleet_id = fields.Many2one('fleet.vehicle', string="Fleet", required=True, ondelete='cascade')
    license_plate = fields.Char(string="No. Polisi", related='fleet_id.license_plate', readonly=True)
    vin_sn = fields.Char(string="No. Rangka", related='fleet_id.vin_sn', readonly=True)
    engine_number = fields.Char(string="No. Mesin", compute='_compute_engine_number', store=True)
    vehicle_type = fields.Char(string="Tipe Kendaraan", compute='_compute_vehicle_type', store=True)
    color = fields.Char(string="Warna", related='fleet_id.color', readonly=True)
    
    # Informasi STNK
    date_terima_stnk = fields.Date(string="Tgl. Terima STNK", required=True)
    no_stnk = fields.Char(string="No. STNK", required=True)
    fuel_type = fields.Selection([
        ('gasoline', 'Bensin'),
        ('diesel', 'Diesel'),
        ('electric', 'Listrik'),
        ('hybrid', 'Hybrid')
    ], string="Bahan Bakar", required=True)
    date_ditetapkan = fields.Date(string="Tanggal Ditetapkan", required=True, store=True)
    cylinder = fields.Integer(string="Cylinder", required=True, store=True)
    date_berlaku = fields.Date(string="Tanggal Berlaku", required=True,  store=True)
    
    # Informasi Biaya
    pkb = fields.Float(string="PKB", default=0.0)
    swdkllj = fields.Float(string="SWDKLLJ", default=0.0)
    jasa = fields.Float(string="JASA", default=0.0)
    admin_plat = fields.Float(string="ADMIN PLAT", default=0.0)
    denda = fields.Float(string="DENDA", default=0.0)
    materai = fields.Float(string="MATERAI", default=0.0)
    total = fields.Float(string="Total", compute='_compute_total', store=True)
    
    # Fields untuk Master Data
    umur_days = fields.Integer(string="Umur (Hari)", compute='_compute_umur', store=True)
    umur_display = fields.Char(string="Umur", compute='_compute_umur', store=True)
    keterangan = fields.Char(string="Keterangan", compute='_compute_keterangan', store=True)
    status_color = fields.Integer(string="Status Color", compute='_compute_keterangan', store=True)

      # Informasi SIO
    date_terima_SIO = fields.Date(string="Tgl. Terima SIO", required=True)
    date_ditetapkan_SIO = fields.Date(string="Tanggal Ditetapkan", required=True, store=True)
    sum_admin_SIO = fields.Integer(string="Jumlah Admin SIO", required=True, store=True)
    date_berlaku_SIO = fields.Date(string="Tanggal Berlaku", required=True,  store=True)

    # Informasi KEUR
    date_terima_KEUR = fields.Date(string="Tgl. Terima KEUR", required=True)
    date_ditetapkan_KEUR = fields.Date(string="Tanggal Ditetapkan", required=True, store=True)
    sum_admin_SIO = fields.Integer(string="Nilai Administrasi KEUR", required=True, store=True)
    date_berlaku_KEUR = fields.Date(string="Tanggal Berlaku", required=True,  store=True)

     # Informasi Izin Angkut
    date_terima_IAK = fields.Date(string="Tgl. Terima IAK", required=True)
    date_ditetapkan_IAK = fields.Date(string="Tanggal Ditetapkan", required=True, store=True)
    sum_admin_IAK = fields.Integer(string="Jumlah Izin Angkut", required=True, store=True)
    date_berlaku_IAK = fields.Date(string="Tanggal Berlaku", required=True,  store=True)

    # Informasi SPK
    nilai_pengajuan_spk = fields.Integer(string="Nilai Pengajuan", required=True, store=True)

    @api.depends('fleet_id')
    def _compute_engine_number(self):
        for record in self:
            # Ambil dari model fleet jika ada field model_id
            if record.fleet_id and hasattr(record.fleet_id, 'model_id'):
                record.engine_number = record.fleet_id.model_id.name if record.fleet_id.model_id else '-'
            else:
                record.engine_number = '-'

    @api.depends('fleet_id')
    def _compute_vehicle_type(self):
        for record in self:
            if record.fleet_id and hasattr(record.fleet_id, 'model_id'):
                record.vehicle_type = record.fleet_id.model_id.name if record.fleet_id.model_id else '-'
            else:
                record.vehicle_type = '-'

    @api.depends('pkb', 'swdkllj', 'jasa', 'admin_plat', 'denda', 'materai')
    def _compute_total(self):
        for record in self:
            record.total = (
                record.pkb + 
                record.swdkllj + 
                record.jasa + 
                record.admin_plat + 
                record.denda + 
                record.materai
            )

    @api.depends('date_ditetapkan', 'date_berlaku')
    def _compute_umur(self):
        for record in self:
            if record.date_ditetapkan and record.date_berlaku:
                delta = record.date_berlaku - record.date_ditetapkan
                record.umur_days = delta.days
                
                if delta.days < 0:
                    record.umur_display = f"Lewat {abs(delta.days)} Hari"
                elif delta.days == 0:
                    record.umur_display = "Hari Ini"
                else:
                    record.umur_display = f"{delta.days} Hari"
            else:
                record.umur_days = 0
                record.umur_display = "-"

    @api.depends('umur_days')
    def _compute_keterangan(self):
        for record in self:
            if record.umur_days < 0:
                record.keterangan = "DENDA!!"
                record.status_color = 1  # Red
            elif record.umur_days <= 30:
                record.keterangan = "Segera Perpanjang"
                record.status_color = 3  # Orange
            elif record.umur_days <= 60:
                record.keterangan = "Perhatian"
                record.status_color = 4  # Yellow
            else:
                record.keterangan = "Normal"
                record.status_color = 10  # Green