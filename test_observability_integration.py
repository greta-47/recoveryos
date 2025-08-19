#!/usr/bin/env python3
"""
Observability Integration Testing Script
Tests metrics, tracing, and PII redaction functionality
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
import time
from observability_enhanced import PIIRedactor
from feature_flags import feature_flags


def test_metrics_endpoint():
    """Test Prometheus metrics endpoint"""
    print("📊 Testing Metrics Endpoint...")

    try:
        response = requests.get("http://localhost:8001/metrics", timeout=10)
        if response.status_code == 200:
            metrics_text = response.text

            expected_metrics = [
                "recoveryos_requests_total",
                "recoveryos_request_duration_seconds",
                "recoveryos_errors_total",
                "recoveryos_active_requests",
            ]

            found_metrics = []
            for metric in expected_metrics:
                if metric in metrics_text:
                    found_metrics.append(metric)

            if len(found_metrics) == len(expected_metrics):
                print("✅ Metrics endpoint: PASS - All expected metrics found")
                assert True
            else:
                print(
                    f"❌ Metrics endpoint: FAIL - Missing metrics: {set(expected_metrics) - set(found_metrics)}"
                )
                assert (
                    False
                ), f"Missing metrics: {set(expected_metrics) - set(found_metrics)}"
        else:
            print(f"❌ Metrics endpoint: FAIL - HTTP {response.status_code}")
            assert False, f"HTTP {response.status_code}"
    except Exception as e:
        print(f"❌ Metrics endpoint: FAIL - {e}")
        assert False, str(e)


def test_elite_metrics_endpoint():
    """Test elite metrics endpoint with feature flag integration"""
    print("📈 Testing Elite Metrics Endpoint...")

    try:
        response = requests.get("http://localhost:8001/elite/metrics", timeout=10)
        if response.status_code == 200:
            data = response.json()

            if feature_flags.is_enabled("enhanced_observability"):
                if "endpoints" in data and "total_requests" in data:
                    print("✅ Elite metrics: PASS - Enhanced metrics returned")
                    assert True
                else:
                    print("❌ Elite metrics: FAIL - Invalid metrics format")
                    assert False, "Invalid metrics format"
            else:
                if "message" in data and "not enabled" in data["message"]:
                    print("✅ Elite metrics: PASS - Feature flag disabled correctly")
                    assert True
                else:
                    print("❌ Elite metrics: FAIL - Feature flag not working")
                    assert False, "Feature flag not working"
        else:
            print(f"❌ Elite metrics: FAIL - HTTP {response.status_code}")
            assert False, f"HTTP {response.status_code}"
    except Exception as e:
        print(f"❌ Elite metrics: FAIL - {e}")
        assert False, str(e)


def test_pii_redaction():
    """Test PII redaction functionality"""
    print("🔒 Testing PII Redaction...")

    test_cases = [
        {
            "input": "Contact john.doe@example.com or call 555-123-4567",
            "expected_redacted": ["[EMAIL_REDACTED]", "[PHONE_REDACTED]"],
        },
        {
            "input": "Patient SSN: 123-45-6789, Medical Record: MRN123456",
            "expected_redacted": ["[SSN_REDACTED]", "[MEDICAL_RECORD_REDACTED]"],
        },
        {
            "input": "Address: 123 Main Street, Credit Card: 4532 1234 5678 9012",
            "expected_redacted": ["[ADDRESS_REDACTED]", "[CARD_REDACTED]"],
        },
    ]

    all_passed = True

    for i, test_case in enumerate(test_cases, 1):
        redacted = PIIRedactor.redact_pii(test_case["input"])

        patterns_found = all(
            pattern in redacted for pattern in test_case["expected_redacted"]
        )

        if patterns_found:
            print(f"✅ PII Test {i}: PASS")
            print(f"   Input:  {test_case['input']}")
            print(f"   Output: {redacted}")
        else:
            print(f"❌ PII Test {i}: FAIL")
            print(f"   Input:  {test_case['input']}")
            print(f"   Output: {redacted}")
            print(f"   Expected patterns: {test_case['expected_redacted']}")
            all_passed = False

    assert all_passed, "Some PII redaction tests failed"


def test_feature_flags():
    """Test feature flag functionality"""
    print("🚩 Testing Feature Flags...")

    try:
        enhanced_enabled = feature_flags.is_enabled("enhanced_observability")
        print(
            f"Enhanced Observability: {'✅ ENABLED' if enhanced_enabled else '❌ DISABLED'}"
        )

        release_enabled = feature_flags.is_enabled("release_20250814")
        print(f"Release 20250814: {'✅ ENABLED' if release_enabled else '❌ DISABLED'}")

        canary_enabled = feature_flags.is_enabled("canary_deployment")
        print(f"Canary Deployment: {'✅ ENABLED' if canary_enabled else '❌ DISABLED'}")

        assert True
    except Exception as e:
        print(f"❌ Feature flags: FAIL - {e}")
        assert False, str(e)


def test_correlation_ids():
    """Test correlation ID generation and tracking"""
    print("🔗 Testing Correlation IDs...")

    try:
        response = requests.post(
            "http://localhost:8001/elite/neuromorphic/process",
            json={"sensor_data": [0.1, 0.2, 0.3]},
            timeout=10,
        )

        correlation_id = response.headers.get("X-Request-ID")

        if correlation_id:
            print(f"✅ Correlation IDs: PASS - ID: {correlation_id}")
            assert True
        else:
            print("❌ Correlation IDs: FAIL - No correlation ID in response")
            assert False, "No correlation ID in response"
    except Exception as e:
        print(f"❌ Correlation IDs: FAIL - {e}")
        assert False, str(e)


def main():
    """Run all observability tests"""
    print("🔍 Observability Integration Testing")
    print("=" * 50)

    print("⏳ Waiting for server to be ready...")
    time.sleep(2)

    tests = [
        test_feature_flags,
        test_pii_redaction,
        test_metrics_endpoint,
        test_elite_metrics_endpoint,
        test_correlation_ids,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()  # Add spacing between tests

    print("=" * 50)
    print(f"🎯 Observability Test Summary: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All observability features working correctly")
        return 0
    else:
        print("❌ Some observability features need attention")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
