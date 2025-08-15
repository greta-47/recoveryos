import logging
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime
import numpy as np
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger("recoveryos")


class PrivacyMechanism(Enum):
    LAPLACE = "laplace"
    GAUSSIAN = "gaussian"
    EXPONENTIAL = "exponential"
    SPARSE_VECTOR = "sparse_vector"


@dataclass
class PrivacyBudget:
    epsilon: float
    delta: float = 1e-5
    used_epsilon: float = 0.0
    used_delta: float = 0.0

    def can_spend(self, epsilon: float, delta: float = 0.0) -> bool:
        return (
            self.used_epsilon + epsilon <= self.epsilon
            and self.used_delta + delta <= self.delta
        )

    def spend(self, epsilon: float, delta: float = 0.0) -> bool:
        if self.can_spend(epsilon, delta):
            self.used_epsilon += epsilon
            self.used_delta += delta
            return True
        return False

    def remaining(self) -> Dict[str, float]:
        return {
            "epsilon": self.epsilon - self.used_epsilon,
            "delta": self.delta - self.used_delta,
        }


class DifferentialPrivacyMechanism:
    def __init__(self, epsilon: float, delta: float = 1e-5, sensitivity: float = 1.0):
        self.epsilon = epsilon
        self.delta = delta
        self.sensitivity = sensitivity

    def laplace_noise(self, shape: tuple, scale: Optional[float] = None) -> np.ndarray:
        if scale is None:
            scale = self.sensitivity / self.epsilon
        return np.random.laplace(0, scale, shape)

    def gaussian_noise(self, shape: tuple, scale: Optional[float] = None) -> np.ndarray:
        if scale is None:
            scale = (
                np.sqrt(2 * np.log(1.25 / self.delta)) * self.sensitivity / self.epsilon
            )
        scale_value = float(scale) if scale is not None else 1.0
        return np.random.normal(0.0, scale_value, shape)

    def exponential_mechanism(
        self, candidates: List[Any], utility_fn: Callable, sensitivity: float
    ) -> Any:
        utilities = [utility_fn(candidate) for candidate in candidates]

        probabilities = []
        for utility in utilities:
            prob = np.exp((self.epsilon * utility) / (2 * sensitivity))
            probabilities.append(prob)

        probabilities = np.array(probabilities)
        probabilities /= probabilities.sum()

        return np.random.choice(candidates, p=probabilities)

    def sparse_vector_technique(
        self, queries: List[Callable], threshold: float, max_responses: int = 1
    ) -> List[Optional[float]]:
        noisy_threshold = threshold + self.laplace_noise((1,))[0]
        responses = []
        response_count = 0

        for query in queries:
            if response_count >= max_responses:
                responses.append(None)
                continue

            true_answer = query()
            noisy_answer = true_answer + self.laplace_noise((1,))[0]

            if noisy_answer >= noisy_threshold:
                responses.append(noisy_answer)
                response_count += 1
            else:
                responses.append(None)

        return responses


class ClinicalPrivacyProtector:
    def __init__(self, global_epsilon: float = 1.0, global_delta: float = 1e-5):
        self.global_budget = PrivacyBudget(global_epsilon, global_delta)
        self.user_budgets: Dict[str, PrivacyBudget] = {}
        self.query_history: List[Dict[str, Any]] = []

    def get_user_budget(self, user_id: str, epsilon: float = 0.1) -> PrivacyBudget:
        if user_id not in self.user_budgets:
            self.user_budgets[user_id] = PrivacyBudget(epsilon)
        return self.user_budgets[user_id]

    def privatize_emotion_analysis(
        self, emotion_scores: Dict[str, float], user_id: str, epsilon: float = 0.05
    ) -> Dict[str, float]:
        budget = self.get_user_budget(user_id)

        if not budget.can_spend(epsilon):
            logger.warning(f"Insufficient privacy budget | User={user_id}")
            return {k: 0.5 for k in emotion_scores.keys()}

        mechanism = DifferentialPrivacyMechanism(epsilon, sensitivity=1.0)
        privatized_scores = {}

        for emotion, score in emotion_scores.items():
            noise = mechanism.laplace_noise((1,))[0]
            privatized_score = np.clip(score + noise, 0.0, 1.0)
            privatized_scores[emotion] = float(privatized_score)

        budget.spend(epsilon)
        self._log_query("emotion_analysis", user_id, epsilon)

        return privatized_scores

    def privatize_risk_assessment(
        self, risk_factors: List[Dict[str, Any]], user_id: str, epsilon: float = 0.1
    ) -> List[Dict[str, Any]]:
        budget = self.get_user_budget(user_id)

        if not budget.can_spend(epsilon):
            logger.warning(f"Insufficient privacy budget | User={user_id}")
            return [
                {
                    "name": "privacy_protected",
                    "score": 0.5,
                    "explanation": "Privacy budget exceeded",
                }
            ]

        mechanism = DifferentialPrivacyMechanism(epsilon, sensitivity=1.0)
        privatized_factors = []

        for factor in risk_factors:
            if "score" in factor:
                noise = mechanism.laplace_noise((1,))[0]
                privatized_score = np.clip(factor["score"] + noise, 0.0, 1.0)

                privatized_factor = factor.copy()
                privatized_factor["score"] = float(privatized_score)
                privatized_factors.append(privatized_factor)

        budget.spend(epsilon)
        self._log_query("risk_assessment", user_id, epsilon)

        return privatized_factors

    def privatize_clinical_insights(
        self, insights: List[str], user_id: str, epsilon: float = 0.08
    ) -> List[str]:
        budget = self.get_user_budget(user_id)

        if not budget.can_spend(epsilon):
            logger.warning(f"Insufficient privacy budget | User={user_id}")
            return ["Clinical insights protected due to privacy constraints."]

        mechanism = DifferentialPrivacyMechanism(epsilon, sensitivity=1.0)

        def utility_fn(insight: str) -> float:
            therapeutic_keywords = [
                "recovery",
                "coping",
                "support",
                "healing",
                "progress",
            ]
            return sum(
                1 for keyword in therapeutic_keywords if keyword in insight.lower()
            )

        if insights:
            selected_insight = mechanism.exponential_mechanism(
                insights, utility_fn, sensitivity=1.0
            )
            budget.spend(epsilon)
            self._log_query("clinical_insights", user_id, epsilon)
            return [selected_insight]

        return insights

    def privatize_aggregated_stats(
        self, stats: Dict[str, float], epsilon: float = 0.2
    ) -> Dict[str, float]:
        if not self.global_budget.can_spend(epsilon):
            logger.warning("Insufficient global privacy budget for aggregated stats")
            return {k: 0.0 for k in stats.keys()}

        mechanism = DifferentialPrivacyMechanism(epsilon, sensitivity=1.0)
        privatized_stats = {}

        for key, value in stats.items():
            noise = mechanism.gaussian_noise((1,))[0]
            privatized_value = max(0.0, value + noise)
            privatized_stats[key] = float(privatized_value)

        self.global_budget.spend(epsilon)
        self._log_query("aggregated_stats", "global", epsilon)

        return privatized_stats

    def check_privacy_budget(self, user_id: str) -> Dict[str, Any]:
        user_budget = self.get_user_budget(user_id)
        global_remaining = self.global_budget.remaining()
        user_remaining = user_budget.remaining()

        return {
            "user_id": user_id,
            "global_budget": global_remaining,
            "user_budget": user_remaining,
            "queries_made": len(
                [q for q in self.query_history if q["user_id"] == user_id]
            ),
            "status": "healthy" if user_remaining["epsilon"] > 0.01 else "depleted",
        }

    def _log_query(self, query_type: str, user_id: str, epsilon_used: float):
        self.query_history.append(
            {
                "query_type": query_type,
                "user_id": user_id,
                "epsilon_used": epsilon_used,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )


class PrivacyAudit:
    def __init__(self, protector: ClinicalPrivacyProtector):
        self.protector = protector

    def generate_privacy_report(self) -> Dict[str, Any]:
        total_queries = len(self.protector.query_history)
        unique_users = len(set(q["user_id"] for q in self.protector.query_history))

        query_types = {}
        for query in self.protector.query_history:
            query_type = query["query_type"]
            query_types[query_type] = query_types.get(query_type, 0) + 1

        global_budget_used = (
            self.protector.global_budget.used_epsilon
            / self.protector.global_budget.epsilon
            * 100
        )

        user_budget_stats = []
        for user_id, budget in self.protector.user_budgets.items():
            budget_used = budget.used_epsilon / budget.epsilon * 100
            user_budget_stats.append(
                {
                    "user_id": user_id,
                    "budget_used_percent": budget_used,
                    "remaining_epsilon": budget.epsilon - budget.used_epsilon,
                }
            )

        return {
            "total_queries": total_queries,
            "unique_users": unique_users,
            "query_types": query_types,
            "global_budget_used_percent": global_budget_used,
            "user_budget_stats": user_budget_stats,
            "privacy_guarantees": {
                "epsilon": self.protector.global_budget.epsilon,
                "delta": self.protector.global_budget.delta,
                "mechanism": "Laplace and Gaussian noise",
            },
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def validate_privacy_compliance(self) -> Dict[str, Any]:
        issues = []

        if (
            self.protector.global_budget.used_epsilon
            > self.protector.global_budget.epsilon
        ):
            issues.append("Global epsilon budget exceeded")

        for user_id, budget in self.protector.user_budgets.items():
            if budget.used_epsilon > budget.epsilon:
                issues.append(f"User {user_id} epsilon budget exceeded")

        high_risk_users = [
            user_id
            for user_id, budget in self.protector.user_budgets.items()
            if budget.used_epsilon / budget.epsilon > 0.8
        ]

        return {
            "compliant": len(issues) == 0,
            "issues": issues,
            "high_risk_users": high_risk_users,
            "recommendations": self._generate_recommendations(issues, high_risk_users),
        }

    def _generate_recommendations(
        self, issues: List[str], high_risk_users: List[str]
    ) -> List[str]:
        recommendations = []

        if issues:
            recommendations.append("Increase privacy budget or reduce query frequency")

        if high_risk_users:
            recommendations.append("Implement query throttling for high-usage users")
            recommendations.append("Consider using more efficient privacy mechanisms")

        if not issues and not high_risk_users:
            recommendations.append(
                "Privacy compliance is healthy - continue monitoring"
            )

        return recommendations


def create_clinical_privacy_protector(
    epsilon: float = 1.0, delta: float = 1e-5
) -> ClinicalPrivacyProtector:
    return ClinicalPrivacyProtector(epsilon, delta)


def apply_differential_privacy(
    data: Union[Dict, List, float],
    epsilon: float = 0.1,
    mechanism: PrivacyMechanism = PrivacyMechanism.LAPLACE,
) -> Any:
    dp_mechanism = DifferentialPrivacyMechanism(epsilon, sensitivity=1.0)

    if isinstance(data, dict):
        privatized = {}
        for key, value in data.items():
            if isinstance(value, (int, float)):
                if mechanism == PrivacyMechanism.LAPLACE:
                    noise = dp_mechanism.laplace_noise((1,))[0]
                else:
                    noise = dp_mechanism.gaussian_noise((1,))[0]
                privatized[key] = float(value + noise)
            else:
                privatized[key] = value
        return privatized

    elif isinstance(data, list) and all(isinstance(x, (int, float)) for x in data):
        if mechanism == PrivacyMechanism.LAPLACE:
            noise = dp_mechanism.laplace_noise((len(data),))
        else:
            noise = dp_mechanism.gaussian_noise((len(data),))
        return [float(x + n) for x, n in zip(data, noise)]

    elif isinstance(data, (int, float)):
        if mechanism == PrivacyMechanism.LAPLACE:
            noise = dp_mechanism.laplace_noise((1,))[0]
        else:
            noise = dp_mechanism.gaussian_noise((1,))[0]
        return float(data + noise)

    return data
