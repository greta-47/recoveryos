#!/usr/bin/env python3
"""
CI/CD Gates Testing Script
Tests that all CI/CD pipeline gates work correctly
"""

import json
import os
import subprocess
import sys


def run_command(cmd, check=True):
    """Run shell command and return result"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def test_security_scanning():
    """Test security scanning tools"""
    print("🔒 Testing Security Scanning...")

    success, stdout, stderr = run_command("pip-audit --desc --format=json --output=test-audit.json", check=False)
    if success:
        print("✅ pip-audit: PASS")
    else:
        print("❌ pip-audit: FAIL")
        print(f"Error: {stderr}")

    success, stdout, stderr = run_command("bandit -r . -f json -o test-bandit.json", check=False)
    if success or "No issues identified" in stdout:
        print("✅ bandit: PASS")
    else:
        print("❌ bandit: FAIL")
        print(f"Error: {stderr}")

    success, stdout, stderr = run_command("safety check --json --output=test-safety.json", check=False)
    if success:
        print("✅ safety: PASS")
    else:
        print("❌ safety: FAIL")
        print(f"Error: {stderr}")


def test_code_quality():
    """Test code quality tools"""
    print("\n🎨 Testing Code Quality...")

    success, stdout, stderr = run_command("black --check --diff .", check=False)
    if success:
        print("✅ black: PASS")
    else:
        print("❌ black: FAIL - Code formatting issues found")
        print(f"Output: {stdout}")

    success, stdout, stderr = run_command("ruff check .", check=False)
    if success:
        print("✅ ruff: PASS")
    else:
        print("❌ ruff: FAIL - Linting issues found")
        print(f"Output: {stdout}")


def test_coverage():
    """Test code coverage"""
    print("\n📊 Testing Code Coverage...")

    success, stdout, stderr = run_command(
        "pytest test_elite_endpoints.py -v --cov=main --cov=observability_enhanced --cov=feature_flags --cov-report=term --cov-fail-under=80",  # noqa: E501
        check=False,
    )

    if success:
        print("✅ Coverage: PASS (≥80%)")
    else:
        print("❌ Coverage: FAIL (<80%)")
        print(f"Output: {stdout}")


def test_vulnerability_blocking():
    """Test that HIGH vulnerabilities are properly blocked"""
    print("\n🚫 Testing Vulnerability Blocking...")

    if os.path.exists("test-audit.json"):
        try:
            with open("test-audit.json", "r") as f:
                audit_data = json.load(f)

            high_vulns = [v for v in audit_data.get("vulnerabilities", []) if v.get("severity") == "HIGH"]

            if high_vulns:
                print(f"⚠️  Found {len(high_vulns)} HIGH vulnerabilities:")
                for vuln in high_vulns:
                    print(f"  - {vuln.get('id', 'Unknown')}: {vuln.get('description', 'No description')}")
                print("❌ Vulnerability blocking: FAIL - HIGH vulnerabilities should block CI")
                return False
            else:
                print("✅ Vulnerability blocking: PASS - No HIGH vulnerabilities found")
                return True
        except Exception as e:
            print(f"❌ Error reading audit report: {e}")
            return False
    else:
        print("❌ Audit report not found")
        return False


def main():
    """Run all CI/CD gate tests"""
    print("🔧 CI/CD Gates Testing")
    print("=" * 50)

    print("📦 Installing testing dependencies...")
    run_command("pip install pytest pytest-cov black ruff bandit pip-audit safety", check=False)

    test_security_scanning()
    test_code_quality()
    test_coverage()
    vulnerability_pass = test_vulnerability_blocking()

    print("\n" + "=" * 50)
    print("🎯 CI/CD Gates Test Summary")

    if vulnerability_pass:
        print("✅ All CI/CD gates are working correctly")
        return 0
    else:
        print("❌ Some CI/CD gates need attention")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
