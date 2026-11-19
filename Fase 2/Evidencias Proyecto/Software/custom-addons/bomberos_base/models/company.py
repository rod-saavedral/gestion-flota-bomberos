from odoo import api, fields, models


class BomberosCompany(models.Model):
    _name = "bomberos.company"
    _description = "Compañía de Bomberos"
    _order = "code, name"

    name = fields.Char(string="Compañía", required=True, index=True)
    code = fields.Char(string="Código", required=True, index=True)
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self._default_currency(),
    )
    user_ids = fields.Many2many(
        "res.users",
        "bomberos_company_user_rel",
        "company_id",
        "user_id",
        string="Usuarios asignados",
        readonly=True,
    )
    _sql_constraints = [
        ("bomberos_company_code_uniq", "unique(code)", "El código de compañía debe ser único."),
    ]

    @api.model
    def _default_currency(self):
        chile_currency = self.env.ref("base.CLP", raise_if_not_found=False)
        return chile_currency or self.env.company.currency_id
