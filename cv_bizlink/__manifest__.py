# -*- coding: utf-8 -*-
{
    'name' : 'Bizlink Connector',
    'version' : '1.0',
    'summary': 'Bizlink Connector',
    'description': """
Bizlink Connector
====================
Consume webservices de Bizlinks
    """,
    'auto_install': False,
    'category': 'tools',
    'depends' : ['account','l10n_pe','cv_catalogo_sunat'],
    'data': [
        'views/account_move.xml',
        'views/res_settings.xml',
    ],
}
