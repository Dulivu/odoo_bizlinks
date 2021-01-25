# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from xml.dom.minidom import Element, Text, parseString
from re import search
import requests
from datetime import datetime
from pytz import timezone


def createElement(dom, tag, text=False):
	el = dom.createElement(tag)
	if text:
		tx = dom.createTextNode(str(text))
		el.appendChild(tx)
	return el

def createSoapEnvelope():
	dom = parseString('<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.ce.ebiz.com/"></soapenv:Envelope>')
	header = dom.createElement('soapenv:Header')
	command = dom.createElement('command')
	invoker = dom.createElement('ws:invoke')
	body = dom.createElement('soapenv:Body')

	dom.childNodes[0].appendChild(header)
	dom.childNodes[0].appendChild(body)

	body.appendChild(invoker)
	invoker.appendChild(command)

	return dom, header, command

def numberToLetters(num):
	parts = str(float(num)).split('.')
	num = int(parts[0])
	if num > 999999:
		raise UserError('El monto es demasiado alto')
	lnum = [int(x) for x in str(num)]
	lnum = lnum[::-1]
	letters = list()

	UNIDADES = ('', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve')
	DECENAS = ('diez', 'once', 'doce', 'trece', 'catorce', 'quince', 'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve')
	DIECES = ('', '', '', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa')
	CIENTOS = ('', 'ciento', 'doscientos', 'trescientos', 'cuatroscientos', 'quinientos', 'seiscientos', 'setecientos', 'ochocientos', 'novecientos')

	for i in range(len(lnum)):
		if i in [0, 3]: # UNIDADES
			if i == 3:
				letters.append('mil')
			if not(lnum[i] == 1 and i == 3):
				letters.append(UNIDADES[lnum[i]])
		if i in [1, 4]: # DECENAS
			if lnum[i] == 1:
				letters[-1] = DECENAS[lnum[i-1]]
			elif lnum[i] == 2:
				letters[-1] = 'veinti%s' % UNIDADES[lnum[i-1]] if lnum[0] > 0 else 'veinte'
			elif lnum[i] > 2:
				letters.append('y' if lnum[i-1] > 0  else '')
				letters.append(DIECES[lnum[i]])
		if i in [2, 5]: # CENTENAS
			cos, res = divmod(num, 100)
			if cos == 1 and res == 0:
				letters.append('cien')
			else:
				letters.append(CIENTOS[lnum[i]])
	letters = list(filter(lambda x: x, letters))
	return ' '.join(letters[::-1]).strip() + ' con ' + parts[1].ljust(2, '0') + '/100 SOLES'


class AccountMove(models.Model):
	_inherit = 'account.move'

	efact_state = fields.Selection([
		('unpublished', 'No publicado'),
		('published', 'Publicado'),
		('declared', 'Declarado'),
		('cancel', 'Anulado'),
	], string="eFact Estado", default='unpublished', copy=False)

	bz_signatura_value = fields.Char('Firma', copy=False)
	bz_hash_code = fields.Char('Codigo HASH', copy=False)
	bz_file_sign_url = fields.Char('Ruta XML', copy=False)
	bz_file_pdf_url = fields.Char('Factura PDF', copy=False)
	bz_file_gif_url = fields.Char('Ruta Codigo', copy=False)
	bz_file_qr_url = fields.Char('Ruta QR', copy=False)

	cancel_date = fields.Date('Fecha de Baja')
	cancel_id = fields.Char('Resumen ID')
	discount_total = fields.Float('Descuento Total', digits=(12,2), compute='_get_total_discount')

	def _get_total_discount(self):
		for me in self:
			total = 0
			for line in me.invoice_line_ids:
				total = total + line.importeDescuento
			me.discount_total = total

	def _get_default_journal_id(self):
		sunat_type = self.env.context.get('sunat_type') or False
		if sunat_type:
			journal = self.env['account.journal'].search([('sunat_document_type', '=', sunat_type)])
			return journal[0].id if journal else False
		else:
			journal = self.env['account.journal'].search([('type', '=', 'sale' if self.type else 'purchase')])
			return journal[0].id if journal else False

	journal_id = fields.Many2one(default=_get_default_journal_id)

	def cancelCmd(self):
		vat = self.company_id.vat

		dom, header, command = createSoapEnvelope()

		soapCommand = dom.createElement('AnularCmd')
		soapCommand.appendChild(dom.createElement('parametros'))

		param = dom.createElement('parameter')
		param.setAttribute('value', vat)
		param.setAttribute('name', 'idEmisor')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.sunat_type)
		param.setAttribute('name', 'tipoDocumento')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.journal_id.code)
		param.setAttribute('name', 'serieGrupoDocumento')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.name.split('-')[1]) # self.name[-8:]
		param.setAttribute('name', 'numeroCorrelativoInicio')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.name.split('-')[1])
		param.setAttribute('name', 'numeroCorrelativoFin')
		soapCommand.appendChild(param)

		return dom, command, soapCommand

	def consultCmd(self):
		vat = self.company_id.vat

		dom, header, command = createSoapEnvelope()

		soapCommand = dom.createElement('ConsultCmd')
		soapCommand.appendChild(dom.createElement('parametros'))

		param = dom.createElement('parameter')
		param.setAttribute('value', vat)
		param.setAttribute('name', 'idEmisor')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.sunat_type)
		param.setAttribute('name', 'tipoDocumento')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.journal_id.code)
		param.setAttribute('name', 'serieGrupoDocumento')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.name.split('-')[1])
		param.setAttribute('name', 'numeroCorrelativoInicio')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.name.split('-')[1])
		param.setAttribute('name', 'numeroCorrelativoFin')
		soapCommand.appendChild(param)

		return dom, command, soapCommand

	def declareCmd(self):
		vat = self.company_id.vat

		dom, header, command = createSoapEnvelope()

		soapCommand = dom.createElement('DeclareCmd')
		soapCommand.appendChild(dom.createElement('parametros'))

		param = dom.createElement('parameter')
		param.setAttribute('value', vat)
		param.setAttribute('name', 'idEmisor')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.sunat_type)
		param.setAttribute('name', 'tipoDocumento')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.journal_id.code)
		param.setAttribute('name', 'serieGrupoDocumento')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.name.split('-')[1])
		param.setAttribute('name', 'numeroCorrelativoInicio')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.name.split('-')[1])
		param.setAttribute('name', 'numeroCorrelativoFin')
		soapCommand.appendChild(param)

		return dom, command, soapCommand

	def signOnLineSummaryCmd(self):
		vat = self.company_id.vat

		dom, header, command = createSoapEnvelope()

		soapCommand = dom.createElement('SignOnLineSummaryCmd')
		soapCommand.appendChild(dom.createElement('parametros'))

		param = dom.createElement('parameter')
		param.setAttribute('value', vat)
		param.setAttribute('name', 'idEmisor')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', 'RA')
		param.setAttribute('name', 'tipoDocumento')
		soapCommand.appendChild(param)

		return dom, command, soapCommand

	def signOnLineCmd(self):
		vat = self.company_id.vat

		dom, header, command = createSoapEnvelope()

		soapCommand = dom.createElement('SignOnLineCmd')
		soapCommand.appendChild(dom.createElement('parametros'))

		param = dom.createElement('parameter')
		param.setAttribute('value', vat)
		param.setAttribute('name', 'idEmisor')
		soapCommand.appendChild(param)

		param = dom.createElement('parameter')
		param.setAttribute('value', self.sunat_type)
		param.setAttribute('name', 'tipoDocumento')
		soapCommand.appendChild(param)

		return dom, command, soapCommand

	def writeXmlDocumentCancel(self, dom, soapCommand):
		document = dom.createElement('documento')

		document.appendChild(createElement(dom, 'numeroDocumentoEmisor', self.company_id.vat))
		document.appendChild(createElement(dom, 'version', '1.0'))
		document.appendChild(createElement(dom, 'versionUBL', '2.0'))
		document.appendChild(createElement(dom, 'tipoDocumentoEmisor', '6'))
		document.appendChild(createElement(dom, 'resumenId', self._get_next_ra_code()))
		document.appendChild(createElement(dom, 'fechaEmisionComprobante', self.invoice_date))
		document.appendChild(createElement(dom, 'fechaGeneracionResumen', fields.Date.context_today(self)))
		document.appendChild(createElement(dom, 'razonSocialEmisor', self.company_id.company_registry))
		document.appendChild(createElement(dom, 'correoEmisor', self.company_id.email))
		document.appendChild(createElement(dom, 'inHabilitado', '1'))
		document.appendChild(createElement(dom, 'resumenTipo', 'RA'))

		resumen = dom.createElement('ResumenItem')
		document.appendChild(resumen)

		resumen.appendChild(createElement(dom, 'numeroFila', '1'))
		resumen.appendChild(createElement(dom, 'tipoDocumento', self.sunat_type))
		resumen.appendChild(createElement(dom, 'serieDocumentoBaja', self.name.split('-')[0]))
		resumen.appendChild(createElement(dom, 'numeroDocumentoBaja', self.name.split('-')[1]))
		resumen.appendChild(createElement(dom, 'motivoBaja', 'ANULACION'))

		soapCommand.appendChild(document)

	def writeXmlDocument(self, dom, soapCommand):
		if not self.journal_id.sunat_document_type:
			raise UserError('El diario debe tener registrado un tipo de documento SUNAT')
		if not self.company_id.ubigeo_id:
			raise UserError('La compañía no tiene registrado un ubigeo')
		if not self.company_id.country_id:
			raise UserError('La compañía no tiene registrado un país')

		if not self.partner_id.vat:
			raise UserError('El cliente no tiene registrado documento de identificación')
		if self.sunat_type != '03' and not self.partner_id.ubigeo_id:
			raise UserError('El cliente no tiene registrado un ubigeo')
		if self.sunat_type != '03' and not self.partner_id.country_id:
			raise UserError('El cliente no tiene registrado un país')

		em_ubi = self.company_id.ubigeo_id.name.split('-')
		ad_ubi = self.partner_id.ubigeo_id.name.split('-')
		ref = '-'

		document = dom.createElement('documento')

		# campos Bizlinks
		document.appendChild(createElement(dom, 'correoEmisor', self.company_id.email))
		document.appendChild(createElement(dom, 'correoAdquiriente', self.partner_id.email))
		document.appendChild(createElement(dom, 'inHabilitado', '1')) # TODO

		# datos de la factura electronica
		document.appendChild(createElement(dom, 'serieNumero', self.name or self.invoice_sequence_number_next_prefix + self.invoice_sequence_number_next)) #FXXX-NNNNNNNN
		document.appendChild(createElement(dom, 'fechaEmision', self.invoice_date)) # YYYY-MM-DD
		document.appendChild(createElement(dom, 'tipoDocumento', self.sunat_type)) # catalogo 1
		document.appendChild(createElement(dom, 'tipoMoneda', self.currency_id.name)) # catalogo 2
		if self.sunat_type == '01' or self.sunat_type == '03':
			document.appendChild(createElement(dom, 'tipoOperacion', self.sunat_ef_type)) # catalogo 51
			if self.ref:
				document.appendChild(createElement(dom, 'tipoReferencia_1', '09'))
				document.appendChild(createElement(dom, 'numeroDocumentoReferencia_1', self.ref))
		if self.sunat_type == '07' or self.sunat_type == '08':
			document.appendChild(createElement(dom, 'codigoSerieNumeroAfectado', self.sunat_nc_type))
			if self.reversed_entry_id:
				ref = self.reversed_entry_id.name
				ref_type = self.reversed_entry_id.journal_id.sunat_document_type
			else:
				ref = search('[a-zA-Z0-9]{4}-[0-9]{8}', self.ref)
				ref = ref.group(0) if ref else '-'
				ref_type = '01' if ref[0] == 'F' else '03'
			document.appendChild(createElement(dom, 'serieNumeroAfectado', ref))
			document.appendChild(createElement(dom, 'motivoDocumento', self.ref.split(', ')[1] or '-'))
			document.appendChild(createElement(dom, 'tipoDocumentoReferenciaPrincipal', ref_type))
			document.appendChild(createElement(dom, 'numeroDocumentoReferenciaPrincipal', ref))

		# datos del emisor
		document.appendChild(createElement(dom, 'tipoDocumentoEmisor', '6')) # catalogo 6 (documento de identidad)
		document.appendChild(createElement(dom, 'numeroDocumentoEmisor', self.company_id.vat))
		document.appendChild(createElement(dom, 'nombreComercialEmisor', self.company_id.name))
		document.appendChild(createElement(dom, 'razonSocialEmisor', self.company_id.company_registry))
		document.appendChild(createElement(dom, 'ubigeoEmisor', self.company_id.ubigeo_id.code)) # No obligatorio para boletas
		document.appendChild(createElement(dom, 'direccionEmisor', self.company_id.street or '-')) # No obligatorio para boletas
		document.appendChild(createElement(dom, 'urbanizacion', self.company_id.street2 or '-')) # No obligatorio para boletas
		document.appendChild(createElement(dom, 'provinciaEmisor', em_ubi[1] or '-')) # No obligatorio para boletas
		document.appendChild(createElement(dom, 'departamentoEmisor', em_ubi[0] or '-')) # No obligatorio para boletas
		document.appendChild(createElement(dom, 'distritoEmisor', em_ubi[2] or '-')) # No obligatorio para boletas
		document.appendChild(createElement(dom, 'paisEmisor', self.company_id.country_id.code)) # No obligatorio para boletas

		# datos del cliente o receptor
		document.appendChild(createElement(dom, 'tipoDocumentoAdquiriente', self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code)) # catalogo 6
		document.appendChild(createElement(dom, 'numeroDocumentoAdquiriente', self.partner_id.vat))
		document.appendChild(createElement(dom, 'razonSocialAdquiriente', self.partner_id.name))
		if self.sunat_type == '01' or ref[0] == 'F': # sólo se valida si es Factura o notas asocidas
			document.appendChild(createElement(dom, 'ubigeoAdquiriente', self.partner_id.ubigeo_id.code)) # No obligatorio para boletas
			document.appendChild(createElement(dom, 'direccionAdquiriente', self.partner_id.street or '-')) # No obligatorio para boletas
			document.appendChild(createElement(dom, 'urbanizacionAdquiriente', self.partner_id.street2 or '-')) # No obligatorio para boletas
			document.appendChild(createElement(dom, 'distritoAdquiriente', ad_ubi[2] or '-')) # No obligatorio para boletas
			document.appendChild(createElement(dom, 'provinciaAdquiriente', ad_ubi[1] or '-')) # No obligatorio para boletas
			document.appendChild(createElement(dom, 'departamentoAdquiriente', ad_ubi[0] or '-')) # No obligatorio para boletas
			document.appendChild(createElement(dom, 'paisAdquiriente', self.partner_id.country_id.code)) # No obligatorio para boletas

		# totales de la factura	
		document.appendChild(createElement(dom, 'totalValorVentaNetoOpGravadas', self.amount_untaxed))
		document.appendChild(createElement(dom, 'totalIgv', self.amount_tax))
		document.appendChild(createElement(dom, 'totalVenta', self.amount_total))
		document.appendChild(createElement(dom, 'totalImpuestos', self.amount_tax))
		if self.discount_type == '2' and self.discount_total > 0:
			document.appendChild(createElement(dom, 'totalDescuentos', round(self.discount_total, 2)))

		# OTROS
		document.appendChild(createElement(dom, 'codigoLeyenda_1', '1000'))
		document.appendChild(createElement(dom, 'textoLeyenda_1', numberToLetters(self.amount_total).upper()))
		cla = self.env['ir.config_parameter'].sudo().get_param('cv_bizlink.bz_codigo_local_anexo')
		document.appendChild(createElement(dom, 'codigoLocalAnexoEmisor', cla)) # Codigo asignado por sunat

		sequence = 1
		for line in self.invoice_line_ids:
			line.writeXmlItem(dom, document, sequence)
			sequence = sequence + 1

		soapCommand.appendChild(document)

	# firmar y publicar
	def bz_publish(self):
		headers = {
			"Accept": "text/xml",
			"Content-Type": "text/xml",
		}

		dom, command, soapCommand = self.signOnLineCmd()
		soapCommand.setAttribute('declare-sunat', '0')
		soapCommand.setAttribute('declare-direct-sunat', '0')
		soapCommand.setAttribute('publish', '1')
		soapCommand.setAttribute('output', 'PDF,GIF,QR')
		self.writeXmlDocument(dom, soapCommand)

		cdata = dom.createCDATASection(soapCommand.toprettyxml())
		command.appendChild(cdata)

		xml = dom.toprettyxml()

		ir = self.env['ir.config_parameter'].sudo()
		iws = ir.get_param('cv_bizlink.bz_ws')
		iuser = ir.get_param('cv_bizlink.bz_user')
		ipass = ir.get_param('cv_bizlink.bz_pass')
		resp = requests.post(iws, data=xml, headers=headers, auth=(iuser, ipass), timeout=(5,90))
		if resp.status_code == 200:
			dom = parseString(resp.text)
			dom = parseString(dom.documentElement.getElementsByTagName('return')[0].firstChild.nodeValue)
			statuses = dom.documentElement.getElementsByTagName('status')
			if statuses.length > 1:
				status = statuses[1].firstChild.nodeValue
			else:
				status = statuses[0].firstChild.nodeValue

			if status == 'ERROR':
				msgs = dom.documentElement.getElementsByTagName('messages')
				message = ''
				for m in msgs:
					message = message + m.getElementsByTagName('descriptionStatus')[0].firstChild.wholeText + '\n'
					message = message + m.getElementsByTagName('descriptionDetail')[0].firstChild.wholeText + '\n'
					message = message + '=============================================' + '\n'
				raise UserError(message)
			else:
				eSignatureValue = dom.documentElement.getElementsByTagName('signatureValue')
				eHashCode = dom.documentElement.getElementsByTagName('hashCode')
				eXmlFileSignUrl = dom.documentElement.getElementsByTagName('xmlFileSignUrl')
				ePdfFileUrl = dom.documentElement.getElementsByTagName('pdfFileUrl')
				eGifFileUrl = dom.documentElement.getElementsByTagName('barCodeFileUrl')
				eQrFileUrl = dom.documentElement.getElementsByTagName('qrCodeFileUrl')

				self.bz_signatura_value = eSignatureValue[0].firstChild.nodeValue if eSignatureValue else False
				self.bz_hash_code = eHashCode[0].firstChild.nodeValue if eHashCode else False
				self.bz_file_sign_url = eXmlFileSignUrl[0].firstChild.nodeValue if eXmlFileSignUrl else False
				self.bz_file_pdf_url = ePdfFileUrl[0].firstChild.nodeValue if ePdfFileUrl else False
				self.bz_file_gif_url = eGifFileUrl[0].firstChild.nodeValue if eGifFileUrl else False
				self.bz_file_qr_url = eQrFileUrl[0].firstChild.nodeValue if eQrFileUrl else False
				self.efact_state = 'published'
		else:
			raise UserError('Ocurrio un error en la comunicación con el servidor, Nro: ' + str(resp.status_code) + '\n' + 'WebService: ' +iws)

	# declarar
	def bz_declare(self):
		headers = {
			"Accept": "text/xml",
			"Content-Type": "text/xml",
		}

		dom, command, soapCommand = self.declareCmd()
		cdata = dom.createCDATASection(soapCommand.toprettyxml())
		command.appendChild(cdata)

		xml = dom.toprettyxml()

		ir = self.env['ir.config_parameter'].sudo()
		iws = ir.get_param('cv_bizlink.bz_ws')
		iuser = ir.get_param('cv_bizlink.bz_user')
		ipass = ir.get_param('cv_bizlink.bz_pass')
		resp = requests.post(iws, data=xml, headers=headers, auth=(iuser, ipass), timeout=(5,90))

		if resp.status_code == 200:
			dom = parseString(resp.text)
			dom = parseString(dom.documentElement.getElementsByTagName('return')[0].firstChild.nodeValue)

			status = dom.documentElement.getElementsByTagName('status')
			status = status[0].firstChild.nodeValue

			msgs = dom.documentElement.getElementsByTagName('messages')
			message = ''
			for m in msgs:
				message = message + m.getElementsByTagName('descriptionStatus')[0].firstChild.wholeText + '\n'
				message = message + m.getElementsByTagName('descriptionDetail')[0].firstChild.wholeText + '\n'
				message = message + '=============================================' + '\n'

			if status == 'ERROR':
				raise UserError(message)
			self.efact_state = 'declared'
		else:
			raise UserError('Ocurrio un error en la comunicación con el servidor, Nro: ' + str(resp.status_code) + '\n' + 'WebService: ' +iws)

	# solicitar baja
	def bz_baja(self):
		if (fields.Date.today() - self.invoice_date).days >= 7:
			raise UserError('No puede comunicar la baja de comprobantes con fecha mayor a 7 días')

		headers = {
			"Accept": "text/xml",
			"Content-Type": "text/xml",
		}

		dom, command, soapCommand = self.signOnLineSummaryCmd()
		soapCommand.setAttribute('declare-sunat', '1')
		soapCommand.setAttribute('replicate', '1')
		soapCommand.setAttribute('output', '')
		self.writeXmlDocumentCancel(dom, soapCommand)

		cdata = dom.createCDATASection(soapCommand.toprettyxml())
		command.appendChild(cdata)

		xml = dom.toprettyxml()

		ir = self.env['ir.config_parameter'].sudo()
		iws = ir.get_param('cv_bizlink.bz_ws')
		iuser = ir.get_param('cv_bizlink.bz_user')
		ipass = ir.get_param('cv_bizlink.bz_pass')
		resp = requests.post(iws, data=xml, headers=headers, auth=(iuser, ipass), timeout=(5,90))

		if resp.status_code == 200:
			dom = parseString(resp.text)
			dom = parseString(dom.documentElement.getElementsByTagName('return')[0].firstChild.nodeValue)
			print(dom.toprettyxml())
			statuses = dom.documentElement.getElementsByTagName('status')
			if statuses.length > 1:
				status = statuses[1].firstChild.nodeValue
			else:
				status = statuses[0].firstChild.nodeValue

			if status == 'ERROR':
				msgs = dom.documentElement.getElementsByTagName('messages')
				message = ''
				for m in msgs:
					message = message + m.getElementsByTagName('descriptionStatus')[0].firstChild.wholeText + '\n'
					message = message + m.getElementsByTagName('descriptionDetail')[0].firstChild.wholeText + '\n'
					message = message + '=============================================' + '\n'
				raise UserError(message)
			else:
				self.cancel_date = fields.Date.context_today(self)
				self.cancel_id = self._get_next_ra_code()
				self.efact_state = 'cancel'
		else:
			raise UserError('Ocurrio un error en la comunicación con el servidor, Nro: ' + str(resp.status_code) + '\n' + 'WebService: ' +iws)

	def _get_next_ra_code(self):
		move = self.env['account.move'].search([('cancel_id', '!=', False), ('cancel_date', '=', fields.Date.context_today(self))], order="id desc", limit=1)
		id = '01'
		if move:
			id = str(int(move[0].cancel_id.split('-')[2]) + 1).zfill(2)
		return 'RA-' + datetime.now(timezone('America/Lima')).strftime('%Y%m%d') + '-' + id

	# firmar, publicar y declarar
	def bz_publish_and_declare(self):
		headers = {
			"Accept": "text/xml",
			"Content-Type": "text/xml",
		}

		dom, command, soapCommand = self.signOnLineCmd()
		soapCommand.setAttribute('declare-sunat', '0')
		soapCommand.setAttribute('declare-direct-sunat', '1')
		soapCommand.setAttribute('publish', '1')
		soapCommand.setAttribute('output', 'PDF,GIF,QR')
		self.writeXmlDocument(dom, soapCommand)

		cdata = dom.createCDATASection(soapCommand.toprettyxml())
		command.appendChild(cdata)

		xml = dom.toprettyxml()

		ir = self.env['ir.config_parameter'].sudo()
		iws = ir.get_param('cv_bizlink.bz_ws')
		iuser = ir.get_param('cv_bizlink.bz_user')
		ipass = ir.get_param('cv_bizlink.bz_pass')
		resp = requests.post(iws, data=xml, headers=headers, auth=(iuser, ipass), timeout=(5,90))

		if resp.status_code == 200:
			dom = parseString(resp.text)
			dom = parseString(dom.documentElement.getElementsByTagName('return')[0].firstChild.nodeValue)
			statuses = dom.documentElement.getElementsByTagName('status')
			if statuses.length > 1:
				status = statuses[1].firstChild.nodeValue
			else:
				status = statuses[0].firstChild.nodeValue

			if status == 'ERROR':
				msgs = dom.documentElement.getElementsByTagName('messages')
				message = ''
				for m in msgs:
					message = message + m.getElementsByTagName('descriptionStatus')[0].firstChild.wholeText + '\n'
					message = message + m.getElementsByTagName('descriptionDetail')[0].firstChild.wholeText + '\n'
					message = message + '=============================================' + '\n'
				raise UserError(message)
			else:
				eSignatureValue = dom.documentElement.getElementsByTagName('signatureValue')
				eHashCode = dom.documentElement.getElementsByTagName('hashCode')
				eXmlFileSignUrl = dom.documentElement.getElementsByTagName('xmlFileSignUrl')
				ePdfFileUrl = dom.documentElement.getElementsByTagName('pdfFileUrl')
				eGifFileUrl = dom.documentElement.getElementsByTagName('barCodeFileUrl')
				eQrFileUrl = dom.documentElement.getElementsByTagName('qrCodeFileUrl')

				self.bz_signatura_value = eSignatureValue[0].firstChild.nodeValue if eSignatureValue else False
				self.bz_hash_code = eHashCode[0].firstChild.nodeValue if eHashCode else False
				self.bz_file_sign_url = eXmlFileSignUrl[0].firstChild.nodeValue if eXmlFileSignUrl else False
				self.bz_file_pdf_url = ePdfFileUrl[0].firstChild.nodeValue if ePdfFileUrl else False
				self.bz_file_gif_url = eGifFileUrl[0].firstChild.nodeValue if eGifFileUrl else False
				self.bz_file_qr_url = eQrFileUrl[0].firstChild.nodeValue if eQrFileUrl else False
				self.efact_state = 'declared'
		else:
			raise UserError('Ocurrio un error en la comunicación con el servidor: ' + str(resp.status_code))

	# anular, sólo es posible si el comprabante fue publicado pero no declarado
	def bz_cancel(self):
		headers = {
			"Accept": "text/xml",
			"Content-Type": "text/xml",
		}

		dom, command, soapCommand = self.cancelCmd()
		cdata = dom.createCDATASection(soapCommand.toprettyxml())
		command.appendChild(cdata)

		xml = dom.toprettyxml()

		ir = self.env['ir.config_parameter'].sudo()
		iws = ir.get_param('cv_bizlink.bz_ws')
		iuser = ir.get_param('cv_bizlink.bz_user')
		ipass = ir.get_param('cv_bizlink.bz_pass')
		resp = requests.post(iws, data=xml, headers=headers, auth=(iuser, ipass), timeout=(5,90))

		if resp.status_code == 200:
			dom = parseString(resp.text)
			dom = parseString(dom.documentElement.getElementsByTagName('return')[0].firstChild.nodeValue)

			status = dom.documentElement.getElementsByTagName('status')
			status = status[0].firstChild.nodeValue

			msgs = dom.documentElement.getElementsByTagName('messages')
			message = ''
			for m in msgs:
				message = message + m.getElementsByTagName('descriptionStatus')[0].firstChild.wholeText + '\n'
				message = message + m.getElementsByTagName('descriptionDetail')[0].firstChild.wholeText + '\n'
				message = message + '=============================================' + '\n'

			if status == 'ERROR':
				raise UserError(message)
			self.efact_state = 'cancel'
		else:
			raise UserError('Ocurrio un error en la comunicación con el servidor, Nro: ' + str(resp.status_code) + '\n' + 'WebService: ' +iws)

	# consulta de estado de comprobantes
	def bz_status_query(self):
		headers = {
			"Accept": "text/xml",
			"Content-Type": "text/xml",
		}

		dom, command, soapCommand = self.consultCmd()
		soapCommand.setAttribute('output', 'PDF,GIF,QR')
		cdata = dom.createCDATASection(soapCommand.toprettyxml())
		command.appendChild(cdata)

		xml = dom.toprettyxml()

		ir = self.env['ir.config_parameter'].sudo()
		iws = ir.get_param('cv_bizlink.bz_ws')
		iuser = ir.get_param('cv_bizlink.bz_user')
		ipass = ir.get_param('cv_bizlink.bz_pass')
		resp = requests.post(iws, data=xml, headers=headers, auth=(iuser, ipass), timeout=(5,90))

		if resp.status_code == 200:
			dom = parseString(resp.text)
			dom = parseString(dom.documentElement.getElementsByTagName('return')[0].firstChild.nodeValue)

			statuses = dom.documentElement.getElementsByTagName('status')
			if statuses.length > 1:
				status = statuses[1].firstChild.nodeValue
			else:
				status = statuses[0].firstChild.nodeValue

			if status == 'ERROR':
				msgs = dom.documentElement.getElementsByTagName('messages')
				message = ''
				for m in msgs:
					message = message + m.getElementsByTagName('descriptionStatus')[0].firstChild.wholeText + '\n'
					message = message + m.getElementsByTagName('descriptionDetail')[0].firstChild.wholeText + '\n'
					message = message + '=============================================' + '\n'
				raise UserError(message)
			else:
				eSignatureValue = dom.documentElement.getElementsByTagName('signatureValue')
				eHashCode = dom.documentElement.getElementsByTagName('hashCode')
				eXmlFileSignUrl = dom.documentElement.getElementsByTagName('xmlFileSignUrl')
				ePdfFileUrl = dom.documentElement.getElementsByTagName('pdfFileUrl')
				eGifFileUrl = dom.documentElement.getElementsByTagName('barCodeFileUrl')
				eQrFileUrl = dom.documentElement.getElementsByTagName('qrCodeFileUrl')

				self.bz_signatura_value = eSignatureValue[0].firstChild.nodeValue if eSignatureValue else False
				self.bz_hash_code = eHashCode[0].firstChild.nodeValue if eHashCode else False
				self.bz_file_sign_url = eXmlFileSignUrl[0].firstChild.nodeValue if eXmlFileSignUrl else False
				self.bz_file_pdf_url = ePdfFileUrl[0].firstChild.nodeValue if ePdfFileUrl else False
				self.bz_file_gif_url = eGifFileUrl[0].firstChild.nodeValue if eGifFileUrl else False
				self.bz_file_qr_url = eQrFileUrl[0].firstChild.nodeValue if eQrFileUrl else False
		else:
			raise UserError('Ocurrio un error en la comunicación con el servidor, Nro: ' + str(resp.status_code) + '\n' + 'WebService: ' +iws)

	def action_nd_reverse(self):
		action = self.env.ref('cv_bizlink.action_view_account_move_nd_reversal').read()[0]

		if self.is_invoice():
			action['name'] = _('Nota de Débito')

		return action


class AccountMoveLine(models.Model):
	_inherit = "account.move.line"

	descuento_fijo = fields.Float('Desc.', digits=(12,2))
	price_taxed = fields.Float('Price Taxed', digits=(24,12), compute="_get_price_untaxed")
	price_untaxed = fields.Float('Price Untaxed', digits=(24,12), compute="_get_price_untaxed")
	price_untaxed_wd = fields.Float('Price Untaxed WD', digits=(24,12), compute="_get_price_untaxed")

	importeTotalSinImpuesto = fields.Float('itsi', digits=(24,12), compute='_get_price_untaxed')
	importeBaseDescuento = fields.Float('ibd', digits=(24,12), compute='_get_price_untaxed')
	importeDescuento = fields.Float('id', digits=(24,12), compute='_get_price_untaxed')

	montoBaseIgv = fields.Float('mbi', digits=(24,12), compute='_get_price_untaxed')
	importeIgv = fields.Float('ig', digits=(24,12), compute='_get_price_untaxed')
	importeTotalImpuestos = fields.Float('iti', digits=(24,12), compute='_get_price_untaxed')

	@api.depends('price_unit', 'tax_ids')
	def _get_price_untaxed(self):
		for line in self:
			line.price_untaxed = line.price_unit
			line.price_untaxed_wd = line.price_unit * ((100-line.discount)/100)
			line.price_taxed = line.price_unit * ((100-line.discount)/100)
			for tax in line.tax_ids:
				if tax.tax_group_id.id == self.env.ref('l10n_pe.tax_group_igv')[0].id and tax.price_include:
					line.price_untaxed = line.price_untaxed / ((100 + tax.amount) / 100)
					line.price_untaxed_wd = line.price_untaxed_wd / ((100 + tax.amount) / 100)
			
			for tax in line.tax_ids:
				if tax.tax_group_id.id == self.env.ref('l10n_pe.tax_group_igv')[0].id and not tax.price_include:
					line.price_taxed = line.price_taxed * ((100 + tax.amount) / 100)

			if line.move_id.discount_type == '1':
				# afectando a la base imponible
				line.importeTotalSinImpuesto = line.price_untaxed_wd * line.quantity # o
				line.importeBaseDescuento = line.price_untaxed * line.quantity
				line.importeDescuento = (line.price_untaxed - line.price_untaxed_wd) * line.quantity

				line.montoBaseIgv = line.price_untaxed_wd * line.quantity # o
				line.importeIgv = (line.price_taxed - line.price_untaxed_wd) * line.quantity # i
				line.importeTotalImpuestos = (line.price_taxed - line.price_untaxed_wd) * line.quantity # i
			elif line.move_id.discount_type == '2':
				# no afecto a la base imponible
				line.importeTotalSinImpuesto = line.price_untaxed * line.quantity # o
				line.importeBaseDescuento = line.price_untaxed * line.quantity
				line.importeDescuento = (line.price_untaxed * (100-line.discount)/100) * line.quantity

				line.montoBaseIgv = line.price_untaxed * line.quantity # o
				line.importeIgv = (line.price_taxed - line.price_untaxed) * line.quantity # i
				line.importeTotalImpuestos = (line.price_taxed - line.price_untaxed) * line.quantity # i

	@api.onchange('discount')
	def onChangeDiscount(self):
		for line in self:
			line.descuento_fijo = (line.price_unit * line.discount) / 100

	@api.onchange('descuento_fijo')
	def onChangeDiscountF(self):
		for line in self:
			if line.price_unit:
				line.discount = (line.descuento_fijo / line.price_unit) * 100

	def writeXmlItem(self, dom, doc, sequence):
		for line in self:
			item = createElement(dom, 'item')
			doc.appendChild(item)

			igvs = line.tax_ids.filtered(lambda r: r.tax_group_id.id == self.env.ref('l10n_pe.tax_group_igv')[0].id)

			item.appendChild(createElement(dom, 'numeroOrdenItem', sequence))
			item.appendChild(createElement(dom, 'codigoProducto', line.product_id.default_code)) # CAPS01 en caso el concepto sea porcentaje de servicio
			item.appendChild(createElement(dom, 'descripcion', line.name)) # debe describir completamente el producto, marca
			item.appendChild(createElement(dom, 'cantidad', line.quantity))
			item.appendChild(createElement(dom, 'unidadMedida', line.sunat_uom_code)) # catalogo NIU o ZZZ
			item.appendChild(createElement(dom, 'importeUnitarioSinImpuesto', round(line.price_untaxed, 2)))
			item.appendChild(createElement(dom, 'importeUnitarioConImpuesto', round(line.price_taxed, 2)))
			item.appendChild(createElement(dom, 'codigoImporteUnitarioConImpuesto', '01')) # 01 Para el precio unitario (INcluye IGV), 02 en caso sea no onerosa
			item.appendChild(createElement(dom, 'importeTotalSinImpuesto', round(line.importeTotalSinImpuesto, 2)))
			item.appendChild(createElement(dom, 'codigoRazonExoneracion', line.sunat_tax_impact_type)) # Catalogo 7, codigo de afectacion del IGV
			if line.discount:
				if line.move_id.discount_type == '1':
					item.appendChild(createElement(dom, 'importeBaseDescuento', round(line.importeBaseDescuento,2 )))
					item.appendChild(createElement(dom, 'factorDescuento', round(line.discount / 100, 2)))
					item.appendChild(createElement(dom, 'importeDescuento', round(line.importeDescuento, 2)))
				elif line.move_id.discount_type == '2':
					item.appendChild(createElement(dom, 'importeBaseDescuentoNoAfecto', round(line.importeBaseDescuento,2 )))
					item.appendChild(createElement(dom, 'factorDescuentoNoAfecto', round(line.discount / 100, 2)))
					item.appendChild(createElement(dom, 'importeDescuentoNoAfecto', round(line.importeDescuento, 2)))
			item.appendChild(createElement(dom, 'montoBaseIgv', round(line.montoBaseIgv, 2)))
			item.appendChild(createElement(dom, 'tasaIgv', igvs[0].amount if igvs else '0'))
			item.appendChild(createElement(dom, 'importeIgv', round(line.importeIgv, 2)))
			item.appendChild(createElement(dom, 'importeTotalImpuestos', round(line.importeTotalImpuestos, 2)))
