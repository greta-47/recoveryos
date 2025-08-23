import json
import os
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class FeatureFlag(Enum):
    RELEASE_20250814 = "release_20250814"
    CANARY_DEPLOYMENT = "canary_deployment"
    ENHANCED_OBSERVABILITY = "enhanced_observability"
    LOAD_BALANCING = "load_balancing"


class FeatureFlagManager:
    """Production-ready feature flag management"""

    def __init__(self, config_path: str = "feature_flags.json"):
        self.config_path = config_path
        self.flags = self._load_flags()

    def _load_flags(self) -> Dict[str, Any]:
        """Load feature flags from configuration file"""
        default_flags = {
            "release_20250814": {
                "enabled": False,
                "rollout_percentage": 0,
                "description": "Elite AI endpoints release",
                "created_at": "2025-08-14T23:47:25Z",
                "environments": {
                    "staging": {"enabled": True, "rollout_percentage": 100},
                    "production": {"enabled": False, "rollout_percentage": 0},
                },
            },
            "canary_deployment": {
                "enabled": False,
                "rollout_percentage": 5,
                "description": "Canary deployment for gradual rollout",
                "auto_rollback": {
                    "enabled": True,
                    "error_rate_threshold": 0.02,
                    "latency_threshold_ms": 1000,
                    "monitoring_window_minutes": 5,
                },
            },
            "enhanced_observability": {
                "enabled": True,
                "rollout_percentage": 100,
                "description": "Enhanced metrics and tracing",
                "features": {
                    "distributed_tracing": True,
                    "prometheus_metrics": True,
                    "structured_logging": True,
                    "pii_redaction": True,
                },
            },
        }

        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    loaded_flags = json.load(f)
                    for key, value in default_flags.items():
                        if key not in loaded_flags:
                            loaded_flags[key] = value
                    return loaded_flags
            except Exception as e:
                print(f"Error loading feature flags: {e}")
                return default_flags
        else:
            self._save_flags(default_flags)
            return default_flags

    def _save_flags(self, flags: Dict[str, Any]):
        """Save feature flags to configuration file"""
        try:
            with open(self.config_path, "w") as f:
                json.dump(flags, f, indent=2)
        except Exception as e:
            print(f"Error saving feature flags: {e}")

    def is_enabled(
        self,
        flag_name: str,
        environment: str = "staging",
        user_id: Optional[str] = None,
    ) -> bool:
        """Check if a feature flag is enabled"""
        flag = self.flags.get(flag_name)
        if not flag:
            return False

        env_config = flag.get("environments", {}).get(environment)
        if env_config:
            if not env_config.get("enabled", False):
                return False
            rollout_percentage = env_config.get("rollout_percentage", 0)
        else:
            if not flag.get("enabled", False):
                return False
            rollout_percentage = flag.get("rollout_percentage", 0)

        if rollout_percentage >= 100:
            return True
        elif rollout_percentage <= 0:
            return False
        else:
            if user_id:
                hash_value = hash(user_id) % 100
                return hash_value < rollout_percentage
            else:
                import random

                return random.randint(0, 99) < rollout_percentage

    def get_flag_config(self, flag_name: str) -> Optional[Dict[str, Any]]:
        """Get complete configuration for a feature flag"""
        return self.flags.get(flag_name)

    def update_flag(
        self,
        flag_name: str,
        enabled: bool,
        rollout_percentage: Optional[int] = None,
        environment: Optional[str] = None,
    ):
        """Update a feature flag configuration"""
        if flag_name not in self.flags:
            self.flags[flag_name] = {
                "enabled": enabled,
                "rollout_percentage": rollout_percentage or 0,
                "description": f"Feature flag {flag_name}",
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
        else:
            if environment:
                if "environments" not in self.flags[flag_name]:
                    self.flags[flag_name]["environments"] = {}
                self.flags[flag_name]["environments"][environment] = {
                    "enabled": enabled,
                    "rollout_percentage": rollout_percentage or 0,
                }
            else:
                self.flags[flag_name]["enabled"] = enabled
                if rollout_percentage is not None:
                    self.flags[flag_name]["rollout_percentage"] = rollout_percentage

        self.flags[flag_name]["updated_at"] = datetime.utcnow().isoformat() + "Z"
        self._save_flags(self.flags)

    def get_all_flags(self) -> Dict[str, Any]:
        """Get all feature flags"""
        return self.flags


feature_flags = FeatureFlagManager()
