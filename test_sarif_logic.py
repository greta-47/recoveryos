#!/usr/bin/env python3
"""Test the SARIF parsing logic locally before pushing to CI"""

import json
import sys


def test_sarif_parsing(sarif_file):
    print(f"Testing SARIF parsing logic with {sarif_file}...")

    with open(sarif_file) as f:
        sarif = json.load(f)

    for run in sarif.get("runs", []):
        rules = run.get("tool", {}).get("driver", {}).get("rules", [])
        rule_lookup = {}
        for rule in rules:
            rule_id = rule.get("id")
            props = rule.get("properties", {})
            if rule_id and "security-severity" in props:
                rule_lookup[rule_id] = float(props["security-severity"])

        print(f"Found {len(rule_lookup)} rules with security-severity")

        critical_found = False
        for result in run.get("results", []):
            rule_id = result.get("ruleId")
            if rule_id in rule_lookup:
                severity = rule_lookup[rule_id]
                print(f"Vulnerability: {rule_id} (severity {severity})")
                if severity >= 9.0:
                    print(
                        f"CRITICAL vulnerability found: {rule_id} (severity {severity})"
                    )
                    critical_found = True

        if critical_found:
            print("RESULT: Would exit 1 (critical vulnerabilities found)")
            return 1
        else:
            print("RESULT: Would exit 0 (no critical vulnerabilities)")

    print("No critical vulnerabilities found")
    return 0


if __name__ == "__main__":
    sarif_file = sys.argv[1] if len(sys.argv) > 1 else "trivy-test.sarif"
    exit_code = test_sarif_parsing(sarif_file)
    sys.exit(exit_code)
