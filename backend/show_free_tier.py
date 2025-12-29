"""Display all free tier limits and features"""
import json
from src.database import SessionLocal
from src.models_billing import BillingTier

db = SessionLocal()

# Get free tier (lowercase)
free_tier = db.query(BillingTier).filter(BillingTier.tier_name == 'free').first()

if not free_tier:
    print("ERROR: Free tier not found in database!")
    db.close()
    exit(1)

print('\n' + '=' * 80)
print('FREE TIER - COMPLETE LIMITS & FEATURES')
print('=' * 80 + '\n')

print(f'Tier Name:      {free_tier.tier_name}')
print(f'Display Name:   {free_tier.display_name}')
print(f'Monthly Price:  ${free_tier.base_price_monthly:.2f} {free_tier.currency}')
print(f'Description:    {free_tier.description}')
print(f'Active:         {free_tier.is_active}')
print(f'Public:         {free_tier.is_public}')

print('\n' + '-' * 80)
print('RESOURCE LIMITS')
print('-' * 80)

# Parse limits JSON
limits = free_tier.limits if isinstance(free_tier.limits, dict) else json.loads(free_tier.limits or '{}')
for key, value in sorted(limits.items()):
    key_formatted = key.replace('_', ' ').title()
    print(f'  {key_formatted:<30} {value}')

print('\n' + '-' * 80)
print('FEATURES INCLUDED')
print('-' * 80)

# Parse features JSON
features = free_tier.features if isinstance(free_tier.features, list) else json.loads(free_tier.features or '[]')
if isinstance(features, list):
    for feature in features:
        print(f'  [OK] {feature}')
elif isinstance(features, dict):
    for key, value in sorted(features.items()):
        status = "[OK]" if value else "[X]"
        key_formatted = key.replace('_', ' ').title()
        print(f'  {status} {key_formatted}')

print('\n' + '-' * 80)
print('OVERAGE PRICING')
print('-' * 80)

# Parse overage pricing JSON
overage = free_tier.overage_pricing if isinstance(free_tier.overage_pricing, dict) else json.loads(free_tier.overage_pricing or '{}')
if overage:
    for key, value in sorted(overage.items()):
        key_formatted = key.replace('_', ' ').title()
        print(f'  {key_formatted:<30} ${value}')
else:
    print('  No overage pricing (hard limits)')

print('\n' + '=' * 80)

db.close()
