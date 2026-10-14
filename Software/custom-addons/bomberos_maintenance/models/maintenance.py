from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class BomberosMaintenanceOrder(models.Model):
    _name = "bomberos.maintenance.order"
    _description = "Orden de mantención"
    _order = "scheduled_date desc, id desc"

    name = fields.Char(string="Número", required=True, readonly=True, copy=False, default="/")
    maintenance_type = fields.Selection(
        [("preventive", "Preventiva"), ("reactive", "Reactiva")],
        string="Tipo de mantención",
        required=True,
        default="preventive",
        index=True,
    )
    vehicle_id = fields.Many2one(
        "bomberos.vehicle",
        string="Vehículo",
        required=True,
        index=True,
        ondelete="restrict",
    )
    company_id = fields.Many2one(
        related="vehicle_id.company_id",
        string="Compañía",
        store=True,
        index=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        string="Moneda",
        readonly=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("scheduled", "Programada"),
            ("in_progress", "En ejecución"),
            ("review", "En revisión"),
            ("done", "Cerrada"),
            ("cancelled", "Cancelada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        index=True,
        readonly=True,
        copy=False,
    )
    scheduled_date = fields.Date(
        string="Fecha programada",
        required=True,
        default=fields.Date.context_today,
        index=True,
    )
    due_odometer_km = fields.Float(string="Kilometraje objetivo", digits=(12, 1))
    started_at = fields.Datetime(string="Inicio real", readonly=True, copy=False)
    completed_at = fields.Datetime(string="Enviada a revisión", readonly=True, copy=False)
    reviewed_at = fields.Datetime(string="Fecha de cierre", readonly=True, copy=False)
    created_by = fields.Many2one("res.users", string="Creada por", default=lambda self: self.env.user)
    reviewer_id = fields.Many2one("res.users", string="Cerrada por", readonly=True, copy=False)
    failure_description = fields.Text(string="Falla reportada")
    diagnosis = fields.Text(string="Diagnóstico")
    work_description = fields.Text(string="Trabajo realizado")
    odometer_km = fields.Float(string="Kilometraje al finalizar", digits=(12, 1))
    material_line_ids = fields.One2many(
        "bomberos.maintenance.material",
        "order_id",
        string="Materiales y repuestos",
    )
    labor_line_ids = fields.One2many(
        "bomberos.maintenance.labor",
        "order_id",
        string="Mano de obra",
    )
    material_cost = fields.Monetary(
        string="Costo de materiales",
        currency_field="currency_id",
        compute="_compute_costs",
        store=True,
    )
    labor_cost = fields.Monetary(
        string="Costo de mano de obra",
        currency_field="currency_id",
        compute="_compute_costs",
        store=True,
    )
    total_cost = fields.Monetary(
        string="Costo total",
        currency_field="currency_id",
        compute="_compute_costs",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "bomberos_maintenance_due_km_nonnegative",
            "check(due_odometer_km is null or due_odometer_km >= 0)",
            "El kilometraje objetivo no puede ser negativo.",
        ),
        (
            "bomberos_maintenance_actual_km_nonnegative",
            "check(odometer_km is null or odometer_km >= 0)",
            "El kilometraje al finalizar no puede ser negativo.",
        ),
    ]

    @api.depends("material_line_ids.subtotal", "labor_line_ids.subtotal")
    def _compute_costs(self):
        for order in self:
            order.material_cost = sum(order.material_line_ids.mapped("subtotal"))
            order.labor_cost = sum(order.labor_line_ids.mapped("subtotal"))
            order.total_cost = order.material_cost + order.labor_cost

    @api.constrains("maintenance_type", "failure_description")
    def _check_reactive_failure(self):
        for order in self:
            if order.maintenance_type == "reactive" and not order.failure_description:
                raise ValidationError(_("Registra la falla reportada para una mantención reactiva."))

    @api.constrains("vehicle_id", "state")
    def _check_single_active_order(self):
        for order in self.filtered(lambda item: item.state == "in_progress"):
            other_order = self.search(
                [
                    ("vehicle_id", "=", order.vehicle_id.id),
                    ("state", "=", "in_progress"),
                    ("id", "!=", order.id),
                ],
                limit=1,
            )
            if other_order:
                raise ValidationError(
                    _("El vehículo ya tiene otra orden de mantención en ejecución.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        sequence = self.env["ir.sequence"]
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = sequence.next_by_code("bomberos.maintenance.order") or "/"
        return super().create(vals_list)

    def write(self, vals):
        if "state" in vals and not self.env.context.get("bomberos_allow_state_transition"):
            raise UserError(_("Cambia el estado usando las acciones del flujo de mantención."))
        if not self.env.context.get("bomberos_allow_state_transition") and self.filtered(
            lambda order: order.state in ("review", "done", "cancelled")
        ):
            raise UserError(_("Las órdenes en revisión o cerradas no se pueden modificar."))
        return super().write(vals)

    def _transition(self, vals):
        return self.with_context(bomberos_allow_state_transition=True).write(vals)

    def action_schedule(self):
        for order in self:
            if order.state != "draft":
                raise UserError(_("Solo se pueden programar órdenes en borrador."))
            if order.vehicle_id.operational_state == "unavailable":
                raise UserError(_("No se puede programar una unidad fuera de servicio."))
        self._transition({"state": "scheduled"})

    def action_start(self):
        for order in self:
            if order.state != "scheduled":
                raise UserError(_("Solo se pueden iniciar órdenes programadas."))
            if order.vehicle_id.operational_state in ("unavailable", "in_maintenance"):
                raise UserError(
                    _("La unidad está fuera de servicio o ya tiene una mantención en curso.")
                )
            order.vehicle_id._set_in_maintenance()
        self._transition(
            {
                "state": "in_progress",
                "started_at": fields.Datetime.now(),
            }
        )

    def action_submit_review(self):
        for order in self:
            if order.state != "in_progress":
                raise UserError(_("Solo se pueden enviar a revisión órdenes en ejecución."))
            if not order.work_description:
                raise UserError(_("Describe el trabajo realizado antes de solicitar revisión."))
            if order.odometer_km:
                self.env["bomberos.vehicle.odometer"].create(
                    {
                        "vehicle_id": order.vehicle_id.id,
                        "date": fields.Date.context_today(order),
                        "km": order.odometer_km,
                        "note": _("Lectura al finalizar %s") % order.name,
                    }
                )
        self._transition(
            {
                "state": "review",
                "completed_at": fields.Datetime.now(),
            }
        )

    def action_close(self):
        if not self.env.user.has_group("bomberos_base.group_bomberos_fleet_manager"):
            raise AccessError(_("Solo la jefatura de flota puede cerrar órdenes."))
        for order in self:
            if order.state != "review":
                raise UserError(_("Solo se pueden cerrar órdenes que estén en revisión."))
        self._transition(
            {
                "state": "done",
                "reviewer_id": self.env.user.id,
                "reviewed_at": fields.Datetime.now(),
            }
        )
        self.mapped("vehicle_id")._restore_after_maintenance()

    def action_cancel(self):
        if not self.env.user.has_group("bomberos_base.group_bomberos_fleet_manager"):
            raise AccessError(_("Solo la jefatura de flota puede cancelar órdenes."))
        if self.filtered(lambda order: order.state not in ("draft", "scheduled")):
            raise UserError(_("Solo se pueden cancelar órdenes en borrador o programadas."))
        self._transition({"state": "cancelled"})


class BomberosMaintenanceMaterial(models.Model):
    _name = "bomberos.maintenance.material"
    _description = "Material utilizado en mantención"
    _order = "id"

    order_id = fields.Many2one(
        "bomberos.maintenance.order",
        string="Orden",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="order_id.company_id", store=True, index=True)
    description = fields.Char(string="Material / repuesto", required=True)
    quantity = fields.Float(string="Cantidad", required=True, default=1, digits=(12, 2))
    unit = fields.Char(string="Unidad", default="unidad")
    unit_cost = fields.Monetary(
        string="Costo unitario",
        currency_field="currency_id",
        required=True,
        default=0,
    )
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=True,
    )

    _sql_constraints = [
        ("bomberos_material_quantity_positive", "check(quantity > 0)", "La cantidad debe ser mayor que cero."),
        ("bomberos_material_cost_nonnegative", "check(unit_cost >= 0)", "El costo no puede ser negativo."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        order_ids = {
            vals.get("order_id") or self.env.context.get("default_order_id")
            for vals in vals_list
            if vals.get("order_id") or self.env.context.get("default_order_id")
        }
        orders = self.env["bomberos.maintenance.order"].browse(order_ids)
        if orders.filtered(lambda order: order.state not in ("draft", "scheduled", "in_progress")):
            raise UserError(_("No se pueden agregar materiales a una orden en revisión o cerrada."))
        return super().create(vals_list)

    def write(self, vals):
        if self.filtered(
            lambda line: line.order_id.state not in ("draft", "scheduled", "in_progress")
        ):
            raise UserError(_("No se pueden modificar materiales de una orden en revisión o cerrada."))
        if vals.get("order_id"):
            order = self.env["bomberos.maintenance.order"].browse(vals["order_id"])
            if order.state not in ("draft", "scheduled", "in_progress"):
                raise UserError(_("No se pueden mover materiales a una orden en revisión o cerrada."))
        return super().write(vals)

    def unlink(self):
        if self.filtered(
            lambda line: line.order_id.state not in ("draft", "scheduled", "in_progress")
        ):
            raise UserError(_("No se pueden eliminar materiales de una orden en revisión o cerrada."))
        return super().unlink()

    @api.depends("quantity", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_cost


class BomberosMaintenanceLabor(models.Model):
    _name = "bomberos.maintenance.labor"
    _description = "Mano de obra de mantención"
    _order = "id"

    order_id = fields.Many2one(
        "bomberos.maintenance.order",
        string="Orden",
        required=True,
        ondelete="cascade",
        index=True,
    )
    company_id = fields.Many2one(related="order_id.company_id", store=True, index=True)
    description = fields.Char(string="Trabajo / especialidad", required=True)
    hours = fields.Float(string="Horas", required=True, default=1, digits=(12, 2))
    hourly_rate = fields.Monetary(
        string="Costo por hora",
        currency_field="currency_id",
        required=True,
        default=0,
    )
    currency_id = fields.Many2one(related="order_id.currency_id", readonly=True)
    subtotal = fields.Monetary(
        string="Subtotal",
        currency_field="currency_id",
        compute="_compute_subtotal",
        store=True,
    )

    _sql_constraints = [
        ("bomberos_labor_hours_positive", "check(hours > 0)", "Las horas deben ser mayores que cero."),
        ("bomberos_labor_rate_nonnegative", "check(hourly_rate >= 0)", "El costo por hora no puede ser negativo."),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        order_ids = {
            vals.get("order_id") or self.env.context.get("default_order_id")
            for vals in vals_list
            if vals.get("order_id") or self.env.context.get("default_order_id")
        }
        orders = self.env["bomberos.maintenance.order"].browse(order_ids)
        if orders.filtered(lambda order: order.state not in ("draft", "scheduled", "in_progress")):
            raise UserError(_("No se puede agregar mano de obra a una orden en revisión o cerrada."))
        return super().create(vals_list)

    def write(self, vals):
        if self.filtered(
            lambda line: line.order_id.state not in ("draft", "scheduled", "in_progress")
        ):
            raise UserError(_("No se puede modificar mano de obra de una orden en revisión o cerrada."))
        if vals.get("order_id"):
            order = self.env["bomberos.maintenance.order"].browse(vals["order_id"])
            if order.state not in ("draft", "scheduled", "in_progress"):
                raise UserError(_("No se puede mover mano de obra a una orden en revisión o cerrada."))
        return super().write(vals)

    def unlink(self):
        if self.filtered(
            lambda line: line.order_id.state not in ("draft", "scheduled", "in_progress")
        ):
            raise UserError(_("No se puede eliminar mano de obra de una orden en revisión o cerrada."))
        return super().unlink()

    @api.depends("hours", "hourly_rate")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.hours * line.hourly_rate
