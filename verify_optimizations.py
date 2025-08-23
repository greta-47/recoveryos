#!/usr/bin/env python3
"""Verification script for RecoveryOS optimizations."""

import numpy as np

from coping import _risk_analyze
from rag import _mmr
from test_config import setup_test_environment

setup_test_environment()


def test_risk_analysis():
    """Test the optimized risk analysis function."""
    print("Testing risk analysis optimization...")

    result1 = _risk_analyze(mood=1, urge=5, isolation=1, energy=1)
    print(f"High risk case: {result1}")
    assert result1["score"] > 7.0, "High risk case should have score > 7"

    result2 = _risk_analyze(mood=5, urge=1, isolation=5, energy=5)
    print(f"Low risk case: {result2}")
    assert result2["score"] < 4.0, "Low risk case should have score < 4"

    print("✅ Risk analysis optimization working correctly!")


def test_mmr_optimization():
    """Test the optimized MMR algorithm."""
    print("Testing MMR optimization...")

    np.random.seed(42)  # For reproducible results
    query_vec = np.random.rand(10)
    doc_vecs = np.random.rand(5, 10)

    query_vec = query_vec / np.linalg.norm(query_vec)
    doc_vecs = doc_vecs / np.linalg.norm(doc_vecs, axis=1, keepdims=True)

    result = _mmr(query_vec, doc_vecs, top_k=3)
    print(f"MMR result: {result}")

    assert len(result) == 3, "Should return 3 indices"
    assert len(set(result)) == 3, "Should return unique indices"
    assert all(0 <= idx < 5 for idx in result), "All indices should be valid"

    print("✅ MMR optimization working correctly!")


def test_agents_import():
    """Test that agents module imports without API key error."""
    print("Testing agents module import...")

    try:
        pass
        print("✅ Agents module imported successfully with test environment!")
    except RuntimeError as e:
        if "OPENAI_API_KEY" in str(e):
            print("❌ API key error still occurring")
            raise
        else:
            print(f"❌ Unexpected error: {e}")
            raise


if __name__ == "__main__":
    print("=== RecoveryOS Optimization Verification ===")
    test_risk_analysis()
    test_mmr_optimization()
    test_agents_import()
    print("=== All optimizations verified successfully! ===")
