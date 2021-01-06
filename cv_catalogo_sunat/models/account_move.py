# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountMove(models.Model):
	_inherit = 'account.move'

	sunat_type = fields.Char('Tipo SUNAT', compute='_get_sunat_type', store=True)

	@api.depends('journal_id')
	def _get_sunat_type(self):
		for record in self:
			record.sunat_type = ('07' if record.type == 'out_refund' else record.journal_id.sunat_document_type) or '-'

	sunat_ef_type = fields.Selection([
		('0101', 'Venta Interna'),
		('0102', 'Exportación'),
		('0103', 'No Domiciliados'),
		('0104', 'Venta Interna - Anticipos'),
		('0105', 'Venta Itinerante'),
		('0106', 'Factura Guía'),
		('0107', 'Venta Arroz Pilado'),
		('0108', 'Factura - Comprobante de Percepción'),
		('0110', 'Factura - Guía Remitente'),
		('0111', 'Factura - Guía Transportista')
	], string="Tipo de Factura", default="0101")

	sunat_nc_type = fields.Selection([
		('01', 'Anulación de la operación'),
		('02', 'Anulación por error en el RUC'),
		('03', 'Corrección por error en la descripción'),
		('04', 'Descuento global'),
		('05', 'Descuento por ítem'),
		('06', 'Devolución total'),
		('07', 'Devolución por ítem'),
		('08', 'Bonificación'),
		('09', 'Disminución en el valor')
	], string='Tipo de Nota de Crédito', default="01")

	sunat_nd_type = fields.Selection([
		('01', 'Interes por mora'),
		('02', 'Aumento en el valor')
	], string='Tipo de Nota de Débito', default="01")


class AccountMoveLine(models.Model):
	_inherit = 'account.move.line'

	sunat_uom_code = fields.Char('Código SUNAT', compute='_get_sunat_uom_code')

	@api.depends('product_id', 'product_uom_id')
	def _get_sunat_uom_code(self):
		for record in self:
			if record.product_id and record.product_uom_id:
				record.sunat_uom_code = record.product_uom_id.sunat_code or ('ZZ' if record.product_id.type == 'service' else 'NIU')
			else:
				record.sunat_uom_code = '-'

	sunat_tax_impact_type = fields.Selection([
		('10', 'Gravado -  Operación Onerosa'),
		('11', 'Gravado – Retiro por premio'),
		('12', 'Gravado – Retiro por donación'),
		('13', 'Gravado – Retiro'),
		('14', 'Gravado – Retiro por publicidad'),
		('15', 'Gravado – Bonificaciones'),
		('16', 'Gravado – Retiro por entrega a trabajadores'),
		('20', 'Exonerado - Operación Onerosa'),
		('30', 'Inafecto - Operación Onerosa'),
		('31', 'Inafecto – Retiro por Bonificación'),
		('32', 'Inafecto – Retiro'),
		('33', 'Inafecto – Retiro por Muestras Médicas'),
		('34', 'Inafecto -  Retiro por Convenio Colectivo'),
		('35', 'Inafecto – Retiro por premio'),
		('36', 'Inafecto -  Retiro por publicidad'),
		('40', 'Exportación')
	], string='Tipo de afectación IGV', default='10')
