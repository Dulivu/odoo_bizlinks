# -*- coding: utf-8 -*-
{
    'name' : 'Catalogo Sunat',
    'version' : '1.0',
    'summary': 'Catalogo Sunat',
    'description': """
Catalogo Sunat
====================
Brinda las tablas y vistas basica del catalogo SUNAT
    """,
    'auto_install': False,
    'category': 'tools',
    'depends' : ['base','account','uom'],
    'data': [
		'security/ir.model.access.csv',
        'views/account_move.xml',
        'views/res_company.xml',
        'views/res_partner.xml',
		'views/ubigeos.xml',
		'views/account_journal.xml',
        'views/uom_uom.xml',
    ],
}
