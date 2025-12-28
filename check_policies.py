from backend.src.database import SessionLocal
from backend.src.models import ApprovalPolicy

db = SessionLocal()
policies = db.query(ApprovalPolicy).filter(ApprovalPolicy.is_active == True).all()

if policies:
    print('Active Auto-Approval Policies:')
    for p in policies:
        print(f'- {p.name}: max amount ${p.max_amount}')
else:
    print('No active auto-approval policies')
    
db.close()
