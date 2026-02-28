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
    safe_vendor = _esc(expense_data['vendor'])
    safe_category = _esc(expense_data['category'])
    safe_description = _esc(expense_data['description'])
    safe_date = _esc(expense_data['date'])
    safe_amount = _esc(expense_data['amount'])
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


def get_expense_rejected_email(expense_data: dict, rejector_name: str, reason: str) -> tuple:
    """Email template for when an expense is rejected"""
    safe_rejector = _esc(rejector_name)
    safe_vendor = _esc(expense_data['vendor'])
    safe_category = _esc(expense_data['category'])
    safe_description = _esc(expense_data['description'])
    safe_amount = _esc(expense_data['amount'])
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


def get_pending_approval_email(expense_data: dict, submitter_name: str, manager_name: str) -> tuple:
    """Email template for managers when an expense needs approval"""
    safe_submitter = _esc(submitter_name)
    safe_manager = _esc(manager_name)
    safe_vendor = _esc(expense_data['vendor'])
    safe_category = _esc(expense_data['category'])
    safe_description = _esc(expense_data['description'])
    safe_date = _esc(expense_data['date'])
    safe_amount = _esc(expense_data['amount'])
    subject = f"Approval Needed: ${expense_data['amount']} expense from {submitter_name}"

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


def get_budget_alert_email(budget_data: dict, current_spending: float, threshold_percent: int) -> tuple:
    """Email template for budget alerts"""
    safe_budget_name = _esc(budget_data['name'])
    safe_period = _esc(budget_data.get('period', 'Monthly'))
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
