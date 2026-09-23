import importlib
import os
import tempfile
import unittest
from datetime import datetime


class SecurityCalendarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        cls.database.close()
        os.environ["DATABASE_URL"] = "sqlite:///" + cls.database.name.replace("\\", "/")
        os.environ["SECRET_KEY"] = "test-only-secret-key"
        os.environ["ADMIN_LOGIN_ID"] = "test-admin"
        os.environ["ADMIN_PASSWORD"] = "test-admin-password"
        cls.module = importlib.import_module("app")
        cls.module.app.config["TESTING"] = True

    @classmethod
    def tearDownClass(cls):
        with cls.module.app.app_context():
            cls.module.db.session.remove()
            cls.module.db.engine.dispose()
        os.unlink(cls.database.name)

    def setUp(self):
        self.client = self.module.app.test_client()

    def token(self):
        with self.client.session_transaction() as session:
            return session["csrf_token"]

    def login(self, username="test-admin", password="test-admin-password"):
        self.client.get("/login")
        return self.client.post("/login", data={
            "login_id": username, "password": password, "csrf_token": self.token()
        })

    def test_protected_routes_and_csrf(self):
        self.assertIn("/login", self.client.get("/").headers["Location"])
        self.assertIn("/login", self.client.get("/admin").headers["Location"])
        self.assertEqual(self.client.get("/api/events").status_code, 302)
        self.assertEqual(self.client.post("/login", data={"login_id": "test-admin"}).status_code, 400)
        self.assertEqual(self.login().status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 200)
        self.assertEqual(self.client.post("/logout").status_code, 400)

    def test_legacy_auto_login_session_is_revoked(self):
        with self.module.app.app_context():
            admin = self.module.User.query.filter_by(login_id="test-admin").first()
            admin_id = admin.id
        with self.client.session_transaction() as session:
            session["_user_id"] = str(admin_id)
            session["_fresh"] = True
        self.assertIn("/login", self.client.get("/admin").headers["Location"])

    def test_tenant_and_deactivated_session(self):
        self.login()
        module = self.module
        with module.app.app_context():
            user = module.User(login_id="test-member", password_hash=module.generate_password_hash("member-password"), display_name="Member")
            module.db.session.add(user)
            module.db.session.commit()
            user_id = user.id
            company = module.SelectionCompany(user_id=user_id, company_name="Two-day internship", join_start_at=datetime(2026, 9, 30, 10), join_end_at=datetime(2026, 10, 2, 0))
            module.db.session.add(company)
            module.db.session.commit()
        self.assertEqual(self.client.get("/api/events").json, [])
        self.client.get("/")
        self.client.post("/logout", data={"csrf_token": self.token()})
        self.assertEqual(self.login("test-member", "member-password").status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 403)
        event = self.client.get("/api/events").json[0]
        self.assertEqual((event["date"], event["end_date"], event["end_time"]), ("2026-09-30", "2026-10-02", "00:00"))
        with module.app.app_context():
            user = module.db.session.get(module.User, user_id)
            user.is_active_account = False
            module.db.session.commit()
        self.assertIn("/login", self.client.get("/api/events").headers["Location"])


if __name__ == "__main__":
    unittest.main()
