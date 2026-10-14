import base64
import json
import werkzeug

from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError

import uuid
import random

from odoo.exceptions import UserError, AccessError
from odoo import api, fields, models, _, tools

from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

import io


class SignPrintReport(http.Controller):
    
    @http.route('/sign_print_report/get_report_data', auth='user', type='json')
    def get_report_data(self, active_id=None, active_model=None, report_name=None):
        if not active_id or not active_model or not report_name:
            return False
        report = request.env['ir.actions.report']._get_report_from_name(report_name)
        pdf = request.env['ir.actions.report'].with_user(SUPERUSER_ID)._render_qweb_pdf(report, active_id)[0]
        content = base64.b64encode(pdf)
        return content
    
    @http.route("/sign_print_report/render_assets_pdf_iframe", type="json", auth="public")
    def render_assets_pdf_iframe(self, **kw):
        context = {'debug': kw.get('debug')} if 'debug' in kw else {}
        return request.env['ir.ui.view'].sudo()._render_template('sign_print_report.assets_pdf_iframe', context)
    
    @http.route('/sign_print_report/sign_print_report_data', auth='user', type='json')
    def sign_print_report_data(self, active_id=None, active_model=None, report_items=None, report_data=None):
        if not active_id or not active_model or not report_items or not report_data:
            return False
        
        signed_report = False
        partner_id = request.env.user.partner_id.id
        content = report_data
        
        # Read original PDF
        initial_pdf = PdfReader(io.BytesIO(base64.b64decode(content)))

        font = "Helvetica"
        normalFontSize = 0.015
        
        # Create overlay PDF with reportlab
        packet = io.BytesIO()
        can = canvas.Canvas(packet)
        pageItems = self.getPageItems(report_items)

        for p in range(0, len(initial_pdf.pages)):
            page = initial_pdf.pages[p]
            width = float(abs(page.mediabox.width))
            height = float(abs(page.mediabox.height))

            page_rotation = 0
            try:
                page_rotation = int(page.get('/Rotate', 0))
            except Exception:
                page_rotation = 0

            if page_rotation:
                can.rotate(page_rotation)
            if page_rotation == 90:
                width, height = height, width
                can.translate(0, -height)
            elif page_rotation == 180:
                can.translate(-width, -height)
            elif page_rotation == 270:
                width, height = height, width
                can.translate(-width, 0)
                
            items = pageItems[p + 1] if (p + 1) in pageItems else []
            partner = request.env['res.partner'].sudo().search([('id', '=', partner_id)])
            
            for item in items:
                if item['type'] == "name" and partner.name:
                    can.setFont(font, height * item['height'] * 0.4)
                    name_x = width * (item['posX'] + item['width'] / 2)
                    name_y = height * (1 - item['posY'] - item['height'] * 0.6)
                    can.drawCentredString(name_x, name_y, partner.name)
                
                if item['type'] == "email" and partner.email:
                    can.setFont(font, height * item['height'] * 0.4)
                    email_x = width * (item['posX'] + item['width'] / 2)
                    email_y = height * (1 - item['posY'] - item['height'] * 0.6)
                    can.drawCentredString(email_x, email_y, partner.email)
                
                if item['type'] == "phone" and partner.phone:
                    can.setFont(font, height * item['height'] * 0.4)
                    phone_x = width * (item['posX'] + item['width'] / 2)
                    phone_y = height * (1 - item['posY'] - item['height'] * 0.6)
                    can.drawCentredString(phone_x, phone_y, partner.phone)

                if item['type'] == "website" and partner.website:
                    can.setFont(font, height * item['height'] * 0.4)
                    website_x = width * (item['posX'] + item['width'] / 2)
                    website_y = height * (1 - item['posY'] - item['height'] * 0.6)
                    can.drawCentredString(website_x, website_y, partner.website)
                    
                if item['type'] == "company" and partner.company_name:
                    can.setFont(font, height * item['height'] * 0.4)
                    company_x = width * (item['posX'] + item['width'] / 2)
                    company_y = height * (1 - item['posY'] - item['height'] * 0.6)
                    can.drawCentredString(company_x, company_y, partner.company_name)

                if item['type'] == "date":
                    now = fields.Date.to_string(fields.Datetime.now())
                    can.setFont(font, height * item['height'] * 0.4)
                    date_x = width * (item['posX'] + item['width'] / 2)
                    date_y = height * (1 - item['posY'] - item['height'] * 0.6)
                    can.drawCentredString(date_x, date_y, now)
                
                if item['type'] == "signature" and partner.report_signature:
                    img_reader = ImageReader(io.BytesIO(base64.b64decode(partner.report_signature)))
                    self._fix_transparency_img(img_reader._image)
                    sx = width * item['posX']
                    sy = height * (1 - item['posY'] - item['height'])
                    swidth = width * item['width']
                    sheight = height * item['height']
                    can.drawImage(img_reader, sx, sy, swidth, sheight, 'auto', True)

            can.showPage()
        can.save()

        # Rewind the buffer to read the overlay PDF
        packet.seek(0)
        item_pdf = PdfReader(packet)
        signed_pdf = PdfWriter()
            
        for p in range(0, len(initial_pdf.pages)):
            page = initial_pdf.pages[p]
            overlay_page = item_pdf.pages[p]
            # Merge overlay into the original page
            page.merge_page(overlay_page)
            signed_pdf.add_page(page)
            
        output = io.BytesIO()
        signed_pdf.write(output)
        signed_report = base64.b64encode(output.getvalue())
        output.close()
        return signed_report
    
    def _fix_transparency_img(self, img):
        pixls = img.load()
        for x in range(img.size[0]):
            for y in range(img.size[1]):
                if pixls[x, y] == (0, 0, 0, 0):
                    pixls[x, y] = (255, 255, 255, 0)
    
    def getPageItems(self, report_items):
        items = {}
        for item in report_items:
            if item['page'] not in items:
                items[item['page']] = []
            items[item['page']].append(item)
        return items