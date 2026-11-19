from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class BomberosMaintenanceAlert(models.Model):
    _name = "bomberos.maintenance.alert"
    _description = "Aviso de mantención"
    _order = "alert_type, id desc"

    name = fields.Char(string="Aviso", required=True)
    maintenance_id = fields.Many2one(
        "bomberos.maintenance.order",
        string="Orden de mantención",
        required=True,
        index=True,
        ondelete="cascade",
    )
    company_id = fields.Many2one(related="maintenance_id.company_id", store=True, index=True)
    alert_type = fields.Selection(
        [
            ("upcoming", "Próxima"),
            ("overdue", "Vencida"),
            ("pending_review", "Pendiente de revisión"),
        ],
        string="Tipo",
        required=True,
        index=True,
    )
    message = fields.Char(string="Detalle", required=True)
    active = fields.Boolean(default=True, index=True)
    acknowledged = fields.Boolean(string="Revisado", default=False, index=True)
    acknowledged_by = fields.Many2one("res.users", string="Revisado por", readonly=True)
    acknowledged_at = fields.Datetime(string="Fecha de revisión", readonly=True)

    _sql_constraints = [
        (
            "bomberos_alert_order_type_uniq",
            "unique(maintenance_id, alert_type)",
            "Ya existe un aviso de este tipo para la orden.",
        ),
    ]

    def action_acknowledge(self):
        if not (
            self.env.user.has_group("bomberos_base.group_bomberos_technician")
            or self.env.user.has_group("bomberos_base.group_bomberos_fleet_manager")
        ):
            raise AccessError(_("Solo técnicos y jefatura pueden marcar avisos como revisados."))
        self.write(
            {
                "acknowledged": True,
                "acknowledged_by": self.env.user.id,
                "acknowledged_at": fields.Datetime.now(),
            }
        )

    @api.model
    def _cron_refresh_alerts(self):
        today = fields.Date.today()
        upcoming_date = today + timedelta(days=30)
        orders = self.env["bomberos.maintenance.order"].sudo().search(
            [("state", "in", ("scheduled", "review"))]
        )
        desired_alerts = {}
        for order in orders:
            alert_type = None
            message = ""
            if order.state == "review":
                alert_type = "pending_review"
                message = _("La orden %s está pendiente de revisión.") % order.name
            else:
                date_overdue = order.scheduled_date and order.scheduled_date <= today
                km_overdue = (
                    order.due_odometer_km
                    and order.vehicle_id.current_odometer_km >= order.due_odometer_km
                )
                if date_overdue or km_overdue:
                    alert_type = "overdue"
                    message = _("La orden %s alcanzó su fecha o kilometraje objetivo.") % order.name
                else:
                    date_upcoming = order.scheduled_date and order.scheduled_date <= upcoming_date
                    km_upcoming = (
                        order.due_odometer_km
                        and order.vehicle_id.current_odometer_km
                        >= max(order.due_odometer_km - 500, 0)
                    )
                    if date_upcoming or km_upcoming:
                        alert_type = "upcoming"
                        message = _("La orden %s vence dentro de 30 días o 500 km.") % order.name
            if alert_type:
                desired_alerts[(order.id, alert_type)] = (order, message)

        Alert = self.sudo().with_context(active_test=False)
        existing_alerts = Alert.search([])
        for alert in existing_alerts:
            if (alert.maintenance_id.id, alert.alert_type) not in desired_alerts:
                alert.write({"active": False})
        for (order_id, alert_type), (order, message) in desired_alerts.items():
            alert = Alert.search(
                [
                    ("maintenance_id", "=", order_id),
                    ("alert_type", "=", alert_type),
                ],
                limit=1,
            )
            vals = {
                "name": dict(self._fields["alert_type"].selection).get(alert_type),
                "message": message,
                "active": True,
            }
            if alert:
                if not alert.active:
                    vals.update(
                        {
                            "acknowledged": False,
                            "acknowledged_by": False,
                            "acknowledged_at": False,
                        }
                    )
                alert.write(vals)
            else:
                vals.update(
                    {
                        "maintenance_id": order_id,
                        "alert_type": alert_type,
                    }
                )
                Alert.create(vals)
