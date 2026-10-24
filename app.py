"""
Personal Expense Tracker - Flask Application
Serves desktop, tablet, and mobile web experiences with SQLite backend & Excel integration.
"""
from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for, flash
import os
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

# Context processor for templates
@app.context_processor
def inject_global_data():
    today = date.today()
    return {
        "current_month": today.strftime("%Y-%m"),
        "current_date": today.isoformat(),
        "today_display": today.strftime("%A, %B %d, %Y"),
        "available_months": database.get_available_months(),
        "categories_list": database.get_categories(),
        "currency": database.get_currency(),
        "supported_currencies": SUPPORTED_CURRENCIES,
    }

# ==================== Web Page Views ====================

@app.route("/")
def dashboard():
    """Main dashboard page."""
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    metrics = database.get_monthly_metrics(month)
    categories = database.get_category_breakdown(month)
    recent_expenses = database.get_expenses(limit=8)
    return render_template(
        "index.html",
        selected_month=month,
        metrics=metrics,
        categories=categories,
        recent_expenses=recent_expenses,
        active_page="dashboard"
    )

@app.route("/expenses")
def expenses_page():
    """Expenses listing and filtering view."""
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    category_id = request.args.get("category_id")
    category_id = int(category_id) if category_id and category_id.isdigit() else None
    payment_method = request.args.get("payment_method") or None
    search = request.args.get("search") or None
    
    expenses = database.get_expenses(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        payment_method=payment_method,
        search=search
    )
    categories = database.get_categories()
    
    total_amount = sum(e["amount"] for e in expenses)
    
    return render_template(
        "expenses.html",
        expenses=expenses,
        categories=categories,
        filters={
            "start_date": start_date or "",
            "end_date": end_date or "",
            "category_id": category_id or "",
            "payment_method": payment_method or "",
            "search": search or ""
        },
        total_amount=round(total_amount, 2),
        active_page="expenses"
    )

@app.route("/reports")
def reports_page():
    """Monthly analytics and reporting view."""
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    metrics = database.get_monthly_metrics(month)
    categories = database.get_category_breakdown(month)
    payment_methods = database.get_payment_method_breakdown(month)
    
    return render_template(
        "reports.html",
        selected_month=month,
        metrics=metrics,
        categories=categories,
        payment_methods=payment_methods,
        active_page="reports"
    )

@app.route("/categories")
def categories_page():
    """Category and budget management view."""
    categories = database.get_categories()
    total_budget = sum(c["monthly_budget"] for c in categories)
    total_spent = sum(c["current_month_spent"] for c in categories)
    return render_template(
        "categories.html",
        categories=categories,
        total_budget=round(total_budget, 2),
        total_spent=round(total_spent, 2),
        active_page="categories"
    )

# ==================== JSON API Endpoints ====================

@app.route("/api/chart-data")
def api_chart_data():
    """Provides chart series for Dashboard & Reports."""
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    category_data = database.get_category_breakdown(month)
    daily_data = database.get_daily_spending_trend(month)
    history_data = database.get_monthly_history(num_months=6)
    payment_data = database.get_payment_method_breakdown(month)
    
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
def api_add_expense():
    """Add a new expense."""
    data = request.get_json() if request.is_json else request.form
    try:
        exp_date = data.get("date") or date.today().isoformat()
        category_id = int(data.get("category_id"))
        amount = float(data.get("amount"))
        payment_method = data.get("payment_method", "Cash")
        description = data.get("description", "").strip()
        notes = data.get("notes", "").strip()
        
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
            notes=notes
        )
        return jsonify({"success": True, "id": expense_id, "message": "Expense added successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/expense/<int:expense_id>", methods=["GET"])
def api_get_expense(expense_id):
    """Retrieve single expense details."""
    exp = database.get_expense_by_id(expense_id)
    if not exp:
        return jsonify({"success": False, "error": "Expense not found"}), 404
    return jsonify({"success": True, "expense": exp})

@app.route("/api/expense/<int:expense_id>", methods=["PUT", "POST"])
def api_update_expense(expense_id):
    """Update an existing expense."""
    data = request.get_json() if request.is_json else request.form
    try:
        exp_date = data.get("date")
        category_id = int(data.get("category_id"))
        amount = float(data.get("amount"))
        payment_method = data.get("payment_method")
        description = data.get("description", "").strip()
        notes = data.get("notes", "").strip()
        
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
            notes=notes
        )
        if not updated:
            return jsonify({"success": False, "error": "Expense not found"}), 404
        return jsonify({"success": True, "message": "Expense updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/expense/<int:expense_id>/delete", methods=["POST", "DELETE"])
def api_delete_expense(expense_id):
    """Delete an expense record."""
    try:
        deleted = database.delete_expense(expense_id)
        if not deleted:
            return jsonify({"success": False, "error": "Expense not found"}), 404
        return jsonify({"success": True, "message": "Expense deleted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# ==================== Category APIs ====================

@app.route("/api/category", methods=["POST"])
def api_add_category():
    """Create a new category."""
    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        icon = data.get("icon", "tag").strip()
        color = data.get("color", "#3B82F6").strip()
        budget = float(data.get("monthly_budget") or 0.0)
        
        if not name:
            return jsonify({"success": False, "error": "Category name is required"}), 400
            
        cat_id = database.add_category(name, icon, color, budget)
        return jsonify({"success": True, "id": cat_id, "message": "Category created successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/category/<int:cat_id>", methods=["PUT", "POST"])
def api_update_category(cat_id):
    """Update category settings and budget."""
    data = request.get_json() if request.is_json else request.form
    try:
        name = data.get("name", "").strip()
        icon = data.get("icon", "tag").strip()
        color = data.get("color", "#3B82F6").strip()
        budget = float(data.get("monthly_budget") or 0.0)
        
        if not name:
            return jsonify({"success": False, "error": "Category name is required"}), 400
            
        updated = database.update_category(cat_id, name, icon, color, budget)
        if not updated:
            return jsonify({"success": False, "error": "Category not found"}), 404
        return jsonify({"success": True, "message": "Category updated successfully!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/category/<int:cat_id>/delete", methods=["POST", "DELETE"])
def api_delete_category(cat_id):
    """Delete a category (only if no expenses linked)."""
    try:
        deleted = database.delete_category(cat_id)
        if not deleted:
            return jsonify({"success": False, "error": "Category not found"}), 404
        return jsonify({"success": True, "message": "Category deleted successfully!"})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
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
        
        # If symbol not supplied, look it up in supported currencies
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
def export_excel():
    """Generates and downloads the multi-tab formatted Excel report."""
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
        currency_symbol=database.get_currency()["symbol"]
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
def import_excel():
    """Accepts an uploaded Excel file and imports expenses."""
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400
        
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "error": "No file selected"}), 400
        
    if not (file.filename.endswith(".xlsx") or file.filename.endswith(".xls")):
        return jsonify({"success": False, "error": "File must be an Excel spreadsheet (.xlsx)"}), 400
        
    try:
        result = excel_service.import_expenses_from_excel(file.stream)
        return jsonify({
            "success": True,
            "message": f"Successfully imported {result['imported']} expenses! ({result['skipped']} skipped)",
            "details": result
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Import failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
