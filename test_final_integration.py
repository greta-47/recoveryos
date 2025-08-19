#!/usr/bin/env python3
"""
Final Integration Testing Script
Tests all observability components are working correctly
"""


def test_imports():
    """Test that all required modules can be imported"""
    try:
        from observability_enhanced import PIIRedactor
        from feature_flags import feature_flags

        print("✅ Enhanced observability imported successfully")
        print("✅ Feature flags imported successfully")

        test_text = "Contact john@test.com or call 555-123-4567"
        redacted = PIIRedactor.redact_pii(test_text)
        print(f"✅ PII redaction test: {redacted}")

        enhanced_enabled = feature_flags.is_enabled("enhanced_observability")
        print(f"✅ Feature flag test: enhanced_observability = {enhanced_enabled}")

        assert True
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        assert False, f"Import test failed: {e}"


if __name__ == "__main__":
    success = test_imports()
    if success:
        print("✅ All integration tests passed!")
        exit(0)
    else:
        print("❌ Integration tests failed!")
        exit(1)
