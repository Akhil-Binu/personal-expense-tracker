"""
Personal Expense Tracker - Flask Application
Serves desktop, tablet, and mobile web experiences with SQLite backend & Excel integration.
"""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash, session
import os
from functools import wraps
from datetime import datetime, date
import database
import excel_service

app = Flask(__name__)
app.secret_key = os.urandom(24)

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
        "currency": database.get_currency(),
        "supported_currencies": SUPPORTED_CURRENCIES,
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
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['username']}!", "success")
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)
        else:
            error = "Invalid username or password. Please try again."
            
    return render_template("login.html", error=error)

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
    """Main dashboard page."""
    user = get_current_user()
    user_id = user["id"]
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    metrics = database.get_monthly_metrics(month, user_id=user_id)
    categories = database.get_category_breakdown(month, user_id=user_id)
    recent_expenses = database.get_expenses(limit=8, user_id=user_id)
    return render_template(
        "index.html",
        selected_month=month,
        metrics=metrics,
        categories=categories,
        recent_expenses=recent_expenses,
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
    
    return render_template(
        "reports.html",
        selected_month=month,
        metrics=metrics,
        categories=categories,
        payment_methods=payment_methods,
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
    return render_template(
        "accounts.html",
        accounts=accounts,
        combined=combined,
        active_page="accounts"
    )

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
    """Add a new expense."""
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
            
        expense_id = database.add_expense(
            expense_date=exp_date,
            category_id=category_id,
            amount=amount,
            payment_method=payment_method,
            description=description,
            notes=notes,
            user_id=user_id,
            account_id=account_id
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
    """Update an existing expense."""
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
            
        updated = database.update_expense(
            expense_id=expense_id,
            expense_date=exp_date,
            category_id=category_id,
            amount=amount,
            payment_method=payment_method,
            description=description,
            notes=notes,
            user_id=user["id"],
            account_id=account_id
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

