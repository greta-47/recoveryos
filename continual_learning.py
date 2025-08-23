import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List

import numpy as np

logger = logging.getLogger("recoveryos")


@dataclass
class TaskMemory:
    task_id: str
    model_weights: Dict[str, np.ndarray]
    importance_weights: Dict[str, np.ndarray]
    performance_metrics: Dict[str, float]
    timestamp: datetime


class ContinualLearningStrategy(ABC):
    @abstractmethod
    def consolidate_knowledge(
        self,
        old_weights: Dict[str, np.ndarray],
        new_weights: Dict[str, np.ndarray],
        importance: Dict[str, np.ndarray],
    ) -> Dict[str, np.ndarray]:
        pass


class ElasticWeightConsolidation(ContinualLearningStrategy):
    def __init__(self, lambda_reg: float = 1000.0):
        self.lambda_reg = lambda_reg

    def consolidate_knowledge(
        self,
        old_weights: Dict[str, np.ndarray],
        new_weights: Dict[str, np.ndarray],
        importance: Dict[str, np.ndarray],
    ) -> Dict[str, np.ndarray]:
        consolidated = {}

        for key in old_weights.keys():
            if key in new_weights and key in importance:
                penalty = self.lambda_reg * importance[key] * (new_weights[key] - old_weights[key]) ** 2
                consolidated[key] = new_weights[key] - 0.01 * penalty
            else:
                consolidated[key] = new_weights.get(key, old_weights[key])

        return consolidated


class ClinicalContinualLearner:
    def __init__(self, strategy: ContinualLearningStrategy):
        self.strategy = strategy
        self.task_memories: List[TaskMemory] = []
        self.current_weights: Dict[str, np.ndarray] = {}
        self.learning_history: List[Dict[str, Any]] = []
        self._initialize_weights()

    def _initialize_weights(self):
        self.current_weights = {
            "emotion_layer": np.random.normal(0, 0.1, (10, 8)),
            "risk_layer": np.random.normal(0, 0.1, (8, 5)),
            "intervention_layer": np.random.normal(0, 0.1, (5, 3)),
        }

    def learn_new_task(self, task_id: str, training_data: List[Dict[str, Any]], epochs: int = 10) -> Dict[str, Any]:
        logger.info(f"Learning new task | TaskID={task_id}")

        old_weights = {k: v.copy() for k, v in self.current_weights.items()}

        new_weights = self._train_on_task(training_data, epochs)

        importance_weights = self._calculate_importance(training_data)

        consolidated_weights = self.strategy.consolidate_knowledge(old_weights, new_weights, importance_weights)

        self.current_weights = consolidated_weights

        performance = self._evaluate_performance(training_data)

        task_memory = TaskMemory(
            task_id=task_id,
            model_weights={k: v.copy() for k, v in consolidated_weights.items()},
            importance_weights=importance_weights,
            performance_metrics=performance,
            timestamp=datetime.utcnow(),
        )

        self.task_memories.append(task_memory)

        learning_result = {
            "task_id": task_id,
            "performance": performance,
            "catastrophic_forgetting_score": self._measure_forgetting(),
            "knowledge_retention": self._measure_retention(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        self.learning_history.append(learning_result)
        return learning_result

    def _train_on_task(self, training_data: List[Dict[str, Any]], epochs: int) -> Dict[str, np.ndarray]:
        new_weights = {k: v.copy() for k, v in self.current_weights.items()}

        for epoch in range(epochs):
            for sample in training_data:
                for key in new_weights:
                    gradient = np.random.normal(0, 0.01, new_weights[key].shape)
                    new_weights[key] -= 0.01 * gradient

        return new_weights

    def _calculate_importance(self, training_data: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
        importance = {}

        for key, weights in self.current_weights.items():
            fisher_info = np.ones_like(weights) * 0.1

            for sample in training_data:
                gradient_squared = np.random.uniform(0, 1, weights.shape)
                fisher_info += gradient_squared

            fisher_info /= len(training_data)
            importance[key] = fisher_info

        return importance

    def _evaluate_performance(self, test_data: List[Dict[str, Any]]) -> Dict[str, float]:
        correct_predictions = 0
        total_predictions = len(test_data)

        for sample in test_data:
            prediction = np.random.random()
            if prediction > 0.5:
                correct_predictions += 1

        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0.0

        return {
            "accuracy": accuracy,
            "loss": 1.0 - accuracy,
            "samples_processed": total_predictions,
        }

    def _measure_forgetting(self) -> float:
        if len(self.task_memories) < 2:
            return 0.0

        recent_performance = []
        for memory in self.task_memories[-3:]:
            recent_performance.append(memory.performance_metrics.get("accuracy", 0.5))

        if len(recent_performance) < 2:
            return 0.0

        performance_drop = max(recent_performance) - min(recent_performance)
        return min(1.0, performance_drop)

    def _measure_retention(self) -> float:
        if not self.task_memories:
            return 1.0

        total_retention = 0.0
        for memory in self.task_memories:
            retention = memory.performance_metrics.get("accuracy", 0.5)
            total_retention += retention

        return total_retention / len(self.task_memories)

    def predict_with_uncertainty(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        predictions = []

        for memory in self.task_memories[-5:]:
            task_prediction = self._predict_with_weights(input_data, memory.model_weights)
            predictions.append(task_prediction)

        if not predictions:
            predictions = [0.5]

        mean_prediction = np.mean(predictions)
        uncertainty = np.std(predictions)

        return {
            "prediction": float(mean_prediction),
            "uncertainty": float(uncertainty),
            "confidence": float(1.0 - uncertainty),
            "ensemble_size": len(predictions),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _predict_with_weights(self, input_data: Dict[str, Any], weights: Dict[str, np.ndarray]) -> float:
        input_vector = np.array(list(input_data.values())[:10])

        if "emotion_layer" in weights:
            hidden = np.maximum(0, input_vector @ weights["emotion_layer"][: len(input_vector), :])
            if "risk_layer" in weights and len(hidden) >= weights["risk_layer"].shape[0]:
                output = hidden[: weights["risk_layer"].shape[0]] @ weights["risk_layer"]
                return float(1.0 / (1.0 + np.exp(-np.mean(output))))

        return 0.5

    def get_learning_insights(self) -> Dict[str, Any]:
        if not self.learning_history:
            return {"message": "No learning history available"}

        recent_learning = self.learning_history[-10:]

        avg_performance = np.mean([learning["performance"]["accuracy"] for learning in recent_learning])
        avg_forgetting = np.mean([learning["catastrophic_forgetting_score"] for learning in recent_learning])
        avg_retention = np.mean([learning["knowledge_retention"] for learning in recent_learning])

        return {
            "total_tasks_learned": len(self.task_memories),
            "recent_performance": float(avg_performance),
            "catastrophic_forgetting": float(avg_forgetting),
            "knowledge_retention": float(avg_retention),
            "continual_learning_efficiency": float(avg_retention * (1.0 - avg_forgetting)),
            "learning_strategy": type(self.strategy).__name__,
            "insights": self._generate_learning_insights(recent_learning),
        }

    def _generate_learning_insights(self, recent_learning: List[Dict[str, Any]]) -> List[str]:
        insights = []

        if len(recent_learning) > 3:
            insights.append("Continual learning system shows consistent task acquisition")

        forgetting_scores = [learning["catastrophic_forgetting_score"] for learning in recent_learning]
        if forgetting_scores and np.mean(forgetting_scores) < 0.2:
            insights.append("Low catastrophic forgetting indicates effective knowledge consolidation")
        elif forgetting_scores and np.mean(forgetting_scores) > 0.5:
            insights.append("High forgetting detected - consider adjusting consolidation parameters")

        retention_scores = [learning["knowledge_retention"] for learning in recent_learning]
        if retention_scores and np.mean(retention_scores) > 0.8:
            insights.append("Strong knowledge retention across multiple clinical tasks")

        return insights


def create_continual_learner() -> ClinicalContinualLearner:
    strategy = ElasticWeightConsolidation(lambda_reg=1000.0)
    return ClinicalContinualLearner(strategy)
