from odoo import api, fields, models

class SignPrintReportWizard(models.TransientModel):
    _name = 'sign.print.report.wizard'
    _description = 'Share Attachments'

    report_template_ids = fields.Many2many('ir.actions.report','sign_print_rpoer_action_report_rel', string='Report Ids')
    report_template = fields.Many2one('ir.actions.report', 'Report', domain="[('id', 'in', report_template_ids)]")
    
    @api.model
    def default_get(self, fields):
        result = super(SignPrintReportWizard, self).default_get(fields)
        ctx = self._context or {}
        active_id = ctx.get('active_id')
        active_model = ctx.get('active_model')
        report = self.env['ir.actions.report'].sudo().search([('model', '=', active_model)])
        if report:
            result['report_template_ids'] = [(6, 0, report.ids)]
        return result