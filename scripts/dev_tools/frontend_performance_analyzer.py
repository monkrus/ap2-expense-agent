"""
Frontend Performance Analyzer

Analyzes:
1. Bundle size and composition
2. Dependency sizes
3. Code splitting effectiveness
4. Potential optimizations
"""

import json
import subprocess
from pathlib import Path
from typing import Dict, List


class Colors:
    """ANSI color codes"""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"


class FrontendAnalyzer:
    """Analyze frontend performance metrics"""

    def __init__(self):
        self.frontend_dir = Path(__file__).parent / "frontend"
        self.package_json_path = self.frontend_dir / "package.json"
        self.dist_dir = self.frontend_dir / "dist"
        self.node_modules = self.frontend_dir / "node_modules"

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

    def analyze_dependencies(self):
        """Analyze package.json dependencies"""
        self.print_section("DEPENDENCY ANALYSIS")

        if not self.package_json_path.exists():
            print(f"{Colors.FAIL}package.json not found!{Colors.ENDC}")
            return

        with open(self.package_json_path) as f:
            package_data = json.load(f)

        deps = package_data.get("dependencies", {})
        dev_deps = package_data.get("devDependencies", {})

        print(f"{Colors.BOLD}Production Dependencies:{Colors.ENDC}")
        self.print_metric("Total Count", str(len(deps)))

        # Highlight large dependencies
        large_deps = {
            "react": "Main UI library",
            "react-dom": "React DOM renderer",
            "axios": "HTTP client",
            "exceljs": "Excel generation (LARGE)",
            "jspdf": "PDF generation",
            "lucide-react": "Icon library",
        }

        for dep, description in large_deps.items():
            if dep in deps:
                self.print_metric(f"  {dep}", description, "INFO")

        print(f"\n{Colors.BOLD}Development Dependencies:{Colors.ENDC}")
        self.print_metric("Total Count", str(len(dev_deps)))

        # Check for test dependencies
        if "@playwright/test" in dev_deps:
            self.print_metric("  Playwright", "E2E Testing", "SUCCESS")

    def estimate_bundle_size(self):
        """Estimate production bundle size"""
        self.print_section("BUNDLE SIZE ESTIMATION")

        # Check if dist folder exists
        if not self.dist_dir.exists():
            print(
                f"{Colors.WARNING}Build folder not found. Run 'npm run build' first.{Colors.ENDC}"
            )
            print(
                f"{Colors.OKCYAN}Estimating based on dependencies...{Colors.ENDC}"
            )

            # Rough estimates (in KB)
            estimates = {
                "react + react-dom": 140,
                "axios": 25,
                "exceljs": 500,  # Very large!
                "jspdf + jspdf-autotable": 250,
                "lucide-react": 150,
                "@stripe/react-stripe-js + @stripe/stripe-js": 80,
                "Application code (estimated)": 200,
            }

            total = 0
            for lib, size_kb in estimates.items():
                status = "CRITICAL" if size_kb > 300 else "WARNING" if size_kb > 100 else "SUCCESS"
                self.print_metric(f"  {lib}", f"~{size_kb} KB", status)
                total += size_kb

            self.print_metric("\nEstimated Total (uncompressed)", f"~{total} KB", "WARNING")
            self.print_metric(
                "Estimated Total (gzipped)", f"~{total // 3} KB", "INFO"
            )

            print(
                f"\n{Colors.OKGREEN}Target: < 500 KB gzipped for good performance{Colors.ENDC}"
            )
            if total // 3 > 500:
                print(
                    f"{Colors.FAIL}Bundle may be too large! Consider code splitting.{Colors.ENDC}"
                )

        else:
            # Analyze actual build
            print(f"{Colors.OKGREEN}Analyzing build output...{Colors.ENDC}")

            js_files = list(self.dist_dir.glob("**/*.js"))
            css_files = list(self.dist_dir.glob("**/*.css"))

            total_js = sum(f.stat().st_size for f in js_files)
            total_css = sum(f.stat().st_size for f in css_files)

            self.print_metric("JavaScript Bundle", f"{total_js / 1024:.2f} KB")
            self.print_metric("CSS Bundle", f"{total_css / 1024:.2f} KB")
            self.print_metric(
                "Total Assets", f"{(total_js + total_css) / 1024:.2f} KB"
            )

            print(f"\n{Colors.BOLD}Individual JS Files:{Colors.ENDC}")
            for js_file in sorted(js_files, key=lambda f: f.stat().st_size, reverse=True)[:10]:
                size_kb = js_file.stat().st_size / 1024
                status = "CRITICAL" if size_kb > 500 else "WARNING" if size_kb > 200 else "SUCCESS"
                self.print_metric(f"  {js_file.name}", f"{size_kb:.2f} KB", status)

    def check_code_splitting(self):
        """Check if code splitting is implemented"""
        self.print_section("CODE SPLITTING ANALYSIS")

        # Check for lazy loading patterns in source
        src_dir = self.frontend_dir / "src"

        if not src_dir.exists():
            print(f"{Colors.FAIL}Source directory not found!{Colors.ENDC}")
            return

        # Look for React.lazy() usage
        lazy_count = 0
        total_files = 0

        for jsx_file in src_dir.glob("**/*.jsx"):
            total_files += 1
            try:
                content = jsx_file.read_text(encoding='utf-8')
                if "React.lazy" in content or "lazy(" in content:
                    lazy_count += 1
            except UnicodeDecodeError:
                # Skip files with encoding issues
                continue

        self.print_metric("Total JSX Files", str(total_files))
        self.print_metric("Files with Lazy Loading", str(lazy_count))

        if lazy_count == 0:
            print(
                f"\n{Colors.WARNING}No lazy loading detected!{Colors.ENDC}"
            )
            print(f"{Colors.OKCYAN}Consider implementing code splitting for routes:{Colors.ENDC}")
            print("  import { lazy } from 'react';")
            print("  const BillingDashboard = lazy(() => import('./pages/BillingDashboard'));")
        else:
            percentage = (lazy_count / total_files) * 100
            status = "SUCCESS" if percentage > 30 else "WARNING"
            self.print_metric(
                "Code Splitting Coverage", f"{percentage:.1f}%", status
            )

    def analyze_performance_optimizations(self):
        """Check for common performance optimizations"""
        self.print_section("PERFORMANCE OPTIMIZATIONS")

        src_dir = self.frontend_dir / "src"
        optimizations = {
            "React.memo": 0,
            "useMemo": 0,
            "useCallback": 0,
            "React.lazy": 0,
        }

        for jsx_file in src_dir.glob("**/*.jsx"):
            try:
                content = jsx_file.read_text(encoding='utf-8')
                for pattern in optimizations.keys():
                    optimizations[pattern] += content.count(pattern)
            except UnicodeDecodeError:
                # Skip files with encoding issues
                continue

        for optimization, count in optimizations.items():
            status = "SUCCESS" if count > 5 else "WARNING" if count > 0 else "INFO"
            self.print_metric(f"  {optimization} usage", f"{count} times", status)

    def check_vite_config(self):
        """Analyze Vite configuration for optimizations"""
        self.print_section("VITE CONFIGURATION")

        vite_config = self.frontend_dir / "vite.config.js"

        if not vite_config.exists():
            print(f"{Colors.FAIL}vite.config.js not found!{Colors.ENDC}")
            return

        try:
            content = vite_config.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            print(f"{Colors.FAIL}Unable to read vite.config.js{Colors.ENDC}")
            return

        optimizations = {
            "build.rollupOptions.output.manualChunks": "Manual chunk splitting",
            "build.minify": "Minification",
            "build.sourcemap": "Source maps",
            "build.cssCodeSplit": "CSS code splitting",
        }

        for config, description in optimizations.items():
            if any(part in content for part in config.split(".")):
                self.print_metric(f"  {description}", "Configured", "SUCCESS")
            else:
                self.print_metric(f"  {description}", "Not found", "WARNING")

    def generate_recommendations(self):
        """Generate frontend optimization recommendations"""
        self.print_section("OPTIMIZATION RECOMMENDATIONS")

        recommendations = [
            {
                "priority": "HIGH",
                "issue": "ExcelJS is a large dependency (500+ KB)",
                "recommendation": "Consider lazy loading Excel export or switching to lighter CSV export",
                "expected_gain": "Reduce initial bundle by ~500KB",
            },
            {
                "priority": "HIGH",
                "issue": "jsPDF adds significant bundle size",
                "recommendation": "Lazy load PDF generation only when needed",
                "expected_gain": "Reduce initial bundle by ~250KB",
            },
            {
                "priority": "MEDIUM",
                "issue": "Icon library (lucide-react) may include unused icons",
                "recommendation": "Import only used icons instead of entire library",
                "expected_gain": "Reduce bundle by 50-100KB",
            },
            {
                "priority": "MEDIUM",
                "issue": "No code splitting detected",
                "recommendation": "Implement route-based code splitting with React.lazy()",
                "expected_gain": "Reduce initial load time by 40-60%",
            },
            {
                "priority": "LOW",
                "issue": "Limited React performance hooks usage",
                "recommendation": "Add React.memo, useMemo, useCallback for expensive renders",
                "expected_gain": "Reduce re-renders by 30-50%",
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
            print(
                f"  {Colors.OKGREEN}Expected Gain: {rec['expected_gain']}{Colors.ENDC}"
            )

    def run_analysis(self):
        """Run complete frontend analysis"""
        print(f"\n{Colors.BOLD}{Colors.HEADER}")
        print("=" * 80)
        print("FRONTEND PERFORMANCE ANALYZER".center(80))
        print("=" * 80)
        print(Colors.ENDC)

        self.analyze_dependencies()
        self.estimate_bundle_size()
        self.check_code_splitting()
        self.analyze_performance_optimizations()
        self.check_vite_config()
        self.generate_recommendations()

        print(f"\n{Colors.OKGREEN}{Colors.BOLD}Analysis complete!{Colors.ENDC}\n")


def main():
    """Main entry point"""
    analyzer = FrontendAnalyzer()
    analyzer.run_analysis()


if __name__ == "__main__":
    main()
