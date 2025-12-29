"""Display all limits, features, and current usage for free tier organization"""
import json
from src.database import SessionLocal
from src.models_billing import BillingTier, OrganizationSubscription
from src.billing.limit_enforcer import LimitEnforcer
from src.models import Organization

db = SessionLocal()

# Get free tier config
free_tier = db.query(BillingTier).filter(BillingTier.tier_name == 'free').first()

# Get the active organization
org = db.query(Organization).filter(Organization.is_active == True).first()

if not org:
    print("ERROR: No active organization found!")
    db.close()
    exit(1)

# Get limit enforcer
enforcer = LimitEnforcer(db)
limits = enforcer.get_org_tier(org.id)
usage = enforcer.get_current_month_usage(org.id)
summary = enforcer.get_usage_summary(org.id)

print('\n' + '=' * 80)
print('FREE TIER - ALL LIMITS, FEATURES & CURRENT USAGE')
print('=' * 80 + '\n')

print(f'Organization: {org.name}')
print(f'Organization ID: {org.id}')
print(f'Tier: {limits.tier_name.upper()}')
print(f'Free Tier: {"Yes" if summary["is_free_tier"] else "No"}')

# MONTHLY LIMITS
print('\n' + '-' * 80)
print('MONTHLY LIMITS & CURRENT USAGE')
print('-' * 80)

monthly_limits = [
    ('Max Organizations', limits.max_organizations, None, 'organizations'),
    ('Max Users', limits.max_users, usage['members'], 'users'),
    ('Max Expenses/Month', limits.max_expenses_per_month, usage['expenses'], 'expenses'),
    ('AI Categorizations/Month', limits.max_ai_categorizations, usage['ai_categorizations'], 'ai'),
    ('OCR Scans/Month', limits.ocr_scans_included, usage['ocr_scans'], 'ocr'),
    ('AP2 Transactions/Month', limits.max_ap2_transactions, usage['ap2_transactions'], 'ap2'),
]

for name, limit, current, key in monthly_limits:
    if current is not None:
        if limit == 0:
            status = "[BLOCKED]"
            display = f"{current}/{limit} {status}"
        elif limit is None:
            status = "[UNLIMITED]"
            display = f"{current} {status}"
        else:
            percentage = int((current / limit) * 100) if limit > 0 else 0
            if current >= limit:
                status = "[AT LIMIT]"
            elif percentage >= 80:
                status = "[WARNING]"
            else:
                status = "[OK]"
            display = f"{current}/{limit} ({percentage}%) {status}"
        print(f'  {name:<30} {display}')
    else:
        if limit == 0:
            print(f'  {name:<30} 0 [BLOCKED]')
        elif limit is None:
            print(f'  {name:<30} Unlimited')
        else:
            print(f'  {name:<30} {limit}')

# DAILY LIMITS (Free tier specific)
print('\n' + '-' * 80)
print('DAILY RATE LIMITS (Free Tier Anti-Abuse)')
print('-' * 80)

daily_limits = [
    ('Expenses per Day', 10),
    ('OCR Scans per Day', 3),
    ('AI Categorizations per Day', 0),
    ('AP2 Transactions per Day', 0),
]

for name, limit in daily_limits:
    if limit == 0:
        print(f'  {name:<30} {limit} [BLOCKED]')
    else:
        print(f'  {name:<30} {limit}')

# STORAGE & DATA
print('\n' + '-' * 80)
print('STORAGE & DATA RETENTION')
print('-' * 80)

# Parse limits JSON to get storage info
tier_limits = free_tier.limits if isinstance(free_tier.limits, dict) else json.loads(free_tier.limits or '{}')
print(f'  Data Retention:                {tier_limits.get("data_retention_days", "N/A")} days')
print(f'  Max File Size:                 N/A (configured at app level)')
print(f'  Max Storage:                   N/A (configured at app level)')

# FEATURES
print('\n' + '-' * 80)
print('FEATURE ACCESS')
print('-' * 80)

features = [
    ('Basic Expense Tracking', True, 'Always enabled'),
    ('OCR Receipt Scanning', True, '20 scans/month'),
    ('Basic Reports', True, 'Always enabled'),
    ('AP2 Payments', limits.max_ap2_transactions > 0, f'{limits.max_ap2_transactions} transactions/month'),
    ('API Access', summary['features']['api_access'], 'Professional tier+'),
    ('SSO/SAML', summary['features']['sso_enabled'], 'Enterprise tier+'),
    ('Custom Integrations', summary['features']['custom_integrations'], 'Enterprise tier+'),
    ('Advanced Analytics', summary['features']['advanced_analytics'], 'Professional tier+'),
    ('Approval Workflows', summary['features'].get('approval_workflows', False), 'Professional tier+'),
    ('Priority Support', summary['features']['priority_support'], 'Professional tier+'),
]

for name, enabled, note in features:
    status = "[OK]" if enabled else "[X]"
    print(f'  {status} {name:<30} {note}')

# CURRENT MONTH USAGE DETAILS
print('\n' + '-' * 80)
print('CURRENT MONTH USAGE BREAKDOWN')
print('-' * 80)

for metric_name, metric_data in summary['usage'].items():
    current = metric_data['current']
    limit = metric_data['limit']

    if metric_data['blocked']:
        status = "[BLOCKED]"
    elif metric_data['warning']:
        status = "[WARNING >80%]"
    elif metric_data['unlimited']:
        status = "[UNLIMITED]"
    else:
        status = "[OK]"

    if limit is None:
        display = f"{current} (unlimited) {status}"
    elif limit == 0:
        display = f"{current}/{limit} (feature disabled) {status}"
    else:
        display = f"{current}/{limit} ({metric_data['percentage']:.0f}%) {status}"

    print(f'  {metric_name.replace("_", " ").title():<30} {display}')

# WHAT YOU CAN DO
print('\n' + '-' * 80)
print('WHAT YOU CAN DO ON FREE TIER')
print('-' * 80)

expenses_left = limits.max_expenses_per_month - usage['expenses']
ocr_left = limits.ocr_scans_included - usage['ocr_scans']
users_left = limits.max_users - usage['members']
ap2_left = limits.max_ap2_transactions - usage['ap2_transactions']

print(f'  [OK] Submit {expenses_left} more expenses this month (out of {limits.max_expenses_per_month} total)')
print(f'  [OK] Use {ocr_left} more OCR scans this month (out of {limits.ocr_scans_included} total)')
if users_left > 0:
    print(f'  [OK] Add {users_left} more user(s) (out of {limits.max_users} total)')
else:
    print(f'  [X] Cannot add more users - at limit ({usage["members"]}/{limits.max_users})')
print(f'  [OK] Use {ap2_left} more AP2 transactions this month (out of {limits.max_ap2_transactions} total)')
print(f'  [OK] Submit up to 10 expenses per day')
print(f'  [OK] Use up to 3 OCR scans per day')
print(f'  [X] Cannot use AI categorization (0 included)')
print(f'  [X] Cannot access API programmatically')
print(f'  [X] Cannot use SSO/SAML')
print(f'  [X] Cannot use custom integrations')
print(f'  [X] Cannot access advanced analytics')

# UPGRADE SUGGESTIONS
print('\n' + '-' * 80)
print('UPGRADE TO GET MORE')
print('-' * 80)
print('  Upgrade to Starter ($29/month) to get:')
print('    - 3 organizations')
print('    - 10 users')
print('    - 100 expenses/month')
print('    - 100 OCR scans/month')
print('    - 50 AI categorizations/month')
print('    - Approval workflows')
print('    - Advanced analytics')

print('\n' + '=' * 80)

db.close()
