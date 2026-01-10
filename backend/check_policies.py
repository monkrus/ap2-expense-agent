from src.database import SessionLocal
from src.models import ApprovalPolicy

db = SessionLocal()
policies = db.query(ApprovalPolicy).all()
print(f'Total Approval Policies: {len(policies)}\n')

for p in policies:
    print(f'Policy: {p.name}')
    print(f'  Auto-approve under: ${p.auto_approve_under if p.auto_approve_under else "None"}')
    print(f'  Is active: {p.is_active}')
    print(f'  Organization: {p.organization_id}')
    print()

db.close()
