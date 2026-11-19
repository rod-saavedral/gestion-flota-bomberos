from odoo import api, fields, models

class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'
    
    report_signature = fields.Image('Signature', help='Signature for Report')