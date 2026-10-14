from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError, UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBomberosMaintenance(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["bomberos.company"].create(
            {"name": "Mantención de prueba", "code": "TEST-MAINT"}
        )
        cls.vehicle = cls.env["bomberos.vehicle"].create(
            {
                "name": "Unidad de prueba",
                "code": "TEST-MT-01",
                "license_plate": "TEST-MT-001",
                "company_id": cls.company.id,
            }
        )
        cls.technician = cls.env["res.users"].create(
            {
                "name": "Técnico de prueba",
                "login": "bomberos-maintenance-technician-test",
                "groups_id": [
                    (6, 0, [cls.env.ref("bomberos_base.group_bomberos_technician").id])
                ],
                "bomberos_company_ids": [(6, 0, cls.company.ids)],
            }
        )
        cls.manager = cls.env["res.users"].create(
            {
                "name": "Jefe de flota de prueba",
                "login": "bomberos-maintenance-manager-test",
                "groups_id": [
                    (6, 0, [cls.env.ref("bomberos_base.group_bomberos_fleet_manager").id])
                ],
                "bomberos_company_ids": [(6, 0, cls.company.ids)],
            }
        )

    def test_reactive_order_costs_and_review_flow(self):
        order = self.env["bomberos.maintenance.order"].create(
            {
                "maintenance_type": "reactive",
                "vehicle_id": self.vehicle.id,
                "scheduled_date": fields.Date.today(),
                "failure_description": "Falla de prueba",
                "material_line_ids": [
                    (
                        0,
                        0,
                        {
                            "description": "Repuesto",
                            "quantity": 2,
                            "unit_cost": 10000,
                        },
                    )
                ],
                "labor_line_ids": [
                    (
                        0,
                        0,
                        {
                            "description": "Mano de obra",
                            "hours": 3,
                            "hourly_rate": 8000,
                        },
                    )
                ],
            }
        )
        self.assertEqual(order.material_cost, 20000)
        self.assertEqual(order.labor_cost, 24000)
        self.assertEqual(order.total_cost, 44000)

        order.action_schedule()
        technician_order = order.with_user(self.technician)
        technician_order.action_start()
        self.assertEqual(order.state, "in_progress")
        self.assertEqual(self.vehicle.operational_state, "in_maintenance")

        with self.assertRaises(UserError):
            technician_order.write({"state": "review"})

        technician_order.write(
            {
                "work_description": "Reparación terminada",
                "odometer_km": 750,
            }
        )
        technician_order.action_submit_review()
        self.assertEqual(order.state, "review")

        manager_order = order.with_user(self.manager)
        manager_order.action_close()
        self.assertEqual(order.state, "done")
        self.assertEqual(order.reviewer_id, self.manager)
        self.assertEqual(self.vehicle.operational_state, "available")
        self.assertEqual(self.vehicle.current_odometer_km, 750)
        with self.assertRaises(UserError):
            order.write({"work_description": "Edición posterior al cierre"})
        with self.assertRaises(UserError):
            order.material_line_ids.write({"unit_cost": 1})

    def test_reactive_order_requires_failure_description(self):
        with self.assertRaises(ValidationError):
            self.env["bomberos.maintenance.order"].create(
                {
                    "maintenance_type": "reactive",
                    "vehicle_id": self.vehicle.id,
                    "scheduled_date": fields.Date.today(),
                }
            )

    def test_only_fleet_manager_can_close_orders(self):
        order = self.env["bomberos.maintenance.order"].create(
            {
                "maintenance_type": "reactive",
                "vehicle_id": self.vehicle.id,
                "scheduled_date": fields.Date.today(),
                "failure_description": "Falla de prueba",
                "state": "review",
            }
        )

        with self.assertRaises(AccessError):
            order.with_user(self.technician).action_close()

    def test_alerts_transition_from_upcoming_to_overdue_without_duplicates(self):
        due_date = fields.Date.today() + timedelta(days=15)
        order = self.env["bomberos.maintenance.order"].create(
            {
                "maintenance_type": "preventive",
                "vehicle_id": self.vehicle.id,
                "scheduled_date": due_date,
                "due_odometer_km": 1000,
                "state": "scheduled",
            }
        )
        Alert = self.env["bomberos.maintenance.alert"].sudo()

        Alert._cron_refresh_alerts()
        upcoming = Alert.search(
            [
                ("maintenance_id", "=", order.id),
                ("alert_type", "=", "upcoming"),
            ]
        )
        self.assertTrue(upcoming.active)

        self.env["bomberos.vehicle.odometer"].create(
            {"vehicle_id": self.vehicle.id, "km": 1000}
        )
        Alert._cron_refresh_alerts()
        overdue = Alert.search(
            [
                ("maintenance_id", "=", order.id),
                ("alert_type", "=", "overdue"),
            ]
        )
        self.assertTrue(overdue.active)
        self.assertFalse(upcoming.active)

        Alert._cron_refresh_alerts()
        self.assertEqual(
            Alert.search_count(
                [
                    ("maintenance_id", "=", order.id),
                    ("alert_type", "=", "overdue"),
                ]
            ),
            1,
        )
