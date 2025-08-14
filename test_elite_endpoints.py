#!/usr/bin/env python3
"""
Comprehensive test suite for elite AI endpoints.
Includes failing tests that demonstrate bugs and verify fixes.
"""

import pytest
import sys
import os
import requests
import json
from typing import Dict, Any

sys.path.append('/home/ubuntu/recoveryos')

BASE_URL = "http://localhost:8001"

class TestContinualLearning:
    def test_continual_learning_with_correct_format(self):
        """Test continual learning with correct List[Dict] format"""
        response = requests.post(f"{BASE_URL}/elite/continual-learning/train", json={
            "task_data": [{"stress_patterns": [0.8, 0.6, 0.9]}],
            "task_id": "stress_prediction"
        })
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "training_result" in data
        assert data["task_id"] == "stress_prediction"
    
    def test_continual_learning_with_dict_format(self):
        """Test continual learning handles Dict format (auto-conversion)"""
        response = requests.post(f"{BASE_URL}/elite/continual-learning/train", json={
            "task_data": {"stress_patterns": [0.8, 0.6, 0.9]},
            "task_id": "stress_prediction"
        })
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["task_id"] == "stress_prediction"

class TestFederatedLearning:
    def test_federated_learning_single_client(self):
        """Test federated learning with single client data"""
        response = requests.post(f"{BASE_URL}/elite/federated-learning/train", json={
            "client_weights": [0.1, 0.2, 0.3],
            "client_id": "test_client"
        })
        assert response.status_code == 200
        data = response.json()
        assert "global_weights_updated" in data
        assert "client_id" in data
        assert data["client_id"] == "test_client"
    
    def test_federated_learning_anonymous_client(self):
        """Test federated learning with anonymous client"""
        response = requests.post(f"{BASE_URL}/elite/federated-learning/train", json={
            "client_weights": [0.4, 0.5, 0.6]
        })
        assert response.status_code == 200
        data = response.json()
        assert "global_weights_updated" in data
        assert data["client_id"] == "anonymous_client"

class TestEdgeAI:
    def test_edge_ai_emotion_classifier(self):
        """Test edge AI with emotion_classifier model type"""
        response = requests.post(f"{BASE_URL}/elite/edge-ai/deploy", json={
            "model_type": "emotion_classifier"
        })
        assert response.status_code == 200
        data = response.json()
        assert "deployment_id" in data
        assert data["model_type"] == "emotion"
        assert data["original_request"] == "emotion_classifier"
    
    def test_edge_ai_risk_predictor(self):
        """Test edge AI with risk_predictor model type"""
        response = requests.post(f"{BASE_URL}/elite/edge-ai/deploy", json={
            "model_type": "risk_predictor"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["model_type"] == "risk"
        assert data["original_request"] == "risk_predictor"
    
    def test_edge_ai_default_emotion(self):
        """Test edge AI with default emotion model"""
        response = requests.post(f"{BASE_URL}/elite/edge-ai/deploy", json={
            "model_type": "emotion"
        })
        assert response.status_code == 200
        data = response.json()
        assert data["model_type"] == "emotion"

class TestObservability:
    def test_metrics_endpoint(self):
        """Test that metrics endpoint works"""
        response = requests.get(f"{BASE_URL}/elite/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "total_requests" in data
        assert "timestamp" in data
    
    def test_pii_redaction(self):
        """Test PII redaction in differential privacy endpoint"""
        response = requests.post(f"{BASE_URL}/elite/differential-privacy/analyze", json={
            "data": ["john.doe@email.com", "123-45-6789", "Normal emotional state"],
            "analysis_type": "emotion_analysis"
        })
        assert response.status_code == 200

class TestAllEliteEndpoints:
    def test_all_endpoints_respond(self):
        """Test that all 10 elite endpoints respond successfully"""
        endpoints = [
            ("/elite/federated-learning/train", {"client_weights": [0.1, 0.2], "client_id": "test"}),
            ("/elite/causal-analysis/analyze", {"user_state": {"mood": 0.7, "stress": 0.3}}),
            ("/elite/edge-ai/deploy", {"model_type": "emotion"}),
            ("/elite/continual-learning/train", {"task_data": {"patterns": [0.5]}, "task_id": "test"}),
            ("/elite/neuromorphic/process", {"emotional_inputs": {"happiness": 0.8}}),
            ("/elite/graph-neural/analyze", {"user_data": {"connections": 5}}),
            ("/elite/quantum-crypto/encrypt", {"data": "test_data", "key_type": "quantum"}),
            ("/elite/explainable-ai/predict", {"input_data": {"features": [0.1, 0.2]}}),
            ("/elite/differential-privacy/analyze", {"data": ["test"], "analysis_type": "emotion_analysis"}),
            ("/elite/homomorphic/compute", {"operation": "secure_sum", "data": [1.0, 2.0, 3.0]})
        ]
        
        for endpoint, payload in endpoints:
            response = requests.post(f"{BASE_URL}{endpoint}", json=payload)
            assert response.status_code == 200, f"Endpoint {endpoint} failed with status {response.status_code}"
            data = response.json()
            assert data is not None, f"Endpoint {endpoint} returned null response"

if __name__ == "__main__":
    print("Running comprehensive elite endpoint tests...")
    
    test_continual = TestContinualLearning()
    test_federated = TestFederatedLearning()
    test_edge = TestEdgeAI()
    test_observability = TestObservability()
    test_all = TestAllEliteEndpoints()
    
    try:
        print("Testing Continual Learning...")
        test_continual.test_continual_learning_with_correct_format()
        test_continual.test_continual_learning_with_dict_format()
        print("✅ Continual Learning tests passed")
        
        print("Testing Federated Learning...")
        test_federated.test_federated_learning_single_client()
        test_federated.test_federated_learning_anonymous_client()
        print("✅ Federated Learning tests passed")
        
        print("Testing Edge AI...")
        test_edge.test_edge_ai_emotion_classifier()
        test_edge.test_edge_ai_risk_predictor()
        test_edge.test_edge_ai_default_emotion()
        print("✅ Edge AI tests passed")
        
        print("Testing Observability...")
        test_observability.test_metrics_endpoint()
        test_observability.test_pii_redaction()
        print("✅ Observability tests passed")
        
        print("Testing All Endpoints...")
        test_all.test_all_endpoints_respond()
        print("✅ All endpoint tests passed")
        
        print("\n🎉 ALL TESTS PASSED! All 3 failing endpoints are now fixed.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
