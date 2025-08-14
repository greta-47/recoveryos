import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime
import numpy as np
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger("recoveryos")

class NodeType(Enum):
    USER = "user"
    FACTOR = "factor"
    INTERVENTION = "intervention"
    OUTCOME = "outcome"
    TEMPORAL = "temporal"

class EdgeType(Enum):
    INFLUENCES = "influences"
    CORRELATES = "correlates"
    PRECEDES = "precedes"
    MODERATES = "moderates"
    MEDIATES = "mediates"

@dataclass
class GraphNode:
    node_id: str
    node_type: NodeType
    features: Dict[str, float]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "features": self.features,
            "metadata": self.metadata
        }

@dataclass
class GraphEdge:
    source: str
    target: str
    edge_type: EdgeType
    weight: float
    confidence: float
    temporal_lag: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "confidence": self.confidence,
            "temporal_lag": self.temporal_lag
        }

class RecoveryKnowledgeGraph:
    def __init__(self):
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.adjacency_matrix: Optional[np.ndarray] = None
        self.node_embeddings: Dict[str, np.ndarray] = {}
        self._initialize_recovery_graph()
    
    def _initialize_recovery_graph(self):
        recovery_factors = [
            ("stress", NodeType.FACTOR, {"baseline": 0.5, "volatility": 0.3}, {"category": "psychological"}),
            ("social_support", NodeType.FACTOR, {"baseline": 0.7, "volatility": 0.2}, {"category": "social"}),
            ("coping_skills", NodeType.FACTOR, {"baseline": 0.6, "volatility": 0.4}, {"category": "behavioral"}),
            ("mood", NodeType.FACTOR, {"baseline": 0.5, "volatility": 0.5}, {"category": "psychological"}),
            ("sleep_quality", NodeType.FACTOR, {"baseline": 0.6, "volatility": 0.3}, {"category": "physiological"}),
            ("physical_health", NodeType.FACTOR, {"baseline": 0.7, "volatility": 0.2}, {"category": "physiological"}),
            ("employment", NodeType.FACTOR, {"baseline": 0.5, "volatility": 0.1}, {"category": "social"}),
            ("financial_stress", NodeType.FACTOR, {"baseline": 0.4, "volatility": 0.3}, {"category": "social"})
        ]
        
        for node_id, node_type, features, metadata in recovery_factors:
            node = GraphNode(node_id, node_type, features, metadata)
            self.add_node(node)
        
        interventions = [
            ("therapy", NodeType.INTERVENTION, {"effectiveness": 0.8, "accessibility": 0.6}, {"type": "professional"}),
            ("meditation", NodeType.INTERVENTION, {"effectiveness": 0.6, "accessibility": 0.9}, {"type": "self_care"}),
            ("exercise", NodeType.INTERVENTION, {"effectiveness": 0.7, "accessibility": 0.8}, {"type": "lifestyle"}),
            ("support_group", NodeType.INTERVENTION, {"effectiveness": 0.7, "accessibility": 0.7}, {"type": "social"}),
            ("medication", NodeType.INTERVENTION, {"effectiveness": 0.8, "accessibility": 0.5}, {"type": "medical"})
        ]
        
        for node_id, node_type, features, metadata in interventions:
            node = GraphNode(node_id, node_type, features, metadata)
            self.add_node(node)
        
        outcomes = [
            ("relapse_risk", NodeType.OUTCOME, {"severity": 0.8, "predictability": 0.7}, {"primary": True}),
            ("quality_of_life", NodeType.OUTCOME, {"importance": 0.9, "measurability": 0.6}, {"primary": False}),
            ("treatment_engagement", NodeType.OUTCOME, {"importance": 0.8, "measurability": 0.8}, {"primary": False})
        ]
        
        for node_id, node_type, features, metadata in outcomes:
            node = GraphNode(node_id, node_type, features, metadata)
            self.add_node(node)
        
        relationships = [
            ("stress", "relapse_risk", EdgeType.INFLUENCES, 0.8, 0.9),
            ("social_support", "stress", EdgeType.INFLUENCES, -0.6, 0.8),
            ("coping_skills", "stress", EdgeType.INFLUENCES, -0.7, 0.85),
            ("mood", "relapse_risk", EdgeType.INFLUENCES, 0.6, 0.75),
            ("sleep_quality", "mood", EdgeType.INFLUENCES, 0.5, 0.7),
            ("physical_health", "mood", EdgeType.INFLUENCES, 0.4, 0.65),
            ("employment", "financial_stress", EdgeType.INFLUENCES, -0.8, 0.9),
            ("financial_stress", "stress", EdgeType.INFLUENCES, 0.7, 0.8),
            ("therapy", "coping_skills", EdgeType.INFLUENCES, 0.8, 0.9),
            ("meditation", "stress", EdgeType.INFLUENCES, -0.5, 0.7),
            ("exercise", "mood", EdgeType.INFLUENCES, 0.6, 0.8),
            ("exercise", "physical_health", EdgeType.INFLUENCES, 0.8, 0.9),
            ("support_group", "social_support", EdgeType.INFLUENCES, 0.7, 0.8),
            ("medication", "mood", EdgeType.INFLUENCES, 0.6, 0.7),
            ("coping_skills", "treatment_engagement", EdgeType.INFLUENCES, 0.5, 0.7),
            ("social_support", "quality_of_life", EdgeType.INFLUENCES, 0.7, 0.8)
        ]
        
        for source, target, edge_type, weight, confidence in relationships:
            edge = GraphEdge(source, target, edge_type, weight, confidence)
            self.add_edge(edge)
        
        logger.info(f"Initialized recovery knowledge graph | Nodes={len(self.nodes)} | Edges={len(self.edges)}")
    
    def add_node(self, node: GraphNode) -> bool:
        if node.node_id not in self.nodes:
            self.nodes[node.node_id] = node
            self.adjacency_matrix = None  # Invalidate cached matrix
            return True
        return False
    
    def add_edge(self, edge: GraphEdge) -> bool:
        if edge.source in self.nodes and edge.target in self.nodes:
            self.edges.append(edge)
            self.adjacency_matrix = None  # Invalidate cached matrix
            return True
        return False
    
    def get_adjacency_matrix(self) -> np.ndarray:
        if self.adjacency_matrix is None:
            n = len(self.nodes)
            self.adjacency_matrix = np.zeros((n, n))
            
            node_to_idx = {node_id: i for i, node_id in enumerate(self.nodes.keys())}
            
            for edge in self.edges:
                i = node_to_idx[edge.source]
                j = node_to_idx[edge.target]
                self.adjacency_matrix[i, j] = edge.weight
        
        return self.adjacency_matrix
    
    def get_neighbors(self, node_id: str, edge_type: Optional[EdgeType] = None) -> List[str]:
        neighbors = []
        for edge in self.edges:
            if edge.source == node_id:
                if edge_type is None or edge.edge_type == edge_type:
                    neighbors.append(edge.target)
        return neighbors
    
    def find_paths(self, source: str, target: str, max_length: int = 3) -> List[List[str]]:
        paths = []
        
        def dfs(current: str, path: List[str], visited: Set[str]):
            if len(path) > max_length:
                return
            
            if current == target and len(path) > 1:
                paths.append(path.copy())
                return
            
            if current in visited:
                return
            
            visited.add(current)
            
            for neighbor in self.get_neighbors(current):
                if neighbor not in visited:
                    path.append(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
            
            visited.remove(current)
        
        dfs(source, [source], set())
        return paths
    
    def calculate_influence_score(self, source: str, target: str) -> float:
        paths = self.find_paths(source, target)
        
        if not paths:
            return 0.0
        
        total_influence = 0.0
        
        for path in paths:
            path_influence = 1.0
            
            for i in range(len(path) - 1):
                edge = self._find_edge(path[i], path[i + 1])
                if edge:
                    path_influence *= edge.weight * edge.confidence
                else:
                    path_influence = 0.0
                    break
            
            path_influence *= (0.8 ** (len(path) - 2))
            total_influence += path_influence
        
        return min(1.0, total_influence)
    
    def _find_edge(self, source: str, target: str) -> Optional[GraphEdge]:
        for edge in self.edges:
            if edge.source == source and edge.target == target:
                return edge
        return None

class GraphNeuralNetwork:
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        self.W1 = np.random.normal(0, 0.1, (input_dim, hidden_dim))
        self.W2 = np.random.normal(0, 0.1, (hidden_dim, output_dim))
        self.b1 = np.zeros(hidden_dim)
        self.b2 = np.zeros(output_dim)
        
        self.training_history: List[Dict[str, Any]] = []
    
    def forward(self, node_features: np.ndarray, adjacency: np.ndarray) -> np.ndarray:
        A_hat = adjacency + np.eye(adjacency.shape[0])
        
        D = np.diag(np.sum(A_hat, axis=1) ** -0.5)
        A_norm = D @ A_hat @ D
        
        H1 = A_norm @ node_features @ self.W1 + self.b1
        H1 = np.maximum(0, H1)  # ReLU activation
        
        H2 = A_norm @ H1 @ self.W2 + self.b2
        
        output = 1.0 / (1.0 + np.exp(-H2))
        
        return output
    
    def predict_node_outcomes(self, graph: RecoveryKnowledgeGraph, 
                            user_state: Dict[str, float]) -> Dict[str, float]:
        node_features = []
        node_order = list(graph.nodes.keys())
        
        for node_id in node_order:
            node = graph.nodes[node_id]
            
            features = list(node.features.values())
            
            if node_id in user_state:
                features.append(user_state[node_id])
            else:
                features.append(0.5)  # Default value
            
            while len(features) < self.input_dim:
                features.append(0.0)
            features = features[:self.input_dim]
            
            node_features.append(features)
        
        node_features = np.array(node_features)
        adjacency = graph.get_adjacency_matrix()
        
        predictions = self.forward(node_features, adjacency)
        
        results = {}
        for i, node_id in enumerate(node_order):
            if graph.nodes[node_id].node_type == NodeType.OUTCOME:
                results[node_id] = float(predictions[i, 0])
        
        return results
    
    def train_step(self, graph: RecoveryKnowledgeGraph, 
                  training_data: List[Dict[str, Any]], 
                  learning_rate: float = 0.01) -> float:
        total_loss = 0.0
        
        for sample in training_data:
            user_state = sample["user_state"]
            true_outcomes = sample["outcomes"]
            
            predictions = self.predict_node_outcomes(graph, user_state)
            
            loss = 0.0
            for outcome, true_value in true_outcomes.items():
                if outcome in predictions:
                    loss += (predictions[outcome] - true_value) ** 2
            
            total_loss += loss
            
            for outcome, true_value in true_outcomes.items():
                if outcome in predictions:
                    error = predictions[outcome] - true_value
                    self.W2 -= learning_rate * error * 0.01
                    self.W1 -= learning_rate * error * 0.001
        
        avg_loss = total_loss / len(training_data)
        
        self.training_history.append({
            "loss": avg_loss,
            "samples": len(training_data),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        return avg_loss

class RecoveryGraphAnalyzer:
    def __init__(self):
        self.knowledge_graph = RecoveryKnowledgeGraph()
        self.gnn = GraphNeuralNetwork(input_dim=4, hidden_dim=8, output_dim=1)
        self.analysis_history: List[Dict[str, Any]] = []
    
    def analyze_user_recovery_network(self, user_id: str, 
                                    user_state: Dict[str, float]) -> Dict[str, Any]:
        outcome_predictions = self.gnn.predict_node_outcomes(self.knowledge_graph, user_state)
        
        influence_analysis = {}
        for factor in user_state.keys():
            if factor in self.knowledge_graph.nodes:
                influence_analysis[factor] = {}
                for outcome in outcome_predictions.keys():
                    influence_score = self.knowledge_graph.calculate_influence_score(factor, outcome)
                    influence_analysis[factor][outcome] = influence_score
        
        critical_paths = self._find_critical_paths(user_state, outcome_predictions)
        
        interventions = self._recommend_interventions(user_state, outcome_predictions)
        
        analysis = {
            "user_id": user_id,
            "user_state": user_state,
            "predicted_outcomes": outcome_predictions,
            "influence_analysis": influence_analysis,
            "critical_paths": critical_paths,
            "intervention_recommendations": interventions,
            "graph_complexity": {
                "nodes": len(self.knowledge_graph.nodes),
                "edges": len(self.knowledge_graph.edges),
                "connectivity": len(self.knowledge_graph.edges) / len(self.knowledge_graph.nodes)
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        self.analysis_history.append(analysis)
        return analysis
    
    def _find_critical_paths(self, user_state: Dict[str, float], 
                           outcomes: Dict[str, float]) -> List[Dict[str, Any]]:
        critical_paths = []
        
        high_risk_factors = [f for f, v in user_state.items() if v > 0.7]
        negative_outcomes = [o for o, v in outcomes.items() if v > 0.6]
        
        for factor in high_risk_factors:
            for outcome in negative_outcomes:
                paths = self.knowledge_graph.find_paths(factor, outcome)
                for path in paths:
                    path_strength = self._calculate_path_strength(path)
                    critical_paths.append({
                        "path": path,
                        "strength": path_strength,
                        "risk_factor": factor,
                        "outcome": outcome,
                        "intervention_points": self._identify_intervention_points(path)
                    })
        
        critical_paths.sort(key=lambda x: x["strength"], reverse=True)
        return critical_paths[:5]  # Top 5 critical paths
    
    def _calculate_path_strength(self, path: List[str]) -> float:
        strength = 1.0
        
        for i in range(len(path) - 1):
            edge = self.knowledge_graph._find_edge(path[i], path[i + 1])
            if edge:
                strength *= abs(edge.weight) * edge.confidence
            else:
                return 0.0
        
        return strength
    
    def _identify_intervention_points(self, path: List[str]) -> List[str]:
        intervention_points = []
        
        for node_id in path:
            node = self.knowledge_graph.nodes.get(node_id)
            if node and node.node_type == NodeType.INTERVENTION:
                intervention_points.append(node_id)
            elif node and node.node_type == NodeType.FACTOR:
                for intervention_id, intervention_node in self.knowledge_graph.nodes.items():
                    if intervention_node.node_type == NodeType.INTERVENTION:
                        if node_id in self.knowledge_graph.get_neighbors(intervention_id):
                            intervention_points.append(intervention_id)
        
        return list(set(intervention_points))
    
    def _recommend_interventions(self, user_state: Dict[str, float], 
                               outcomes: Dict[str, float]) -> List[Dict[str, Any]]:
        recommendations = []
        
        for intervention_id, intervention_node in self.knowledge_graph.nodes.items():
            if intervention_node.node_type == NodeType.INTERVENTION:
                intervention_score = 0.0
                affected_outcomes = []
                
                for outcome in outcomes.keys():
                    influence = self.knowledge_graph.calculate_influence_score(intervention_id, outcome)
                    if influence > 0.1:
                        intervention_score += influence * (1.0 - outcomes[outcome])
                        affected_outcomes.append(outcome)
                
                if intervention_score > 0.0:
                    recommendations.append({
                        "intervention": intervention_id,
                        "effectiveness": intervention_node.features.get("effectiveness", 0.5),
                        "accessibility": intervention_node.features.get("accessibility", 0.5),
                        "potential_impact": intervention_score,
                        "affected_outcomes": affected_outcomes,
                        "priority": intervention_score * intervention_node.features.get("effectiveness", 0.5)
                    })
        
        recommendations.sort(key=lambda x: x["priority"], reverse=True)
        return recommendations[:3]  # Top 3 recommendations
    
    def update_graph_with_user_data(self, user_data: List[Dict[str, Any]]):
        edge_updates = defaultdict(list)
        
        for data_point in user_data:
            user_state = data_point.get("user_state", {})
            outcomes = data_point.get("outcomes", {})
            
            for factor, factor_value in user_state.items():
                for outcome, outcome_value in outcomes.items():
                    correlation = np.corrcoef([factor_value], [outcome_value])[0, 1]
                    if not np.isnan(correlation):
                        edge_updates[(factor, outcome)].append(correlation)
        
        for (source, target), correlations in edge_updates.items():
            avg_correlation = np.mean(correlations)
            edge = self.knowledge_graph._find_edge(source, target)
            
            if edge:
                alpha = 0.1
                new_weight = (1 - alpha) * edge.weight + alpha * avg_correlation
                new_confidence = min(1.0, edge.confidence + 0.01)
                
                updated_edge = GraphEdge(
                    source=edge.source,
                    target=edge.target,
                    edge_type=edge.edge_type,
                    weight=float(new_weight),
                    confidence=float(new_confidence),
                    temporal_lag=edge.temporal_lag
                )
                
                for i, e in enumerate(self.knowledge_graph.edges):
                    if e.source == edge.source and e.target == edge.target:
                        self.knowledge_graph.edges[i] = updated_edge
                        break
        
        logger.info(f"Updated graph with {len(user_data)} data points")
    
    def get_graph_insights(self) -> Dict[str, Any]:
        if not self.analysis_history:
            return {"message": "No analysis history available"}
        
        recent_analyses = self.analysis_history[-10:]
        
        common_risk_factors = defaultdict(int)
        common_interventions = defaultdict(int)
        
        for analysis in recent_analyses:
            for path in analysis.get("critical_paths", []):
                common_risk_factors[path["risk_factor"]] += 1
                for intervention in path.get("intervention_points", []):
                    common_interventions[intervention] += 1
        
        return {
            "total_analyses": len(self.analysis_history),
            "graph_structure": {
                "nodes": len(self.knowledge_graph.nodes),
                "edges": len(self.knowledge_graph.edges),
                "node_types": {nt.value: sum(1 for n in self.knowledge_graph.nodes.values() if n.node_type == nt) 
                              for nt in NodeType}
            },
            "common_risk_factors": dict(common_risk_factors),
            "effective_interventions": dict(common_interventions),
            "gnn_training_progress": len(self.gnn.training_history),
            "insights": self._generate_graph_insights(recent_analyses)
        }
    
    def _generate_graph_insights(self, analyses: List[Dict[str, Any]]) -> List[str]:
        insights = []
        
        if len(analyses) > 5:
            insights.append("Graph neural network analysis shows consistent recovery factor patterns")
        
        outcome_trends = defaultdict(list)
        for analysis in analyses:
            for outcome, value in analysis.get("predicted_outcomes", {}).items():
                outcome_trends[outcome].append(value)
        
        for outcome, values in outcome_trends.items():
            if len(values) > 3:
                trend = np.polyfit(range(len(values)), values, 1)[0]
                if trend > 0.05:
                    insights.append(f"Graph analysis indicates increasing risk trend for {outcome}")
                elif trend < -0.05:
                    insights.append(f"Graph analysis shows improving trend for {outcome}")
        
        return insights

def create_recovery_graph_analyzer() -> RecoveryGraphAnalyzer:
    return RecoveryGraphAnalyzer()

def analyze_recovery_network(user_id: str, user_state: Dict[str, float]) -> Dict[str, Any]:
    analyzer = create_recovery_graph_analyzer()
    return analyzer.analyze_user_recovery_network(user_id, user_state)
