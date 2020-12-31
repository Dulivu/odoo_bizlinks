# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    sunat_document_type = fields.Selection([
        ('01', 'Factura'),
        ('03', 'Boleta de venta'),
        ('07', 'Nota de crédito'), # una nota de crédito será normalmente una factura rectificativa
        ('08', 'Nota de débito')
    ], string='Tipo de documento SUNAT', help='Llenar este campo sólo para el caso de Facturas, Boletas ó Notas de débito. Para Notas de crédito se usará automáticamente el valor 07 no requiere un diario contable')
