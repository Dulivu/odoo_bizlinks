# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    default_nc_journal_id = fields.Many2one('account.journal', string="Notas de crédito", domain=[('sunat_document_type','=','07')])
    default_nd_journal_id = fields.Many2one('account.journal', string="Notas de débito", domain=[('sunat_document_type','=','08')])
