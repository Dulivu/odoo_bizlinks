# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMoveND(models.TransientModel):
    _name = 'account.move.debit.note'
    _description = 'Nota de débito'

    move_id = fields.Many2one('account.move', string='Journal Entry',
        domain=[('state', '=', 'posted'), ('type', 'in', ('out_invoice'))])
    date = fields.Date(string='Fecha de rectificación', default=fields.Date.context_today, required=True)
    reason = fields.Char('Motivo')
    amount = fields.Float('Monto', digits=(12,2), required=True)

    def _default_journal_id(self):
        ids = self.env.context.get('active_ids')
        if ids:
            moves = self.env['account.move'].search([('id', '=', ids[0])])
            if moves:
                return moves.journal_id.default_nd_journal_id.id
        return False

    journal_id = fields.Many2one('account.journal', string='Usar un diario especifico', required=True, default=_default_journal_id)

    # computed fields
    residual = fields.Monetary(compute="_compute_from_moves")
    currency_id = fields.Many2one('res.currency', compute="_compute_from_moves")
    move_type = fields.Char(compute="_compute_from_moves")

    @api.model
    def default_get(self, fields):
        res = super(AccountMoveND, self).default_get(fields)
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.env['account.move']
        #res['refund_method'] = (len(move_ids) > 1 or move_ids.type == 'entry') and 'cancel' or 'refund'
        res['residual'] = len(move_ids) == 1 and move_ids.amount_residual or 0
        res['currency_id'] = len(move_ids.currency_id) == 1 and move_ids.currency_id.id or False
        res['move_type'] = len(move_ids) == 1 and move_ids.type or False
        res['move_id'] = move_ids[0].id if move_ids else False
        return res

    @api.depends('move_id')
    def _compute_from_moves(self):
        move_ids = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.move_id
        for record in self:
            record.residual = len(move_ids) == 1 and move_ids.amount_residual or 0
            record.currency_id = len(move_ids.currency_id) == 1 and move_ids.currency_id or False
            record.move_type = len(move_ids) == 1 and move_ids.type or False

    def _prepare_default_reversal(self, move):
        return {
            'ref': _('Nota de débito de: %s, %s') % (move.name, self.reason) if self.reason else _('Nota de débito de: %s') % (move.name),
            'date': self.date or move.date,
            'invoice_date': move.is_invoice(include_receipts=True) and (self.date or move.date) or False,
            'journal_id': self.journal_id and self.journal_id.id or move.journal_id.id,
            'invoice_payment_term_id': None,
            'auto_post': False, #True if self.date > fields.Date.context_today(self) else False,
            'invoice_user_id': move.invoice_user_id.id,
            'partner_id': move.partner_id.id,
            'type': 'out_invoice',
            'currency_id': move.currency_id.id,
            #'reversed_entry_id': move.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.env.ref('cv_bizlink.default_product_nd')[0].id,
                'name': 'Ajuste al precio, factura %s' % move.name,
                'quantity': 1,
                'price_unit': self.amount,
                'tax_ids': [(4,self.env.ref('cv_bizlink.default_product_nd')[0].taxes_id[0].id)],
                #'sunat_tax_impact_type': '30'
            })]
        }

    def reverse_moves(self):
        moves = self.env['account.move'].browse(self.env.context['active_ids']) if self.env.context.get('active_model') == 'account.move' else self.move_id
        default_values_list = []
        for move in moves:
            default_values_list.append(self._prepare_default_reversal(move))

        move = self.env['account.move'].create(default_values_list[0])

        return {
            'name': _('Notas de débito'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': move.id,
        }
