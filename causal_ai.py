import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import numpy as np

logger = logging.getLogger("recoveryos")


class CausalRelationType(Enum):
    DIRECT_CAUSE = "direct_cause"
    INDIRECT_CAUSE = "indirect_cause"
    MEDIATOR = "mediator"
    MODERATOR = "moderator"
    CONFOUNDER = "confounder"
    COLLIDER = "collider"


@dataclass
class CausalEdge:
    source: str
    target: str
    relation_type: CausalRelationType
    strength: float
    confidence: float
    evidence_sources: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation_type": self.relation_type.value,
            "strength": self.strength,
            "confidence": self.confidence,
            "evidence_sources": self.evidence_sources,
        }


@dataclass
class CausalNode:
    name: str
    node_type: str
    description: str
    measurable: bool = True
    interventionable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "node_type": self.node_type,
            "description": self.description,
            "measurable": self.measurable,
            "interventionable": self.interventionable,
        }


class RecoveryCausalGraph:
    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: List[CausalEdge] = []
        self._initialize_recovery_graph()

    def _initialize_recovery_graph(self):
        recovery_nodes = [
            CausalNode(
                "stress_level",
                "psychological",
                "Current stress and anxiety levels",
                True,
                True,
            ),
            CausalNode(
                "social_support",
                "social",
                "Quality and quantity of social connections",
                True,
                True,
            ),
            CausalNode(
                "coping_skills",
                "behavioral",
                "Availability and use of healthy coping mechanisms",
                True,
                True,
            ),
            CausalNode(
                "substance_craving",
                "physiological",
                "Intensity of substance use urges",
                True,
                False,
            ),
            CausalNode(
                "mood_state",
                "psychological",
                "Current emotional and mood state",
                True,
                True,
            ),
            CausalNode(
                "sleep_quality",
                "physiological",
                "Sleep duration and quality",
                True,
                True,
            ),
            CausalNode(
                "relapse_risk",
                "outcome",
                "Probability of substance use relapse",
                True,
                False,
            ),
            CausalNode(
                "trauma_triggers",
                "psychological",
                "Exposure to trauma-related triggers",
                True,
                True,
            ),
            CausalNode(
                "medication_adherence",
                "behavioral",
                "Consistency with prescribed medications",
                True,
                True,
            ),
            CausalNode(
                "therapy_engagement",
                "behavioral",
                "Active participation in therapeutic activities",
                True,
                True,
            ),
            CausalNode(
                "employment_status",
                "social",
                "Work and financial stability",
                True,
                True,
            ),
            CausalNode(
                "physical_health",
                "physiological",
                "Overall physical health and wellness",
                True,
                True,
            ),
        ]

        for node in recovery_nodes:
            self.nodes[node.name] = node

        recovery_edges = [
            CausalEdge(
                "stress_level",
                "substance_craving",
                CausalRelationType.DIRECT_CAUSE,
                0.7,
                0.85,
                ["clinical_studies", "patient_reports"],
            ),
            CausalEdge(
                "social_support",
                "stress_level",
                CausalRelationType.DIRECT_CAUSE,
                -0.6,
                0.80,
                ["social_psychology", "recovery_research"],
            ),
            CausalEdge(
                "coping_skills",
                "stress_level",
                CausalRelationType.DIRECT_CAUSE,
                -0.8,
                0.90,
                ["cbt_research", "clinical_trials"],
            ),
            CausalEdge(
                "substance_craving",
                "relapse_risk",
                CausalRelationType.DIRECT_CAUSE,
                0.9,
                0.95,
                ["addiction_research", "longitudinal_studies"],
            ),
            CausalEdge(
                "mood_state",
                "substance_craving",
                CausalRelationType.DIRECT_CAUSE,
                0.5,
                0.75,
                ["psychiatric_research"],
            ),
            CausalEdge(
                "sleep_quality",
                "mood_state",
                CausalRelationType.DIRECT_CAUSE,
                0.6,
                0.80,
                ["sleep_research", "mental_health"],
            ),
            CausalEdge(
                "trauma_triggers",
                "stress_level",
                CausalRelationType.DIRECT_CAUSE,
                0.8,
                0.85,
                ["trauma_research", "ptsd_studies"],
            ),
            CausalEdge(
                "medication_adherence",
                "mood_state",
                CausalRelationType.DIRECT_CAUSE,
                0.4,
                0.70,
                ["pharmacological_studies"],
            ),
            CausalEdge(
                "therapy_engagement",
                "coping_skills",
                CausalRelationType.DIRECT_CAUSE,
                0.7,
                0.85,
                ["therapy_research"],
            ),
            CausalEdge(
                "employment_status",
                "stress_level",
                CausalRelationType.INDIRECT_CAUSE,
                -0.3,
                0.65,
                ["socioeconomic_research"],
            ),
            CausalEdge(
                "physical_health",
                "mood_state",
                CausalRelationType.INDIRECT_CAUSE,
                0.4,
                0.70,
                ["health_psychology"],
            ),
            CausalEdge(
                "social_support",
                "therapy_engagement",
                CausalRelationType.MODERATOR,
                0.3,
                0.60,
                ["social_research"],
            ),
        ]

        self.edges.extend(recovery_edges)

    def add_node(self, node: CausalNode) -> bool:
        if node.name not in self.nodes:
            self.nodes[node.name] = node
            logger.info(f"Added causal node | Name={node.name} | Type={node.node_type}")
            return True
        return False

    def add_edge(self, edge: CausalEdge) -> bool:
        if edge.source in self.nodes and edge.target in self.nodes:
            self.edges.append(edge)
            logger.info(f"Added causal edge | {edge.source} -> {edge.target} | Strength={edge.strength}")
            return True
        return False

    def get_direct_causes(self, target: str) -> List[CausalEdge]:
        return [
            edge
            for edge in self.edges
            if edge.target == target and edge.relation_type == CausalRelationType.DIRECT_CAUSE
        ]

    def get_all_causes(self, target: str, visited: Optional[Set[str]] = None) -> List[str]:
        if visited is None:
            visited = set()

        if target in visited:
            return []

        visited.add(target)
        causes = []

        for edge in self.edges:
            if edge.target == target:
                causes.append(edge.source)
                causes.extend(self.get_all_causes(edge.source, visited.copy()))

        return list(set(causes))

    def find_intervention_points(self, target: str) -> List[Dict[str, Any]]:
        intervention_points = []

        for node_name, node in self.nodes.items():
            if node.interventionable:
                causes = self.get_all_causes(target)
                if node_name in causes:
                    direct_edges = [e for e in self.edges if e.source == node_name and e.target == target]
                    indirect_strength = self._calculate_indirect_effect(node_name, target)

                    intervention_points.append(
                        {
                            "node": node_name,
                            "description": node.description,
                            "direct_effect": (direct_edges[0].strength if direct_edges else 0.0),
                            "indirect_effect": indirect_strength,
                            "total_effect": (direct_edges[0].strength if direct_edges else 0.0) + indirect_strength,
                            "interventionable": True,
                        }
                    )

        return sorted(intervention_points, key=lambda x: abs(x["total_effect"]), reverse=True)

    def _calculate_indirect_effect(self, source: str, target: str) -> float:
        paths = self._find_all_paths(source, target)
        total_indirect = 0.0

        for path in paths:
            if len(path) > 2:
                path_strength = 1.0
                for i in range(len(path) - 1):
                    edge = self._find_edge(path[i], path[i + 1])
                    if edge:
                        path_strength *= edge.strength
                total_indirect += path_strength

        return total_indirect

    def _find_all_paths(self, source: str, target: str, path: Optional[List[str]] = None) -> List[List[str]]:
        if path is None:
            path = [source]

        if source == target:
            return [path]

        paths = []
        for edge in self.edges:
            if edge.source == source and edge.target not in path:
                new_paths = self._find_all_paths(edge.target, target, path + [edge.target])
                paths.extend(new_paths)

        return paths

    def _find_edge(self, source: str, target: str) -> Optional[CausalEdge]:
        for edge in self.edges:
            if edge.source == source and edge.target == target:
                return edge
        return None


class CounterfactualReasoning:
    def __init__(self, causal_graph: RecoveryCausalGraph):
        self.graph = causal_graph

    def generate_counterfactual(
        self, observed_state: Dict[str, float], intervention: Dict[str, float]
    ) -> Dict[str, Any]:
        original_outcome = self._predict_outcome(observed_state)

        counterfactual_state = observed_state.copy()
        counterfactual_state.update(intervention)

        counterfactual_outcome = self._predict_outcome(counterfactual_state)

        effect_size = counterfactual_outcome.get("relapse_risk", 0.5) - original_outcome.get("relapse_risk", 0.5)

        return {
            "original_state": observed_state,
            "intervention": intervention,
            "counterfactual_state": counterfactual_state,
            "original_outcome": original_outcome,
            "counterfactual_outcome": counterfactual_outcome,
            "causal_effect": effect_size,
            "explanation": self._generate_explanation(intervention, effect_size),
            "confidence": self._calculate_confidence(intervention),
        }

    def _predict_outcome(self, state: Dict[str, float]) -> Dict[str, float]:
        outcomes = {}

        for node_name, node in self.graph.nodes.items():
            if node.node_type == "outcome":
                causes = self.graph.get_direct_causes(node_name)
                predicted_value = 0.5

                for edge in causes:
                    if edge.source in state:
                        contribution = state[edge.source] * edge.strength * edge.confidence
                        predicted_value += contribution * 0.1

                outcomes[node_name] = np.clip(predicted_value, 0.0, 1.0)

        return outcomes

    def _generate_explanation(self, intervention: Dict[str, float], effect_size: float) -> str:
        if abs(effect_size) < 0.05:
            return f"The intervention on {list(intervention.keys())} would have minimal impact on relapse risk."

        direction = "reduce" if effect_size < 0 else "increase"
        magnitude = "significantly" if abs(effect_size) > 0.2 else "moderately"

        intervention_desc = ", ".join([f"{k} to {v:.2f}" for k, v in intervention.items()])

        return f"Changing {intervention_desc} would {magnitude} {direction} relapse risk by {abs(effect_size):.2f}."

    def _calculate_confidence(self, intervention: Dict[str, float]) -> float:
        confidences = []

        for var in intervention.keys():
            if var in self.graph.nodes:
                related_edges = [e for e in self.graph.edges if e.source == var or e.target == var]
                avg_confidence = np.mean([e.confidence for e in related_edges]) if related_edges else 0.5
                confidences.append(avg_confidence)

        return float(np.mean(np.array(confidences))) if confidences else 0.5


class CausalInferenceEngine:
    def __init__(self):
        self.causal_graph = RecoveryCausalGraph()
        self.counterfactual_reasoner = CounterfactualReasoning(self.causal_graph)
        self.inference_history: List[Dict[str, Any]] = []

    def analyze_causal_factors(self, user_state: Dict[str, float], target: str = "relapse_risk") -> Dict[str, Any]:
        direct_causes = self.causal_graph.get_direct_causes(target)
        all_causes = self.causal_graph.get_all_causes(target)

        factor_analysis = []
        for cause in direct_causes:
            if cause.source in user_state:
                current_value = user_state[cause.source]
                causal_contribution = current_value * cause.strength

                factor_analysis.append(
                    {
                        "factor": cause.source,
                        "current_value": current_value,
                        "causal_strength": cause.strength,
                        "contribution": causal_contribution,
                        "confidence": cause.confidence,
                        "description": self.causal_graph.nodes[cause.source].description,
                    }
                )

        factor_analysis.sort(key=lambda x: abs(x["contribution"]), reverse=True)

        analysis = {
            "target": target,
            "user_state": user_state,
            "direct_factors": factor_analysis,
            "all_causal_factors": all_causes,
            "top_risk_factors": factor_analysis[:3],
            "intervention_recommendations": self.causal_graph.find_intervention_points(target)[:3],
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        self.inference_history.append(analysis)
        return analysis

    def suggest_interventions(
        self, user_state: Dict[str, float], target_improvement: float = 0.2
    ) -> List[Dict[str, Any]]:
        intervention_points = self.causal_graph.find_intervention_points("relapse_risk")
        suggestions = []

        for point in intervention_points[:5]:
            node_name = point["node"]
            current_value = user_state.get(node_name, 0.5)

            if point["total_effect"] > 0:
                suggested_change = max(0.0, current_value - target_improvement)
                action = "reduce"
            else:
                suggested_change = min(1.0, current_value + target_improvement)
                action = "increase"

            intervention = {node_name: suggested_change}
            counterfactual = self.counterfactual_reasoner.generate_counterfactual(user_state, intervention)

            suggestions.append(
                {
                    "intervention_target": node_name,
                    "current_value": current_value,
                    "suggested_value": suggested_change,
                    "action": action,
                    "expected_effect": counterfactual["causal_effect"],
                    "confidence": counterfactual["confidence"],
                    "explanation": counterfactual["explanation"],
                    "description": self.causal_graph.nodes[node_name].description,
                }
            )

        return sorted(suggestions, key=lambda x: abs(x["expected_effect"]), reverse=True)

    def what_if_analysis(self, user_state: Dict[str, float], hypothetical_changes: Dict[str, float]) -> Dict[str, Any]:
        counterfactual = self.counterfactual_reasoner.generate_counterfactual(user_state, hypothetical_changes)

        analysis = {
            "scenario": "what_if_analysis",
            "hypothetical_changes": hypothetical_changes,
            "predicted_outcome": counterfactual["counterfactual_outcome"],
            "causal_effect": counterfactual["causal_effect"],
            "explanation": counterfactual["explanation"],
            "confidence": counterfactual["confidence"],
            "recommendation": self._generate_recommendation(counterfactual["causal_effect"]),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        return analysis

    def _generate_recommendation(self, causal_effect: float) -> str:
        if causal_effect < -0.1:
            return (
                "This intervention shows strong potential for reducing relapse risk. Consider implementing gradually."
            )
        elif causal_effect < -0.05:
            return "This intervention may provide modest benefits. Monitor progress carefully."
        elif causal_effect > 0.1:
            return "This change may increase relapse risk. Consider alternative approaches."
        else:
            return "This intervention is unlikely to significantly impact relapse risk."

    def get_causal_insights(self, user_id: str) -> Dict[str, Any]:
        user_analyses = [a for a in self.inference_history if a.get("user_id") == user_id]

        if not user_analyses:
            return {"message": "No causal analysis history available for this user"}

        latest_analysis = user_analyses[-1]

        return {
            "user_id": user_id,
            "total_analyses": len(user_analyses),
            "latest_analysis": latest_analysis,
            "causal_graph_summary": {
                "nodes": len(self.causal_graph.nodes),
                "edges": len(self.causal_graph.edges),
                "interventionable_factors": len([n for n in self.causal_graph.nodes.values() if n.interventionable]),
            },
            "insights": self._extract_insights(user_analyses),
        }

    def _extract_insights(self, analyses: List[Dict[str, Any]]) -> List[str]:
        insights = []

        if len(analyses) > 1:
            insights.append("Longitudinal causal analysis shows patterns in recovery factors.")

        common_factors: Dict[str, int] = {}
        for analysis in analyses:
            for factor in analysis.get("top_risk_factors", []):
                factor_name = factor["factor"]
                common_factors[factor_name] = common_factors.get(factor_name, 0) + 1

        if common_factors:
            most_common = max(common_factors.keys(), key=lambda k: common_factors[k])
            insights.append(f"'{most_common}' appears as a consistent causal factor across analyses.")

        return insights


def create_causal_inference_engine() -> CausalInferenceEngine:
    return CausalInferenceEngine()


def analyze_recovery_causality(user_state: Dict[str, float]) -> Dict[str, Any]:
    engine = create_causal_inference_engine()
    return engine.analyze_causal_factors(user_state)
