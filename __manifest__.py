{
    'name': 'KICT Document Upload to GDrive',
    'version': '2.0',
    'summary': 'Upload dan Preview Dokumen ke Google Drive berdasarkan kategori dan tahun',
    'description': """
        Modul ini mengintegrasikan Odoo dengan Google Drive untuk mengunggah dokumen fleet,
        menyimpannya berdasarkan kategori dan tahun, serta menampilkan preview dokumen di Odoo.
    """,
    'author': 'KICT Dev Team',
    'category': 'Document Management',
    'depends': ['fleet', 'base', 'fleet_extended_version'],
    'images': ['static/description/icon.png'],
    'data': [
        'security/ir.model.access.csv',
        'views/kict_document_views.xml',
        'views/kict_stnk_views.xml',
        'views/kict_sio_views.xml',
        'views/kict_keur_views.xml',
        'views/kict_iak_views.xml',
        
    ],
    'external_dependencies': {
        'python': ['google-auth', 'google-auth-oauthlib', 'google-api-python-client'],
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
