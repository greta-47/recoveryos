import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("recoveryos")


class EliteFeature(Enum):
    FEDERATED_LEARNING = "federated_learning"
    DIFFERENTIAL_PRIVACY = "differential_privacy"
    CAUSAL_AI = "causal_ai"
    EDGE_AI = "edge_ai"
    NEUROMORPHIC = "neuromorphic"
    GRAPH_NEURAL_NETWORKS = "graph_neural_networks"
    QUANTUM_CRYPTO = "quantum_crypto"
    CONTINUAL_LEARNING = "continual_learning"
    HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"
    EXPLAINABLE_AI = "explainable_ai"


@dataclass
class FeatureConfig:
    enabled: bool = False
    priority: int = 1
    resource_allocation: float = 0.1
    safety_level: str = "high"
    clinical_validation: bool = True
    rollout_percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EliteSystemConfig:
    features: Dict[str, FeatureConfig]
    global_safety_mode: str = "maximum"
    clinical_oversight: bool = True
    privacy_level: str = "mathematical"
    performance_monitoring: bool = True
    auto_scaling: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "features": {k: v.to_dict() for k, v in self.features.items()},
            "global_safety_mode": self.global_safety_mode,
            "clinical_oversight": self.clinical_oversight,
            "privacy_level": self.privacy_level,
            "performance_monitoring": self.performance_monitoring,
            "auto_scaling": self.auto_scaling,
        }


class EliteConfigManager:
    def __init__(self, config_path: str = "elite_config.json"):
        self.config_path = config_path
        self.config = self._load_or_create_config()
        self.feature_metrics: Dict[str, Dict[str, Any]] = {}
        self.rollout_history: List[Dict[str, Any]] = []

    def _load_or_create_config(self) -> EliteSystemConfig:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    config_data = json.load(f)
                return self._deserialize_config(config_data)
            except Exception as e:
                logger.error(f"Failed to load config | Error={str(e)}")

        return self._create_default_config()

    def _create_default_config(self) -> EliteSystemConfig:
        default_features = {}

        for feature in EliteFeature:
            if feature in [
                EliteFeature.DIFFERENTIAL_PRIVACY,
                EliteFeature.EXPLAINABLE_AI,
            ]:
                default_features[feature.value] = FeatureConfig(
                    enabled=True,
                    priority=1,
                    resource_allocation=0.2,
                    rollout_percentage=100.0,
                )
            elif feature in [EliteFeature.CAUSAL_AI, EliteFeature.EDGE_AI]:
                default_features[feature.value] = FeatureConfig(
                    enabled=True,
                    priority=2,
                    resource_allocation=0.15,
                    rollout_percentage=50.0,
                )
            else:
                default_features[feature.value] = FeatureConfig(
                    enabled=False,
                    priority=3,
                    resource_allocation=0.05,
                    rollout_percentage=0.0,
                )

        config = EliteSystemConfig(features=default_features)
        self._save_config(config)
        return config

    def _deserialize_config(self, config_data: Dict[str, Any]) -> EliteSystemConfig:
        features = {}
        for feature_name, feature_data in config_data.get("features", {}).items():
            features[feature_name] = FeatureConfig(**feature_data)

        return EliteSystemConfig(
            features=features,
            global_safety_mode=config_data.get("global_safety_mode", "maximum"),
            clinical_oversight=config_data.get("clinical_oversight", True),
            privacy_level=config_data.get("privacy_level", "mathematical"),
            performance_monitoring=config_data.get("performance_monitoring", True),
            auto_scaling=config_data.get("auto_scaling", True),
        )

    def _save_config(self, config: EliteSystemConfig):
        try:
            with open(self.config_path, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
            logger.info(f"Saved elite configuration | Path={self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config | Error={str(e)}")

    def is_feature_enabled(self, feature: Union[EliteFeature, str]) -> bool:
        feature_name = feature.value if isinstance(feature, EliteFeature) else feature
        feature_config = self.config.features.get(feature_name)

        if not feature_config or not feature_config.enabled:
            return False

        if feature_config.rollout_percentage < 100.0:
            import random

            return random.random() * 100 < feature_config.rollout_percentage

        return True

    def get_feature_config(self, feature: Union[EliteFeature, str]) -> Optional[FeatureConfig]:
        feature_name = feature.value if isinstance(feature, EliteFeature) else feature
        return self.config.features.get(feature_name)

    def enable_feature(
        self,
        feature: Union[EliteFeature, str],
        rollout_percentage: float = 100.0,
        priority: int = 2,
    ) -> bool:
        feature_name = feature.value if isinstance(feature, EliteFeature) else feature

        if feature_name not in self.config.features:
            logger.error(f"Unknown feature | Feature={feature_name}")
            return False

        old_config = self.config.features[feature_name]
        self.config.features[feature_name].enabled = True
        self.config.features[feature_name].rollout_percentage = rollout_percentage
        self.config.features[feature_name].priority = priority

        self._save_config(self.config)

        self.rollout_history.append(
            {
                "feature": feature_name,
                "action": "enable",
                "rollout_percentage": rollout_percentage,
                "previous_state": old_config.enabled,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        logger.info(f"Enabled elite feature | Feature={feature_name} | Rollout={rollout_percentage}%")
        return True

    def disable_feature(self, feature: Union[EliteFeature, str]) -> bool:
        feature_name = feature.value if isinstance(feature, EliteFeature) else feature

        if feature_name not in self.config.features:
            return False

        old_config = self.config.features[feature_name]
        self.config.features[feature_name].enabled = False
        self.config.features[feature_name].rollout_percentage = 0.0

        self._save_config(self.config)

        self.rollout_history.append(
            {
                "feature": feature_name,
                "action": "disable",
                "previous_state": old_config.enabled,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

        logger.info(f"Disabled elite feature | Feature={feature_name}")
        return True

    def gradual_rollout(
        self,
        feature: Union[EliteFeature, str],
        target_percentage: float,
        increment: float = 10.0,
    ) -> Dict[str, Any]:
        feature_name = feature.value if isinstance(feature, EliteFeature) else feature
        feature_config = self.get_feature_config(feature_name)

        if not feature_config:
            return {"error": f"Feature {feature_name} not found"}

        current_percentage = feature_config.rollout_percentage

        if current_percentage >= target_percentage:
            return {
                "feature": feature_name,
                "current_percentage": current_percentage,
                "target_percentage": target_percentage,
                "status": "target_reached",
            }

        new_percentage = min(target_percentage, current_percentage + increment)
        feature_config.rollout_percentage = new_percentage
        feature_config.enabled = True

        self._save_config(self.config)

        rollout_info = {
            "feature": feature_name,
            "previous_percentage": current_percentage,
            "new_percentage": new_percentage,
            "target_percentage": target_percentage,
            "increment": increment,
            "status": ("in_progress" if new_percentage < target_percentage else "completed"),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        self.rollout_history.append(rollout_info)
        logger.info(f"Gradual rollout update | {rollout_info}")

        return rollout_info

    def record_feature_metrics(self, feature: Union[EliteFeature, str], metrics: Dict[str, Any]):
        feature_name = feature.value if isinstance(feature, EliteFeature) else feature

        if feature_name not in self.feature_metrics:
            self.feature_metrics[feature_name] = {
                "performance_history": [],
                "error_count": 0,
                "success_count": 0,
                "avg_latency": 0.0,
            }

        self.feature_metrics[feature_name]["performance_history"].append(
            {**metrics, "timestamp": datetime.utcnow().isoformat() + "Z"}
        )

        if metrics.get("success", True):
            self.feature_metrics[feature_name]["success_count"] += 1
        else:
            self.feature_metrics[feature_name]["error_count"] += 1

        if "latency_ms" in metrics:
            current_avg = self.feature_metrics[feature_name]["avg_latency"]
            total_calls = (
                self.feature_metrics[feature_name]["success_count"] + self.feature_metrics[feature_name]["error_count"]
            )

            new_avg = ((current_avg * (total_calls - 1)) + metrics["latency_ms"]) / total_calls
            self.feature_metrics[feature_name]["avg_latency"] = new_avg

        self._auto_adjust_rollout(feature_name)

    def _auto_adjust_rollout(self, feature_name: str):
        if not self.config.auto_scaling:
            return

        metrics = self.feature_metrics.get(feature_name, {})
        total_calls = metrics.get("success_count", 0) + metrics.get("error_count", 0)

        if total_calls < 10:
            return

        error_rate = metrics.get("error_count", 0) / total_calls
        avg_latency = metrics.get("avg_latency", 0)

        feature_config = self.config.features.get(feature_name)
        if not feature_config:
            return

        current_rollout = feature_config.rollout_percentage

        if error_rate > 0.1 and current_rollout > 10:
            new_rollout = max(10, current_rollout - 20)
            feature_config.rollout_percentage = new_rollout
            logger.warning(f"Auto-reduced rollout due to errors | Feature={feature_name} | NewRollout={new_rollout}%")

        elif error_rate < 0.02 and avg_latency < 100 and current_rollout < 100:
            new_rollout = min(100, current_rollout + 10)
            feature_config.rollout_percentage = new_rollout
            logger.info(
                f"Auto-increased rollout due to good performance | Feature={feature_name} | NewRollout={new_rollout}%"
            )

        self._save_config(self.config)

    def get_system_status(self) -> Dict[str, Any]:
        enabled_features = []
        disabled_features = []

        for feature_name, config in self.config.features.items():
            if config.enabled:
                enabled_features.append(
                    {
                        "name": feature_name,
                        "rollout_percentage": config.rollout_percentage,
                        "priority": config.priority,
                        "metrics": self.feature_metrics.get(feature_name, {}),
                    }
                )
            else:
                disabled_features.append(feature_name)

        return {
            "enabled_features": enabled_features,
            "disabled_features": disabled_features,
            "global_config": {
                "safety_mode": self.config.global_safety_mode,
                "clinical_oversight": self.config.clinical_oversight,
                "privacy_level": self.config.privacy_level,
                "auto_scaling": self.config.auto_scaling,
            },
            "rollout_history": self.rollout_history[-10:],
            "system_health": self._calculate_system_health(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

    def _calculate_system_health(self) -> Dict[str, Any]:
        total_features = len(self.config.features)
        enabled_features = sum(1 for f in self.config.features.values() if f.enabled)

        total_errors = sum(m.get("error_count", 0) for m in self.feature_metrics.values())
        total_successes = sum(m.get("success_count", 0) for m in self.feature_metrics.values())

        success_rate = (
            total_successes / (total_successes + total_errors) if (total_successes + total_errors) > 0 else 1.0
        )

        avg_latencies = [m.get("avg_latency", 0) for m in self.feature_metrics.values() if m.get("avg_latency", 0) > 0]
        avg_system_latency = sum(avg_latencies) / len(avg_latencies) if avg_latencies else 0

        health_score = (
            success_rate * 0.6
            + (enabled_features / total_features) * 0.2
            + (1.0 - min(1.0, avg_system_latency / 1000)) * 0.2
        )

        return {
            "health_score": health_score,
            "success_rate": success_rate,
            "enabled_feature_ratio": enabled_features / total_features,
            "avg_latency_ms": avg_system_latency,
            "status": ("excellent" if health_score > 0.9 else "good" if health_score > 0.7 else "needs_attention"),
        }


_config_manager = None


def get_elite_config() -> EliteConfigManager:
    global _config_manager
    if _config_manager is None:
        _config_manager = EliteConfigManager()
    return _config_manager


def is_elite_feature_enabled(feature: Union[EliteFeature, str]) -> bool:
    return get_elite_config().is_feature_enabled(feature)


def record_elite_metrics(feature: Union[EliteFeature, str], metrics: Dict[str, Any]):
    get_elite_config().record_feature_metrics(feature, metrics)
