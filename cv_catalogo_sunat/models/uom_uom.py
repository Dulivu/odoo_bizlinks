# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class UOM(models.Model):
	_inherit = 'uom.uom'

	sunat_code = fields.Char('Código SUNAT')
