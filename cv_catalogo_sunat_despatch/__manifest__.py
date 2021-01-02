# -*- coding: utf-8 -*-
{
    'name' : 'Catalogo Sunat GR',
    'version' : '1.0',
    'summary': 'Catalogo Sunat GR',
    'description': """
Catalogo Sunat
====================
Brinda las tablas y vistas basica del catalogo SUNAT
    """,
    'auto_install': False,
    'category': 'tools',
    'depends' : ['base','account','uom','l10n_pe'],
    'data': [
		#'security/ir.model.access.csv',
        'views/stock_move.xml',
    ],
}
