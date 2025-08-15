import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime
import numpy as np
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger("recoveryos")


@dataclass
class Explanation:
    explanation_type: str
    feature_importance: Dict[str, float]
    counterfactual: Optional[Dict[str, Any]]
    confidence: float
    reasoning_chain: List[str]
    timestamp: datetime


class ExplanationMethod(ABC):
    @abstractmethod
    def explain(
        self, input_data: Dict[str, Any], prediction: Dict[str, Any]
    ) -> Explanation:
        pass


class SHAPExplainer(ExplanationMethod):
    def __init__(self):
        self.baseline_values = {
            "stress_level": 0.5,
            "social_support": 0.7,
            "coping_skills": 0.6,
            "mood_state": 0.5,
            "sleep_quality": 0.6,
        }

    def explain(
        self, input_data: Dict[str, Any], prediction: Dict[str, Any]
    ) -> Explanation:
        feature_importance = {}
        reasoning_chain = []

        for feature, value in input_data.items():
            if feature in self.baseline_values:
                baseline = self.baseline_values[feature]
                contribution = (value - baseline) * self._get_feature_weight(feature)
                feature_importance[feature] = contribution

                if abs(contribution) > 0.1:
                    direction = "increases" if contribution > 0 else "decreases"
                    reasoning_chain.append(
                        f"{feature} ({value:.2f}) {direction} risk by {abs(contribution):.2f}"
                    )

        counterfactual = self._generate_counterfactual(input_data, prediction)

        return Explanation(
            explanation_type="SHAP",
            feature_importance=feature_importance,
            counterfactual=counterfactual,
            confidence=0.85,
            reasoning_chain=reasoning_chain,
            timestamp=datetime.utcnow(),
        )

    def _get_feature_weight(self, feature: str) -> float:
        weights = {
            "stress_level": 0.8,
            "social_support": -0.6,
            "coping_skills": -0.7,
            "mood_state": 0.5,
            "sleep_quality": -0.4,
        }
        return weights.get(feature, 0.1)

    def _generate_counterfactual(
        self, input_data: Dict[str, Any], prediction: Dict[str, Any]
    ) -> Dict[str, Any]:
        current_risk = prediction.get("risk_score", 0.5)
        target_risk = max(0.1, current_risk - 0.3)

        counterfactual = input_data.copy()

        if "stress_level" in counterfactual and counterfactual["stress_level"] > 0.3:
            counterfactual["stress_level"] = 0.3

        if "coping_skills" in counterfactual and counterfactual["coping_skills"] < 0.8:
            counterfactual["coping_skills"] = 0.8

        return {
            "modified_features": counterfactual,
            "expected_risk": target_risk,
            "changes_needed": self._describe_changes(input_data, counterfactual),
        }

    def _describe_changes(
        self, original: Dict[str, Any], modified: Dict[str, Any]
    ) -> List[str]:
        changes = []

        for key, new_value in modified.items():
            if key in original and abs(original[key] - new_value) > 0.05:
                if new_value > original[key]:
                    changes.append(
                        f"Increase {key} from {original[key]:.2f} to {new_value:.2f}"
                    )
                else:
                    changes.append(
                        f"Reduce {key} from {original[key]:.2f} to {new_value:.2f}"
                    )

        return changes


class LIMEExplainer(ExplanationMethod):
    def __init__(self, num_samples: int = 100):
        self.num_samples = num_samples

    def explain(
        self, input_data: Dict[str, Any], prediction: Dict[str, Any]
    ) -> Explanation:
        feature_importance = self._local_linear_approximation(input_data, prediction)

        reasoning_chain = []
        for feature, importance in sorted(
            feature_importance.items(), key=lambda x: abs(x[1]), reverse=True
        )[:3]:
            effect = "protective" if importance < 0 else "risk-increasing"
            reasoning_chain.append(
                f"{feature} has {effect} effect (weight: {importance:.3f})"
            )

        return Explanation(
            explanation_type="LIME",
            feature_importance=feature_importance,
            counterfactual=None,
            confidence=0.75,
            reasoning_chain=reasoning_chain,
            timestamp=datetime.utcnow(),
        )

    def _local_linear_approximation(
        self, input_data: Dict[str, Any], prediction: Dict[str, Any]
    ) -> Dict[str, float]:
        feature_importance = {}

        for feature in input_data.keys():
            perturbations = []
            predictions = []

            for _ in range(self.num_samples):
                perturbed_data = input_data.copy()
                noise = np.random.normal(0, 0.1)
                perturbed_data[feature] = max(0, min(1, input_data[feature] + noise))

                perturbed_prediction = self._simulate_prediction(perturbed_data)

                perturbations.append(perturbed_data[feature])
                predictions.append(perturbed_prediction)

            if len(set(perturbations)) > 1:
                correlation = np.corrcoef(perturbations, predictions)[0, 1]
                feature_importance[feature] = (
                    correlation if not np.isnan(correlation) else 0.0
                )
            else:
                feature_importance[feature] = 0.0

        return feature_importance

    def _simulate_prediction(self, data: Dict[str, Any]) -> float:
        risk_score = 0.5

        if "stress_level" in data:
            risk_score += data["stress_level"] * 0.3
        if "social_support" in data:
            risk_score -= data["social_support"] * 0.2
        if "coping_skills" in data:
            risk_score -= data["coping_skills"] * 0.25

        return max(0, min(1, risk_score))


class CausalExplainer(ExplanationMethod):
    def __init__(self):
        self.causal_graph = {
            "stress_level": ["mood_state", "relapse_risk"],
            "social_support": ["stress_level", "coping_skills"],
            "coping_skills": ["stress_level", "relapse_risk"],
            "mood_state": ["relapse_risk"],
            "sleep_quality": ["mood_state", "stress_level"],
        }

    def explain(
        self, input_data: Dict[str, Any], prediction: Dict[str, Any]
    ) -> Explanation:
        causal_effects = self._calculate_causal_effects(input_data)

        reasoning_chain = []
        for cause, effect_size in sorted(
            causal_effects.items(), key=lambda x: abs(x[1]), reverse=True
        ):
            if abs(effect_size) > 0.05:
                direction = "increases" if effect_size > 0 else "decreases"
                reasoning_chain.append(
                    f"{cause} causally {direction} relapse risk by {abs(effect_size):.2f}"
                )

        counterfactual = self._causal_counterfactual(input_data, causal_effects)

        return Explanation(
            explanation_type="Causal",
            feature_importance=causal_effects,
            counterfactual=counterfactual,
            confidence=0.90,
            reasoning_chain=reasoning_chain,
            timestamp=datetime.utcnow(),
        )

    def _calculate_causal_effects(self, input_data: Dict[str, Any]) -> Dict[str, float]:
        causal_effects = {}

        for cause, targets in self.causal_graph.items():
            if cause in input_data and "relapse_risk" in targets:
                direct_effect = self._direct_causal_effect(cause, input_data[cause])
                indirect_effect = self._indirect_causal_effect(cause, input_data)

                causal_effects[cause] = direct_effect + indirect_effect

        return causal_effects

    def _direct_causal_effect(self, cause: str, value: float) -> float:
        causal_strengths = {
            "stress_level": 0.6,
            "social_support": -0.4,
            "coping_skills": -0.5,
            "mood_state": 0.3,
            "sleep_quality": -0.2,
        }

        strength = causal_strengths.get(cause, 0.0)
        return (value - 0.5) * strength

    def _indirect_causal_effect(self, cause: str, input_data: Dict[str, Any]) -> float:
        indirect_effect = 0.0

        if cause == "social_support":
            if "stress_level" in input_data:
                mediated_effect = -0.3 * input_data["stress_level"] * 0.6
                indirect_effect += mediated_effect

        elif cause == "sleep_quality":
            if "mood_state" in input_data:
                mediated_effect = 0.4 * input_data["mood_state"] * 0.3
                indirect_effect += mediated_effect

        return indirect_effect

    def _causal_counterfactual(
        self, input_data: Dict[str, Any], causal_effects: Dict[str, float]
    ) -> Dict[str, Any]:
        interventions = {}

        strongest_cause = max(causal_effects.items(), key=lambda x: abs(x[1]))
        cause_name, effect_size = strongest_cause

        if effect_size > 0.1:
            if cause_name == "stress_level":
                interventions[cause_name] = max(
                    0.1, input_data.get(cause_name, 0.5) - 0.4
                )
            elif cause_name == "mood_state":
                interventions[cause_name] = max(
                    0.1, input_data.get(cause_name, 0.5) - 0.3
                )

        elif effect_size < -0.1:
            if cause_name in ["social_support", "coping_skills"]:
                interventions[cause_name] = min(
                    1.0, input_data.get(cause_name, 0.5) + 0.3
                )

        return {
            "causal_intervention": interventions,
            "expected_effect": -effect_size * 0.8,
            "intervention_type": "causal_manipulation",
        }


class ExplainableAIEngine:
    def __init__(self):
        self.explainers = {
            "shap": SHAPExplainer(),
            "lime": LIMEExplainer(),
            "causal": CausalExplainer(),
        }
        self.explanation_history: List[Dict[str, Any]] = []

    def explain_prediction(
        self,
        input_data: Dict[str, Any],
        prediction: Dict[str, Any],
        methods: List[str] = ["shap", "causal"],
    ) -> Dict[str, Any]:
        explanations = {}

        for method in methods:
            if method in self.explainers:
                try:
                    explanation = self.explainers[method].explain(
                        input_data, prediction
                    )
                    explanations[method] = {
                        "feature_importance": explanation.feature_importance,
                        "reasoning_chain": explanation.reasoning_chain,
                        "confidence": explanation.confidence,
                        "counterfactual": explanation.counterfactual,
                    }
                except Exception as e:
                    logger.error(f"Explanation method {method} failed | Error={str(e)}")
                    explanations[method] = {"error": str(e)}

        consensus_explanation = self._build_consensus(explanations)

        result = {
            "input_data": input_data,
            "prediction": prediction,
            "explanations": explanations,
            "consensus": consensus_explanation,
            "explanation_quality": self._assess_explanation_quality(explanations),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        self.explanation_history.append(result)
        return result

    def _build_consensus(self, explanations: Dict[str, Any]) -> Dict[str, Any]:
        feature_votes = {}
        reasoning_points = []

        for method, explanation in explanations.items():
            if "error" not in explanation:
                for feature, importance in explanation.get(
                    "feature_importance", {}
                ).items():
                    if feature not in feature_votes:
                        feature_votes[feature] = []
                    feature_votes[feature].append(importance)

                reasoning_points.extend(explanation.get("reasoning_chain", []))

        consensus_importance = {}
        for feature, votes in feature_votes.items():
            consensus_importance[feature] = np.mean(votes)

        top_factors = sorted(
            consensus_importance.items(), key=lambda x: abs(x[1]), reverse=True
        )[:3]

        return {
            "top_risk_factors": [
                {"factor": f, "importance": i} for f, i in top_factors
            ],
            "consensus_reasoning": reasoning_points[:5],
            "explanation_agreement": len(feature_votes) / max(1, len(explanations)),
        }

    def _assess_explanation_quality(
        self, explanations: Dict[str, Any]
    ) -> Dict[str, Any]:
        quality_metrics = {
            "completeness": len(explanations) / len(self.explainers),
            "consistency": 0.0,
            "interpretability": 0.0,
        }

        valid_explanations = [e for e in explanations.values() if "error" not in e]

        if len(valid_explanations) > 1:
            feature_correlations = []

            for i, exp1 in enumerate(valid_explanations):
                for exp2 in valid_explanations[i + 1 :]:
                    common_features = set(
                        exp1.get("feature_importance", {}).keys()
                    ) & set(exp2.get("feature_importance", {}).keys())

                    if common_features:
                        corr_values = []
                        for feature in common_features:
                            imp1 = exp1["feature_importance"][feature]
                            imp2 = exp2["feature_importance"][feature]
                            corr_values.append(imp1 * imp2)

                        if corr_values:
                            feature_correlations.append(np.mean(corr_values))

            if feature_correlations:
                quality_metrics["consistency"] = float(np.mean(feature_correlations))

        reasoning_lengths = [
            len(e.get("reasoning_chain", [])) for e in valid_explanations
        ]
        if reasoning_lengths:
            quality_metrics["interpretability"] = min(
                1.0, float(np.mean(reasoning_lengths)) / 5.0
            )

        return quality_metrics

    def get_explanation_insights(self) -> Dict[str, Any]:
        if not self.explanation_history:
            return {"message": "No explanations generated yet"}

        recent_explanations = self.explanation_history[-10:]

        method_usage = {}
        avg_quality = {}

        for exp in recent_explanations:
            for method in exp.get("explanations", {}).keys():
                method_usage[method] = method_usage.get(method, 0) + 1

            quality = exp.get("explanation_quality", {})
            for metric, value in quality.items():
                if metric not in avg_quality:
                    avg_quality[metric] = []
                avg_quality[metric].append(value)

        for metric in avg_quality:
            avg_quality[metric] = np.mean(avg_quality[metric])

        return {
            "total_explanations": len(self.explanation_history),
            "recent_explanations": len(recent_explanations),
            "method_usage": method_usage,
            "average_quality": avg_quality,
            "explainability_insights": [
                "Multi-method explanations provide robust understanding of AI decisions",
                "Causal explanations offer actionable insights for clinical interventions",
                "Counterfactual reasoning helps identify specific improvement pathways",
            ],
        }


def create_explainable_ai_engine() -> ExplainableAIEngine:
    return ExplainableAIEngine()


def explain_clinical_prediction(
    input_data: Dict[str, Any], prediction: Dict[str, Any]
) -> Dict[str, Any]:
    engine = create_explainable_ai_engine()
    return engine.explain_prediction(input_data, prediction)
