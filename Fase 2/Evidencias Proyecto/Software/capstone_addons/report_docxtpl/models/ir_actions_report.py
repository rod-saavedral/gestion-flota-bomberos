# -*- coding:utf-8 -*-

from odoo import _, api, fields, models, tools


class IrActionReport(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(selection_add=[('docxtpl', 'Docx tempalte')], 
        ondelete={'docxtpl': "cascade"})
    docxtpl_id = fields.Many2one('docx.template', "Template")

    def _render_docxtpl(self, report_ref, res_ids, data=None):
        if isinstance(report_ref, models.Model):
            report_ref.ensure_one()
            if report_ref.report_type != "docxtpl":
                raise RuntimeError(
                    "Docx template in only available on docx report.\n"
                    "(current: '{}', expected 'docxtpl'".format(report_ref.report_type)
                )            
            filename, filetype, file = report_ref.docxtpl_id.render(res_ids, data)
            return file.read(), filetype

        self.ensure_one()
        if self.report_type != "docxtpl":
            raise RuntimeError(
                "Docx template in only available on docx report.\n"
                "(current: '{}', expected 'docxtpl'".format(self.report_type)
            )
        return self.docxtpl_id.render(res_ids, data)

    def get_docxtpl_from_report_name(self, report_name):
        return self.search(
            [('report_name', '=', report_name), ('report_type', '=', 'docxtpl')], limit=1
        )


class IrActions(models.Model):
    _inherit = "ir.actions.actions"

    def get_bindings(self, model_name):
        result = super(IrActions, self).get_bindings(model_name)
        if result.get('report'):
            for report in result.get('report'):
                docxtpl = self.env["docx.template"].search([("report_id", "=", report.get("id")), ("direct_print", "=", True)], limit=1)
                if docxtpl:
                    report.update({
                        "direct_print": True
                    })
        return result