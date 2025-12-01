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
    engine_number = fields.Char(string="No. Mesin",related='fleet_id.engine_number')
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
    date_berlaku = fields.Date(string="Tanggal Berlaku", required=True, store=True)
    
    # Informasi SPK untuk Perpanjangan
    tanggal_spk = fields.Date(string="Tanggal SPK")
    no_spk = fields.Char(string="No. SPK")
    status_perpanjangan = fields.Selection([
        ('closed', 'Closed'),
        ('butuh_approval', 'Butuh Approval'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected')
    ], string='Status Perpanjangan', default='butuh_approval')
    notes = fields.Text(string='Catatan')
    
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
    date_terima_SIO = fields.Date(string="Tgl. Terima SIO")
    date_ditetapkan_SIO = fields.Date(string="Tanggal Ditetapkan SIO", store=True)
    sum_admin_SIO = fields.Float(string="Jumlah Admin SIO", store=True)
    date_berlaku_SIO = fields.Date(string="Tanggal Berlaku SIO", store=True)

    # Informasi KEUR
    date_terima_KEUR = fields.Date(string="Tgl. Terima KEUR")
    date_ditetapkan_KEUR = fields.Date(string="Tanggal Ditetapkan KEUR", store=True)
    sum_admin_KEUR = fields.Float(string="Nilai Administrasi KEUR", store=True)
    date_berlaku_KEUR = fields.Date(string="Tanggal Berlaku KEUR", store=True)

    # Informasi Izin Angkut
    date_terima_IAK = fields.Date(string="Tgl. Terima IAK")
    date_ditetapkan_IAK = fields.Date(string="Tanggal Ditetapkan IAK", store=True)
    sum_admin_IAK = fields.Float(string="Jumlah Izin Angkut", store=True)
    date_berlaku_IAK = fields.Date(string="Tanggal Berlaku IAK", store=True)

    # Informasi SPK
    nilai_pengajuan_spk = fields.Float(string="Nilai Pengajuan", store=True)
    
    # Relasi ke history perpanjangan
    renewal_ids = fields.One2many('kict.notice.renewal', 'notice_id', string='History Perpanjangan')
    renewal_count = fields.Integer(string='Jumlah Perpanjangan', compute='_compute_renewal_count')

    @api.depends('fleet_id')
    def _compute_engine_number(self):
        for record in self:
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
                record.pkb + record.swdkllj + record.jasa + 
                record.admin_plat + record.denda + record.materai
            )

    @api.depends('date_berlaku')
    def _compute_umur(self):
        """Hitung sisa hari dari hari ini sampai tanggal berlaku (kadaluarsa)"""
        today = date.today()
        for record in self:
            if record.date_berlaku:
                # Hitung selisih dari hari ini ke tanggal berlaku
                delta = record.date_berlaku - today
                record.umur_days = delta.days
                
                if delta.days < 0:
                    # Sudah lewat tanggal berlaku (kadaluarsa)
                    record.umur_display = f"Lewat {abs(delta.days)} Hari"
                elif delta.days == 0:
                    record.umur_display = "Hari Ini (Segera Perpanjang!)"
                else:
                    # Masih ada sisa hari
                    record.umur_display = f"Sisa {delta.days} Hari"
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
    
    @api.depends('renewal_ids')
    def _compute_renewal_count(self):
        for record in self:
            record.renewal_count = len(record.renewal_ids)
    
    def action_view_renewals(self):
        """Method untuk membuka history perpanjangan dari smart button"""
        self.ensure_one()
        return {
            'name': 'History Perpanjangan',
            'type': 'ir.actions.act_window',
            'res_model': 'kict.notice.renewal',
            'view_mode': 'tree,form',
            'domain': [('notice_id', '=', self.id)],
            'context': {'default_notice_id': self.id},
            'target': 'current',
        }
    
    @api.model_create_multi
    def create(self, vals_list):
        """Override create untuk otomatis membuat record di renewal ketika ada biaya"""
        records = super(KictNotice, self).create(vals_list)
        for record in records:
            # Cek apakah ada data biaya yang diinput
            if record.tanggal_spk and record.no_spk and record.total > 0:
                # Buat record di kict.notice.renewal
                self.env['kict.notice.renewal'].create({
                    'notice_id': record.id,
                    'tanggal_spk': record.tanggal_spk,
                    'no_spk': record.no_spk,
                    'date_ditetapkan': record.date_ditetapkan,
                    'date_berlaku': record.date_berlaku,
                    'pkb': record.pkb,
                    'swdkllj': record.swdkllj,
                    'jasa': record.jasa,
                    'admin_plat': record.admin_plat,
                    'denda': record.denda,
                    'materai': record.materai,
                    'keterangan': record.status_perpanjangan,
                    'notes': record.notes,
                })
        return records
    
    def write(self, vals):
        """Override write untuk update/create renewal ketika data biaya berubah"""
        result = super(KictNotice, self).write(vals)
        
        # Cek apakah ada perubahan pada biaya atau SPK
        biaya_fields = ['pkb', 'swdkllj', 'jasa', 'admin_plat', 'denda', 'materai', 
                       'tanggal_spk', 'no_spk', 'status_perpanjangan', 'notes',
                       'date_ditetapkan', 'date_berlaku']
        
        if any(field in vals for field in biaya_fields):
            for record in self:
                if record.tanggal_spk and record.no_spk and record.total > 0:
                    # Cek apakah sudah ada renewal dengan SPK yang sama
                    existing_renewal = self.env['kict.notice.renewal'].search([
                        ('notice_id', '=', record.id),
                        ('no_spk', '=', record.no_spk)
                    ], limit=1)
                    
                    renewal_vals = {
                        'tanggal_spk': record.tanggal_spk,
                        'no_spk': record.no_spk,
                        'date_ditetapkan': record.date_ditetapkan,
                        'date_berlaku': record.date_berlaku,
                        'pkb': record.pkb,
                        'swdkllj': record.swdkllj,
                        'jasa': record.jasa,
                        'admin_plat': record.admin_plat,
                        'denda': record.denda,
                        'materai': record.materai,
                        'keterangan': record.status_perpanjangan,
                        'notes': record.notes,
                    }
                    
                    if existing_renewal:
                        # Update existing renewal
                        existing_renewal.write(renewal_vals)
                    else:
                        # Create new renewal
                        renewal_vals['notice_id'] = record.id
                        self.env['kict.notice.renewal'].create(renewal_vals)
        
        return result


class KictNoticeRenewal(models.Model):
    """Model untuk History Perpanjangan Pajak"""
    _name = 'kict.notice.renewal'
    _description = 'History Perpanjangan Pajak Kendaraan'
    _order = 'tanggal_spk desc'

    notice_id = fields.Many2one('kict.notice', string='Notice Reference', required=True, ondelete='cascade')
    tanggal_spk = fields.Date(string='Tanggal SPK', required=True)
    no_spk = fields.Char(string='No. SPK', required=True)
    date_ditetapkan = fields.Date(string='Tanggal Ditetapkan', required=True)
    date_berlaku = fields.Date(string='Tanggal Berlaku', required=True)
    
    # Biaya Detail
    pkb = fields.Float(string='PKB', default=0.0)
    swdkllj = fields.Float(string='SWDKLLJ', default=0.0)
    jasa = fields.Float(string='JASA', default=0.0)
    admin_plat = fields.Float(string='ADMIN PLAT', default=0.0)
    denda = fields.Float(string='DENDA', default=0.0)
    materai = fields.Float(string='MATERAI', default=0.0)
    biaya_estimasi = fields.Float(string='Biaya Estimasi', compute='_compute_biaya_estimasi', store=True)
    
    keterangan = fields.Selection([
        ('closed', 'Closed'),
        ('butuh_approval', 'Butuh Approval'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected')
    ], string='Keterangan', default='butuh_approval')
    
    notes = fields.Text(string='Catatan')

    @api.depends('pkb', 'swdkllj', 'jasa', 'admin_plat', 'denda', 'materai')
    def _compute_biaya_estimasi(self):
        for record in self:
            record.biaya_estimasi = (
                record.pkb + record.swdkllj + record.jasa + 
                record.admin_plat + record.denda + record.materai
            )