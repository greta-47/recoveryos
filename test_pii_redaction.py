#!/usr/bin/env python3
"""
PII Redaction Testing Script
Tests the enhanced observability PII redaction capabilities
"""

import json
from observability_enhanced import PIIRedactor


def test_pii_redaction():
    """Test PII redaction with various sensitive data patterns"""

    test_cases = [
        {
            "name": "Email addresses",
            "input": "Contact john.doe@example.com or support@recoveryos.app for help",
            "expected_patterns": ["[EMAIL_REDACTED]"],
        },
        {
            "name": "Phone numbers",
            "input": "Call us at 555-123-4567 or (555) 987-6543",
            "expected_patterns": ["[PHONE_REDACTED]"],
        },
        {
            "name": "SSN",
            "input": "Patient SSN: 123-45-6789",
            "expected_patterns": ["[SSN_REDACTED]"],
        },
        {
            "name": "Credit card",
            "input": "Card number: 4532 1234 5678 9012",
            "expected_patterns": ["[CARD_REDACTED]"],
        },
        {
            "name": "Medical record",
            "input": "Medical record number: MRN123456",
            "expected_patterns": ["[MEDICAL_RECORD_REDACTED]"],
        },
        {
            "name": "Patient ID",
            "input": "Patient ID: patient_id_789012",
            "expected_patterns": ["[PATIENT_ID_REDACTED]"],
        },
        {
            "name": "Address",
            "input": "Lives at 123 Main Street, Anytown",
            "expected_patterns": ["[ADDRESS_REDACTED]"],
        },
        {
            "name": "Date of birth",
            "input": "DOB: 01/15/1985",
            "expected_patterns": ["[DOB_REDACTED]"],
        },
    ]

    print("🔒 PII Redaction Test Results")
    print("=" * 50)

    all_passed = True

    for test_case in test_cases:
        print(f"\n📝 Test: {test_case['name']}")
        print(f"Input:  {test_case['input']}")

        redacted = PIIRedactor.redact_pii(test_case["input"])
        print(f"Output: {redacted}")

        patterns_found = []
        for pattern in test_case["expected_patterns"]:
            if pattern in redacted:
                patterns_found.append(pattern)

        if patterns_found:
            print(f"✅ PASS - Found redaction patterns: {patterns_found}")
        else:
            print("❌ FAIL - No redaction patterns found")
            all_passed = False

    print("\n📝 Test: Dictionary redaction")
    test_dict = {
        "user_email": "patient@example.com",
        "phone": "555-123-4567",
        "medical_data": {"ssn": "123-45-6789", "patient_id": "patient_id_12345"},
        "notes": ["Contact at john@test.com", "Phone: 555-987-6543"],
    }

    print(f"Input:  {json.dumps(test_dict, indent=2)}")

    redacted_dict = PIIRedactor.redact_dict(test_dict)
    print(f"Output: {json.dumps(redacted_dict, indent=2)}")

    redacted_str = json.dumps(redacted_dict)
    if "[EMAIL_REDACTED]" in redacted_str and "[PHONE_REDACTED]" in redacted_str:
        print("✅ PASS - Dictionary redaction working")
    else:
        print("❌ FAIL - Dictionary redaction failed")
        all_passed = False

    print(f"\n{'='*50}")
    if all_passed:
        print("🎉 All PII redaction tests PASSED")
        return True
    else:
        print("⚠️  Some PII redaction tests FAILED")
        return False


if __name__ == "__main__":
    success = test_pii_redaction()
    exit(0 if success else 1)
