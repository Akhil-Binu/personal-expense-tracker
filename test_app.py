"""
Test suite for Personal Expense Tracker.
Tests database operations, API endpoints, Excel import/export, and page rendering.
"""
import io
import unittest
from datetime import date
from app import app
import database
import excel_service

class ExpenseTrackerTestCase(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()
        database.init_db(seed_sample_data=True)
        # Log in as default user 1 for dashboard tests
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1

    def test_account_creation_and_recovery(self):
        """Test user registration, recovery phrase generation, and account recovery."""
        # Log out for registration
        with self.client.session_transaction() as sess:
            sess.clear()

        # 1. Register a new user
        res_reg = self.client.post("/register", data={
            "username": "alice_finance",
            "email": "alice@example.com",
            "password": "originalPassword123",
            "confirm_password": "originalPassword123"
        })
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn(b"Save Your Backup Keywords", res_reg.data)
        self.assertIn(b"alice_finance", res_reg.data)

        # 2. Verify user in database
        alice = database.get_user_by_username("alice_finance")
        self.assertIsNotNone(alice)

        # 3. Test invalid login
        self.assertIsNone(database.authenticate_user("alice_finance", "wrongPassword"))
        # Test valid login
        self.assertIsNotNone(database.authenticate_user("alice_finance", "originalPassword123"))

        # 4. Perform direct recovery using generated phrase via create_user
        user_data = database.create_user("bob_crypto", "initialPassword")
        phrase = user_data["recovery_phrase"]
        self.assertEqual(len(user_data["recovery_words"]), 12)

        # 5. Recover bob_crypto's password with recovery phrase
        res_rec = self.client.post("/recover", data={
            "username": "bob_crypto",
            "recovery_phrase": phrase,
            "new_password": "brandNewPassword789",
            "confirm_password": "brandNewPassword789"
        }, follow_redirects=True)
        self.assertEqual(res_rec.status_code, 200)

        # Verify old password fails and new password succeeds
        self.assertIsNone(database.authenticate_user("bob_crypto", "initialPassword"))
        self.assertIsNotNone(database.authenticate_user("bob_crypto", "brandNewPassword789"))

    def test_pages_render_successfully(self):
        """Test all 4 main views load with 200 OK."""
        # 1. Dashboard
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"FinanceFlow", res.data)
        self.assertIn(b"Financial Overview", res.data)

        # 2. Expenses Page
        res = self.client.get("/expenses")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Expense Management", res.data)

        # 3. Reports Page
        res = self.client.get("/reports")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Monthly Analytics Report", res.data)

        # 4. Categories Page
        res = self.client.get("/categories")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Monthly Budgets & Categories", res.data)

    def test_currency_settings(self):
        """Test getting and changing currency settings."""
        # 1. Get current currency
        res = self.client.get("/api/settings/currency")
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIn("currency", json_data)
        self.assertIn("supported", json_data)

        # 2. Change currency to INR (₹)
        res_post = self.client.post("/api/settings/currency", json={"code": "INR"})
        self.assertEqual(res_post.status_code, 200)
        curr = database.get_currency()
        self.assertEqual(curr["code"], "INR")
        self.assertEqual(curr["symbol"], "₹")

        # 3. Change back to USD ($)
        self.client.post("/api/settings/currency", json={"code": "USD"})
        curr_usd = database.get_currency()
        self.assertEqual(curr_usd["code"], "USD")
        self.assertEqual(curr_usd["symbol"], "$")

    def test_add_and_get_expense(self):
        """Test adding an expense via JSON API."""
        categories = database.get_categories()
        first_cat_id = categories[0]["id"]

        payload = {
            "amount": 75.50,
            "description": "Team lunch buffet",
            "category_id": first_cat_id,
            "date": date.today().isoformat(),
            "payment_method": "Credit Card",
            "notes": "Office social"
        }
        res = self.client.post("/api/expense", json=payload)
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertTrue(json_data["success"])
        new_id = json_data["id"]

        # Fetch expense details
        res_get = self.client.get(f"/api/expense/{new_id}")
        self.assertEqual(res_get.status_code, 200)
        exp_data = res_get.get_json()["expense"]
        self.assertEqual(exp_data["description"], "Team lunch buffet")
        self.assertEqual(exp_data["amount"], 75.50)

    def test_update_and_delete_expense(self):
        """Test modifying and deleting an expense."""
        categories = database.get_categories()
        cat_id = categories[0]["id"]
        exp_id = database.add_expense(
            expense_date=date.today().isoformat(),
            category_id=cat_id,
            amount=30.00,
            payment_method="Cash",
            description="Bookstore magazine"
        )

        # Update
        update_payload = {
            "amount": 35.00,
            "description": "Bookstore magazine and pen",
            "category_id": cat_id,
            "date": date.today().isoformat(),
            "payment_method": "Cash",
            "notes": "Updated note"
        }
        res_upd = self.client.put(f"/api/expense/{exp_id}", json=update_payload)
        self.assertEqual(res_upd.status_code, 200)

        # Check updated
        updated_exp = database.get_expense_by_id(exp_id)
        self.assertEqual(updated_exp["amount"], 35.00)
        self.assertEqual(updated_exp["description"], "Bookstore magazine and pen")

        # Delete
        res_del = self.client.post(f"/api/expense/{exp_id}/delete")
        self.assertEqual(res_del.status_code, 200)
        self.assertIsNone(database.get_expense_by_id(exp_id))

    def test_category_api(self):
        """Test creating, updating and deleting custom category."""
        payload = {
            "name": "Software Subscriptions",
            "icon": "bolt",
            "color": "#6366F1",
            "monthly_budget": 80.0
        }
        res = self.client.post("/api/category", json=payload)
        self.assertEqual(res.status_code, 200)
        cat_id = res.get_json()["id"]

        cat = database.get_category_by_id(cat_id)
        self.assertEqual(cat["name"], "Software Subscriptions")
        self.assertEqual(cat["monthly_budget"], 80.0)

        # Delete category (should succeed since no expenses linked)
        res_del = self.client.post(f"/api/category/{cat_id}/delete")
        self.assertEqual(res_del.status_code, 200)
        self.assertIsNone(database.get_category_by_id(cat_id))

    def test_chart_data_api(self):
        """Test API chart data endpoint returns proper structure."""
        res = self.client.get("/api/chart-data")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("categories", data)
        self.assertIn("daily", data)
        self.assertIn("history", data)
        self.assertIn("payment_methods", data)

    def test_excel_export_download(self):
        """Test downloading the generated Excel report."""
        res = self.client.get("/export/excel")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(
            res.mimetype,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        self.assertGreater(len(res.data), 1000)

    def test_excel_template_and_import(self):
        """Test Excel template generation and round-trip import."""
        # 1. Download template
        tpl_res = self.client.get("/export/template")
        self.assertEqual(tpl_res.status_code, 200)
        self.assertGreater(len(tpl_res.data), 1000)

        # 2. Upload template back via /import/excel
        data = {
            "file": (io.BytesIO(tpl_res.data), "test_import.xlsx")
        }
        imp_res = self.client.post(
            "/import/excel",
            data=data,
            content_type="multipart/form-data"
        )
        self.assertEqual(imp_res.status_code, 200)
        json_res = imp_res.get_json()
        self.assertTrue(json_res["success"])
        self.assertGreaterEqual(json_res["details"]["imported"], 1)

if __name__ == "__main__":
    unittest.main()
