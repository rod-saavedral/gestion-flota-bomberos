from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBomberosVehicle(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env["bomberos.company"].create(
            {"name": "Flota de prueba", "code": "TEST-FLEET"}
        )
        cls.vehicle = cls.env["bomberos.vehicle"].create(
            {
                "name": "Unidad de prueba",
                "code": "TEST-01",
                "license_plate": "TEST-001",
                "company_id": cls.company.id,
                "vehicle_type": "pump",
            }
        )

    def test_odometer_updates_vehicle_and_rejects_decrease(self):
        Odometer = self.env["bomberos.vehicle.odometer"]
        Odometer.create({"vehicle_id": self.vehicle.id, "km": 12500})

        self.assertEqual(self.vehicle.current_odometer_km, 12500)

        with self.assertRaises(ValidationError):
            Odometer.create({"vehicle_id": self.vehicle.id, "km": 12400})

    def test_user_cannot_set_vehicle_unavailable(self):
        consultant = self.env["res.users"].create(
            {
                "name": "Consultor de prueba",
                "login": "bomberos-vehicle-consultant-test",
                "groups_id": [
                    (6, 0, [self.env.ref("bomberos_base.group_bomberos_consultant").id])
                ],
                "bomberos_company_ids": [(6, 0, self.company.ids)],
            }
        )

        with self.assertRaises(AccessError):
            self.vehicle.with_user(consultant).action_set_unavailable()

    def test_vehicle_records_are_limited_to_assigned_company(self):
        other_company = self.env["bomberos.company"].create(
            {"name": "Otra compañía", "code": "TEST-FLEET-OTHER"}
        )
        other_vehicle = self.env["bomberos.vehicle"].create(
            {
                "name": "Otra unidad",
                "code": "TEST-02",
                "license_plate": "TEST-002",
                "company_id": other_company.id,
            }
        )
        consultant = self.env["res.users"].create(
            {
                "name": "Consulta de compañía",
                "login": "bomberos-company-scope-test",
                "groups_id": [
                    (6, 0, [self.env.ref("bomberos_base.group_bomberos_consultant").id])
                ],
                "bomberos_company_ids": [(6, 0, self.company.ids)],
            }
        )

        visible_ids = self.env["bomberos.vehicle"].with_user(consultant).search([]).ids

        self.assertIn(self.vehicle.id, visible_ids)
        self.assertNotIn(other_vehicle.id, visible_ids)
