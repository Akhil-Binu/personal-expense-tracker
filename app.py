"""
Personal Expense Tracker - Flask Application (FinanceFlow v2.0)
Serves desktop, tablet, and mobile web experiences with SQLite backend,
multi-account balances, subscriptions, goals, cash flow, receipt uploads,
AI spending insights, 2FA security, and progressive web app (PWA) capabilities.
"""
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, redirect, url_for, flash, session
import os
import uuid
from functools import wraps
from datetime import datetime, date
from werkzeug.utils import secure_filename
import database
import excel_service
import auth_service
import analytics_service

app = Flask(__name__)
app.secret_key = os.urandom(24)

__version__ = "2.0.0"

UPLOAD_FOLDER = os.path.join(app.root_path, "static", "uploads", "receipts")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
ALLOWED_RECEIPT_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf"}

# Initialize database on startup
database.init_db(seed_sample_data=True)

SUPPORTED_CURRENCIES = [
    {"code": "USD", "symbol": "$", "label": "USD ($) - US Dollar"},
    {"code": "INR", "symbol": "₹", "label": "INR (₹) - Indian Rupee"},
    {"code": "EUR", "symbol": "€", "label": "EUR (€) - Euro"},
    {"code": "GBP", "symbol": "£", "label": "GBP (£) - British Pound"},
    {"code": "JPY", "symbol": "¥", "label": "JPY (¥) - Japanese Yen"},
    {"code": "CAD", "symbol": "C$", "label": "CAD (C$) - Canadian Dollar"},
    {"code": "AUD", "symbol": "A$", "label": "AUD (A$) - Australian Dollar"},
    {"code": "AED", "symbol": "AED", "label": "AED (AED) - UAE Dirham"},
    {"code": "SGD", "symbol": "S$", "label": "SGD (S$) - Singapore Dollar"},
    {"code": "CHF", "symbol": "CHF", "label": "CHF (CHF) - Swiss Franc"},
]

def get_current_user():
    """Returns the authenticated user dict from session or None."""
    user_id = session.get("user_id")
    if user_id:
        return database.get_user_by_id(user_id)
    return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_user():
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required", "login_required": True}), 401
            return redirect(url_for("login_page", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Context processor for templates
@app.context_processor
def inject_global_data():
    today = date.today()
    user = get_current_user()
    user_id = user["id"] if user else 1
    return {
        "current_user": user,
        "current_month": today.strftime("%Y-%m"),
        "current_date": today.isoformat(),
        "today_display": today.strftime("%A, %B %d, %Y"),
        "available_months": database.get_available_months(user_id=user_id),
        "categories_list": database.get_categories(user_id=user_id),
        "bank_accounts_list": database.get_bank_accounts(user_id=user_id),
        "combined_bank_balance": database.get_combined_balance(user_id=user_id),
        "cash_flow_summary": database.get_cash_flow_summary(user_id=user_id),
        "upcoming_subs_count": len(database.get_upcoming_subscriptions(user_id=user_id, days=7)),
        "active_goals_count": len(database.get_goals(user_id=user_id)),
        "debt_summary": database.get_debt_summary(user_id=user_id),
        "currency": database.get_currency(),
        "supported_currencies": SUPPORTED_CURRENCIES,
        "app_version": __version__,
    }

# ==================== Authentication Views ====================

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if get_current_user():
        return redirect(url_for("dashboard"))
        
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        
        user = database.authenticate_user(username, password)
        if user:
            # Check if Two-Factor Authentication is enabled
            if user.get("two_factor_enabled"):
                session["pending_2fa_user_id"] = user["id"]
                next_url = request.args.get("next") or url_for("dashboard")
                return redirect(url_for("verify_2fa_page", next=next_url))
                
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['username']}!", "success")
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        else:
            error = "Invalid username or password. Please try again."
            
    return render_template("login.html", error=error)

@app.route("/verify-2fa", methods=["GET", "POST"])
def verify_2fa_page():
    pending_user_id = session.get("pending_2fa_user_id")
    if not pending_user_id:
        return redirect(url_for("login_page"))
        
    user = database.get_user_by_id(pending_user_id)
    if not user:
        session.pop("pending_2fa_user_id", None)
        return redirect(url_for("login_page"))
        
    error = None
    if request.method == "POST":
        totp_code = request.form.get("totp_code", "").strip()
        recovery_phrase = request.form.get("recovery_phrase", "").strip()
        
        verified = False
        if totp_code:
            verified = auth_service.verify_totp_code(user.get("totp_secret"), totp_code)
        elif recovery_phrase:
            verified = auth_service.verify_phrase(user.get("recovery_phrase_hash"), recovery_phrase)
            
        if verified:
            session.pop("pending_2fa_user_id", None)
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['username']}! 2FA verified successfully.", "success")
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        else:
            error = "Invalid 6-digit verification code or recovery phrase. Please try again."
            
    return render_template("verify_2fa.html", username=user["username"], error=error)

@app.route("/register", methods=["GET", "POST"])
def register_page():
    if get_current_user():
        return redirect(url_for("dashboard"))
        
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if password != confirm_password:
            error = "Passwords do not match."
        elif len(password) < 6:
            error = "Password must be at least 6 characters long."
        else:
            try:
                user_data = database.create_user(username=username, password=password, email=email)
                # Automatically log in the user
                session["user_id"] = user_data["id"]
                # Render the backup keywords presentation screen
                return render_template(
                    "backup_keywords.html",
                    username=user_data["username"],
                    words=user_data["recovery_words"],
                    phrase=user_data["recovery_phrase"]
                )
            except ValueError as ve:
                error = str(ve)
            except Exception as e:
                error = f"Registration error: {str(e)}"
                
    return render_template("register.html", error=error)

@app.route("/recover", methods=["GET", "POST"])
def recover_page():
    """Account recovery page using the 12 backup keywords."""
    error = None
    success = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        recovery_phrase = request.form.get("recovery_phrase", "").strip()
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        
        if new_password != confirm_password:
            error = "Passwords do not match."
        elif len(new_password) < 6:
            error = "New password must be at least 6 characters long."
        else:
            try:
                database.recover_user_password(username, recovery_phrase, new_password)
                flash("Your password has been successfully reset! You can now log in.", "success")
                return redirect(url_for("login_page"))
            except ValueError as ve:
                error = str(ve)
            except Exception as e:
                error = f"Recovery failed: {str(e)}"
                
    return render_template("recover.html", error=error, success=success)

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login_page"))

# ==================== Web Page Views ====================

@app.route("/")
@login_required
def dashboard():
    """Main dashboard page (v2.0 with Cash Flow, Upcoming Subscriptions, Goals, and AI Insights)."""
    user = get_current_user()
    user_id = user["id"]
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    metrics = database.get_monthly_metrics(month, user_id=user_id)
    categories = database.get_category_breakdown(month, user_id=user_id)
    recent_expenses = database.get_expenses(limit=8, user_id=user_id)
    cash_flow = database.get_cash_flow_summary(user_id=user_id, month_str=month)
    upcoming_subs = database.get_upcoming_subscriptions(user_id=user_id, days=14)
    active_goals = database.get_goals(user_id=user_id)
    smart_insights = analytics_service.generate_smart_insights(user_id=user_id, month_str=month)
    debt_summary = database.get_debt_summary(user_id=user_id)
    return render_template(
        "index.html",
        selected_month=month,
        metrics=metrics,
        categories=categories,
        recent_expenses=recent_expenses,
        cash_flow=cash_flow,
        upcoming_subs=upcoming_subs,
        active_goals=active_goals,
        smart_insights=smart_insights,
        debt_summary=debt_summary,
        active_page="dashboard"
    )

@app.route("/expenses")
@login_required
def expenses_page():
    """Expenses listing and filtering view."""
    user = get_current_user()
    user_id = user["id"]
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    category_id = request.args.get("category_id")
    category_id = int(category_id) if category_id and category_id.isdigit() else None
    account_id = request.args.get("account_id")
    account_id = int(account_id) if account_id and account_id.isdigit() else None
    payment_method = request.args.get("payment_method") or None
    search = request.args.get("search") or None
    
    expenses = database.get_expenses(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        payment_method=payment_method,
        search=search,
        user_id=user_id,
        account_id=account_id
    )
    categories = database.get_categories(user_id=user_id)
    accounts = database.get_bank_accounts(user_id=user_id)
    total_amount = sum(e["amount"] for e in expenses)
    
    return render_template(
        "expenses.html",
        expenses=expenses,
        categories=categories,
        accounts=accounts,
        filters={
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category_id": category_id or "",
            "account_id": account_id or "",
            "payment_method": payment_method or "",
            "search": search or ""
        },
        total_amount=round(total_amount, 2),
        active_page="expenses"
    )

@app.route("/income")
@login_required
def income_page():
    """Income streams and cash flow management view (v2.0)."""
    user = get_current_user()
    user_id = user["id"]
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    incomes = database.get_income_list(user_id=user_id, start_date=start_date, end_date=end_date)
    accounts = database.get_bank_accounts(user_id=user_id)
    cash_flow = database.get_cash_flow_summary(user_id=user_id)
    total_income = sum(i["amount"] for i in incomes)
    
    return render_template(
        "income.html",
        incomes=incomes,
        accounts=accounts,
        cash_flow=cash_flow,
        total_income=round(total_income, 2),
        filters={"start_date": start_date or "", "end_date": end_date or ""},
        active_page="income"
    )

@app.route("/subscriptions")
@login_required
def subscriptions_page():
    """Recurring subscriptions & upcoming bills management view (v2.0)."""
    user = get_current_user()
    user_id = user["id"]
    subscriptions = database.get_subscriptions(user_id=user_id)
    categories = database.get_categories(user_id=user_id)
    accounts = database.get_bank_accounts(user_id=user_id)
    upcoming = database.get_upcoming_subscriptions(user_id=user_id, days=30)
    
    total_monthly = sum(
        s["amount"] if s.get("billing_cycle", "Monthly") == "Monthly"
        else (s["amount"] * 4.33 if s.get("billing_cycle") == "Weekly" else s["amount"] / 12)
        for s in subscriptions if s.get("is_active")
    )
    
    return render_template(
        "subscriptions.html",
        subscriptions=subscriptions,
        categories=categories,
        accounts=accounts,
        upcoming=upcoming,
        total_monthly=round(total_monthly, 2),
        active_page="subscriptions"
    )

@app.route("/goals")
@login_required
def goals_page():
    """Financial goals & savings pockets view (v2.0)."""
    user = get_current_user()
    user_id = user["id"]
    goals = database.get_goals(user_id=user_id)
    accounts = database.get_bank_accounts(user_id=user_id)
    
    total_target = sum(g["target_amount"] for g in goals)
    total_saved = sum(g["current_amount"] for g in goals)
    overall_progress = round((total_saved / total_target * 100), 1) if total_target > 0 else 0.0
    
    return render_template(
        "goals.html",
        goals=goals,
        accounts=accounts,
        total_target=round(total_target, 2),
        total_saved=round(total_saved, 2),
        overall_progress=overall_progress,
        active_page="goals"
    )

@app.route("/statement")
@login_required
def statement_page():
    """Publication-grade printable financial statement & PDF export (v2.0)."""
    user = get_current_user()
    user_id = user["id"]
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    
    metrics = database.get_monthly_metrics(month, user_id=user_id)
    categories = database.get_category_breakdown(month, user_id=user_id)
    expenses = database.get_expenses(start_date=f"{month}-01", end_date=f"{month}-31", user_id=user_id)
    incomes = database.get_income_list(user_id=user_id, start_date=f"{month}-01", end_date=f"{month}-31")
    accounts = database.get_bank_accounts(user_id=user_id)
    cash_flow = database.get_cash_flow_summary(user_id=user_id, month_str=month)
    
    try:
        dt = datetime.strptime(month, "%Y-%m")
        month_name = dt.strftime("%B %Y")
    except Exception:
        month_name = month
        
    return render_template(
        "statement.html",
        selected_month=month,
        month_name=month_name,
        metrics=metrics,
        categories=categories,
        expenses=expenses,
        incomes=incomes,
        accounts=accounts,
        cash_flow=cash_flow,
        active_page="statement"
    )

@app.route("/reports")
@login_required
def reports_page():
    """Monthly analytics and reporting view."""
    user = get_current_user()
    user_id = user["id"]
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    metrics = database.get_monthly_metrics(month, user_id=user_id)
    categories = database.get_category_breakdown(month, user_id=user_id)
    payment_methods = database.get_payment_method_breakdown(month, user_id=user_id)
    cash_flow = database.get_cash_flow_summary(user_id=user_id, month_str=month)
    smart_insights = analytics_service.generate_smart_insights(user_id=user_id, month_str=month)
    
    return render_template(
        "reports.html",
        selected_month=month,
        metrics=metrics,
        categories=categories,
        payment_methods=payment_methods,
        cash_flow=cash_flow,
        smart_insights=smart_insights,
        active_page="reports"
    )

@app.route("/categories")
@login_required
def categories_page():
    """Category and budget management view."""
    user = get_current_user()
    user_id = user["id"]
    categories = database.get_categories(user_id=user_id)
    total_budget = sum(c["monthly_budget"] for c in categories)
    total_spent = sum(c["current_month_spent"] for c in categories)
    return render_template(
        "categories.html",
        categories=categories,
        total_budget=round(total_budget, 2),
        total_spent=round(total_spent, 2),
        active_page="categories"
    )

@app.route("/accounts")
@login_required
def accounts_page():
    """Bank accounts and combined net balance management view."""
    user = get_current_user()
    user_id = user["id"]
    accounts = database.get_bank_accounts(user_id=user_id)
    combined = database.get_combined_balance(user_id=user_id)
    transfers = database.get_transfers(user_id=user_id, limit=20)
    return render_template(
        "accounts.html",
        accounts=accounts,
        combined=combined,
        transfers=transfers,
        active_page="accounts"
    )

@app.route("/debts")
@login_required
def debts_page():
    """Debts, Loans, Credit Cards & Peer Credit management view."""
    user = get_current_user()
    user_id = user["id"]
    debt_type = request.args.get("type") or None
    status = request.args.get("status") or None
    debts = database.get_debts(user_id=user_id, debt_type=debt_type, status=status)
    summary = database.get_debt_summary(user_id=user_id)
    accounts = database.get_bank_accounts(user_id=user_id)
    return render_template(
        "debts.html",
        debts=debts,
        summary=summary,
        accounts=accounts,
        selected_type=debt_type,
        selected_status=status,
        active_page="debts"
    )

# ==================== PWA Routes ====================

@app.route("/manifest.json")
def pwa_manifest():
    return send_from_directory(os.path.join(app.root_path, "static"), "manifest.json", mimetype="application/manifest+json")

@app.route("/service-worker.js")
def pwa_service_worker():
    response = send_from_directory(os.path.join(app.root_path, "static"), "service-worker.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response

# ==================== JSON API Endpoints ====================

@app.route("/api/chart-data")
@login_required
def api_chart_data():
    """Provides chart series for Dashboard & Reports."""
    user = get_current_user()
    user_id = user["id"]
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    category_data = database.get_category_breakdown(month, user_id=user_id)
    daily_data = database.get_daily_spending_trend(month, user_id=user_id)
    history_data = database.get_monthly_history(num_months=6, user_id=user_id)
    payment_data = database.get_payment_method_breakdown(month, user_id=user_id)
    
    return jsonify({
        "categories": {
            "labels": [c["name"] for c in category_data if c["spent"] > 0],
            "values": [c["spent"] for c in category_data if c["spent"] > 0],
            "colors": [c["color"] for c in category_data if c["spent"] > 0]
        },
        "daily": daily_data,
        "history": {
            "labels": [h["label"] for h in history_data],
            "values": [h["total"] for h in history_data]
        },
        "payment_methods": {
            "labels": [p["payment_method"] for p in payment_data],
            "values": [round(p["total"], 2) for p in payment_data]
        }
    })

@app.route("/api/expense", methods=["POST"])
@login_required
def api_add_expense():
    """Add a new expense with optional receipt attachment."""
    user = get_current_user()
    user_id = user["id"]
    data = request.get_json() if request.is_json else request.form
    try:
        exp_date = data.get("date") or date.today().isoformat()
        category_id = int(data.get("category_id"))
        amount = float(data.get("amount"))
        payment_method = data.get("payment_method", "Cash")
        description = data.get("description", "").strip()
        notes = data.get("notes", "").strip()
        account_id = data.get("account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        
        if not description:
            return jsonify({"success": False, "error": "Description is required"}), 400
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than zero"}), 400
            
        receipt_filename = None
        if "receipt" in request.files:
            file = request.files["receipt"]
            if file and file.filename:
                ext = os.path.splitext(secure_filename(file.filename))[1].lower()
                if ext.lstrip(".") in ALLOWED_RECEIPT_EXTENSIONS:
                    unique_name = f"{uuid.uuid4().hex}{ext}"
                    file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_name))
                    receipt_filename = unique_name

        expense_id = database.add_expense(
            expense_date=exp_date,
            category_id=category_id,
            amount=amount,
            payment_method=payment_method,
            description=description,
            notes=notes,
            user_id=user_id,
            account_id=account_id,
            receipt_filename=receipt_filename
        )
        return jsonify({"success": True, "id": expense_id, "message": "Expense added successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/expense/<int:expense_id>", methods=["GET"])
@login_required
def api_get_expense(expense_id):
    """Retrieve single expense details."""
    user = get_current_user()
    exp = database.get_expense_by_id(expense_id, user_id=user["id"])
    if not exp:
        return jsonify({"success": False, "error": "Expense not found"}), 404
    return jsonify({"success": True, "expense": exp})

@app.route("/api/expense/<int:expense_id>", methods=["PUT", "POST"])
@login_required
def api_update_expense(expense_id):
    """Update an existing expense with optional receipt replacement."""
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        exp_date = data.get("date")
        category_id = int(data.get("category_id"))
        amount = float(data.get("amount"))
        payment_method = data.get("payment_method")
        description = data.get("description", "").strip()
        notes = data.get("notes", "").strip()
        account_id = data.get("account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        
        if not description:
            return jsonify({"success": False, "error": "Description is required"}), 400
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than zero"}), 400
            
        receipt_filename = None
        if "receipt" in request.files:
            file = request.files["receipt"]
            if file and file.filename:
                ext = os.path.splitext(secure_filename(file.filename))[1].lower()
                if ext.lstrip(".") in ALLOWED_RECEIPT_EXTENSIONS:
                    unique_name = f"{uuid.uuid4().hex}{ext}"
                    file.save(os.path.join(app.config["UPLOAD_FOLDER"], unique_name))
                    receipt_filename = unique_name

        updated = database.update_expense(
            expense_id=expense_id,
            expense_date=exp_date,
            category_id=category_id,
            amount=amount,
            payment_method=payment_method,
            description=description,
            notes=notes,
            user_id=user["id"],
            account_id=account_id,
            receipt_filename=receipt_filename
        )
        if not updated:
            return jsonify({"success": False, "error": "Expense not found"}), 404
        return jsonify({"success": True, "message": "Expense updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/expense/<int:expense_id>/delete", methods=["POST", "DELETE"])
@login_required
def api_delete_expense(expense_id):
    """Delete an expense record."""
    user = get_current_user()
    try:
        deleted = database.delete_expense(expense_id, user_id=user["id"])
        if not deleted:
            return jsonify({"success": False, "error": "Expense not found"}), 404
        return jsonify({"success": True, "message": "Expense deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Income APIs (v2.0) ====================

@app.route("/api/income", methods=["GET", "POST"])
@login_required
def api_income_collection():
    """List all income or create a new income stream."""
    user = get_current_user()
    if request.method == "GET":
        month = request.args.get("month")
        incomes = database.get_income(user_id=user["id"], month_str=month)
        return jsonify({"success": True, "income": incomes})

    data = request.get_json() if request.is_json else request.form
    try:
        inc_date = data.get("date") or date.today().isoformat()
        source = data.get("source", "").strip()
        amount = float(data.get("amount") or 0.0)
        payment_method = data.get("payment_method", "Bank Transfer").strip()
        notes = data.get("notes", "").strip()
        account_id = data.get("account_id") or data.get("bank_account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        
        if not source:
            return jsonify({"success": False, "error": "Income source is required"}), 400
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than zero"}), 400
            
        income_id = database.add_income(
            date_str=inc_date,
            source=source,
            amount=amount,
            payment_method=payment_method,
            account_id=account_id,
            notes=notes,
            user_id=user["id"]
        )
        created = database.get_income_by_id(income_id, user_id=user["id"])
        return jsonify({"success": True, "id": income_id, "income": created, "message": "Income added successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/income/<int:income_id>", methods=["GET"])
@login_required
def api_get_income(income_id):
    user = get_current_user()
    inc = database.get_income_by_id(income_id, user_id=user["id"])
    if not inc:
        return jsonify({"success": False, "error": "Income record not found"}), 404
    return jsonify({"success": True, "income": inc})

@app.route("/api/income/<int:income_id>", methods=["PUT", "POST"])
@login_required
def api_update_income(income_id):
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        inc_date = data.get("date") or date.today().isoformat()
        source = data.get("source", "").strip()
        amount = float(data.get("amount") or 0.0)
        payment_method = data.get("payment_method", "Bank Transfer").strip()
        notes = data.get("notes", "").strip()
        account_id = data.get("account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        
        if not source:
            return jsonify({"success": False, "error": "Income source is required"}), 400
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be greater than zero"}), 400
            
        updated = database.update_income(
            income_id=income_id,
            date_str=inc_date,
            source=source,
            amount=amount,
            payment_method=payment_method,
            account_id=account_id,
            notes=notes,
            user_id=user["id"]
        )
        if not updated:
            return jsonify({"success": False, "error": "Income record not found"}), 404
        return jsonify({"success": True, "message": "Income updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/income/<int:income_id>", methods=["DELETE"])
@app.route("/api/income/<int:income_id>/delete", methods=["POST", "DELETE"])
@login_required
def api_delete_income(income_id):
    user = get_current_user()
    try:
        deleted = database.delete_income(income_id, user_id=user["id"])
        if not deleted:
            return jsonify({"success": False, "error": "Income record not found"}), 404
        return jsonify({"success": True, "message": "Income record deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Account Transfers APIs (v2.0) ====================

@app.route("/api/transfer", methods=["POST"])
@login_required
def api_add_transfer():
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        t_date = data.get("date") or data.get("transfer_date") or date.today().isoformat()
        from_acc = int(data.get("from_account_id"))
        to_acc = int(data.get("to_account_id"))
        amount = float(data.get("amount") or 0.0)
        notes = data.get("notes", "").strip()
        
        if from_acc == to_acc:
            return jsonify({"success": False, "error": "Source and destination accounts must be different"}), 400
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be positive"}), 400
            
        t_id = database.add_transfer(
            date_str=t_date,
            from_account_id=from_acc,
            to_account_id=to_acc,
            amount=amount,
            notes=notes,
            user_id=user["id"]
        )
        return jsonify({"success": True, "id": t_id, "message": "Transfer completed successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/transfer/<int:transfer_id>/delete", methods=["POST", "DELETE"])
@login_required
def api_delete_transfer(transfer_id):
    user = get_current_user()
    try:
        deleted = database.delete_transfer(transfer_id, user_id=user["id"])
        if not deleted:
            return jsonify({"success": False, "error": "Transfer record not found"}), 404
        return jsonify({"success": True, "message": "Transfer record deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Subscriptions APIs (v2.0) ====================

@app.route("/api/subscription", methods=["GET", "POST"])
@login_required
def api_subscription_collection():
    user = get_current_user()
    if request.method == "GET":
        active_only = request.args.get("active") == "1"
        subs = database.get_subscriptions(user_id=user["id"], active_only=active_only)
        return jsonify({"success": True, "subscriptions": subs})

    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        amount = float(data.get("amount") or 0.0)
        category_id = data.get("category_id")
        category_id = int(category_id) if category_id and str(category_id).isdigit() else None
        account_id = data.get("account_id") or data.get("bank_account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        billing_cycle = data.get("billing_cycle", "Monthly").strip()
        billing_day = int(data.get("billing_day") or 1)
        next_due_date = data.get("next_due_date") or date.today().isoformat()
        notes = data.get("notes", "").strip()
        auto_log = int(data.get("auto_log", 0))
        
        if not name:
            return jsonify({"success": False, "error": "Subscription name is required"}), 400
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be positive"}), 400
            
        sub_id = database.add_subscription(
            name=name,
            amount=amount,
            category_id=category_id,
            account_id=account_id,
            billing_cycle=billing_cycle,
            billing_day=billing_day,
            next_due_date=next_due_date,
            notes=notes,
            auto_log=auto_log,
            user_id=user["id"]
        )
        created = database.get_subscription_by_id(sub_id, user_id=user["id"])
        return jsonify({"success": True, "id": sub_id, "subscription": created, "message": "Subscription added successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/subscription/<int:sub_id>", methods=["GET"])
@login_required
def api_get_subscription(sub_id):
    user = get_current_user()
    sub = database.get_subscription_by_id(sub_id, user_id=user["id"])
    if not sub:
        return jsonify({"success": False, "error": "Subscription not found"}), 404
    return jsonify({"success": True, "subscription": sub})

@app.route("/api/subscription/<int:sub_id>", methods=["PUT", "POST"])
@login_required
def api_update_subscription(sub_id):
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        amount = float(data.get("amount") or 0.0)
        category_id = data.get("category_id")
        category_id = int(category_id) if category_id and str(category_id).isdigit() else None
        account_id = data.get("account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        billing_cycle = data.get("billing_cycle", "Monthly").strip()
        billing_day = int(data.get("billing_day") or 1)
        next_due_date = data.get("next_due_date") or date.today().isoformat()
        is_active = int(data.get("is_active", 1))
        notes = data.get("notes", "").strip()
        auto_log = int(data.get("auto_log", 0))
        
        if not name:
            return jsonify({"success": False, "error": "Subscription name is required"}), 400
        if amount <= 0:
            return jsonify({"success": False, "error": "Amount must be positive"}), 400
            
        updated = database.update_subscription(
            sub_id=sub_id,
            name=name,
            amount=amount,
            category_id=category_id,
            account_id=account_id,
            billing_cycle=billing_cycle,
            billing_day=billing_day,
            next_due_date=next_due_date,
            is_active=is_active,
            notes=notes,
            auto_log=auto_log,
            user_id=user["id"]
        )
        if not updated:
            return jsonify({"success": False, "error": "Subscription not found"}), 404
        return jsonify({"success": True, "message": "Subscription updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/subscription/<int:sub_id>", methods=["DELETE"])
@app.route("/api/subscription/<int:sub_id>/delete", methods=["POST", "DELETE"])
@login_required
def api_delete_subscription(sub_id):
    user = get_current_user()
    try:
        deleted = database.delete_subscription(sub_id, user_id=user["id"])
        if not deleted:
            return jsonify({"success": False, "error": "Subscription not found"}), 404
        return jsonify({"success": True, "message": "Subscription deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/subscription/<int:sub_id>/pay", methods=["POST"])
@login_required
def api_pay_subscription(sub_id):
    """1-click logs subscription as expense and advances its next due date."""
    user = get_current_user()
    try:
        next_date = database.mark_subscription_paid(sub_id, user_id=user["id"])
        return jsonify({"success": True, "next_due_date": next_date, "message": f"Bill paid and advanced to {next_date}!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Goals APIs (v2.0) ====================

@app.route("/api/goal", methods=["GET", "POST"])
@login_required
def api_goal_collection():
    user = get_current_user()
    if request.method == "GET":
        goals = database.get_goals(user_id=user["id"])
        return jsonify({"success": True, "goals": goals})

    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        target_amount = float(data.get("target_amount") or 0.0)
        current_amount = float(data.get("current_amount") or 0.0)
        target_date = data.get("target_date") or None
        color = data.get("color", "#10B981").strip()
        icon = data.get("icon", "bullseye").strip()
        account_id = data.get("account_id") or data.get("bank_account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        notes = data.get("notes", "").strip()
        
        if not name:
            return jsonify({"success": False, "error": "Goal name is required"}), 400
        if target_amount <= 0:
            return jsonify({"success": False, "error": "Target amount must be positive"}), 400
            
        goal_id = database.add_goal(
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
            color=color,
            icon=icon,
            account_id=account_id,
            notes=notes,
            user_id=user["id"]
        )
        created = database.get_goal_by_id(goal_id, user_id=user["id"])
        return jsonify({"success": True, "id": goal_id, "goal": created, "message": "Goal created successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/goal/<int:goal_id>", methods=["GET"])
@login_required
def api_get_goal(goal_id):
    user = get_current_user()
    g = database.get_goal_by_id(goal_id, user_id=user["id"])
    if not g:
        return jsonify({"success": False, "error": "Goal not found"}), 404
    return jsonify({"success": True, "goal": g})

@app.route("/api/goal/<int:goal_id>", methods=["PUT", "POST"])
@login_required
def api_update_goal(goal_id):
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        target_amount = float(data.get("target_amount") or 0.0)
        current_amount = float(data.get("current_amount") or 0.0)
        target_date = data.get("target_date") or None
        color = data.get("color", "#10B981").strip()
        icon = data.get("icon", "bullseye").strip()
        account_id = data.get("account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        notes = data.get("notes", "").strip()
        
        if not name:
            return jsonify({"success": False, "error": "Goal name is required"}), 400
        if target_amount <= 0:
            return jsonify({"success": False, "error": "Target amount must be positive"}), 400
            
        updated = database.update_goal(
            goal_id=goal_id,
            name=name,
            target_amount=target_amount,
            current_amount=current_amount,
            target_date=target_date,
            color=color,
            icon=icon,
            account_id=account_id,
            notes=notes,
            user_id=user["id"]
        )
        if not updated:
            return jsonify({"success": False, "error": "Goal not found"}), 404
        return jsonify({"success": True, "message": "Goal updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/goal/<int:goal_id>/contribute", methods=["POST"])
@login_required
def api_contribute_goal(goal_id):
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        amount = float(data.get("amount") or 0.0)
        from_account_id = data.get("from_account_id") or data.get("bank_account_id") or data.get("account_id")
        from_account_id = int(from_account_id) if from_account_id and str(from_account_id).isdigit() else None
        
        if amount <= 0:
            return jsonify({"success": False, "error": "Contribution amount must be positive"}), 400
            
        new_total = database.contribute_to_goal(goal_id, amount, from_account_id=from_account_id, user_id=user["id"])
        goal_data = database.get_goal_by_id(goal_id, user_id=user["id"])
        return jsonify({
            "success": True,
            "current_amount": new_total,
            "goal": goal_data,
            "message": f"Contributed successfully! Current total: {new_total}"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/goal/<int:goal_id>", methods=["DELETE"])
@app.route("/api/goal/<int:goal_id>/delete", methods=["POST", "DELETE"])
@login_required
def api_delete_goal(goal_id):
    user = get_current_user()
    try:
        deleted = database.delete_goal(goal_id, user_id=user["id"])
        if not deleted:
            return jsonify({"success": False, "error": "Goal not found"}), 404
        return jsonify({"success": True, "message": "Goal deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Smart AI Insights API (v2.0) ====================

@app.route("/api/insights")
@login_required
def api_get_insights():
    user = get_current_user()
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    insights = analytics_service.generate_smart_insights(user_id=user["id"], month_str=month)
    return jsonify({"success": True, "insights": insights})

# ==================== Two-Factor Authentication Security APIs (v2.0) ====================

@app.route("/api/2fa/setup", methods=["POST"])
@login_required
def api_2fa_setup():
    user = get_current_user()
    secret = auth_service.generate_totp_secret()
    uri = auth_service.get_totp_uri(secret, user["username"])
    return jsonify({
        "success": True,
        "secret": secret,
        "uri": uri,
        "username": user["username"]
    })

@app.route("/api/2fa/verify-and-enable", methods=["POST"])
@login_required
def api_2fa_verify_and_enable():
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    secret = data.get("secret", "").strip()
    code = data.get("code", "").strip()
    
    if not secret or not code:
        return jsonify({"success": False, "error": "Secret and verification code are required"}), 400
        
    if auth_service.verify_totp_code(secret, code):
        database.update_user_2fa(user["id"], enabled=True, secret=secret)
        return jsonify({"success": True, "message": "Two-Factor Authentication is now enabled!"})
    else:
        return jsonify({"success": False, "error": "Invalid 6-digit verification code. Please check your authenticator app and try again."}), 400

@app.route("/api/2fa/disable", methods=["POST"])
@login_required
def api_2fa_disable():
    user = get_current_user()
    database.update_user_2fa(user["id"], enabled=False)
    return jsonify({"success": True, "message": "Two-Factor Authentication has been disabled."})

@app.route("/api/2fa/status", methods=["GET"])
@login_required
def api_2fa_status():
    user = get_current_user()
    info = database.get_user_2fa_info(user["id"])
    return jsonify({
        "success": True,
        "enabled": bool(info.get("two_factor_enabled")),
        "has_secret": bool(info.get("totp_secret"))
    })

# ==================== Debts, Loans & Credit APIs ====================

@app.route("/api/debt", methods=["GET", "POST"])
@login_required
def api_debt_collection():
    """List or create debt, peer credit, loan, or credit card records."""
    user = get_current_user()
    if request.method == "GET":
        debt_type = request.args.get("type")
        status = request.args.get("status")
        debts = database.get_debts(user_id=user["id"], debt_type=debt_type, status=status)
        summary = database.get_debt_summary(user_id=user["id"])
        return jsonify({"success": True, "debts": debts, "summary": summary})

    data = request.get_json() if request.is_json else request.form
    try:
        debt_type = data.get("debt_type", "friend_lent").strip()
        person = data.get("person_or_institution", "").strip()
        total_amount = float(data.get("total_amount") or 0.0)
        paid_amount = float(data.get("paid_amount") or 0.0)
        interest_rate = float(data.get("interest_rate") or 0.0)
        due_date = data.get("due_date") or None
        account_id = data.get("account_id") or data.get("bank_account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        notes = data.get("notes", "").strip()
        
        debt_id = database.add_debt(
            debt_type=debt_type,
            person_or_institution=person,
            total_amount=total_amount,
            paid_amount=paid_amount,
            interest_rate=interest_rate,
            due_date=due_date,
            account_id=account_id,
            notes=notes,
            user_id=user["id"]
        )
        created = database.get_debt_by_id(debt_id, user_id=user["id"])
        return jsonify({
            "success": True,
            "id": debt_id,
            "debt": created,
            "message": "Debt record created successfully!"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/debt/summary", methods=["GET"])
@login_required
def api_debt_summary():
    user = get_current_user()
    summary = database.get_debt_summary(user_id=user["id"])
    return jsonify({"success": True, "summary": summary})

@app.route("/api/debt/<int:debt_id>", methods=["GET"])
@login_required
def api_get_debt(debt_id):
    user = get_current_user()
    debt = database.get_debt_by_id(debt_id, user_id=user["id"])
    if not debt:
        return jsonify({"success": False, "error": "Debt record not found"}), 404
    payments = database.get_debt_payments(debt_id, user_id=user["id"])
    return jsonify({"success": True, "debt": debt, "payments": payments})

@app.route("/api/debt/<int:debt_id>", methods=["PUT", "POST"])
@login_required
def api_update_debt(debt_id):
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        debt_type = data.get("debt_type", "friend_lent").strip()
        person = data.get("person_or_institution", "").strip()
        total_amount = float(data.get("total_amount") or 0.0)
        interest_rate = float(data.get("interest_rate") or 0.0)
        due_date = data.get("due_date") or None
        account_id = data.get("account_id") or data.get("bank_account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        notes = data.get("notes", "").strip()
        
        updated = database.update_debt(
            debt_id=debt_id,
            debt_type=debt_type,
            person_or_institution=person,
            total_amount=total_amount,
            interest_rate=interest_rate,
            due_date=due_date,
            account_id=account_id,
            notes=notes,
            user_id=user["id"]
        )
        if not updated:
            return jsonify({"success": False, "error": "Debt record not found"}), 404
        return jsonify({"success": True, "message": "Debt record updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/debt/<int:debt_id>", methods=["DELETE"])
@app.route("/api/debt/<int:debt_id>/delete", methods=["POST", "DELETE"])
@login_required
def api_delete_debt(debt_id):
    user = get_current_user()
    try:
        deleted = database.delete_debt(debt_id, user_id=user["id"])
        if not deleted:
            return jsonify({"success": False, "error": "Debt record not found"}), 404
        return jsonify({"success": True, "message": "Debt record deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/debt/<int:debt_id>/payment", methods=["POST"])
@login_required
def api_record_debt_payment(debt_id):
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        amount = float(data.get("amount") or 0.0)
        payment_date = data.get("payment_date") or data.get("date") or date.today().isoformat()
        account_id = data.get("account_id") or data.get("bank_account_id")
        account_id = int(account_id) if account_id and str(account_id).isdigit() else None
        notes = data.get("notes", "").strip()
        record_in_account = bool(int(data.get("record_in_account", 1)))
        
        result = database.record_debt_payment(
            debt_id=debt_id,
            amount=amount,
            payment_date=payment_date,
            account_id=account_id,
            notes=notes,
            record_in_account=record_in_account,
            user_id=user["id"]
        )
        return jsonify({
            "success": True,
            "message": "Payment recorded successfully!",
            "result": result
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Bank Account APIs ====================

@app.route("/api/account", methods=["POST"])
@login_required
def api_add_account():
    """Create a new bank account."""
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        account_type = data.get("account_type", "Checking").strip()
        initial_balance = float(data.get("initial_balance") or 0.0)
        account_number = data.get("account_number", "").strip()
        color = data.get("color", "#0D9488").strip()
        icon = data.get("icon", "building-columns").strip()

        if not name:
            return jsonify({"success": False, "error": "Account name is required"}), 400

        acc_id = database.add_bank_account(
            name=name,
            account_type=account_type,
            initial_balance=initial_balance,
            account_number=account_number,
            color=color,
            icon=icon,
            user_id=user["id"]
        )
        return jsonify({"success": True, "id": acc_id, "message": "Bank account created successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/account/<int:account_id>", methods=["GET"])
@login_required
def api_get_account(account_id):
    """Retrieve details for a single bank account."""
    user = get_current_user()
    acc = database.get_bank_account_by_id(account_id, user_id=user["id"])
    if not acc:
        return jsonify({"success": False, "error": "Bank account not found"}), 404
    return jsonify({"success": True, "account": acc})

@app.route("/api/account/<int:account_id>", methods=["PUT", "POST"])
@login_required
def api_update_account(account_id):
    """Update an existing bank account."""
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        account_type = data.get("account_type", "Checking").strip()
        initial_balance = float(data.get("initial_balance") or 0.0)
        account_number = data.get("account_number", "").strip()
        color = data.get("color", "#0D9488").strip()
        icon = data.get("icon", "building-columns").strip()

        if not name:
            return jsonify({"success": False, "error": "Account name is required"}), 400

        updated = database.update_bank_account(
            account_id=account_id,
            name=name,
            account_type=account_type,
            initial_balance=initial_balance,
            account_number=account_number,
            color=color,
            icon=icon,
            user_id=user["id"]
        )
        if not updated:
            return jsonify({"success": False, "error": "Bank account not found"}), 404
        return jsonify({"success": True, "message": "Bank account updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/account/<int:account_id>/delete", methods=["POST", "DELETE"])
@login_required
def api_delete_account(account_id):
    """Delete a bank account."""
    user = get_current_user()
    try:
        deleted = database.delete_bank_account(account_id, user_id=user["id"])
        if not deleted:
            return jsonify({"success": False, "error": "Bank account not found"}), 404
        return jsonify({"success": True, "message": "Bank account deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Category APIs ====================

@app.route("/api/category", methods=["POST"])
@login_required
def api_add_category():
    """Create a new category."""
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        icon = data.get("icon", "tag").strip()
        color = data.get("color", "#3B82F6").strip()
        budget = float(data.get("monthly_budget") or 0.0)
        
        if not name:
            return jsonify({"success": False, "error": "Category name is required"}), 400
            
        cat_id = database.add_category(name, icon, color, budget, user_id=user["id"])
        return jsonify({"success": True, "id": cat_id, "message": "Category created successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/category/<int:cat_id>", methods=["PUT", "POST"])
@login_required
def api_update_category(cat_id):
    """Update category settings and budget."""
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        icon = data.get("icon", "tag").strip()
        color = data.get("color", "#3B82F6").strip()
        budget = float(data.get("monthly_budget") or 0.0)
        
        if not name:
            return jsonify({"success": False, "error": "Category name is required"}), 400
            
        updated = database.update_category(cat_id, name, icon, color, budget, user_id=user["id"])
        if not updated:
            return jsonify({"success": False, "error": "Category not found"}), 404
        return jsonify({"success": True, "message": "Category updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/category/<int:cat_id>/delete", methods=["POST", "DELETE"])
@login_required
def api_delete_category(cat_id):
    """Delete a category (only if no expenses linked)."""
    user = get_current_user()
    try:
        deleted = database.delete_category(cat_id, user_id=user["id"])
        if not deleted:
            return jsonify({"success": False, "error": "Category not found"}), 404
        return jsonify({"success": True, "message": "Category deleted successfully!"})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Monthly Budget APIs ====================

@app.route("/api/budget", methods=["GET"])
@login_required
def api_get_budget():
    """Retrieve current monthly budget status and all category budgets."""
    user = get_current_user()
    user_id = user["id"]
    categories = database.get_categories(user_id=user_id)
    total_budget = sum(c["monthly_budget"] for c in categories)
    total_spent = sum(c["current_month_spent"] for c in categories)
    return jsonify({
        "success": True,
        "total_budget": round(total_budget, 2),
        "total_spent": round(total_spent, 2),
        "categories": categories
    })

@app.route("/api/budget", methods=["POST", "PUT"])
@login_required
def api_update_budget():
    """
    Update monthly budget.
    Supports either:
      - 'category_budgets': dict { cat_id: budget } or list of { id, budget }
      - 'total_budget': overall monthly budget amount distributed across categories
    """
    user = get_current_user()
    user_id = user["id"]
    data = request.get_json() if request.is_json else request.form
    try:
        if "category_budgets" in data:
            category_budgets = data["category_budgets"]
            database.update_monthly_budgets(category_budgets, user_id=user_id)
        elif "total_budget" in data:
            total_budget = float(data["total_budget"])
            database.set_total_monthly_budget(total_budget, user_id=user_id)
        else:
            return jsonify({"success": False, "error": "Missing 'category_budgets' or 'total_budget'"}), 400

        categories = database.get_categories(user_id=user_id)
        new_total = sum(c["monthly_budget"] for c in categories)
        return jsonify({
            "success": True,
            "message": "Monthly budget updated successfully!",
            "total_budget": round(new_total, 2),
            "categories": categories
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/category/<int:cat_id>/budget", methods=["POST", "PUT"])
@login_required
def api_update_single_category_budget(cat_id):
    """Update an individual category's monthly budget."""
    user = get_current_user()
    data = request.get_json() if request.is_json else request.form
    try:
        monthly_budget = float(data.get("monthly_budget", 0.0))
        updated = database.update_category_budget(cat_id, monthly_budget, user_id=user["id"])
        if not updated:
            return jsonify({"success": False, "error": "Category not found"}), 404
        return jsonify({"success": True, "message": "Category budget updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Settings & Currency APIs ====================

@app.route("/api/settings/currency", methods=["GET", "POST"])
def api_currency_settings():
    """Get or update active currency settings."""
    if request.method == "POST":
        data = request.get_json() if request.is_json else request.form
        code = (data.get("code") or "USD").strip().upper()
        symbol = data.get("symbol")
        
        if not symbol:
            matched = next((c["symbol"] for c in SUPPORTED_CURRENCIES if c["code"] == code), "$")
            symbol = matched
            
        database.set_currency(code, symbol)
        return jsonify({
            "success": True,
            "message": f"Currency changed to {code} ({symbol})",
            "currency": {"code": code, "symbol": symbol}
        })
        
    return jsonify({
        "currency": database.get_currency(),
        "supported": SUPPORTED_CURRENCIES
    })

# ==================== Excel Export & Import Routes ====================

@app.route("/export/excel")
@login_required
def export_excel():
    """Generates and downloads the multi-tab formatted Excel report."""
    user = get_current_user()
    user_id = user["id"]
    month = request.args.get("month")
    category_id = request.args.get("category_id")
    category_id = int(category_id) if category_id and category_id.isdigit() else None
    payment_method = request.args.get("payment_method") or None
    search = request.args.get("search") or None
    
    excel_stream = excel_service.export_expenses_to_excel(
        month_str=month,
        category_id=category_id,
        payment_method=payment_method,
        search=search,
        currency_symbol=database.get_currency()["symbol"],
        user_id=user_id
    )
    filename = f"Expense_Report_{month or 'All'}_{datetime.now().strftime('%Y%m%d')}.xlsx"
    return send_file(
        excel_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

@app.route("/export/template")
def download_template():
    """Downloads an Excel template formatted for importing expenses."""
    template_stream = excel_service.generate_import_template()
    return send_file(
        template_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="Expense_Import_Template.xlsx"
    )

@app.route("/import/excel", methods=["POST"])
@login_required
def import_excel():
    """Accepts an uploaded Excel file and imports expenses."""
    user = get_current_user()
    user_id = user["id"]
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400
        
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        return jsonify({"success": False, "error": "File must be an Excel spreadsheet (.xlsx)"}), 400
        
    try:
        result = excel_service.import_expenses_from_excel(file.stream, user_id=user_id)
        return jsonify({
            "success": True,
            "message": f"Successfully imported {result['imported']} expenses! ({result['skipped']} skipped)",
            "details": result
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Import failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)

