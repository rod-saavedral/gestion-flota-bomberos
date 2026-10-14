from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestBomberosCompanySecurity(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_one = cls.env["bomberos.company"].create(
            {"name": "Prueba Talcahuano 01", "code": "TEST-SEC-01"}
        )
        cls.company_two = cls.env["bomberos.company"].create(
            {"name": "Prueba Talcahuano 02", "code": "TEST-SEC-02"}
        )

    def _make_user(self, login, group_xmlid, companies):
        return self.env["res.users"].create(
            {
                "name": login,
                "login": login,
                "email": f"{login}@example.test",
                "groups_id": [(6, 0, [self.env.ref(group_xmlid).id])],
                "bomberos_company_ids": [(6, 0, companies.ids)],
            }
        )

    def test_consultant_is_limited_to_assigned_companies(self):
        consultant = self._make_user(
            "bomberos-consultant-test",
            "bomberos_base.group_bomberos_consultant",
            self.company_one,
        )

        visible_ids = self.env["bomberos.company"].with_user(consultant).search([]).ids

        self.assertEqual(visible_ids, self.company_one.ids)

    def test_fleet_manager_can_read_all_companies(self):
        manager = self._make_user(
            "bomberos-manager-test",
            "bomberos_base.group_bomberos_fleet_manager",
            self.company_one,
        )

        visible_ids = self.env["bomberos.company"].with_user(manager).search([]).ids

        self.assertIn(self.company_one.id, visible_ids)
        self.assertIn(self.company_two.id, visible_ids)
