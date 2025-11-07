{
    'name': 'KICT Document Upload GDrive',
    'version': '1.0',
    'summary': 'Upload dan Preview Dokumen ke Google Drive berdasarkan kategori dan tahun',
    'description': """
        Modul ini mengintegrasikan Odoo dengan Google Drive untuk mengunggah dokumen fleet,
        menyimpannya berdasarkan kategori dan tahun, serta menampilkan preview dokumen di Odoo.
    """,
    'author': 'KICT Dev Team',
    'category': 'Document Management',
    'depends': ['fleet', 'base'],
    'data': [
        'security/ir.model.access.csv',
        'views/kict_document_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
