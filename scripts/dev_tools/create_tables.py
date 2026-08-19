"""
Quick script to create all database tables from SQLAlchemy models
This bypasses the migration issues with PostgreSQL-specific code
"""
from backend.src.database import engine, Base
from backend.src.models import *
from backend.src.models_billing import *

print("Creating all tables...")
Base.metadata.create_all(bind=engine)
print("✅ All tables created successfully!")
