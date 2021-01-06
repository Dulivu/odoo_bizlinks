# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from xml.dom.minidom import Element, Text, parseString
import requests


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


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    efact_state = fields.Selection([
        ('unpublished', 'No publicado'),
        ('declared', 'Declarado')
    ], string="eFact Estado", default='unpublished')

    total_weitgh = fields.Float('Peso Total', digits=(12,2), compute='_compute_total_weigth')
    carrier_id = fields.Many2one('res.partner', string="Transportista")

    bz_signatura_value = fields.Char('Firma', copy=False)
    bz_hash_code = fields.Char('Codigo HASH', copy=False)
    bz_file_sign_url = fields.Char('Ruta XML', copy=False)
    bz_file_pdf_url = fields.Char('Factura PDF', copy=False)

    @api.depends('move_line_ids_without_package')
    def _compute_total_weigth(self):
        for record in self:
            w = 0
            for line in record.move_line_ids_without_package:
                w = w + line.sunat_weigth
            record.total_weitgh = w

    def signOnLineDespatchCmd(self):
        vat = self.company_id.vat

        dom, header, command = createSoapEnvelope()

        soapCommand = dom.createElement('SignOnLineDespatchCmd')

        param = dom.createElement('parameter')
        param.setAttribute('value', vat)
        param.setAttribute('name', 'idEmisor')
        soapCommand.appendChild(param)

        param = dom.createElement('parameter')
        param.setAttribute('value', '09')
        param.setAttribute('name', 'tipoDocumento')
        soapCommand.appendChild(param)

        return dom, command, soapCommand

    def writeXmlDocument(self, dom, soapCommand):
        if not self.partner_id:
            raise UserError('Debe ingresar una direccion de entrega')
        if not self.partner_id.ubigeo_id:
            raise UserError('La direccion de entrega debe tener un Ubigeo registrado')
        if not self.picking_type_id.warehouse_id.partner_id.ubigeo_id:
            raise UserError('El almacen no tiene un Ubigeo registrado')

        document = dom.createElement('documento')

        # datos Bizlinks
        document.appendChild(createElement(dom, 'correoEmisor', self.company_id.email))
        document.appendChild(createElement(dom, 'correoAdquiriente', self.partner_id.parent_id.email if self.partner_id.parent_id else self.partner_id.email))
        document.appendChild(createElement(dom, 'inHabilitado', '1'))
        document.appendChild(createElement(dom, 'serieNumeroGuia', self.name)) # T###-NNNNNNNN

        # datos SUNAT
        document.appendChild(createElement(dom, 'fechaEmisionGuia', fields.Date.from_string(fields.Datetime.context_timestamp(self, self.date))))
        document.appendChild(createElement(dom, 'tipoDocumentoGuia', '09')) # Cat. 09 - GUIA DE REMISION REMITENTE
        # documento relacionado (C)
        #document.appendChild(createElement(dom, 'numeroDocumentoRelacionado', self.origin))
        #document.appendChild(createElement(dom, 'codigoDocumentoRelacionado', self.sunat_origin_type))
        # datos del remitente
        document.appendChild(createElement(dom, 'numeroDocumentoRemitente', self.company_id.vat))
        document.appendChild(createElement(dom, 'tipoDocumentoRemitente', '6')) # Catalogo 06, puesto en RUC por defecto
        document.appendChild(createElement(dom, 'razonSocialRemitente', self.company_id.company_registry))
        # datos del destinatario
        document.appendChild(createElement(dom, 'numeroDocumentoDestinatario', self.partner_id.vat))
        document.appendChild(createElement(dom, 'tipoDocumentoDestinatario', self.partner_id.l10n_latam_identification_type_id.l10n_pe_vat_code))
        document.appendChild(createElement(dom, 'razonSocialDestinatario', self.partner_id.parent_id.name if self.partner_id.parent_id else self.partner_id.name))
        # datos asociado al establecimiento del tercero (C)
        #document.appendChild(createElement(dom, 'numeroDocumentoEstablecimiento', self.picking_type_id.warehouse_id.partner_id.vat))
        #document.appendChild(createElement(dom, 'tipoDocumentoEstablecimiento', self.picking_type_id.warehouse_id.partner_id.l10n_latam_identification_type_id.name))
        #document.appendChild(createElement(dom, 'razonSocialEstablecimiento', self.picking_type_id.warehouse_id.partner_id.name))
        # datos del envio
        document.appendChild(createElement(dom, 'motivoTraslado', self.sunat_transfer_reason))
        if self.note:
            document.appendChild(createElement(dom, 'descripcionMotivoTraslado', self.note))
        document.appendChild(createElement(dom, 'pesoBrutoTotalBienes', self.total_weitgh)) # TODO: agregar pesos al documento
        document.appendChild(createElement(dom, 'unidadMedidaPesoBruto', 'KG')) # TODO: por defecto se deberá usar KG para todos los pesos
        document.appendChild(createElement(dom, 'modalidadTraslado', self.sunat_transfer_type))
        document.appendChild(createElement(dom, 'fechaInicioTraslado', fields.Date.from_string(self.date_done)))
        # transportista (C)
        if self.carrier_id:
            document.appendChild(createElement(dom, 'numeroRucTransportista', self.carrier_id.vat))
            document.appendChild(createElement(dom, 'tipoDocumentoTransportista', self.carrier_id.l10n_latam_identification_type_id.name))
            document.appendChild(createElement(dom, 'razonSocialTransportista', self.carrier_id.name))
        # conductor (C)
        #document.appendChild(createElement(dom, 'numeroDocumentoConductor', self.sunat_transfer_id.vat))
        #document.appendChild(createElement(dom, 'tipoDocumentoConductor', self.sunat_transfer_id.vat))
        # dirección del punto de llegada y partida
        document.appendChild(createElement(dom, 'ubigeoPtoLlegada', self.partner_id.ubigeo_id.code))
        document.appendChild(createElement(dom, 'direccionPtoLlegada', self.partner_id.street or self.partner_id.street_name))
        document.appendChild(createElement(dom, 'ubigeoPtoPartida', self.picking_type_id.warehouse_id.partner_id.ubigeo_id.code))
        document.appendChild(createElement(dom, 'direccionPtoPartida', self.picking_type_id.warehouse_id.partner_id.street))

        sequence = 1
        for line in self.move_line_ids_without_package:
            line.writeXmlItem(dom, document, sequence)
            sequence = sequence + 1

        soapCommand.appendChild(document)

    def bz_publish_and_declare(self):
        headers = {
            "Accept": "text/xml",
            "Content-Type": "text/xml",
        }

        dom, command, soapCommand = self.signOnLineDespatchCmd()
        soapCommand.setAttribute('declare-sunat', '0')
        soapCommand.setAttribute('declare-direct-sunat', '1')
        soapCommand.setAttribute('publish', '1')
        soapCommand.setAttribute('output', 'PDF')
        self.writeXmlDocument(dom, soapCommand)

        cdata = dom.createCDATASection(soapCommand.toprettyxml())
        command.appendChild(cdata)

        xml = dom.toprettyxml()

        ir = self.env['ir.config_parameter'].sudo()
        iws = ir.get_param('cv_bizlink.bz_ws')
        iuser = ir.get_param('cv_bizlink.bz_user')
        ipass = ir.get_param('cv_bizlink.bz_pass')
        resp = requests.post(iws, data=xml, headers=headers, auth=(iuser, ipass), timeout=(5,60))

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
                eSignatureValue = dom.documentElement.getElementsByTagName('signatureValue')
                eHashCode = dom.documentElement.getElementsByTagName('hashCode')
                eXmlFileSignUrl = dom.documentElement.getElementsByTagName('xmlFileSignUrl')
                ePdfFileUrl = dom.documentElement.getElementsByTagName('pdfFileUrl')

                self.bz_signatura_value = eSignatureValue[0].firstChild.nodeValue if eSignatureValue else False
                self.bz_hash_code = eHashCode[0].firstChild.nodeValue if eHashCode else False
                self.bz_file_sign_url = eXmlFileSignUrl[0].firstChild.nodeValue if eXmlFileSignUrl else False
                self.bz_file_pdf_url = ePdfFileUrl[0].firstChild.nodeValue if ePdfFileUrl else False
                self.efact_state = 'declared'
        else:
            raise UserError('Ocurrio un error en la comunicación con el servidor: ' + str(resp.status_code))


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def writeXmlItem(self, dom, doc, sequence):
        for line in self:
            item = createElement(dom, 'GuiaItem')
            doc.appendChild(item)

            item.appendChild(createElement(dom, 'numeroOrdenItem', sequence))
            item.appendChild(createElement(dom, 'cantidad', line.qty_done))
            item.appendChild(createElement(dom, 'unidadMedida', line.sunat_uom_code)) # catalogo NIU o ZZZ
            item.appendChild(createElement(dom, 'descripcion', line.product_id.name))
            item.appendChild(createElement(dom, 'codigo', line.product_id.default_code))
