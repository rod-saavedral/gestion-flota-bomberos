from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class BomberosVehicleOdometer(models.Model):
    _name = "bomberos.vehicle.odometer"
    _description = "Lectura de kilometraje"
    _order = "date desc, id desc"

    vehicle_id = fields.Many2one(
        "bomberos.vehicle",
        string="Vehículo",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="vehicle_id.company_id",
        store=True,
        index=True,
    )
    date = fields.Date(string="Fecha de lectura", required=True, default=fields.Date.context_today)
    km = fields.Float(string="Kilometraje", required=True, digits=(12, 1))
    user_id = fields.Many2one("res.users", string="Registrado por", default=lambda self: self.env.user)
    note = fields.Char(string="Observación")

    _sql_constraints = [
        ("bomberos_odometer_km_nonnegative", "check(km >= 0)", "El kilometraje no puede ser negativo."),
    ]

    @api.constrains("vehicle_id", "km")
    def _check_monotonic_kilometers(self):
        for reading in self:
            other_readings = self.search(
                [
                    ("vehicle_id", "=", reading.vehicle_id.id),
                    ("id", "!=", reading.id),
                ],
                order="km desc, id desc",
                limit=1,
            )
            highest_previous = max(
                reading.vehicle_id.current_odometer_km,
                other_readings.km if other_readings else 0,
            )
            if reading.km < highest_previous:
                raise ValidationError(
                    _("La lectura debe ser igual o mayor al kilometraje registrado anteriormente.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        readings = super().create(vals_list)
        for vehicle in readings.mapped("vehicle_id"):
            vehicle.sudo().write(
                {
                    "current_odometer_km": max(
                        readings.filtered(lambda reading: reading.vehicle_id == vehicle).mapped("km")
                    )
                }
            )
        return readings

    def write(self, vals):
        previous_vehicles = self.mapped("vehicle_id")
        result = super().write(vals)
        for vehicle in previous_vehicles | self.mapped("vehicle_id"):
            latest = self.search(
                [("vehicle_id", "=", vehicle.id)],
                order="km desc, id desc",
                limit=1,
            )
            vehicle.sudo().write({"current_odometer_km": latest.km if latest else 0})
        return result
