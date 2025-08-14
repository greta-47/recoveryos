#!/usr/bin/env python3
"""
Diagnostic test script for the 3 failing elite endpoints.
This will help categorize each failure type and capture detailed error information.
"""

import sys
import logging
import traceback
import json
from typing import Dict, Any

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

sys.path.append('/home/ubuntu/recoveryos')

def test_continual_learning():
    """Test continual learning endpoint and module directly"""
    print("=== CONTINUAL LEARNING DIAGNOSIS ===")
    
    try:
        from continual_learning import create_continual_learner
        print("✅ Import successful")
        
        learner = create_continual_learner()
        print("✅ Learner created")
        
        # Test the actual function signature
        print("Testing learn_new_task signature...")
        
        # This is what the endpoint is passing (WRONG)
        task_id = "stress_prediction"
        training_data_dict = {"stress_patterns": [0.8, 0.6, 0.9]}
        
        print(f"Current endpoint passes: task_id='{task_id}', training_data={training_data_dict}")
        
        # Check what the function actually expects
        import inspect
        sig = inspect.signature(learner.learn_new_task)
        print(f"Function signature: {sig}")
        
        # Try with correct format (List[Dict[str, Any]])
        correct_training_data = [{"stress_patterns": [0.8, 0.6, 0.9]}]
        result = learner.learn_new_task(task_id, correct_training_data)
        print(f"✅ With correct format: {result}")
        
        # Try with wrong format (what endpoint currently sends)
        try:
            result_wrong = learner.learn_new_task(task_id, training_data_dict)
            print(f"❌ With wrong format: {result_wrong}")
        except Exception as e:
            print(f"❌ Wrong format fails: {e}")
        
        return "CONTRACT_ERROR: training_data should be List[Dict[str, Any]], not Dict[str, Any]"
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return f"ERROR: {e}"

def test_federated_learning():
    """Test federated learning endpoint and module directly"""
    print("\n=== FEDERATED LEARNING DIAGNOSIS ===")
    
    try:
        from federated_learning import create_federated_manager
        print("✅ Import successful")
        
        manager = create_federated_manager()
        print("✅ Manager created")
        
        # Test the actual function signature
        print("Testing federated_round signature...")
        
        # This is what the endpoint is passing (WRONG)
        client_data_wrong = {"client_weights": [0.1, 0.2, 0.3], "client_id": "test_client"}
        
        print(f"Current endpoint passes: {client_data_wrong}")
        
        # Check what the function actually expects
        import inspect
        sig = inspect.signature(manager.federated_round)
        print(f"Function signature: {sig}")
        
        # Try with correct format (Dict[client_id, data])
        correct_client_data = {
            "client_123": {"mock_data": [0.1, 0.2, 0.3]},
            "client_456": {"mock_data": [0.4, 0.5, 0.6]},
            "client_789": {"mock_data": [0.7, 0.8, 0.9]}
        }
        result = manager.federated_round(correct_client_data)
        print(f"✅ With correct format: {result is not None}")
        
        # Try with wrong format (what endpoint currently sends)
        try:
            result_wrong = manager.federated_round(client_data_wrong)
            print(f"❌ With wrong format: {result_wrong}")
        except Exception as e:
            print(f"❌ Wrong format fails: {e}")
        
        return "CONTRACT_ERROR: client_data should be Dict[client_id, data], not single client data"
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return f"ERROR: {e}"

def test_edge_ai():
    """Test edge AI endpoint and module directly"""
    print("\n=== EDGE AI DIAGNOSIS ===")
    
    try:
        from edge_ai import create_edge_ai_manager
        print("✅ Import successful")
        
        manager = create_edge_ai_manager()
        print("✅ Manager created")
        
        # Test the actual function signature
        print("Testing deploy_model signature...")
        
        # Check what the function actually expects
        import inspect
        sig = inspect.signature(manager.deploy_model)
        print(f"Function signature: {sig}")
        
        # Try with correct format
        model_type = "emotion_classifier"
        result = manager.deploy_model(model_type)
        print(f"✅ Deploy result: {result}")
        
        if result:
            client_code = manager.get_client_deployment_code(result)
            print(f"✅ Client code length: {len(client_code) if client_code else 0}")
        
        return "SUCCESS: Edge AI module works correctly"
        
    except Exception as e:
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return f"ERROR: {e}"

def main():
    """Run all diagnostic tests"""
    print("🔧 ELITE ENDPOINT FAILURE DIAGNOSIS")
    print("=" * 50)
    
    results = {}
    
    results["continual_learning"] = test_continual_learning()
    results["federated_learning"] = test_federated_learning()
    results["edge_ai"] = test_edge_ai()
    
    print("\n" + "=" * 50)
    print("📊 DIAGNOSIS SUMMARY")
    print("=" * 50)
    
    for endpoint, result in results.items():
        print(f"{endpoint}: {result}")
    
    return results

if __name__ == "__main__":
    main()
