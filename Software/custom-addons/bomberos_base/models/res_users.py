from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    bomberos_company_ids = fields.Many2many(
        "bomberos.company",
        "bomberos_company_user_rel",
        "user_id",
        "company_id",
        string="Compañías de Bomberos asignadas",
    )
