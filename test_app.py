"""
Test suite for Personal Expense Tracker.
Tests database operations, API endpoints, Excel import/export, and page rendering.
"""
import io
import unittest
import uuid
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

        rand_tag = uuid.uuid4().hex[:6]
        user_alice = f"alice_{rand_tag}"
        user_bob = f"bob_{rand_tag}"

        # 1. Register a new user
        res_reg = self.client.post("/register", data={
            "username": user_alice,
            "email": f"{user_alice}@example.com",
            "password": "originalPassword123",
            "confirm_password": "originalPassword123"
        })
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn(b"Save Your Backup Keywords", res_reg.data)
        self.assertIn(user_alice.encode(), res_reg.data)

        # 2. Verify user in database
        alice = database.get_user_by_username(user_alice)
        self.assertIsNotNone(alice)

        # 3. Test invalid login
        self.assertIsNone(database.authenticate_user(user_alice, "wrongPassword"))
        # Test valid login
        self.assertIsNotNone(database.authenticate_user(user_alice, "originalPassword123"))

        # 4. Perform direct recovery using generated phrase via create_user
        user_data = database.create_user(user_bob, "initialPassword")
        phrase = user_data["recovery_phrase"]
        self.assertEqual(len(user_data["recovery_words"]), 12)

        # 5. Recover bob's password with recovery phrase
        res_rec = self.client.post("/recover", data={
            "username": user_bob,
            "recovery_phrase": phrase,
            "new_password": "brandNewPassword789",
            "confirm_password": "brandNewPassword789"
        }, follow_redirects=True)
        self.assertEqual(res_rec.status_code, 200)

        # Verify old password fails and new password succeeds
        self.assertIsNone(database.authenticate_user(user_bob, "initialPassword"))
        self.assertIsNotNone(database.authenticate_user(user_bob, "brandNewPassword789"))

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

        # 5. Bank Accounts Page
        res = self.client.get("/accounts")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Bank Accounts & Net Balance", res.data)
        self.assertIn(b"Total Combined Net Balance", res.data)

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

    def test_bank_account_crud_and_combined_balance(self):
        """Test creating bank accounts, linking expenses, calculating individual and combined balances."""
        # 1. Create a dedicated test user
        user = database.create_user(f"charlie_{uuid.uuid4().hex[:6]}", "securePassword123")
        user_id = user["id"]

        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id

        # 2. Add two bank accounts
        res1 = self.client.post("/api/account", json={
            "name": "Barclays Checking",
            "account_type": "Checking",
            "initial_balance": 4000.0,
            "account_number": "5512",
            "color": "#0D9488",
            "icon": "building-columns"
        })
        self.assertEqual(res1.status_code, 200)
        acc1_id = res1.get_json()["id"]

        res2 = self.client.post("/api/account", json={
            "name": "Vanguard High-Yield",
            "account_type": "Savings",
            "initial_balance": 10000.0,
            "account_number": "9944",
            "color": "#3B82F6",
            "icon": "piggy-bank"
        })
        self.assertEqual(res2.status_code, 200)
        acc2_id = res2.get_json()["id"]

        # 3. Verify accounts retrieved
        acc1 = database.get_bank_account_by_id(acc1_id, user_id=user_id)
        self.assertIsNotNone(acc1)
        self.assertEqual(acc1["name"], "Barclays Checking")

        # 4. Check initial combined balance
        comb_before = database.get_combined_balance(user_id=user_id)
        # Note: create_user seeds 3 default accounts: 3000 + 8000 + 500 = 11500 + 4000 + 10000 = 25500
        self.assertEqual(comb_before["total_spent"], 0.0)
        expected_initial = 11500.0 + 4000.0 + 10000.0
        self.assertEqual(comb_before["total_initial"], expected_initial)
        self.assertEqual(comb_before["total_current"], expected_initial)

        # 5. Log an expense tied to acc1
        categories = database.get_categories(user_id=user_id)
        cat_id = categories[0]["id"]
        exp_res = self.client.post("/api/expense", json={
            "amount": 250.00,
            "description": "Smart Desk Chair",
            "category_id": cat_id,
            "date": date.today().isoformat(),
            "payment_method": "Debit Card",
            "account_id": acc1_id
        })
        self.assertEqual(exp_res.status_code, 200)

        # 6. Verify acc1 balance deducted
        accounts = database.get_bank_accounts(user_id=user_id)
        acc1_data = next(a for a in accounts if a["id"] == acc1_id)
        self.assertEqual(acc1_data["total_spent"], 250.00)
        self.assertEqual(acc1_data["current_balance"], 3750.00)

        # 7. Verify combined balance updated
        comb_after = database.get_combined_balance(user_id=user_id)
        self.assertEqual(comb_after["total_spent"], 250.00)
        self.assertEqual(comb_after["total_current"], expected_initial - 250.00)

        # 8. Update acc2
        upd_res = self.client.put(f"/api/account/{acc2_id}", json={
            "name": "Vanguard High-Yield Premium",
            "account_type": "Savings",
            "initial_balance": 12000.0,
            "account_number": "9944",
            "color": "#3B82F6",
            "icon": "vault"
        })
        self.assertEqual(upd_res.status_code, 200)
        acc2_updated = database.get_bank_account_by_id(acc2_id, user_id=user_id)
        self.assertEqual(acc2_updated["name"], "Vanguard High-Yield Premium")
        self.assertEqual(acc2_updated["initial_balance"], 12000.0)

        # 9. Delete acc2
        del_res = self.client.post(f"/api/account/{acc2_id}/delete")
        self.assertEqual(del_res.status_code, 200)
        self.assertIsNone(database.get_bank_account_by_id(acc2_id, user_id=user_id))

    def test_monthly_budget_api(self):
        """Test getting and updating monthly budgets (batch, overall, and single category)."""
        # 1. Get current budget data
        res = self.client.get("/api/budget")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertIn("categories", data)
        self.assertIn("total_budget", data)
        self.assertGreater(len(data["categories"]), 0)

        cat1_id = data["categories"][0]["id"]
        cat2_id = data["categories"][1]["id"]

        # 2. Update category budgets in batch
        update_payload = {
            "category_budgets": {
                str(cat1_id): 650.0,
                str(cat2_id): 350.0
            }
        }
        res_post = self.client.post("/api/budget", json=update_payload)
        self.assertEqual(res_post.status_code, 200)
        self.assertTrue(res_post.get_json()["success"])

        cat1 = database.get_category_by_id(cat1_id)
        self.assertEqual(cat1["monthly_budget"], 650.0)
        cat2 = database.get_category_by_id(cat2_id)
        self.assertEqual(cat2["monthly_budget"], 350.0)

        # 3. Scale total monthly budget proportionally
        res_total = self.client.post("/api/budget", json={"total_budget": 5000.0})
        self.assertEqual(res_total.status_code, 200)
        json_total = res_total.get_json()
        self.assertTrue(json_total["success"])
        # Total budget should be ~5000.00
        self.assertAlmostEqual(json_total["total_budget"], 5000.0, delta=1.0)

        # 4. Update single category budget
        res_single = self.client.put(f"/api/category/{cat1_id}/budget", json={"monthly_budget": 777.0})
        self.assertEqual(res_single.status_code, 200)
        cat1_updated = database.get_category_by_id(cat1_id)
        self.assertEqual(cat1_updated["monthly_budget"], 777.0)

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

    def test_v2_pages_and_pwa_assets(self):
        """Test v2.0 pages render and PWA manifest/service worker load."""
        for path in ["/income", "/subscriptions", "/goals", "/statement"]:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 200, f"Page {path} failed to load")

        # PWA manifest
        res_manifest = self.client.get("/manifest.json")
        self.assertEqual(res_manifest.status_code, 200)
        self.assertIn(b"FinanceFlow", res_manifest.data)

        # Service worker
        res_sw = self.client.get("/service-worker.js")
        self.assertEqual(res_sw.status_code, 200)
        self.assertIn(b"financeflow-v2.0.3", res_sw.data)

    def test_income_and_transfers_api(self):
        """Test Income CRUD and Inter-Account Transfers."""
        # Add income
        income_payload = {
            "source": "Consulting Project",
            "amount": 2500.0,
            "category": "Freelance",
            "date": "2026-10-15",
            "bank_account_id": 1,
            "notes": "Q4 strategy advisory"
        }
        res = self.client.post("/api/income", json=income_payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        income_id = data["income"]["id"]

        # List income
        res_list = self.client.get("/api/income")
        self.assertEqual(res_list.status_code, 200)
        items = res_list.get_json()["income"]
        self.assertTrue(any(i["id"] == income_id for i in items))

        # Check Cash Flow summary
        cf = database.get_cash_flow_summary(user_id=1)
        self.assertGreaterEqual(cf["total_income"], 2500.0)

        # Inter-Account Transfer (Account 1 to Account 2)
        accounts = database.get_bank_accounts(user_id=1)
        if len(accounts) >= 2:
            from_acc = accounts[0]["id"]
            to_acc = accounts[1]["id"]
            from_init = accounts[0]["current_balance"]
            to_init = accounts[1]["current_balance"]

            transfer_payload = {
                "from_account_id": from_acc,
                "to_account_id": to_acc,
                "amount": 300.0,
                "transfer_date": "2026-10-20",
                "notes": "Emergency fund deposit"
            }
            res_tf = self.client.post("/api/transfer", json=transfer_payload)
            self.assertEqual(res_tf.status_code, 200)
            tf_data = res_tf.get_json()
            self.assertTrue(tf_data["success"])

            # Verify balance updates
            acc1 = database.get_bank_account_by_id(from_acc, user_id=1)
            acc2 = database.get_bank_account_by_id(to_acc, user_id=1)
            self.assertAlmostEqual(acc1["current_balance"], from_init - 300.0, places=2)
            self.assertAlmostEqual(acc2["current_balance"], to_init + 300.0, places=2)

        # Delete income
        res_del = self.client.delete(f"/api/income/{income_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["success"])

    def test_subscriptions_and_mark_paid(self):
        """Test recurring subscriptions lifecycle and 1-click pay."""
        sub_payload = {
            "name": "Cloud Hosting Pro",
            "amount": 49.99,
            "billing_cycle": "Monthly",
            "next_due_date": "2026-11-01",
            "category_id": 1,
            "bank_account_id": 1,
            "notes": "Production server"
        }
        res = self.client.post("/api/subscription", json=sub_payload)
        self.assertEqual(res.status_code, 200)
        sub = res.get_json()["subscription"]
        sub_id = sub["id"]

        # List subscriptions
        res_list = self.client.get("/api/subscription")
        self.assertEqual(res_list.status_code, 200)
        subs = res_list.get_json()["subscriptions"]
        self.assertTrue(any(s["id"] == sub_id for s in subs))

        # Mark paid
        expenses_before = len(database.get_expenses(user_id=1))
        res_pay = self.client.post(f"/api/subscription/{sub_id}/pay")
        self.assertEqual(res_pay.status_code, 200)
        self.assertTrue(res_pay.get_json()["success"])

        # Check expense was recorded
        expenses_after = len(database.get_expenses(user_id=1))
        self.assertEqual(expenses_after, expenses_before + 1)

        # Delete subscription
        res_del = self.client.delete(f"/api/subscription/{sub_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["success"])

    def test_goals_and_contributions(self):
        """Test savings goals and contributions."""
        goal_payload = {
            "name": "Japan Trip 2027",
            "target_amount": 4000.0,
            "target_date": "2027-04-01",
            "icon": "bi-airplane",
            "color": "#0ea5e9",
            "notes": "Flights and ryokan"
        }
        res = self.client.post("/api/goal", json=goal_payload)
        self.assertEqual(res.status_code, 200)
        goal = res.get_json()["goal"]
        goal_id = goal["id"]

        # Contribute to goal
        res_contrib = self.client.post(f"/api/goal/{goal_id}/contribute", json={
            "amount": 500.0,
            "bank_account_id": 1,
            "category_id": 1
        })
        self.assertEqual(res_contrib.status_code, 200)
        contrib_data = res_contrib.get_json()
        self.assertTrue(contrib_data["success"])
        self.assertAlmostEqual(contrib_data["goal"]["current_amount"], 500.0)

        # Delete goal
        res_del = self.client.delete(f"/api/goal/{goal_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertTrue(res_del.get_json()["success"])

    def test_two_factor_auth_flow(self):
        """Test RFC 6238 TOTP 2FA setup, verify, and disable."""
        import auth_service

        # 1. Initiate 2FA setup via POST
        res_setup = self.client.post("/api/2fa/setup")
        self.assertEqual(res_setup.status_code, 200)
        setup_data = res_setup.get_json()
        self.assertTrue(setup_data["success"])
        secret = setup_data["secret"]
        self.assertTrue(len(secret) >= 16)

        # 2. Generate valid TOTP code
        code = auth_service.generate_totp_code(secret)
        self.assertEqual(len(code), 6)

        # 3. Verify and enable with secret + code
        res_enable = self.client.post("/api/2fa/verify-and-enable", json={"secret": secret, "code": code})
        self.assertEqual(res_enable.status_code, 200)
        self.assertTrue(res_enable.get_json()["success"])

        # Check status
        res_status = self.client.get("/api/2fa/status")
        self.assertTrue(res_status.get_json()["enabled"])

        # 4. Disable 2FA
        res_disable = self.client.post("/api/2fa/disable")
        self.assertEqual(res_disable.status_code, 200)
        self.assertTrue(res_disable.get_json()["success"])

    def test_analytics_and_insights(self):
        """Test smart AI insights and budget velocity."""
        import analytics_service
        # API insights test
        res = self.client.get("/api/insights")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        insights = data["insights"]
        self.assertIsInstance(insights, list)
        self.assertGreaterEqual(len(insights), 1)
        self.assertIn("title", insights[0])
        self.assertIn("message", insights[0])

        # Velocity calculation service test
        velocity = analytics_service.calculate_budget_velocity(user_id=1)
        self.assertIn("velocity_ratio", velocity)
        self.assertIn("status", velocity)
        self.assertIn("daily_run_rate", velocity)
        self.assertIn("month_pct_elapsed", velocity)

    def test_printable_statement_and_receipt_upload(self):
        """Test receipt attachment upload and printable financial statement rendering."""
        # 1. Add expense with receipt attachment
        dummy_receipt = (io.BytesIO(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...fake-png"), "receipt.png")
        data = {
            "date": "2026-10-25",
            "category_id": "1",
            "amount": "142.50",
            "payment_method": "Credit Card",
            "description": "Team lunch at Bistro",
            "notes": "Quarterly milestone celebration",
            "receipt": dummy_receipt
        }
        res_exp = self.client.post("/api/expense", data=data, content_type="multipart/form-data")
        self.assertEqual(res_exp.status_code, 200)
        exp_id = res_exp.get_json()["id"]

        # Fetch expense and check receipt was persisted
        exp = database.get_expense_by_id(exp_id, user_id=1)
        self.assertIsNotNone(exp["receipt_filename"])
        self.assertTrue(exp["receipt_filename"].endswith(".png"))

        # 2. Render printable statement
        res_stmt = self.client.get("/statement?start_date=2026-10-01&end_date=2026-10-31")
        self.assertEqual(res_stmt.status_code, 200)
        self.assertIn(b"Financial Statement", res_stmt.data)
        self.assertIn(b"Cash Flow Summary", res_stmt.data)
        self.assertIn(b"Team lunch at Bistro", res_stmt.data)

    def test_debts_and_credit_api(self):
        """Test peer credit (friend lent/borrowed), bank loans, credit cards, and repayments."""
        # 1. Render /debts page
        res_page = self.client.get("/debts")
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b"Debts, Loans & Peer Credit", res_page.data)
        self.assertIn(b"Owed to You (Receivable)", res_page.data)

        # 2. Add debt: Given to Friend (Lent / Receivable)
        res_lent = self.client.post("/api/debt", json={
            "debt_type": "friend_lent",
            "person_or_institution": "Alex Miller",
            "total_amount": 200.0,
            "paid_amount": 0.0,
            "account_id": 1,
            "notes": "Concert festival ticket"
        })
        self.assertEqual(res_lent.status_code, 200)
        lent_data = res_lent.get_json()
        self.assertTrue(lent_data["success"])
        lent_id = lent_data["id"]

        # 3. Add debt: Taken from Friend (Borrowed / Payable)
        res_borrowed = self.client.post("/api/debt", json={
            "debt_type": "friend_borrowed",
            "person_or_institution": "Sarah Davis",
            "total_amount": 150.0,
            "paid_amount": 0.0,
            "account_id": 1,
            "notes": "Group hotel booking"
        })
        self.assertEqual(res_borrowed.status_code, 200)
        borrowed_id = res_borrowed.get_json()["id"]

        # 4. Add Formal Loan (Payable)
        res_loan = self.client.post("/api/debt", json={
            "debt_type": "loan",
            "person_or_institution": "Citi Personal Loan",
            "total_amount": 3000.0,
            "paid_amount": 500.0,
            "interest_rate": 6.5,
            "account_id": 1,
            "notes": "Home renovation"
        })
        self.assertEqual(res_loan.status_code, 200)
        loan_id = res_loan.get_json()["id"]

        # 5. Check Summary API
        res_sum = self.client.get("/api/debt/summary")
        self.assertEqual(res_sum.status_code, 200)
        sum_data = res_sum.get_json()["summary"]
        self.assertGreaterEqual(sum_data["total_receivable"], 200.0)
        self.assertGreaterEqual(sum_data["total_payable"], 2650.0)

        # 6. Record Repayment on Lent Debt (Friend Alex pays back $50)
        acc_before = database.get_bank_account_by_id(1, user_id=1)["current_balance"]
        res_pay1 = self.client.post(f"/api/debt/{lent_id}/payment", json={
            "amount": 50.0,
            "account_id": 1,
            "record_in_account": 1,
            "notes": "Partial repayment via cash/transfer"
        })
        self.assertEqual(res_pay1.status_code, 200)
        pay_res1 = res_pay1.get_json()
        self.assertTrue(pay_res1["success"])
        self.assertEqual(pay_res1["result"]["new_remaining_amount"], 150.0)

        # Check bank account balance credited
        acc_after = database.get_bank_account_by_id(1, user_id=1)["current_balance"]
        self.assertAlmostEqual(acc_after, acc_before + 50.0, places=2)

        # 7. Record Full Repayment on Borrowed Debt (Pay Sarah $150 in full)
        res_pay2 = self.client.post(f"/api/debt/{borrowed_id}/payment", json={
            "amount": 150.0,
            "account_id": 1,
            "record_in_account": 1
        })
        self.assertEqual(res_pay2.status_code, 200)
        pay_res2 = res_pay2.get_json()
        self.assertTrue(pay_res2["success"])
        self.assertEqual(pay_res2["result"]["status"], "settled")
        self.assertEqual(pay_res2["result"]["is_settled"], 1)

        # 8. Delete loan
        res_del = self.client.delete(f"/api/debt/{loan_id}")
        self.assertEqual(res_del.status_code, 200)
        self.assertIsNone(database.get_debt_by_id(loan_id, user_id=1))


    def test_optional_category_spending_limit_and_total_monthly_budget(self):
        """Test that category spending limits are optional (uncapped) and total monthly budget can be set to any arbitrary amount."""
        # 1. Create a category with no spending limit (optional / blank / 0.0)
        res_cat = self.client.post("/api/category", json={
            "name": "Hobbies & Leisure",
            "icon": "gamepad",
            "color": "#8B5CF6",
            "monthly_budget": ""  # Omitted / blank spending limit
        })
        self.assertEqual(res_cat.status_code, 200)
        cat_data = res_cat.get_json()
        self.assertTrue(cat_data["success"])
        new_cat_id = cat_data["id"]

        cat = database.get_category_by_id(new_cat_id, user_id=1)
        self.assertIsNotNone(cat)
        self.assertEqual(cat["monthly_budget"], 0.0)

        # 2. Verify categories page renders Uncapped label for this category
        res_page = self.client.get("/categories")
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b"Hobbies &amp; Leisure", res_page.data)
        self.assertIn(b"Uncapped", res_page.data)
        self.assertIn(b"No Limit Set (Optional)", res_page.data)

        # 3. Set an arbitrary standalone overall monthly budget (e.g. 4,750.00)
        res_budget = self.client.post("/api/budget", json={
            "total_budget": 4750.00
        })
        self.assertEqual(res_budget.status_code, 200)
        b_data = res_budget.get_json()
        self.assertTrue(b_data["success"])
        self.assertEqual(b_data["total_budget"], 4750.00)
        self.assertEqual(b_data["explicit_budget"], 4750.00)

        # 4. Verify database and metrics prioritize the explicit overall monthly budget
        self.assertEqual(database.get_user_monthly_budget(user_id=1), 4750.00)
        self.assertEqual(database.get_explicit_monthly_budget(user_id=1), 4750.00)

        metrics = database.get_monthly_metrics(user_id=1)
        self.assertEqual(metrics["total_budget"], 4750.00)

        # 5. Check GET /api/budget returns the custom total budget
        res_get_b = self.client.get("/api/budget")
        self.assertEqual(res_get_b.status_code, 200)
        get_b_data = res_get_b.get_json()
        self.assertEqual(get_b_data["total_budget"], 4750.00)
        self.assertEqual(get_b_data["explicit_budget"], 4750.00)

        # 6. Verify Dashboard and Categories page reflect the overall budget
        res_dash = self.client.get("/")
        self.assertEqual(res_dash.status_code, 200)
        self.assertIn(b"4750.00", res_dash.data)

        res_cat_page = self.client.get("/categories")
        self.assertEqual(res_cat_page.status_code, 200)
        self.assertIn(b"4750.00", res_cat_page.data)
        self.assertIn(b"Custom overall monthly budget", res_cat_page.data)

        # 7. Update category with a limit, then update back to 0.0 (uncapped)
        res_upd1 = self.client.put(f"/api/category/{new_cat_id}", json={
            "name": "Hobbies & Leisure",
            "icon": "gamepad",
            "color": "#8B5CF6",
            "monthly_budget": 150.00
        })
        self.assertEqual(res_upd1.status_code, 200)
        self.assertEqual(database.get_category_by_id(new_cat_id, user_id=1)["monthly_budget"], 150.00)

        res_upd2 = self.client.put(f"/api/category/{new_cat_id}", json={
            "name": "Hobbies & Leisure",
            "icon": "gamepad",
            "color": "#8B5CF6",
            "monthly_budget": 0.0  # Clear back to uncapped
        })
        self.assertEqual(res_upd2.status_code, 200)
        self.assertEqual(database.get_category_by_id(new_cat_id, user_id=1)["monthly_budget"], 0.0)

        # 8. Clean up category
        res_del = self.client.delete(f"/api/category/{new_cat_id}/delete")
        self.assertEqual(res_del.status_code, 200)


    def test_performance_headers_and_compression(self):
        """Test that static assets receive browser cache headers and responses are gzip compressed."""
        # 1. Check static asset caching headers
        res_css = self.client.get("/static/css/style.css")
        self.assertEqual(res_css.status_code, 200)
        self.assertIn("Cache-Control", res_css.headers)
        self.assertIn("public", res_css.headers["Cache-Control"])
        self.assertIn("max-age=86400", res_css.headers["Cache-Control"])

        # 2. Check HTML response gzip compression
        res_gz = self.client.get("/", headers={"Accept-Encoding": "gzip"})
        self.assertEqual(res_gz.status_code, 200)
        self.assertEqual(res_gz.headers.get("Content-Encoding"), "gzip")



    def test_auth_headers_and_verify_2fa(self):
        """Test that auth views (login, register, recover, verify-2fa) render clean top headers and no sidebar."""
        # 1. Clear session to simulate unauthenticated visitor
        with self.client.session_transaction() as sess:
            sess.clear()

        # 2. Check /login header
        res_login = self.client.get("/login")
        self.assertEqual(res_login.status_code, 200)
        self.assertIn(b"FinanceFlow", res_login.data)
        self.assertIn(b"toggleDarkMode()", res_login.data)
        self.assertIn(b"Create Account", res_login.data)
        self.assertNotIn(b"Export to Excel", res_login.data)
        self.assertNotIn(b"Mobile Navigation Menu", res_login.data)

        # 3. Check /register header
        res_reg = self.client.get("/register")
        self.assertEqual(res_reg.status_code, 200)
        self.assertIn(b"FinanceFlow", res_reg.data)
        self.assertIn(b"toggleDarkMode()", res_reg.data)
        self.assertIn(b"Sign In", res_reg.data)

        # 4. Check /recover header
        res_rec = self.client.get("/recover")
        self.assertEqual(res_rec.status_code, 200)
        self.assertIn(b"FinanceFlow", res_rec.data)
        self.assertIn(b"toggleDarkMode()", res_rec.data)

        # 5. Check /verify-2fa when pending_2fa_user_id is NOT set -> redirects to /login
        res_2fa_anon = self.client.get("/verify-2fa")
        self.assertEqual(res_2fa_anon.status_code, 302)
        self.assertIn("/login", res_2fa_anon.location)

        # 6. Check /verify-2fa when pending_2fa_user_id IS set -> renders standalone page with top header
        with self.client.session_transaction() as sess:
            sess["pending_2fa_user_id"] = 1

        res_2fa = self.client.get("/verify-2fa")
        self.assertEqual(res_2fa.status_code, 200)
        self.assertIn(b"Two-Factor Verification", res_2fa.data)
        self.assertIn(b"6-Digit Security Code", res_2fa.data)
        self.assertIn(b"Back to Sign In", res_2fa.data)
        self.assertIn(b"toggleDarkMode()", res_2fa.data)
        # Ensure it does NOT contain the base.html application sidebar or export controls
        self.assertNotIn(b"Export to Excel", res_2fa.data)
        self.assertNotIn(b"openMobileDrawer", res_2fa.data)
        self.assertNotIn(b"toggleMobileDrawer", res_2fa.data)


if __name__ == "__main__":
    unittest.main()
