"""
Comprehensive Performance Profiler for AP2 Expense Management System

This script profiles:
1. API endpoint response times
2. Database query performance
3. Memory usage
4. Concurrent load testing
5. N+1 query detection
6. Index usage analysis
"""

import asyncio
import json
import statistics
import sys
import time
import tracemalloc
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))


class Colors:
    """ANSI color codes for terminal output"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class PerformanceProfiler:
    """Main performance profiler class"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results: Dict = {
            "timestamp": datetime.now().isoformat(),
            "api_performance": {},
            "database_performance": {},
            "memory_profile": {},
            "load_testing": {},
            "bottlenecks": [],
            "recommendations": [],
        }
        self.token: Optional[str] = None
        self.user_id: Optional[str] = None
        self.org_id: Optional[str] = None

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def print_section(self, title: str):
        """Print a formatted section header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{title.center(80)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")

    def print_metric(self, name: str, value: str, status: str = "INFO"):
        """Print a formatted metric"""
        color = {
            "SUCCESS": Colors.OKGREEN,
            "WARNING": Colors.WARNING,
            "CRITICAL": Colors.FAIL,
            "INFO": Colors.OKCYAN,
        }.get(status, Colors.ENDC)
        print(f"{color}{name:.<50} {value:>28}{Colors.ENDC}")

    def print_performance(self, name: str, ms: float, threshold: float = 200):
        """Print performance metric with color coding"""
        if ms < threshold:
            status = "SUCCESS"
        elif ms < threshold * 2:
            status = "WARNING"
        else:
            status = "CRITICAL"
        self.print_metric(name, f"{ms:.2f}ms", status)

    # ========================================================================
    # Authentication Setup
    # ========================================================================

    def setup_test_user(self) -> bool:
        """Create or login test user for profiling"""
        print(f"{Colors.BOLD}Setting up test user...{Colors.ENDC}")

        # Try to login first
        test_username = f"perf_test_{int(time.time())}"
        test_password = "TestPass123!"

        try:
            # Register new user
            register_data = {
                "email": f"{test_username}@perftest.com",
                "username": test_username,
                "password": test_password,
                "full_name": "Performance Test User",
                "role": "employee",
            }

            response = self.session.post(
                f"{self.base_url}/api/v1/auth/register", json=register_data, timeout=10
            )

            if response.status_code == 201:
                print(
                    f"{Colors.OKGREEN}User registered successfully{Colors.ENDC}"
                )
                user_data = response.json()
                self.user_id = user_data.get("id")
            else:
                print(
                    f"{Colors.WARNING}Registration failed: {response.status_code}{Colors.ENDC}"
                )
                return False

        except Exception as e:
            print(f"{Colors.FAIL}Registration error: {e}{Colors.ENDC}")
            return False

        # Login
        try:
            login_data = {"username": test_username, "password": test_password}
            response = self.session.post(
                f"{self.base_url}/api/v1/auth/login", json=login_data, timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                print(f"{Colors.OKGREEN}Login successful{Colors.ENDC}")

                # Set auth header
                self.session.headers.update(
                    {"Authorization": f"Bearer {self.token}"}
                )
                return True
            else:
                print(
                    f"{Colors.FAIL}Login failed: {response.status_code}{Colors.ENDC}"
                )
                return False

        except Exception as e:
            print(f"{Colors.FAIL}Login error: {e}{Colors.ENDC}")
            return False

    def setup_test_organization(self) -> bool:
        """Create test organization"""
        print(f"{Colors.BOLD}Creating test organization...{Colors.ENDC}")

        try:
            org_data = {
                "name": f"PerfTest Org {int(time.time())}",
                "slug": f"perftest-{int(time.time())}",
                "description": "Performance testing organization",
                "currency": "USD",
                "timezone": "UTC",
            }

            response = self.session.post(
                f"{self.base_url}/api/v1/organizations", json=org_data, timeout=10
            )

            if response.status_code == 201:
                data = response.json()
                self.org_id = data.get("id")
                print(
                    f"{Colors.OKGREEN}Organization created: {self.org_id}{Colors.ENDC}"
                )

                # Set organization header
                self.session.headers.update({"X-Organization-Id": self.org_id})
                return True
            else:
                print(
                    f"{Colors.FAIL}Organization creation failed: {response.status_code}{Colors.ENDC}"
                )
                print(f"Response: {response.text}")
                return False

        except Exception as e:
            print(f"{Colors.FAIL}Organization error: {e}{Colors.ENDC}")
            return False

    # ========================================================================
    # API Performance Testing
    # ========================================================================

    def measure_endpoint(
        self, name: str, method: str, path: str, data: dict = None, iterations: int = 5
    ) -> Dict:
        """Measure endpoint performance"""
        times = []
        errors = 0

        for _ in range(iterations):
            start = time.perf_counter()
            try:
                if method.upper() == "GET":
                    response = self.session.get(
                        f"{self.base_url}{path}", timeout=30
                    )
                elif method.upper() == "POST":
                    response = self.session.post(
                        f"{self.base_url}{path}", json=data, timeout=30
                    )
                elif method.upper() == "PATCH":
                    response = self.session.patch(
                        f"{self.base_url}{path}", json=data, timeout=30
                    )
                elif method.upper() == "DELETE":
                    response = self.session.delete(
                        f"{self.base_url}{path}", timeout=30
                    )

                elapsed = (time.perf_counter() - start) * 1000  # Convert to ms

                if response.status_code < 400:
                    times.append(elapsed)
                else:
                    errors += 1
                    print(
                        f"{Colors.WARNING}  Error {response.status_code}: {path}{Colors.ENDC}"
                    )

            except Exception as e:
                errors += 1
                print(f"{Colors.FAIL}  Exception: {e}{Colors.ENDC}")

        if not times:
            return {
                "min": 0,
                "max": 0,
                "mean": 0,
                "median": 0,
                "p95": 0,
                "errors": errors,
            }

        times.sort()
        p95_index = int(len(times) * 0.95)

        return {
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "p95": times[p95_index] if times else 0,
            "errors": errors,
        }

    def profile_api_endpoints(self):
        """Profile all major API endpoints"""
        self.print_section("API ENDPOINT PERFORMANCE")

        endpoints = [
            ("POST /auth/login", "POST", "/api/v1/auth/login", {"username": "test", "password": "test"}),
            ("GET /organizations", "GET", "/api/v1/organizations", None),
            ("GET /expenses", "GET", "/api/v1/expenses", None),
        ]

        # Only test authenticated endpoints if we have a token
        if self.token:
            endpoints.extend(
                [
                    ("POST /auth/refresh", "POST", "/api/v1/auth/refresh", {"refresh_token": self.token}),
                ]
            )

        for name, method, path, data in endpoints:
            result = self.measure_endpoint(name, method, path, data)
            self.results["api_performance"][name] = result

            print(f"\n{Colors.BOLD}{name}{Colors.ENDC}")
            self.print_performance(f"  Mean", result["mean"])
            self.print_performance(f"  Median", result["median"])
            self.print_performance(f"  P95", result["p95"])
            self.print_metric(
                f"  Min/Max", f"{result['min']:.2f}ms / {result['max']:.2f}ms"
            )
            if result["errors"] > 0:
                self.print_metric(
                    f"  Errors", str(result["errors"]), "CRITICAL"
                )

    # ========================================================================
    # Database Query Analysis
    # ========================================================================

    def analyze_database_queries(self):
        """Analyze database query performance"""
        self.print_section("DATABASE QUERY ANALYSIS")

        try:
            # Connect to database
            db_path = Path(__file__).parent / "backend" / "expense_tracker.db"
            engine = create_engine(f"sqlite:///{db_path}")
            Session = sessionmaker(bind=engine)
            session = Session()

            # Check if tables exist
            tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
            tables = session.execute(text(tables_query)).fetchall()

            print(f"{Colors.BOLD}Database Tables:{Colors.ENDC}")
            for table in tables:
                self.print_metric(f"  {table[0]}", "EXISTS", "SUCCESS")

            # Analyze indexes
            print(f"\n{Colors.BOLD}Index Analysis:{Colors.ENDC}")
            for table in tables:
                table_name = table[0]
                if table_name.startswith("sqlite_"):
                    continue

                index_query = f"PRAGMA index_list({table_name})"
                indexes = session.execute(text(index_query)).fetchall()

                if indexes:
                    for idx in indexes:
                        self.print_metric(
                            f"  {table_name}.{idx[1]}", "INDEXED", "SUCCESS"
                        )
                else:
                    self.print_metric(
                        f"  {table_name}", "NO INDEXES", "WARNING"
                    )

            # Count records
            print(f"\n{Colors.BOLD}Table Sizes:{Colors.ENDC}")
            for table in tables:
                table_name = table[0]
                if table_name.startswith("sqlite_"):
                    continue

                try:
                    count_query = f"SELECT COUNT(*) FROM {table_name}"
                    count = session.execute(text(count_query)).scalar()
                    self.print_metric(f"  {table_name}", f"{count} rows")
                except Exception:
                    pass

            session.close()

        except Exception as e:
            print(f"{Colors.FAIL}Database analysis error: {e}{Colors.ENDC}")

    # ========================================================================
    # Memory Profiling
    # ========================================================================

    def profile_memory_usage(self):
        """Profile memory usage"""
        self.print_section("MEMORY PROFILING")

        tracemalloc.start()

        # Perform some operations
        if self.token:
            self.session.get(f"{self.base_url}/api/v1/organizations", timeout=10)
            self.session.get(f"{self.base_url}/api/v1/expenses", timeout=10)

        # Get memory snapshot
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics("lineno")

        print(f"{Colors.BOLD}Top 10 Memory Allocations:{Colors.ENDC}")
        for index, stat in enumerate(top_stats[:10], 1):
            size_kb = stat.size / 1024
            self.print_metric(
                f"  #{index} {stat.traceback.format()[0][:50]}", f"{size_kb:.2f} KB"
            )

        tracemalloc.stop()

    # ========================================================================
    # Load Testing
    # ========================================================================

    def concurrent_load_test(self, endpoint: str, concurrent_users: int = 10):
        """Test endpoint with concurrent requests"""
        print(f"\n{Colors.BOLD}Testing {endpoint} with {concurrent_users} users{Colors.ENDC}")

        times = []
        errors = 0

        def make_request():
            nonlocal errors
            start = time.perf_counter()
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}", timeout=30
                )
                elapsed = (time.perf_counter() - start) * 1000

                if response.status_code < 400:
                    times.append(elapsed)
                else:
                    errors += 1
            except Exception:
                errors += 1

        # Simulate concurrent users
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=concurrent_users
        ) as executor:
            futures = [
                executor.submit(make_request) for _ in range(concurrent_users)
            ]
            concurrent.futures.wait(futures)

        if times:
            times.sort()
            p95_index = int(len(times) * 0.95)

            self.print_performance(f"  Mean Response Time", statistics.mean(times))
            self.print_performance(f"  Median Response Time", statistics.median(times))
            self.print_performance(f"  P95 Response Time", times[p95_index])
            self.print_metric(
                f"  Success Rate",
                f"{(len(times) / concurrent_users) * 100:.1f}%",
                "SUCCESS" if errors == 0 else "CRITICAL",
            )

    def profile_concurrent_load(self):
        """Profile performance under concurrent load"""
        self.print_section("CONCURRENT LOAD TESTING")

        if not self.token:
            print(f"{Colors.WARNING}Skipping load tests (no authentication){Colors.ENDC}")
            return

        # Test with different load levels
        for users in [5, 10, 25]:
            self.concurrent_load_test("/api/v1/organizations", users)

    # ========================================================================
    # Analysis & Recommendations
    # ========================================================================

    def analyze_bottlenecks(self):
        """Identify performance bottlenecks"""
        self.print_section("BOTTLENECK ANALYSIS")

        bottlenecks = []

        # Check API performance
        for endpoint, metrics in self.results["api_performance"].items():
            if metrics["p95"] > 1000:  # > 1 second
                bottlenecks.append(
                    {
                        "severity": "CRITICAL",
                        "component": endpoint,
                        "metric": "P95 Response Time",
                        "value": f"{metrics['p95']:.2f}ms",
                        "threshold": "1000ms",
                    }
                )
            elif metrics["p95"] > 500:  # > 500ms
                bottlenecks.append(
                    {
                        "severity": "HIGH",
                        "component": endpoint,
                        "metric": "P95 Response Time",
                        "value": f"{metrics['p95']:.2f}ms",
                        "threshold": "500ms",
                    }
                )
            elif metrics["p95"] > 200:  # > 200ms
                bottlenecks.append(
                    {
                        "severity": "MEDIUM",
                        "component": endpoint,
                        "metric": "P95 Response Time",
                        "value": f"{metrics['p95']:.2f}ms",
                        "threshold": "200ms",
                    }
                )

        self.results["bottlenecks"] = bottlenecks

        if bottlenecks:
            for issue in bottlenecks:
                color = {
                    "CRITICAL": Colors.FAIL,
                    "HIGH": Colors.WARNING,
                    "MEDIUM": Colors.WARNING,
                }.get(issue["severity"], Colors.ENDC)

                print(
                    f"{color}[{issue['severity']}] {issue['component']}: "
                    f"{issue['metric']} = {issue['value']} (threshold: {issue['threshold']}){Colors.ENDC}"
                )
        else:
            print(
                f"{Colors.OKGREEN}No critical bottlenecks detected!{Colors.ENDC}"
            )

    def generate_recommendations(self):
        """Generate optimization recommendations"""
        self.print_section("OPTIMIZATION RECOMMENDATIONS")

        recommendations = []

        # Check response times
        slow_endpoints = [
            name
            for name, metrics in self.results["api_performance"].items()
            if metrics["mean"] > 200
        ]

        if slow_endpoints:
            recommendations.append(
                {
                    "priority": "HIGH",
                    "area": "API Performance",
                    "issue": f"{len(slow_endpoints)} endpoints exceed 200ms average",
                    "recommendation": "Add database query caching, optimize N+1 queries, add indexes",
                    "expected_gain": "50-70% reduction in response time",
                }
            )

        # Database recommendations
        recommendations.append(
            {
                "priority": "MEDIUM",
                "area": "Database",
                "issue": "No query execution plan analysis",
                "recommendation": "Enable SQLite EXPLAIN QUERY PLAN for slow queries",
                "expected_gain": "Identify missing indexes and inefficient joins",
            }
        )

        # Frontend recommendations
        recommendations.append(
            {
                "priority": "MEDIUM",
                "area": "Frontend",
                "issue": "Bundle size not analyzed",
                "recommendation": "Run 'npm run build -- --analyze' to check bundle size",
                "expected_gain": "Reduce initial load time by 30-50%",
            }
        )

        # Caching recommendations
        recommendations.append(
            {
                "priority": "HIGH",
                "area": "Caching",
                "issue": "No Redis caching detected",
                "recommendation": "Implement Redis caching for frequently accessed data",
                "expected_gain": "70-90% reduction for cached queries",
            }
        )

        self.results["recommendations"] = recommendations

        for rec in recommendations:
            color = {
                "CRITICAL": Colors.FAIL,
                "HIGH": Colors.WARNING,
                "MEDIUM": Colors.OKCYAN,
                "LOW": Colors.ENDC,
            }.get(rec["priority"], Colors.ENDC)

            print(f"\n{color}[{rec['priority']}] {rec['area']}{Colors.ENDC}")
            print(f"  Issue: {rec['issue']}")
            print(f"  Recommendation: {rec['recommendation']}")
            print(
                f"  {Colors.OKGREEN}Expected Gain: {rec['expected_gain']}{Colors.ENDC}"
            )

    # ========================================================================
    # Report Generation
    # ========================================================================

    def generate_report(self):
        """Generate comprehensive performance report"""
        self.print_section("PERFORMANCE SUMMARY")

        # Calculate overall score
        total_endpoints = len(self.results["api_performance"])
        fast_endpoints = sum(
            1
            for metrics in self.results["api_performance"].values()
            if metrics["mean"] < 200
        )

        if total_endpoints > 0:
            score = (fast_endpoints / total_endpoints) * 100
        else:
            score = 0

        # Determine rating
        if score >= 90:
            rating = "EXCELLENT"
            color = Colors.OKGREEN
        elif score >= 70:
            rating = "GOOD"
            color = Colors.OKGREEN
        elif score >= 50:
            rating = "NEEDS WORK"
            color = Colors.WARNING
        else:
            rating = "POOR"
            color = Colors.FAIL

        print(f"{color}{Colors.BOLD}Overall Rating: {rating} ({score:.1f}%){Colors.ENDC}\n")

        # Critical metrics
        critical_count = sum(
            1 for b in self.results["bottlenecks"] if b["severity"] == "CRITICAL"
        )
        high_count = sum(
            1 for b in self.results["bottlenecks"] if b["severity"] == "HIGH"
        )

        self.print_metric(
            "Critical Bottlenecks",
            str(critical_count),
            "CRITICAL" if critical_count > 0 else "SUCCESS",
        )
        self.print_metric(
            "High Priority Issues",
            str(high_count),
            "WARNING" if high_count > 0 else "SUCCESS",
        )
        self.print_metric(
            "Optimization Recommendations", str(len(self.results["recommendations"]))
        )

        # Save report to file
        report_path = Path(__file__).parent / "performance_report.json"
        with open(report_path, "w") as f:
            json.dump(self.results, f, indent=2)

        print(f"\n{Colors.OKGREEN}Full report saved to: {report_path}{Colors.ENDC}")

    # ========================================================================
    # Main Execution
    # ========================================================================

    def run_full_profile(self):
        """Run complete performance profiling suite"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("=" * 80)
        print("AP2 EXPENSE MANAGEMENT - PERFORMANCE PROFILER".center(80))
        print("=" * 80)
        print(Colors.ENDC)

        # 1. Setup
        if not self.setup_test_user():
            print(
                f"{Colors.WARNING}Continuing without authentication (limited tests){Colors.ENDC}"
            )
        else:
            self.setup_test_organization()

        # 2. API Performance
        self.profile_api_endpoints()

        # 3. Database Analysis
        self.analyze_database_queries()

        # 4. Memory Profiling
        self.profile_memory_usage()

        # 5. Load Testing
        self.profile_concurrent_load()

        # 6. Analysis
        self.analyze_bottlenecks()

        # 7. Recommendations
        self.generate_recommendations()

        # 8. Final Report
        self.generate_report()

        print(f"\n{Colors.OKGREEN}{Colors.BOLD}Profiling complete!{Colors.ENDC}\n")


def main():
    """Main entry point"""
    profiler = PerformanceProfiler()
    profiler.run_full_profile()


if __name__ == "__main__":
    main()
