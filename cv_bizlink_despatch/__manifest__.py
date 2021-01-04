# -*- coding: utf-8 -*-
{
    'name' : 'Bizlink Connector GR',
    'version' : '1.0',
    'summary': 'Bizlink Connector GR',
    'description': """
Bizlink Connector GR
====================
Consume webservices de Bizlinks
    """,
    'auto_install': False,
    'category': 'tools',
    'depends' : ['stock','cv_catalogo_sunat','cv_catalogo_sunat_despatch','cv_bizlink'],
    'data': [
        'views/stock_move.xml'
    ],
}
