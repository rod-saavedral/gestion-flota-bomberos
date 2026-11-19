from odoo import fields, models


class BomberosCompany(models.Model):
    _inherit = "bomberos.company"

    vehicle_count = fields.Integer(
        string="Vehículos",
        compute="_compute_vehicle_count",
    )

    def _compute_vehicle_count(self):
        vehicle_model = self.env["bomberos.vehicle"]
        for company in self:
            company.vehicle_count = vehicle_model.search_count(
                [("company_id", "=", company.id)]
            )
