# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.tools.translate import _


class AccountMoveReversal(models.TransientModel):
    _inherit = 'account.move.reversal'

    def _default_journal_id(self):
        ids = self.env.context.get('active_ids')
        if ids:
            moves = self.env['account.move'].search([('id', '=', ids[0])])
            if moves:
                return moves.journal_id.default_nc_journal_id.id
        return False

    journal_id = fields.Many2one(default=_default_journal_id)
