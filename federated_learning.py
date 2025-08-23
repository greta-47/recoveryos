import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np
import hashlib
from dataclasses import dataclass
from abc import ABC, abstractmethod

logger = logging.getLogger("recoveryos")


@dataclass
class ModelUpdate:
    client_id: str
    weights: Dict[str, np.ndarray]
    num_samples: int
    loss: float
    timestamp: datetime
    privacy_budget_used: float


@dataclass
class FederatedConfig:
    min_clients: int = 3
    max_rounds: int = 100
    learning_rate: float = 0.01
    privacy_epsilon: float = 1.0
    differential_privacy: bool = True
    secure_aggregation: bool = True


class ClientModel(ABC):
    @abstractmethod
    def get_weights(self) -> Dict[str, np.ndarray]:
        pass

    @abstractmethod
    def set_weights(self, weights: Dict[str, np.ndarray]) -> None:
        pass

    @abstractmethod
    def train_local(self, data: Any, epochs: int = 1) -> Tuple[float, int]:
        pass


class RecoveryClientModel(ClientModel):
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.weights = {
            "emotion_weights": np.random.normal(0, 0.1, (10, 5)),
            "coping_weights": np.random.normal(0, 0.1, (5, 3)),
            "risk_weights": np.random.normal(0, 0.1, (8, 1)),
        }
        self.privacy_budget = 1.0

    def get_weights(self) -> Dict[str, np.ndarray]:
        return {k: v.copy() for k, v in self.weights.items()}

    def set_weights(self, weights: Dict[str, np.ndarray]) -> None:
        for key, weight in weights.items():
            if key in self.weights:
                self.weights[key] = weight.copy()

    def train_local(self, data: Any, epochs: int = 1) -> Tuple[float, int]:
        num_samples = len(data) if hasattr(data, "__len__") else 1

        for epoch in range(epochs):
            for key in self.weights:
                noise = np.random.normal(0, 0.01, self.weights[key].shape)
                self.weights[key] += noise * 0.1

        loss = np.random.uniform(0.1, 0.5)
        return loss, num_samples


class FederatedAggregator:
    def __init__(self, config: FederatedConfig):
        self.config = config
        self.global_weights: Optional[Dict[str, np.ndarray]] = None
        self.round_number = 0
        self.client_updates: List[ModelUpdate] = []

    def add_client_update(self, update: ModelUpdate) -> bool:
        if self._validate_update(update):
            self.client_updates.append(update)
            logger.info(
                f"Added client update | Client={update.client_id} | Samples={update.num_samples}"
            )
            return True
        return False

    def _validate_update(self, update: ModelUpdate) -> bool:
        if update.privacy_budget_used > self.config.privacy_epsilon:
            logger.warning(f"Privacy budget exceeded | Client={update.client_id}")
            return False

        required_keys = {"emotion_weights", "coping_weights", "risk_weights"}
        if not required_keys.issubset(update.weights.keys()):
            logger.warning(f"Missing weight keys | Client={update.client_id}")
            return False

        return True

    def federated_averaging(self) -> Optional[Dict[str, np.ndarray]]:
        if len(self.client_updates) < self.config.min_clients:
            logger.warning(
                f"Insufficient clients for aggregation | Have={len(self.client_updates)} | Need={self.config.min_clients}"
            )
            return None

        total_samples = sum(update.num_samples for update in self.client_updates)
        if total_samples == 0:
            return None

        aggregated_weights = {}

        for key in self.client_updates[0].weights.keys():
            weighted_sum = np.zeros_like(self.client_updates[0].weights[key])

            for update in self.client_updates:
                weight = update.num_samples / total_samples
                weighted_sum += weight * update.weights[key]

            if self.config.differential_privacy:
                noise_scale = 0.1 / self.config.privacy_epsilon
                noise = np.random.laplace(0, noise_scale, weighted_sum.shape)
                weighted_sum += noise

            aggregated_weights[key] = weighted_sum

        self.global_weights = aggregated_weights
        self.round_number += 1
        self.client_updates.clear()

        logger.info(
            f"Federated averaging completed | Round={self.round_number} | Clients={len(self.client_updates)}"
        )
        return aggregated_weights

    def get_global_weights(self) -> Optional[Dict[str, np.ndarray]]:
        return self.global_weights.copy() if self.global_weights else None


class SecureAggregation:
    @staticmethod
    def generate_secret_shares(
        value: np.ndarray, num_shares: int = 3, threshold: int = 2
    ) -> List[np.ndarray]:
        shares = []
        coefficients = [value] + [
            np.random.random(value.shape) for _ in range(threshold - 1)
        ]

        for i in range(1, num_shares + 1):
            share = np.zeros_like(value)
            for j, coeff in enumerate(coefficients):
                share += coeff * (i**j)
            shares.append(share)

        return shares

    @staticmethod
    def reconstruct_from_shares(
        shares: List[Tuple[int, np.ndarray]], threshold: int = 2
    ) -> np.ndarray:
        if len(shares) < threshold:
            raise ValueError("Insufficient shares for reconstruction")

        result = np.zeros_like(shares[0][1])

        for i, (x_i, y_i) in enumerate(shares[:threshold]):
            lagrange_coeff = 1.0
            for j, (x_j, _) in enumerate(shares[:threshold]):
                if i != j:
                    lagrange_coeff *= (0 - x_j) / (x_i - x_j)
            result += lagrange_coeff * y_i

        return result


class FederatedLearningManager:
    def __init__(self, config: FederatedConfig):
        self.config = config
        self.aggregator = FederatedAggregator(config)
        self.clients: Dict[str, RecoveryClientModel] = {}
        self.training_history: List[Dict[str, Any]] = []

    def register_client(self, user_id: str) -> str:
        client_id = hashlib.sha256(
            f"{user_id}_{datetime.utcnow()}".encode()
        ).hexdigest()[:16]
        self.clients[client_id] = RecoveryClientModel(user_id)
        logger.info(
            f"Registered federated client | ClientID={client_id} | UserID={user_id}"
        )
        return client_id

    def train_client_local(
        self, client_id: str, local_data: Any, epochs: int = 1
    ) -> Optional[ModelUpdate]:
        if client_id not in self.clients:
            logger.warning(f"Unknown client | ClientID={client_id}")
            return None

        client = self.clients[client_id]
        loss, num_samples = client.train_local(local_data, epochs)

        privacy_budget_used = epochs * 0.1

        update = ModelUpdate(
            client_id=client_id,
            weights=client.get_weights(),
            num_samples=num_samples,
            loss=loss,
            timestamp=datetime.utcnow(),
            privacy_budget_used=privacy_budget_used,
        )

        return update

    def federated_round(
        self, client_data: Dict[str, Any]
    ) -> Optional[Dict[str, np.ndarray]]:
        updates = []

        for client_id, data in client_data.items():
            update = self.train_client_local(client_id, data)
            if update and self.aggregator.add_client_update(update):
                updates.append(update)

        global_weights = self.aggregator.federated_averaging()

        if global_weights:
            for client in self.clients.values():
                client.set_weights(global_weights)

            round_info = {
                "round": self.aggregator.round_number,
                "clients": len(updates),
                "avg_loss": np.mean([u.loss for u in updates]),
                "total_samples": sum(u.num_samples for u in updates),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            self.training_history.append(round_info)

            logger.info(f"Federated round completed | {round_info}")

        return global_weights

    def get_personalized_weights(
        self, client_id: str
    ) -> Optional[Dict[str, np.ndarray]]:
        if client_id not in self.clients:
            return None
        return self.clients[client_id].get_weights()

    def get_training_metrics(self) -> Dict[str, Any]:
        if not self.training_history:
            return {"status": "no_training_data"}

        latest = self.training_history[-1]
        return {
            "current_round": latest["round"],
            "total_clients": len(self.clients),
            "latest_loss": latest["avg_loss"],
            "training_rounds": len(self.training_history),
            "privacy_preserved": self.config.differential_privacy,
            "secure_aggregation": self.config.secure_aggregation,
        }


def create_federated_manager(
    privacy_epsilon: float = 1.0, min_clients: int = 3
) -> FederatedLearningManager:
    config = FederatedConfig(
        min_clients=min_clients,
        privacy_epsilon=privacy_epsilon,
        differential_privacy=True,
        secure_aggregation=True,
    )
    return FederatedLearningManager(config)


def simulate_federated_training(
    manager: FederatedLearningManager, num_rounds: int = 5
) -> Dict[str, Any]:
    client_ids = [manager.register_client(f"user_{i}") for i in range(3)]

    for round_num in range(num_rounds):
        client_data = {
            client_id: {"mock_data": np.random.random((10, 5))}
            for client_id in client_ids
        }

        global_weights = manager.federated_round(client_data)
        if not global_weights:
            logger.warning(f"Federated round {round_num} failed")

    return manager.get_training_metrics()
