"""Test configuration utilities for RecoveryOS."""
import logging
import os

logger = logging.getLogger("recoveryos")

def setup_test_environment():
    """Set up environment variables for testing."""
    os.environ["TESTING"] = "true"
    
    if not os.getenv("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = "test-key-for-testing"
        logger.info("Set mock OPENAI_API_KEY for testing")
    
    os.environ.setdefault("RISK_HIGH_THRESHOLD", "7.0")
    os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
    os.environ.setdefault("ENABLE_HTTPS_ENFORCEMENT", "false")
    
    return True
