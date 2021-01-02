# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = 'stock.picking'

    sunat_origin_type = fields.Selection([
        ('01', 'Número DAM'),
        ('02', 'Número de orden de entrega'),
        ('03', 'Número Scop'),
        ('04', 'Número de manifiesto de carga'),
        ('05', 'Número de constancia de detraccion'),
        ('06', 'Otros')
    ], string="Tipo de documento de origen SUNAT")

    sunat_transfer_reason = fields.Selection([
        ('01', 'Venta'),
        ('14', 'Venta sujeta a confirmacion del comprador'),
        ('02', 'Compra'),
        ('04', 'Traslado entre establecimiento de la misma empresa'),
        ('18', 'Traslado emisor itinerante CP'),
        ('08', 'Importacion'),
        ('09', 'Exportacion'),
        ('19', 'Traslado a zona primaria'),
        ('13', 'Otros'),
    ], string="Motivo del traslado SUNAT")

    sunat_transfer_type = fields.Selection([
        ('01', 'Transporte público'),
        ('02', 'Transporte privado')
    ], string="Modalidad de traslado SUNAT")

    def _default_transfer_id(self):
        for record in self:
            if record.picking_type_id:
                record.sunat_transfer_id = record.picking_type_id.warehouse_id.partner_id

    sunat_transfer_id = fields.Many2one('res.partner', 'Transportista', default=_default_transfer_id)

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    sunat_uom_code = fields.Char('Código SUNAT', compute='_get_sunat_uom_code')
    sunat_weigth = fields.Float('Peso', digits=(12,2), compute='_get_sunat_weigth')

    @api.depends('product_id', 'product_uom_id')
    def _get_sunat_uom_code(self):
        for record in self:
            if record.product_id and record.product_uom_id:
                record.sunat_uom_code = record.product_uom_id.sunat_code or ('ZZ' if record.product_id.type == 'service' else 'NIU')
            else:
                record.sunat_uom_code = '-'

    @api.depends('product_id', 'product_uom_id', 'qty_done')
    def _get_sunat_weigth(self):
        for record in self:
            if record.product_id and record.product_uom_id:
                total = record.product_uom_id._compute_quantity(record.qty_done, record.product_id.uom_id)
                record.sunat_weigth = record.product_id.weight * total
            else:
                record.sunat_weigth = 0.0
