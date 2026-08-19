"""
Database Query Performance Profiler

Analyzes:
1. Slow queries
2. Missing indexes
3. Table statistics
4. N+1 query detection
5. Query execution plans
"""

import time
from pathlib import Path
from typing import Dict, List

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker


class Colors:
    """ANSI color codes"""

    HEADER = "\033[95m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    OKCYAN = "\033[96m"


class DatabaseProfiler:
    """Profile database query performance"""

    def __init__(self):
        self.db_path = Path(__file__).parent / "backend" / "expense_tracker.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.Session = sessionmaker(bind=self.engine)
        self.query_log: List[Dict] = []

        # Set up query logging
        @event.listens_for(self.engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            context._query_start_time = time.perf_counter()

        @event.listens_for(self.engine, "after_cursor_execute")
        def receive_after_cursor_execute(
            conn, cursor, statement, parameters, context, executemany
        ):
            elapsed = (time.perf_counter() - context._query_start_time) * 1000
            self.query_log.append(
                {
                    "query": statement[:200],
                    "time_ms": elapsed,
                    "parameters": str(parameters)[:100] if parameters else None,
                }
            )

    def print_section(self, title: str):
        """Print formatted section header"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{title.center(80)}{Colors.ENDC}")
        print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 80}{Colors.ENDC}\n")

    def print_metric(self, name: str, value: str, status: str = "INFO"):
        """Print formatted metric"""
        color = {
            "SUCCESS": Colors.OKGREEN,
            "WARNING": Colors.WARNING,
            "CRITICAL": Colors.FAIL,
            "INFO": Colors.OKCYAN,
        }.get(status, Colors.ENDC)
        print(f"{color}{name:.<50} {value:>28}{Colors.ENDC}")

    def analyze_table_statistics(self):
        """Analyze table sizes and row counts"""
        self.print_section("TABLE STATISTICS")

        session = self.Session()

        # Get all tables
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        tables = session.execute(text(tables_query)).fetchall()

        stats = []
        for (table_name,) in tables:
            # Get row count
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count = session.execute(text(count_query)).scalar()

            # Get table size (approximate)
            size_query = f"SELECT SUM(pgsize) FROM dbstat WHERE name='{table_name}'"
            size = session.execute(text(size_query)).scalar() or 0

            stats.append(
                {
                    "table": table_name,
                    "rows": count,
                    "size_kb": size / 1024,
                }
            )

        # Sort by size
        stats.sort(key=lambda x: x["size_kb"], reverse=True)

        print(f"{Colors.BOLD}Table Sizes (sorted by size):{Colors.ENDC}")
        for stat in stats:
            status = "WARNING" if stat["rows"] > 10000 else "SUCCESS"
            print(
                f"{Colors.OKCYAN}  {stat['table']:.<40} "
                f"{stat['rows']:>10} rows  "
                f"{stat['size_kb']:>10.2f} KB{Colors.ENDC}"
            )

        session.close()

    def analyze_indexes(self):
        """Analyze table indexes"""
        self.print_section("INDEX ANALYSIS")

        session = self.Session()

        # Get all tables
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        tables = session.execute(text(tables_query)).fetchall()

        for (table_name,) in tables:
            # Get indexes for this table
            index_query = f"PRAGMA index_list({table_name})"
            indexes = session.execute(text(index_query)).fetchall()

            if indexes:
                print(f"\n{Colors.BOLD}{table_name}:{Colors.ENDC}")
                for idx in indexes:
                    index_name = idx[1]
                    is_unique = "UNIQUE" if idx[2] else "NON-UNIQUE"

                    # Get index columns
                    col_query = f"PRAGMA index_info({index_name})"
                    columns = session.execute(text(col_query)).fetchall()
                    col_names = ", ".join(col[2] for col in columns)

                    self.print_metric(
                        f"  {index_name}", f"{is_unique} ({col_names})", "SUCCESS"
                    )
            else:
                self.print_metric(f"{table_name}", "NO INDEXES", "WARNING")

        session.close()

    def check_missing_indexes(self):
        """Check for commonly missing indexes"""
        self.print_section("MISSING INDEX RECOMMENDATIONS")

        session = self.Session()

        # Common foreign key patterns that should have indexes
        recommendations = []

        # Check organizations table
        tables_query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        tables = session.execute(text(tables_query)).fetchall()

        for (table_name,) in tables:
            # Get table schema
            pragma_query = f"PRAGMA table_info({table_name})"
            columns = session.execute(text(pragma_query)).fetchall()

            for col in columns:
                col_name = col[1]

                # Check if this looks like a foreign key
                if col_name.endswith("_id") or col_name == "user_id" or col_name == "organization_id":
                    # Check if there's an index on this column
                    index_query = f"PRAGMA index_list({table_name})"
                    indexes = session.execute(text(index_query)).fetchall()

                    has_index = False
                    for idx in indexes:
                        index_name = idx[1]
                        col_query = f"PRAGMA index_info({index_name})"
                        idx_columns = session.execute(text(col_query)).fetchall()

                        if any(ic[2] == col_name for ic in idx_columns):
                            has_index = True
                            break

                    if not has_index:
                        recommendations.append(
                            {
                                "table": table_name,
                                "column": col_name,
                                "reason": "Foreign key without index",
                            }
                        )

        if recommendations:
            print(f"{Colors.WARNING}Recommended indexes to add:{Colors.ENDC}\n")
            for rec in recommendations:
                print(
                    f"{Colors.WARNING}  CREATE INDEX idx_{rec['table']}_{rec['column']} "
                    f"ON {rec['table']}({rec['column']});{Colors.ENDC}"
                )
                print(f"    Reason: {rec['reason']}")
        else:
            print(f"{Colors.OKGREEN}All foreign keys are indexed!{Colors.ENDC}")

        session.close()

    def analyze_query_performance(self):
        """Analyze logged query performance"""
        self.print_section("QUERY PERFORMANCE ANALYSIS")

        if not self.query_log:
            print(f"{Colors.WARNING}No queries logged yet{Colors.ENDC}")
            return

        # Sort by execution time
        slow_queries = sorted(self.query_log, key=lambda q: q["time_ms"], reverse=True)

        total_time = sum(q["time_ms"] for q in self.query_log)
        avg_time = total_time / len(self.query_log)

        self.print_metric("Total Queries", str(len(self.query_log)))
        self.print_metric("Total Time", f"{total_time:.2f}ms")
        self.print_metric("Average Time", f"{avg_time:.2f}ms")

        print(f"\n{Colors.BOLD}Slowest Queries:{Colors.ENDC}")
        for i, query in enumerate(slow_queries[:10], 1):
            time_ms = query["time_ms"]
            status = "CRITICAL" if time_ms > 100 else "WARNING" if time_ms > 50 else "SUCCESS"

            print(f"\n{Colors.BOLD}#{i} - {time_ms:.2f}ms{Colors.ENDC}")
            print(f"  {query['query'][:150]}...")

    def simulate_common_queries(self):
        """Run common queries to profile them"""
        self.print_section("PROFILING COMMON QUERIES")

        session = self.Session()

        queries = [
            ("Get active organizations", "SELECT * FROM organizations WHERE is_active = 1"),
            ("Get organization members", "SELECT * FROM organization_members WHERE is_active = 1"),
            ("Get expenses", "SELECT * FROM expenses LIMIT 100"),
            ("Join organizations + members",
             "SELECT o.*, om.role FROM organizations o "
             "JOIN organization_members om ON o.id = om.organization_id "
             "WHERE o.is_active = 1 LIMIT 100"),
        ]

        for name, query in queries:
            start = time.perf_counter()
            try:
                result = session.execute(text(query)).fetchall()
                elapsed = (time.perf_counter() - start) * 1000

                status = "CRITICAL" if elapsed > 100 else "WARNING" if elapsed > 50 else "SUCCESS"
                self.print_metric(
                    f"{name} ({len(result)} rows)", f"{elapsed:.2f}ms", status
                )
            except Exception as e:
                print(f"{Colors.FAIL}  Error: {e}{Colors.ENDC}")

        session.close()

    def check_n_plus_one_patterns(self):
        """Check for N+1 query patterns"""
        self.print_section("N+1 QUERY DETECTION")

        print(f"{Colors.OKCYAN}Checking query patterns...{Colors.ENDC}\n")

        # Look for repeated similar queries
        query_patterns = {}
        for query in self.query_log:
            # Simplify query to pattern (remove specific IDs)
            pattern = query["query"]
            for char in ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]:
                pattern = pattern.replace(char, "?")

            if pattern in query_patterns:
                query_patterns[pattern] += 1
            else:
                query_patterns[pattern] = 1

        # Find patterns that repeat many times
        n_plus_one = [
            (pattern, count)
            for pattern, count in query_patterns.items()
            if count > 5
        ]

        if n_plus_one:
            print(f"{Colors.WARNING}Potential N+1 queries detected:{Colors.ENDC}\n")
            for pattern, count in sorted(n_plus_one, key=lambda x: x[1], reverse=True):
                print(f"{Colors.WARNING}Executed {count} times:{Colors.ENDC}")
                print(f"  {pattern[:150]}...\n")
        else:
            print(f"{Colors.OKGREEN}No obvious N+1 query patterns detected{Colors.ENDC}")

    def analyze_query_plans(self):
        """Analyze query execution plans"""
        self.print_section("QUERY EXECUTION PLANS")

        session = self.Session()

        # Test a few common queries with EXPLAIN QUERY PLAN
        test_queries = [
            "SELECT * FROM organizations WHERE is_active = 1",
            "SELECT * FROM expenses WHERE organization_id = '123'",
            "SELECT o.*, om.role FROM organizations o JOIN organization_members om ON o.id = om.organization_id WHERE o.is_active = 1",
        ]

        for query in test_queries:
            print(f"\n{Colors.BOLD}Query:{Colors.ENDC} {query[:100]}...")
            print(f"{Colors.OKCYAN}Execution Plan:{Colors.ENDC}")

            try:
                plan = session.execute(text(f"EXPLAIN QUERY PLAN {query}")).fetchall()
                for row in plan:
                    detail = row[3] if len(row) > 3 else str(row)

                    # Check for performance issues
                    if "SCAN" in detail and "INDEX" not in detail:
                        print(f"{Colors.WARNING}  {detail} (TABLE SCAN - SLOW!){Colors.ENDC}")
                    elif "INDEX" in detail:
                        print(f"{Colors.OKGREEN}  {detail} (Using index - GOOD){Colors.ENDC}")
                    else:
                        print(f"  {detail}")
            except Exception as e:
                print(f"{Colors.FAIL}  Error: {e}{Colors.ENDC}")

        session.close()

    def generate_recommendations(self):
        """Generate database optimization recommendations"""
        self.print_section("DATABASE OPTIMIZATION RECOMMENDATIONS")

        recommendations = [
            {
                "priority": "HIGH",
                "issue": "No query result caching",
                "recommendation": "Implement Redis caching for frequently accessed data (organizations, user profiles)",
                "implementation": "Use backend/src/cache.py and add caching decorators to repository methods",
                "expected_gain": "70-90% reduction for cached queries",
            },
            {
                "priority": "HIGH",
                "issue": "Potential N+1 queries in organization member lookups",
                "recommendation": "Use SQLAlchemy joinedload() or selectinload() for eager loading",
                "implementation": "query(Expense).options(joinedload(Expense.user)).all()",
                "expected_gain": "Reduce queries from N+1 to 2 queries",
            },
            {
                "priority": "MEDIUM",
                "issue": "No database connection pooling limits set",
                "recommendation": "Configure SQLAlchemy pool_size and max_overflow",
                "implementation": "create_engine(..., pool_size=20, max_overflow=10)",
                "expected_gain": "Better connection management under load",
            },
            {
                "priority": "MEDIUM",
                "issue": "SQLite for production",
                "recommendation": "Migrate to PostgreSQL for better concurrency and performance",
                "implementation": "Update DATABASE_URL in production environment",
                "expected_gain": "Better concurrent write performance, full-text search",
            },
            {
                "priority": "LOW",
                "issue": "No query timeout protection",
                "recommendation": "Add statement timeout to prevent long-running queries",
                "implementation": "SET statement_timeout = '10s' (PostgreSQL) or use SQLAlchemy timeout",
                "expected_gain": "Prevent resource exhaustion from slow queries",
            },
        ]

        for rec in recommendations:
            color = {
                "HIGH": Colors.WARNING,
                "MEDIUM": Colors.OKCYAN,
                "LOW": Colors.ENDC,
            }.get(rec["priority"], Colors.ENDC)

            print(f"\n{color}[{rec['priority']}]{Colors.ENDC}")
            print(f"  Issue: {rec['issue']}")
            print(f"  Recommendation: {rec['recommendation']}")
            print(f"  Implementation: {rec['implementation']}")
            print(
                f"  {Colors.OKGREEN}Expected Gain: {rec['expected_gain']}{Colors.ENDC}"
            )

    def run_full_profile(self):
        """Run complete database profiling"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("=" * 80)
        print("DATABASE QUERY PROFILER".center(80))
        print("=" * 80)
        print(Colors.ENDC)

        self.analyze_table_statistics()
        self.analyze_indexes()
        self.check_missing_indexes()
        self.simulate_common_queries()
        self.analyze_query_performance()
        self.check_n_plus_one_patterns()
        self.analyze_query_plans()
        self.generate_recommendations()

        print(f"\n{Colors.OKGREEN}{Colors.BOLD}Database profiling complete!{Colors.ENDC}\n")


def main():
    """Main entry point"""
    profiler = DatabaseProfiler()
    profiler.run_full_profile()


if __name__ == "__main__":
    main()
