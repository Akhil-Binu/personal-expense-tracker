"""
Analytics and AI Spending Insights Engine for FinanceFlow v2.0.
Calculates budget burn velocity, detects month-over-month anomalies,
analyzes net cash flow, and generates actionable financial guidance.
"""
import calendar
from datetime import date, datetime, timedelta
import database

def generate_smart_insights(user_id=1, month_str=None):
    """
    Generates intelligent, actionable financial cards based on real-time
    spending patterns, budget velocity, subscriptions, and financial goals.
    """
    user_id = user_id or 1
    today = date.today()
    if not month_str:
        month_str = today.strftime("%Y-%m")
        
    curr_info = database.get_currency()
    curr_sym = curr_info.get("symbol", "$")
    
    insights = []
    
    # 1. Cash Flow & Savings Rate Insight
    cash_flow = database.get_cash_flow_summary(user_id=user_id, month_str=month_str)
    income = cash_flow["total_income"]
    expenses = cash_flow["total_expenses"]
    net = cash_flow["net_cash_flow"]
    rate = cash_flow["savings_rate"]
    
    if income > 0:
        if rate >= 20.0:
            insights.append({
                "type": "success",
                "badge": "High Savings",
                "icon": "shield-check",
                "title": f"Strong Savings Rate ({rate}%)",
                "message": f"Outstanding job! You've retained {curr_sym}{net:,.2f} of your {curr_sym}{income:,.2f} income this month, outperforming the standard 20% savings rule."
            })
        elif rate > 0:
            insights.append({
                "type": "info",
                "badge": "Cash Flow",
                "icon": "chart-line-up",
                "title": f"Positive Cash Flow (+{rate}%)",
                "message": f"You have saved {curr_sym}{net:,.2f} so far this month. Consider allocating a portion of this surplus towards your savings goals."
            })
        else:
            deficit = abs(net)
            insights.append({
                "type": "danger",
                "badge": "Cash Deficit",
                "icon": "triangle-exclamation",
                "title": "Expenses Exceed Income",
                "message": f"Your monthly outlays ({curr_sym}{expenses:,.2f}) exceed your logged income ({curr_sym}{income:,.2f}) by {curr_sym}{deficit:,.2f}. Review variable expenses to curb deficit."
            })
    elif expenses > 0:
        insights.append({
            "type": "info",
            "badge": "Tip",
            "icon": "circle-plus",
            "title": "Log Your Monthly Income",
            "message": "Add your salary or freelance income to unlock net cash flow tracking, savings rates, and automated balance reconciliation."
        })

    # 2. Budget Velocity & Burn Rate (for current month)
    if month_str == today.strftime("%Y-%m"):
        year, month = today.year, today.month
        days_in_month = calendar.monthrange(year, month)[1]
        days_passed = max(1, today.day)
        month_progress_ratio = days_passed / days_in_month
        
        categories = database.get_category_breakdown(month_str=month_str, user_id=user_id)
        velocity_alerts = 0
        for cat in categories:
            budget = cat["monthly_budget"]
            spent = cat["spent"]
            if budget > 0 and spent > 0:
                projected_spend = (spent / days_passed) * days_in_month
                if spent > budget:
                    insights.append({
                        "type": "danger",
                        "badge": "Budget Overrun",
                        "icon": "circle-exclamation",
                        "title": f"{cat['name']} Exceeded Budget",
                        "message": f"You have spent {curr_sym}{spent:,.2f} of your {curr_sym}{budget:,.2f} budget ({cat['budget_utilization']}% utilized)."
                    })
                    velocity_alerts += 1
                elif projected_spend > (budget * 1.15) and spent > 25.0:
                    exceed_by = round(projected_spend - budget, 2)
                    insights.append({
                        "type": "warning",
                        "badge": "Pace Warning",
                        "icon": "gauge-high",
                        "title": f"{cat['name']} Pace Warning",
                        "message": f"At your current daily burn rate, {cat['name']} is projected to reach {curr_sym}{projected_spend:,.2f} by month-end, exceeding your budget by {curr_sym}{exceed_by:,.2f}."
                    })
                    velocity_alerts += 1
                    
        # Overall budget burn rate if no specific alert triggered
        if velocity_alerts == 0 and categories:
            total_budget = sum(c["monthly_budget"] for c in categories)
            total_spent = sum(c["spent"] for c in categories)
            if total_budget > 0:
                utilization = round((total_spent / total_budget) * 100, 1)
                expected_utilization = round(month_progress_ratio * 100, 1)
                if utilization <= expected_utilization:
                    insights.append({
                        "type": "success",
                        "badge": "On Track",
                        "icon": "circle-check",
                        "title": "Budgets Under Control",
                        "message": f"{days_passed} days through the month, you've utilized {utilization}% of your total budget (healthy expected: ~{expected_utilization}%)."
                    })

    # 3. Recurring Subscriptions Snapshot
    subs = database.get_subscriptions(user_id=user_id, active_only=True)
    if subs:
        sub_monthly_total = 0.0
        for s in subs:
            cycle = s.get("billing_cycle", "Monthly").capitalize()
            amt = s["amount"]
            if cycle == "Weekly":
                sub_monthly_total += amt * 4.33
            elif cycle == "Quarterly":
                sub_monthly_total += amt / 3.0
            elif cycle == "Yearly":
                sub_monthly_total += amt / 12.0
            else:
                sub_monthly_total += amt
                
        sub_monthly_total = round(sub_monthly_total, 2)
        annual_total = round(sub_monthly_total * 12, 2)
        
        upcoming = [s for s in subs if 0 <= s.get("days_until_due", 999) <= 7]
        if upcoming:
            names = ", ".join(f"'{s['name']}' ({curr_sym}{s['amount']:,.2f})" for s in upcoming[:2])
            insights.append({
                "type": "info",
                "badge": "Bills Due Soon",
                "icon": "bell-ring",
                "title": f"{len(upcoming)} Subscription Due This Week",
                "message": f"Upcoming: {names}. Total monthly commitments stand at {curr_sym}{sub_monthly_total:,.2f}/mo ({curr_sym}{annual_total:,.2f}/yr)."
            })
        else:
            insights.append({
                "type": "info",
                "badge": "Subscriptions",
                "icon": "repeat",
                "title": f"{len(subs)} Active Subscriptions",
                "message": f"You are currently committed to {curr_sym}{sub_monthly_total:,.2f}/month across {len(subs)} recurring services."
            })

    # 4. Financial Goals Progress
    goals = database.get_goals(user_id=user_id)
    if goals:
        active_goals = [g for g in goals if not g.get("is_completed")]
        if active_goals:
            # Sort by highest progress percentage
            active_goals.sort(key=lambda x: x["progress_percentage"], reverse=True)
            top_g = active_goals[0]
            insights.append({
                "type": "success" if top_g["progress_percentage"] >= 75 else "info",
                "badge": "Savings Goal",
                "icon": "bullseye-arrow",
                "title": f"Goal Highlight: {top_g['name']}",
                "message": f"You're {top_g['progress_percentage']}% of the way to your target ({curr_sym}{top_g['current_amount']:,.2f} of {curr_sym}{top_g['target_amount']:,.2f}). Only {curr_sym}{top_g['remaining_amount']:,.2f} to go!"
            })

    return insights

def calculate_budget_velocity(user_id=1, month_str=None):
    """
    Computes real-time spending velocity and projected month-end totals.
    """
    user_id = user_id or 1
    today = date.today()
    if not month_str:
        month_str = today.strftime("%Y-%m")
    try:
        dt = datetime.strptime(month_str, "%Y-%m")
        year, month = dt.year, dt.month
    except Exception:
        year, month = today.year, today.month
        
    days_in_month = calendar.monthrange(year, month)[1]
    days_passed = today.day if (year == today.year and month == today.month) else days_in_month
    days_passed = max(1, min(days_passed, days_in_month))
    month_pct_elapsed = round((days_passed / days_in_month) * 100, 1)

    categories = database.get_category_breakdown(month_str=month_str, user_id=user_id)
    total_budget = sum(c["monthly_budget"] for c in categories)
    total_spent = sum(c["spent"] for c in categories)

    daily_run_rate = round(total_spent / days_passed, 2)
    projected_monthly_spend = round(daily_run_rate * days_in_month, 2)
    velocity_ratio = round(projected_monthly_spend / total_budget, 2) if total_budget > 0 else 1.0

    if total_budget == 0:
        status = "No Budget Set"
        color = "secondary"
    elif velocity_ratio <= 0.85:
        status = "Under Budget"
        color = "success"
    elif velocity_ratio <= 1.0:
        status = "On Track"
        color = "primary"
    elif velocity_ratio <= 1.15:
        status = "Slightly Over Pace"
        color = "warning"
    else:
        status = "Critical Overrun"
        color = "danger"

    return {
        "month_str": month_str,
        "days_in_month": days_in_month,
        "days_passed": days_passed,
        "month_pct_elapsed": month_pct_elapsed,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "daily_run_rate": daily_run_rate,
        "projected_monthly_spend": projected_monthly_spend,
        "velocity_ratio": velocity_ratio,
        "status": status,
        "color": color
    }
