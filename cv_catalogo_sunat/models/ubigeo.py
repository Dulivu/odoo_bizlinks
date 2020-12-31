# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class Ubigeo(models.Model):
    _name = 'ubigeo'

    name = fields.Char('Descripción')
    code = fields.Char('Codigo')