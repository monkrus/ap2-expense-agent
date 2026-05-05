"""
Email Templates for AP2 Expense Management
Centralized email template management
"""

import html


def _esc(value) -> str:
    """Escape a value for safe HTML interpolation."""
    return html.escape(str(value))


def get_expense_approved_email(expense_data: dict, approver_name: str) -> tuple:
    """Email template for when an expense is approved"""
    safe_approver = _esc(approver_name)
    safe_vendor = _esc(expense_data["vendor"])
    safe_category = _esc(expense_data["category"])
    safe_description = _esc(expense_data["description"])
    safe_date = _esc(expense_data["date"])
    safe_amount = _esc(expense_data["amount"])
    subject = f"Expense Approved: ${expense_data['amount']} - {expense_data['vendor']}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 8px 8px;
            }}
            .expense-details {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #10b981;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .detail-label {{
                font-weight: bold;
                color: #6b7280;
            }}
            .detail-value {{
                color: #111827;
            }}
            .status-badge {{
                background: #10b981;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                display: inline-block;
                font-weight: bold;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #6b7280;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✅ Expense Approved</h1>
            </div>
            <div class="content">
                <p>Good news! Your expense has been approved by {safe_approver}.</p>

                <div class="expense-details">
                    <div class="detail-row">
                        <span class="detail-label">Amount:</span>
                        <span class="detail-value">${safe_amount}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Vendor:</span>
                        <span class="detail-value">{safe_vendor}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Category:</span>
                        <span class="detail-value">{safe_category}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Description:</span>
                        <span class="detail-value">{safe_description}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Date:</span>
                        <span class="detail-value">{safe_date}</span>
                    </div>
                </div>

                <div class="status-badge">APPROVED</div>

                <p>The approved expense will be processed for reimbursement according to your organization's payment schedule.</p>

                <div class="footer">
                    <p>AP2 Expense Manager<br>
                    <a href="http://localhost:5173">View Dashboard</a></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Expense Approved

    Good news! Your expense has been approved by {safe_approver}.

    Expense Details:
    - Amount: ${safe_amount}
    - Vendor: {safe_vendor}
    - Category: {safe_category}
    - Description: {safe_description}
    - Date: {safe_date}

    Status: APPROVED

    The approved expense will be processed for reimbursement according to your organization's payment schedule.

    AP2 Expense Manager
    """

    return subject, html_body, text_body


def get_expense_rejected_email(
    expense_data: dict, rejector_name: str, reason: str
) -> tuple:
    """Email template for when an expense is rejected"""
    safe_rejector = _esc(rejector_name)
    safe_vendor = _esc(expense_data["vendor"])
    safe_category = _esc(expense_data["category"])
    safe_description = _esc(expense_data["description"])
    safe_amount = _esc(expense_data["amount"])
    safe_reason = _esc(reason)
    subject = f"Expense Rejected: ${expense_data['amount']} - {expense_data['vendor']}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 8px 8px;
            }}
            .expense-details {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #ef4444;
            }}
            .reason-box {{
                background: #fee2e2;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #dc2626;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .detail-label {{
                font-weight: bold;
                color: #6b7280;
            }}
            .detail-value {{
                color: #111827;
            }}
            .status-badge {{
                background: #ef4444;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                display: inline-block;
                font-weight: bold;
                margin: 20px 0;
            }}
            .action-button {{
                display: inline-block;
                padding: 12px 24px;
                background: #3b82f6;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin-top: 20px;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #6b7280;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>❌ Expense Rejected</h1>
            </div>
            <div class="content">
                <p>Your expense has been rejected by {safe_rejector}.</p>

                <div class="expense-details">
                    <div class="detail-row">
                        <span class="detail-label">Amount:</span>
                        <span class="detail-value">${safe_amount}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Vendor:</span>
                        <span class="detail-value">{safe_vendor}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Category:</span>
                        <span class="detail-value">{safe_category}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Description:</span>
                        <span class="detail-value">{safe_description}</span>
                    </div>
                </div>

                <div class="status-badge">REJECTED</div>

                <div class="reason-box">
                    <strong>Rejection Reason:</strong><br>
                    {safe_reason}
                </div>

                <p>If you believe this rejection was made in error or have additional information to provide, please contact {safe_rejector} or submit a corrected expense.</p>

                <a href="http://localhost:5173/expenses/new" class="action-button">Submit New Expense</a>

                <div class="footer">
                    <p>AP2 Expense Manager<br>
                    <a href="http://localhost:5173">View Dashboard</a></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Expense Rejected

    Your expense has been rejected by {safe_rejector}.

    Expense Details:
    - Amount: ${safe_amount}
    - Vendor: {safe_vendor}
    - Category: {safe_category}
    - Description: {safe_description}

    Status: REJECTED

    Rejection Reason:
    {safe_reason}

    If you believe this rejection was made in error or have additional information to provide, please contact {safe_rejector} or submit a corrected expense.

    AP2 Expense Manager
    """

    return subject, html_body, text_body


def get_pending_approval_email(
    expense_data: dict, submitter_name: str, manager_name: str
) -> tuple:
    """Email template for managers when an expense needs approval"""
    safe_submitter = _esc(submitter_name)
    safe_manager = _esc(manager_name)
    safe_vendor = _esc(expense_data["vendor"])
    safe_category = _esc(expense_data["category"])
    safe_description = _esc(expense_data["description"])
    safe_date = _esc(expense_data["date"])
    safe_amount = _esc(expense_data["amount"])
    subject = (
        f"Approval Needed: ${expense_data['amount']} expense from {submitter_name}"
    )

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 8px 8px;
            }}
            .expense-details {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid #f59e0b;
            }}
            .detail-row {{
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e5e7eb;
            }}
            .detail-label {{
                font-weight: bold;
                color: #6b7280;
            }}
            .detail-value {{
                color: #111827;
            }}
            .action-buttons {{
                margin: 30px 0;
                text-align: center;
            }}
            .approve-button {{
                display: inline-block;
                padding: 12px 32px;
                background: #10b981;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 0 10px;
                font-weight: bold;
            }}
            .reject-button {{
                display: inline-block;
                padding: 12px 32px;
                background: #ef4444;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                margin: 0 10px;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #6b7280;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⏳ Approval Needed</h1>
            </div>
            <div class="content">
                <p>Hi {safe_manager},</p>
                <p>{safe_submitter} has submitted an expense that requires your approval.</p>

                <div class="expense-details">
                    <div class="detail-row">
                        <span class="detail-label">Amount:</span>
                        <span class="detail-value">${safe_amount}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Vendor:</span>
                        <span class="detail-value">{safe_vendor}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Category:</span>
                        <span class="detail-value">{safe_category}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Description:</span>
                        <span class="detail-value">{safe_description}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">Submitted:</span>
                        <span class="detail-value">{safe_date}</span>
                    </div>
                </div>

                <div class="action-buttons">
                    <a href="http://localhost:5173/expenses/{expense_data['id']}/approve" class="approve-button">✓ Approve</a>
                    <a href="http://localhost:5173/expenses/{expense_data['id']}/reject" class="reject-button">✗ Reject</a>
                </div>

                <p style="text-align: center; color: #6b7280;">Or review in the <a href="http://localhost:5173/expenses">expense dashboard</a></p>

                <div class="footer">
                    <p>AP2 Expense Manager</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Approval Needed

    Hi {safe_manager},

    {safe_submitter} has submitted an expense that requires your approval.

    Expense Details:
    - Amount: ${safe_amount}
    - Vendor: {safe_vendor}
    - Category: {safe_category}
    - Description: {safe_description}
    - Submitted: {safe_date}

    Please review and approve or reject this expense in your dashboard.

    AP2 Expense Manager
    """

    return subject, html_body, text_body


def get_budget_alert_email(
    budget_data: dict, current_spending: float, threshold_percent: int
) -> tuple:
    """Email template for budget alerts"""
    safe_budget_name = _esc(budget_data["name"])
    safe_period = _esc(budget_data.get("period", "Monthly"))
    subject = f"Budget Alert: {budget_data['name']} at {threshold_percent}% ({current_spending}/{budget_data['amount']})"

    alert_level = "warning" if threshold_percent < 100 else "critical"
    alert_color = "#f59e0b" if alert_level == "warning" else "#ef4444"
    alert_icon = "⚠️" if alert_level == "warning" else "🚨"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .container {{
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: {alert_color};
                color: white;
                padding: 30px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                background: #f9f9f9;
                padding: 30px;
                border-radius: 0 0 8px 8px;
            }}
            .alert-box {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
                border-left: 4px solid {alert_color};
            }}
            .progress-bar {{
                width: 100%;
                height: 30px;
                background: #e5e7eb;
                border-radius: 15px;
                overflow: hidden;
                margin: 20px 0;
            }}
            .progress-fill {{
                height: 100%;
                background: {alert_color};
                width: {min(threshold_percent, 100)}%;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                color: #6b7280;
                font-size: 14px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{alert_icon} Budget Alert: {threshold_percent}% Reached</h1>
            </div>
            <div class="content">
                <div class="alert-box">
                    <h2>{safe_budget_name}</h2>
                    <p><strong>Current Spending:</strong> ${current_spending:,.2f} / ${budget_data['amount']:,.2f}</p>

                    <div class="progress-bar">
                        <div class="progress-fill">{threshold_percent}%</div>
                    </div>

                    <p><strong>Remaining:</strong> ${budget_data['amount'] - current_spending:,.2f}</p>
                    <p><strong>Period:</strong> {safe_period}</p>
                </div>

                {"<p><strong>Warning:</strong> You are approaching your budget limit. Please review your spending.</p>" if alert_level == "warning" else "<p><strong>Critical:</strong> Your budget has been exceeded. Immediate attention required.</p>"}

                <div class="footer">
                    <p>AP2 Expense Manager<br>
                    <a href="http://localhost:5173/budgets">View Budget Details</a></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Budget Alert: {threshold_percent}% Reached

    {safe_budget_name}

    Current Spending: ${current_spending:,.2f} / ${budget_data['amount']:,.2f}
    Progress: {threshold_percent}%
    Remaining: ${budget_data['amount'] - current_spending:,.2f}
    Period: {safe_period}

    {"Warning: You are approaching your budget limit. Please review your spending." if alert_level == "warning" else "Critical: Your budget has been exceeded. Immediate attention required."}

    AP2 Expense Manager
    """

    return subject, html_body, text_body


def get_auto_approved_email(
    expense_data: dict, approval_via: str, mandate_details: dict = None
) -> tuple:
    """Email template for AI auto-approved expenses via Intent Mandate or Approval Policy."""
    safe_vendor = _esc(expense_data.get("vendor", "Unknown"))
    safe_category = _esc(expense_data.get("category", "Other"))
    safe_description = _esc(expense_data.get("description", ""))
    safe_date = _esc(expense_data.get("date", ""))
    amount = expense_data.get("amount", 0)

    if approval_via == "intent_mandate":
        badge_color = "#7c3aed"
        badge_text = "AI Agent (AP2 Intent Mandate)"
        icon = "&#10024;"
    else:
        badge_color = "#2563eb"
        badge_text = "Approval Policy"
        icon = "&#128203;"

    mandate_section = ""
    if mandate_details:
        safe_mandate_name = _esc(mandate_details.get("name", ""))
        constraints = mandate_details.get("constraints", {})
        mandate_section = f"""
                    <div style="background: #f3f4f6; padding: 12px 16px; border-radius: 6px; margin-top: 16px;">
                        <p style="margin: 0 0 4px 0; font-weight: 600; font-size: 13px; color: #374151;">Matched Rule:</p>
                        <p style="margin: 0; font-size: 13px; color: #6b7280;">{safe_mandate_name or 'Intent Mandate'}</p>
                        {"<p style='margin: 4px 0 0 0; font-size: 12px; color: #9ca3af;'>Max per transaction: $" + f"{constraints.get('max_amount', 'N/A')}" + "</p>" if constraints.get('max_amount') else ""}
                    </div>"""

    subject = f"Expense Auto-Approved: ${amount:,.2f} at {expense_data.get('vendor', 'Unknown')}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, {badge_color} 0%, #4f46e5 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
            .detail-box {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {badge_color}; }}
            .badge {{ display: inline-block; background: {badge_color}; color: white; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{icon} Expense Auto-Approved</h1>
                <p>Your expense was approved instantly by AI</p>
            </div>
            <div class="content">
                <p>Great news! Your expense has been <strong>automatically approved</strong> -- no manager review needed.</p>

                <div class="detail-box">
                    <p style="margin-top:0;"><span class="badge">{badge_text}</span></p>
                    <table style="width:100%; border-collapse:collapse; margin-top:12px;">
                        <tr><td style="padding:6px 0; color:#6b7280; width:120px;">Amount</td><td style="padding:6px 0; font-weight:600;">${amount:,.2f}</td></tr>
                        <tr><td style="padding:6px 0; color:#6b7280;">Vendor</td><td style="padding:6px 0;">{safe_vendor}</td></tr>
                        <tr><td style="padding:6px 0; color:#6b7280;">Category</td><td style="padding:6px 0;">{safe_category}</td></tr>
                        <tr><td style="padding:6px 0; color:#6b7280;">Description</td><td style="padding:6px 0;">{safe_description}</td></tr>
                        <tr><td style="padding:6px 0; color:#6b7280;">Date</td><td style="padding:6px 0;">{safe_date}</td></tr>
                    </table>
                    {mandate_section}
                </div>

                <div class="footer">
                    <p>AP2 Expense Manager<br>
                    <a href="http://localhost:5173">View in Dashboard</a></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Expense Auto-Approved

    Your expense was automatically approved by {badge_text}.

    Amount: ${amount:,.2f}
    Vendor: {safe_vendor}
    Category: {safe_category}
    Description: {safe_description}
    Date: {safe_date}

    AP2 Expense Manager
    """

    return subject, html_body, text_body


def get_monthly_auto_approval_summary_email(summary: dict) -> tuple:
    """
    Monthly digest email showing auto-approval statistics.

    summary keys:
        user_name, month_label, total_expenses, auto_approved_count,
        manual_count, auto_approval_rate, total_amount, auto_approved_amount,
        time_saved_minutes, by_mandate_count, by_policy_count,
        top_vendors (list of {vendor, count, amount})
    """
    safe_name = _esc(summary.get("user_name", "there"))
    month_label = _esc(summary.get("month_label", "Last Month"))
    total = summary.get("total_expenses", 0)
    auto_count = summary.get("auto_approved_count", 0)
    manual_count = summary.get("manual_count", 0)
    rate = summary.get("auto_approval_rate", 0)
    total_amount = summary.get("total_amount", 0)
    auto_amount = summary.get("auto_approved_amount", 0)
    time_saved = summary.get("time_saved_minutes", 0)
    by_mandate = summary.get("by_mandate_count", 0)
    by_policy = summary.get("by_policy_count", 0)
    top_vendors = summary.get("top_vendors", [])

    # Build top vendors rows
    vendor_rows = ""
    for v in top_vendors[:5]:
        vendor_rows += (
            f'<tr><td style="padding:6px 12px; border-bottom:1px solid #e5e7eb;">{_esc(v["vendor"])}</td>'
            f'<td style="padding:6px 12px; border-bottom:1px solid #e5e7eb; text-align:center;">{v["count"]}</td>'
            f'<td style="padding:6px 12px; border-bottom:1px solid #e5e7eb; text-align:right;">${v["amount"]:,.2f}</td></tr>'
        )

    vendor_table = ""
    if vendor_rows:
        vendor_table = f"""
                <h3 style="margin:24px 0 8px 0; font-size:15px; color:#374151;">Top Auto-Approved Vendors</h3>
                <table style="width:100%; border-collapse:collapse; font-size:13px;">
                    <thead><tr style="background:#f3f4f6;">
                        <th style="padding:8px 12px; text-align:left;">Vendor</th>
                        <th style="padding:8px 12px; text-align:center;">Count</th>
                        <th style="padding:8px 12px; text-align:right;">Amount</th>
                    </tr></thead>
                    <tbody>{vendor_rows}</tbody>
                </table>"""

    # Rate color
    if rate >= 60:
        rate_color = "#16a34a"
        rate_label = "Excellent"
    elif rate >= 40:
        rate_color = "#ca8a04"
        rate_label = "Good"
    else:
        rate_color = "#6b7280"
        rate_label = "Getting started"

    subject = f"Monthly Report: {auto_count} expenses auto-approved in {summary.get('month_label', 'last month')}"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%); color: white; padding: 30px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }}
            .stat-grid {{ display: flex; gap: 12px; margin: 20px 0; flex-wrap: wrap; }}
            .stat-card {{ flex: 1; min-width: 120px; background: white; padding: 16px; border-radius: 8px; text-align: center; }}
            .stat-value {{ font-size: 28px; font-weight: 700; color: #111827; }}
            .stat-label {{ font-size: 12px; color: #6b7280; margin-top: 4px; }}
            .highlight {{ background: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #7c3aed; }}
            .footer {{ text-align: center; margin-top: 30px; color: #6b7280; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>&#128202; Monthly Auto-Approval Report</h1>
                <p>{month_label}</p>
            </div>
            <div class="content">
                <p>Hi {safe_name},</p>
                <p>Here's your monthly summary of AI-powered expense approvals.</p>

                <div class="stat-grid">
                    <div class="stat-card">
                        <div class="stat-value" style="color:{rate_color};">{rate:.0f}%</div>
                        <div class="stat-label">Auto-Approval Rate<br><strong style="color:{rate_color};">{rate_label}</strong></div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{auto_count}</div>
                        <div class="stat-label">Auto-Approved</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{time_saved}</div>
                        <div class="stat-label">Minutes Saved</div>
                    </div>
                </div>

                <div class="highlight">
                    <table style="width:100%; border-collapse:collapse; font-size:14px;">
                        <tr><td style="padding:4px 0; color:#6b7280;">Total expenses submitted</td><td style="padding:4px 0; text-align:right; font-weight:600;">{total}</td></tr>
                        <tr><td style="padding:4px 0; color:#6b7280;">Auto-approved (AI Agent)</td><td style="padding:4px 0; text-align:right; font-weight:600; color:#7c3aed;">{by_mandate}</td></tr>
                        <tr><td style="padding:4px 0; color:#6b7280;">Auto-approved (Policy)</td><td style="padding:4px 0; text-align:right; font-weight:600; color:#2563eb;">{by_policy}</td></tr>
                        <tr><td style="padding:4px 0; color:#6b7280;">Manual approval</td><td style="padding:4px 0; text-align:right; font-weight:600;">{manual_count}</td></tr>
                        <tr style="border-top:1px solid #e5e7eb;"><td style="padding:8px 0 4px; color:#6b7280;">Total amount</td><td style="padding:8px 0 4px; text-align:right; font-weight:600;">${total_amount:,.2f}</td></tr>
                        <tr><td style="padding:4px 0; color:#6b7280;">Auto-approved amount</td><td style="padding:4px 0; text-align:right; font-weight:600; color:#16a34a;">${auto_amount:,.2f}</td></tr>
                    </table>
                </div>

                {vendor_table}

                {"<p style='margin-top:20px; padding:12px 16px; background:#fef3c7; border-radius:6px; font-size:13px; color:#92400e;'>&#128161; <strong>Tip:</strong> Create more Intent Mandates to increase your auto-approval rate and save even more time. Visit AP2 Automation in your dashboard.</p>" if rate < 60 else ""}

                <div class="footer">
                    <p>AP2 Expense Manager<br>
                    <a href="http://localhost:5173">View Dashboard</a></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Monthly Auto-Approval Report - {month_label}

    Hi {safe_name},

    Auto-Approval Rate: {rate:.0f}% ({rate_label})
    Total Expenses: {total}
    Auto-Approved: {auto_count} ({by_mandate} by AI Agent, {by_policy} by Policy)
    Manual: {manual_count}
    Total Amount: ${total_amount:,.2f}
    Auto-Approved Amount: ${auto_amount:,.2f}
    Time Saved: {time_saved} minutes

    AP2 Expense Manager
    """

    return subject, html_body, text_body
