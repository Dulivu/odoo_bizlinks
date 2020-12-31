# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResPartner(models.Model):
	_inherit = 'res.partner'

	ubigeo_id = fields.Many2one('ubigeo', string='Ubigeo')
	vat = fields.Char(required=True)

	# TODO: este campo aun no se utiliza
	cid_code = fields.Selection([
		('0', 'DOC.TRIB.NO.DOM.SIN.RUC'),
		('1', 'DOC. NACIONAL DE IDENTIDAD'),
		('4', 'CARNET DE EXTRANJERIA'),
		('6', 'REG. UNICO DE CONTRIBUYENTES'),
		('7', 'PASAPORTE'),
		('A', 'CED. DIPLOMATICA DE IDENTIDAD')
	], string='Tipo de documento de identidad')
