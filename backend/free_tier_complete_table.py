"""Generate a complete table of ALL free tier limits"""
import json
from src.database import SessionLocal
from src.models_billing import BillingTier
from src.models import Organization
from src.billing.limit_enforcer import LimitEnforcer

db = SessionLocal()

# Get free tier from database
free_tier = db.query(BillingTier).filter(BillingTier.tier_name == 'free').first()

# Get organization to check enforcer limits
org = db.query(Organization).filter(Organization.is_active == True).first()

if org:
    enforcer = LimitEnforcer(db)
    enforcer_limits = enforcer.get_org_tier(org.id)
else:
    enforcer_limits = None

# Parse JSON fields
tier_limits = free_tier.limits if isinstance(free_tier.limits, dict) else json.loads(free_tier.limits or '{}')
tier_features = free_tier.features if isinstance(free_tier.features, list) else json.loads(free_tier.features or '[]')
tier_overage = free_tier.overage_pricing if isinstance(free_tier.overage_pricing, dict) else json.loads(free_tier.overage_pricing or '{}')

print('\n' + '=' * 100)
print('FREE TIER - COMPLETE LIMITS TABLE')
print('=' * 100)

print(f'\nTier: {free_tier.display_name}')
print(f'Price: ${free_tier.base_price_monthly:.2f} {free_tier.currency}/month')
print(f'Description: {free_tier.description}')

print('\n' + '=' * 100)
print('CATEGORY 1: RESOURCE LIMITS (Monthly)')
print('=' * 100)

print(f'{"Limit Type":<40} {"Value":<20} {"Notes"}')
print('-' * 100)

resource_limits = [
    ('Organizations', tier_limits.get('max_organizations'), 'Max organizations you can create'),
    ('Users', tier_limits.get('max_users'), 'Max users per organization (including admin)'),
    ('Expenses per Month', tier_limits.get('max_expenses_per_month'), 'Max expense submissions per calendar month'),
    ('OCR Scans per Month', tier_limits.get('ocr_scans_included'), 'Receipt OCR scanning included'),
    ('AI Categorizations per Month', tier_limits.get('max_ai_categorizations'), '0 = Feature disabled'),
    ('AP2 Transactions per Month', tier_limits.get('max_ap2_transactions'), 'Automated AP2 payments'),
]

for name, value, note in resource_limits:
    value_str = str(value) if value is not None else 'N/A'
    if value == 0:
        value_str = '0 (Blocked)'
    print(f'{name:<40} {value_str:<20} {note}')

print('\n' + '=' * 100)
print('CATEGORY 2: DAILY RATE LIMITS (Anti-Abuse)')
print('=' * 100)

print(f'{"Limit Type":<40} {"Value":<20} {"Notes"}')
print('-' * 100)

daily_limits = [
    ('Expenses per Day', '10', 'Max 10 expense submissions per day'),
    ('OCR Scans per Day', '3', 'Max 3 OCR scans per day'),
    ('AI Categorizations per Day', '0 (Blocked)', 'Feature not available'),
    ('AP2 Transactions per Day', '0 (Blocked)', 'Feature not available'),
]

for name, value, note in daily_limits:
    print(f'{name:<40} {value:<20} {note}')

print('\n' + '=' * 100)
print('CATEGORY 3: DATA & STORAGE')
print('=' * 100)

print(f'{"Limit Type":<40} {"Value":<20} {"Notes"}')
print('-' * 100)

storage_limits = [
    ('Data Retention', f"{tier_limits.get('data_retention_days')} days", 'Data older than this is deleted'),
    ('Max File Size per Upload', 'App-level config', 'Typically 10MB for receipts'),
    ('Total Storage Quota', 'App-level config', 'Not enforced at tier level'),
]

for name, value, note in storage_limits:
    print(f'{name:<40} {value:<20} {note}')

print('\n' + '=' * 100)
print('CATEGORY 4: FEATURES INCLUDED')
print('=' * 100)

print(f'{"Feature":<40} {"Included":<20} {"Details"}')
print('-' * 100)

if isinstance(tier_features, list):
    for feature in tier_features:
        details = {
            'basic_expense_tracking': 'Core expense submission & management',
            'ocr_receipt_scanning': '20 scans/month included',
            'basic_reports': 'Standard expense reports & exports',
            'ap2_payments': '20 transactions/month included',
        }.get(feature, '')
        print(f'{feature:<40} {"[OK] Yes":<20} {details}')

print('\n' + '=' * 100)
print('CATEGORY 5: PREMIUM FEATURES (Not Included)')
print('=' * 100)

print(f'{"Feature":<40} {"Available":<20} {"Upgrade Tier Required"}')
print('-' * 100)

premium_features = [
    ('AI Expense Categorization', '[X] No', 'Starter ($29/mo) - 50/month'),
    ('API Access', '[X] No', 'Professional ($99/mo)'),
    ('Approval Workflows', '[X] No', 'Professional ($99/mo)'),
    ('Advanced Analytics', '[X] No', 'Professional ($99/mo)'),
    ('Custom Integrations', '[X] No', 'Enterprise ($299/mo)'),
    ('SSO/SAML Authentication', '[X] No', 'Enterprise ($299/mo)'),
    ('Priority Support', '[X] No', 'Professional ($99/mo)'),
    ('Custom Branding', '[X] No', 'Enterprise ($299/mo)'),
    ('Multi-Currency Support', '[X] No', 'Professional ($99/mo)'),
    ('Audit Logs', '[X] No', 'Enterprise ($299/mo)'),
]

for name, available, upgrade in premium_features:
    print(f'{name:<40} {available:<20} {upgrade}')

print('\n' + '=' * 100)
print('CATEGORY 6: OVERAGE PRICING')
print('=' * 100)

print(f'{"Overage Type":<40} {"Cost":<20} {"Notes"}')
print('-' * 100)

overage_items = [
    ('Per Additional User', '$0', 'Hard limit - cannot exceed'),
    ('Per Additional Organization', '$0', 'Hard limit - cannot exceed'),
    ('Per Additional Expense', '$0', 'Hard limit - blocked at 30/month'),
    ('Per Additional OCR Scan', '$0', 'Hard limit - blocked at 20/month'),
    ('Per Additional AI Categorization', '$0', 'Feature disabled'),
    ('Per Additional AP2 Transaction', '$0', 'Hard limit - blocked at 20/month'),
]

for name, cost, note in overage_items:
    print(f'{name:<40} {cost:<20} {note}')

print('\n' + '=' * 100)
print('SUMMARY: WHAT FREE TIER GIVES YOU')
print('=' * 100)

print('''
[OK] 1 Organization
[OK] 2 Users (including admin)
[OK] 30 Expenses per month (10/day max)
[OK] 20 OCR Receipt Scans per month (3/day max)
[OK] 20 AP2 Payment Transactions per month
[OK] 90 Days Data Retention
[OK] Basic Expense Tracking
[OK] Basic Reports & Exports
[OK] Email Support

[X] No AI Categorization
[X] No API Access
[X] No Approval Workflows
[X] No Advanced Analytics
[X] No SSO/SAML
[X] No Custom Integrations
[X] No Priority Support
[X] Cannot exceed any limits (hard blocks)
''')

print('=' * 100)
print('UPGRADE COMPARISON')
print('=' * 100)

print(f'{"Feature":<30} {"Free":<15} {"Starter":<15} {"Professional":<20}')
print('-' * 100)

comparison = [
    ('Organizations', '1', '3', '10'),
    ('Users', '2', '10', '50'),
    ('Expenses/month', '30', '100', '500'),
    ('OCR Scans/month', '20', '100', 'Unlimited'),
    ('AI Categorizations', '0', '50', '200'),
    ('AP2 Transactions', '20', '100', 'Unlimited'),
    ('Data Retention', '90 days', '1 year', '3 years'),
    ('API Access', 'No', 'No', 'Yes'),
    ('Approval Workflows', 'No', 'Yes', 'Yes'),
    ('Advanced Analytics', 'No', 'Yes', 'Yes'),
    ('Price/month', '$0', '$29', '$99'),
]

for feature, free, starter, pro in comparison:
    print(f'{feature:<30} {free:<15} {starter:<15} {pro:<20}')

print('\n' + '=' * 100)

db.close()
