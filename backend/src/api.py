from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

from .agent import ExpenseManagementAgent
from .config import settings

app = FastAPI(
    title="AP2 Expense Management Agent",
    description="AI-powered expense management with AP2 protocol",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = ExpenseManagementAgent(
    api_key=settings.google_api_key or os.getenv("GOOGLE_API_KEY", ""),
    project_id=settings.google_cloud_project or os.getenv("GOOGLE_CLOUD_PROJECT", "")
)

class ExpenseSubmission(BaseModel):
    user_id: str
    amount: float
    vendor: str
    category: str
    description: str

class ExpenseApproval(BaseModel):
    expense_id: str
    approver_id: str

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "AP2 Expense Management Agent"}

@app.post("/api/v1/expenses")
async def submit_expense(data: ExpenseSubmission):
    try:
        expense = agent.submit_expense(
            user_id=data.user_id,
            amount=data.amount,
            vendor=data.vendor,
            category=data.category,
            description=data.description
        )
        return {"success": True, "expense": expense}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/expenses/approve")
async def approve_expense(data: ExpenseApproval):
    try:
        result = agent.approve_and_process_expense(
            expense_id=data.expense_id,
            approver_id=data.approver_id
        )
        return {"success": True, "result": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/v1/expenses/report")
async def get_report(user_id: Optional[str] = None):
    report = agent.get_expense_report(user_id)
    return report

@app.get("/api/v1/audit/{transaction_id}")
async def get_audit(transaction_id: str):
    try:
        audit = agent.get_audit_trail(transaction_id)
        return audit
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))