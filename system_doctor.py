#!/usr/bin/env python
"""
AP2 Expense Management System - Health Check
Comprehensive diagnostic tool
"""
import sys
import os
import subprocess
import socket
import requests
from pathlib import Path

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")

def print_check(status, message):
    if status == "OK":
        print(f"{Colors.GREEN}[OK]{Colors.END}     {message}")
    elif status == "WARN":
        print(f"{Colors.YELLOW}[WARN]{Colors.END}   {message}")
    elif status == "FAIL":
        print(f"{Colors.RED}[FAIL]{Colors.END}   {message}")
    else:
        print(f"[INFO]   {message}")

def check_port(port, service_name):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    if result == 0:
        print_check("OK", f"{service_name} is running on port {port}")
        return True
    else:
        print_check("FAIL", f"{service_name} is NOT running on port {port}")
        return False

def check_file(filepath, description):
    if Path(filepath).exists():
        print_check("OK", f"{description}: {filepath}")
        return True
    else:
        print_check("FAIL", f"{description} NOT FOUND: {filepath}")
        return False

def check_directory(dirpath, description):
    path = Path(dirpath)
    if path.exists() and path.is_dir():
        print_check("OK", f"{description}: {dirpath}")
        return True
    else:
        print_check("FAIL", f"{description} NOT FOUND: {dirpath}")
        return False

def check_api_endpoint(url, description):
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print_check("OK", f"{description} - Status: {response.status_code}")
            return True
        else:
            print_check("WARN", f"{description} - Status: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_check("FAIL", f"{description} - Connection refused")
        return False
    except requests.exceptions.Timeout:
        print_check("FAIL", f"{description} - Timeout")
        return False
    except Exception as e:
        print_check("FAIL", f"{description} - Error: {str(e)}")
        return False

def check_database():
    try:
        sys.path.insert(0, 'backend')
        from src.database import SessionLocal
        from src.models import User

        db = SessionLocal()
        user_count = db.query(User).count()
        db.close()

        print_check("OK", f"Database connected - {user_count} users found")
        return True
    except Exception as e:
        print_check("FAIL", f"Database connection failed: {str(e)}")
        return False

def main():
    print_header("AP2 EXPENSE MANAGEMENT - SYSTEM DIAGNOSTIC")

    # Check 1: Project Structure
    print_header("1. PROJECT STRUCTURE")
    backend_ok = check_directory("backend", "Backend directory")
    frontend_ok = check_directory("frontend", "Frontend directory")
    check_file("backend/src/api.py", "Main API file")
    check_file("frontend/src/main.jsx", "Main frontend file")
    check_file("backend/.env", "Backend environment file")

    # Check 2: Backend Server
    print_header("2. BACKEND SERVER (Port 8000)")
    backend_running = check_port(8000, "Backend API")

    if backend_running:
        check_api_endpoint("http://localhost:8000/docs", "API Documentation (/docs)")
        check_api_endpoint("http://localhost:8000/health", "Health endpoint")
    else:
        print_check("WARN", "Backend server is not running. Start with:")
        print(f"        cd backend && .venv\\Scripts\\python.exe -m uvicorn src.api:app --reload")

    # Check 3: Frontend Server
    print_header("3. FRONTEND SERVER (Port 5173)")
    frontend_running = check_port(5173, "Frontend (Vite)")

    if not frontend_running:
        print_check("WARN", "Frontend server is not running. Start with:")
        print(f"        cd frontend && npm run dev")

    # Check 4: Database
    print_header("4. DATABASE")
    check_file("backend/expenses.db", "SQLite database")
    if backend_ok:
        check_database()

    # Check 5: Python Dependencies
    print_header("5. PYTHON ENVIRONMENT")
    check_directory("backend/venv", "Python virtual environment")
    check_directory("backend/.venv", "Python virtual environment (.venv)")

    # Check 6: Node Dependencies
    print_header("6. NODE ENVIRONMENT")
    check_directory("frontend/node_modules", "Node modules")
    check_file("frontend/package.json", "Package.json")

    # Check 7: Test Users
    print_header("7. TEST USERS")
    if backend_running:
        try:
            # Test login
            response = requests.post(
                "http://localhost:8000/api/v1/auth/login",
                json={"username": "adminfree", "password": "Testme1!"},
                timeout=5
            )
            if response.status_code == 200:
                print_check("OK", "Admin user (adminfree) can login")
            else:
                print_check("FAIL", f"Admin login failed: {response.status_code}")
        except Exception as e:
            print_check("FAIL", f"Login test failed: {str(e)}")

    # Summary
    print_header("DIAGNOSTIC SUMMARY")

    issues = []
    if not backend_running:
        issues.append("Backend server not running")
    if not frontend_running:
        issues.append("Frontend server not running")

    if not issues:
        print_check("OK", "All systems operational!")
        print(f"\n{Colors.GREEN}Access the application at: http://localhost:5173{Colors.END}")
        print(f"{Colors.GREEN}API Documentation at: http://localhost:8000/docs{Colors.END}")
    else:
        print_check("WARN", f"Found {len(issues)} issue(s):")
        for issue in issues:
            print(f"        - {issue}")
        print(f"\n{Colors.YELLOW}Run servers using the commands shown above{Colors.END}")

    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
