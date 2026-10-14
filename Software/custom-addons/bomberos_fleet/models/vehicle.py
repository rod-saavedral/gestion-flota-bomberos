from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class BomberosVehicle(models.Model):
    _name = "bomberos.vehicle"
    _description = "Vehículo de emergencia"
    _order = "company_id, code"

    name = fields.Char(string="Nombre de unidad", required=True, index=True)
    code = fields.Char(string="Código interno", required=True, index=True)
    license_plate = fields.Char(string="Patente", required=True, index=True)
    vehicle_type = fields.Selection(
        [
            ("pump", "Carro bomba"),
            ("rescue", "Rescate"),
            ("ambulance", "Ambulancia"),
            ("tanker", "Aljibe"),
            ("command", "Comandancia"),
            ("other", "Otro"),
        ],
        string="Tipo",
        required=True,
        default="pump",
    )
    company_id = fields.Many2one(
        "bomberos.company",
        string="Compañía",
        required=True,
        index=True,
        ondelete="restrict",
    )
    make = fields.Char(string="Marca")
    model_name = fields.Char(string="Modelo")
    year = fields.Integer(string="Año")
    vin = fields.Char(string="Número de chasis")
    engine_number = fields.Char(string="Número de motor")
    capacity = fields.Char(string="Capacidad / especificación")
    operational_state = fields.Selection(
        [
            ("available", "Disponible"),
            ("in_maintenance", "En mantención"),
            ("unavailable", "Fuera de servicio"),
        ],
        string="Estado operativo",
        required=True,
        default="available",
        index=True,
    )
    current_odometer_km = fields.Float(
        string="Kilometraje actual",
        digits=(12, 1),
        default=0,
        readonly=True,
    )
    odometer_ids = fields.One2many(
        "bomberos.vehicle.odometer",
        "vehicle_id",
        string="Historial de kilometraje",
    )
    document_ids = fields.Many2many(
        "ir.attachment",
        "bomberos_vehicle_attachment_rel",
        "vehicle_id",
        "attachment_id",
        string="Documentos",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "bomberos_vehicle_code_company_uniq",
            "unique(company_id, code)",
            "El código debe ser único dentro de la compañía.",
        ),
        (
            "bomberos_vehicle_plate_company_uniq",
            "unique(company_id, license_plate)",
            "La patente debe ser única dentro de la compañía.",
        ),
        (
            "bomberos_vehicle_year_valid",
            "check(year is null or year >= 1900)",
            "El año del vehículo debe ser igual o posterior a 1900.",
        ),
    ]

    @api.constrains("current_odometer_km")
    def _check_current_odometer(self):
        for vehicle in self:
            if vehicle.current_odometer_km < 0:
                raise UserError(_("El kilometraje no puede ser negativo."))

    def action_set_unavailable(self):
        if not self.env.user.has_group("bomberos_base.group_bomberos_fleet_manager"):
            raise AccessError(_("Solo la jefatura de flota puede cambiar el estado operativo."))
        if self.filtered(lambda vehicle: vehicle.operational_state == "in_maintenance"):
            raise UserError(_("No se puede retirar del servicio una unidad con una mantención en curso."))
        self.write({"operational_state": "unavailable"})

    def action_set_available(self):
        if not self.env.user.has_group("bomberos_base.group_bomberos_fleet_manager"):
            raise AccessError(_("Solo la jefatura de flota puede cambiar el estado operativo."))
        if self.filtered(lambda vehicle: vehicle.operational_state == "in_maintenance"):
            raise UserError(_("No se puede habilitar una unidad con una mantención en curso."))
        self.write({"operational_state": "available"})

    def _set_in_maintenance(self):
        self.sudo().write({"operational_state": "in_maintenance"})

    def _restore_after_maintenance(self):
        for vehicle in self.sudo():
            active_orders = self.env["bomberos.maintenance.order"].sudo().search_count(
                [
                    ("vehicle_id", "=", vehicle.id),
                    ("state", "=", "in_progress"),
                ]
            )
            if not active_orders and vehicle.operational_state == "in_maintenance":
                vehicle.write({"operational_state": "available"})

    def action_view_odometer(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Historial de kilometraje"),
            "res_model": "bomberos.vehicle.odometer",
            "view_mode": "list,form",
            "domain": [("vehicle_id", "=", self.id)],
            "context": {"default_vehicle_id": self.id},
        }
