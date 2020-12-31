# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    ubigeo_id = fields.Many2one('ubigeo', string='Ubigeo')
