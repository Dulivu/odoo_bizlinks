# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    bz_ws = fields.Char('Bizlink WebService')
    bz_user = fields.Char('Bizlink Usuario')
    bz_pass = fields.Char('Bizlink Contraseña')
    bz_codigo_local_anexo = fields.Char('Codigo Local Anexo')

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        ir = self.env['ir.config_parameter'].sudo()
        ir.set_param('cv_bizlink.bz_ws', self.bz_ws)
        ir.set_param('cv_bizlink.bz_user', self.bz_user)
        ir.set_param('cv_bizlink.bz_pass', self.bz_pass)
        ir.set_param('cv_bizlink.bz_codigo_local_anexo', self.bz_codigo_local_anexo)
        return res

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        ir = self.env['ir.config_parameter'].sudo()
        res.update({
            'bz_ws': ir.get_param('cv_bizlink.bz_ws', False),
            'bz_user': ir.get_param('cv_bizlink.bz_user', False),
            'bz_pass': ir.get_param('cv_bizlink.bz_pass', False),
            'bz_codigo_local_anexo': ir.get_param('cv_bizlink.bz_codigo_local_anexo', False)
        })
        return res
