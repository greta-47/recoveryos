import heapq
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("recoveryos")


class NeuronType(Enum):
    EXCITATORY = "excitatory"
    INHIBITORY = "inhibitory"
    SENSORY = "sensory"
    MOTOR = "motor"


@dataclass
class Spike:
    neuron_id: int
    timestamp: float
    amplitude: float = 1.0

    def __lt__(self, other):
        return self.timestamp < other.timestamp


@dataclass
class Synapse:
    pre_neuron: int
    post_neuron: int
    weight: float
    delay: float
    plasticity: bool = True

    def transmit_spike(self, spike: Spike) -> Spike:
        return Spike(
            neuron_id=self.post_neuron,
            timestamp=spike.timestamp + self.delay,
            amplitude=spike.amplitude * self.weight,
        )


class SpikingNeuron:
    def __init__(self, neuron_id: int, neuron_type: NeuronType, threshold: float = 1.0):
        self.neuron_id = neuron_id
        self.neuron_type = neuron_type
        self.threshold = threshold
        self.membrane_potential = 0.0
        self.refractory_period = 2.0  # ms
        self.last_spike_time = -float("inf")
        self.leak_rate = 0.1
        self.spike_history: List[float] = []

    def update(self, current_time: float, input_current: float = 0.0) -> Optional[Spike]:
        if current_time - self.last_spike_time < self.refractory_period:
            return None

        time_delta = current_time - getattr(self, "last_update_time", current_time)
        self.membrane_potential *= np.exp(-self.leak_rate * time_delta)

        self.membrane_potential += input_current

        if self.membrane_potential >= self.threshold:
            spike = Spike(self.neuron_id, current_time)
            self.membrane_potential = 0.0  # Reset
            self.last_spike_time = current_time
            self.spike_history.append(current_time)

            cutoff_time = current_time - 1000.0  # Last 1 second
            self.spike_history = [t for t in self.spike_history if t > cutoff_time]

            return spike

        self.last_update_time = current_time
        return None

    def get_firing_rate(self, window_ms: float = 100.0) -> float:
        current_time = datetime.utcnow().timestamp() * 1000
        recent_spikes = [t for t in self.spike_history if t > current_time - window_ms]
        return len(recent_spikes) / (window_ms / 1000.0)  # Hz


class SpikingNeuralNetwork:
    def __init__(self, name: str):
        self.name = name
        self.neurons: Dict[int, SpikingNeuron] = {}
        self.synapses: List[Synapse] = []
        self.spike_queue: List[Spike] = []
        self.current_time = 0.0
        self.time_step = 0.1  # ms
        self.network_activity: List[Dict[str, Any]] = []

    def add_neuron(self, neuron: SpikingNeuron) -> bool:
        if neuron.neuron_id not in self.neurons:
            self.neurons[neuron.neuron_id] = neuron
            logger.debug(f"Added neuron | ID={neuron.neuron_id} | Type={neuron.neuron_type.value}")
            return True
        return False

    def add_synapse(self, synapse: Synapse) -> bool:
        if synapse.pre_neuron in self.neurons and synapse.post_neuron in self.neurons:
            self.synapses.append(synapse)
            logger.debug(f"Added synapse | {synapse.pre_neuron} -> {synapse.post_neuron} | Weight={synapse.weight}")
            return True
        return False

    def inject_current(self, neuron_id: int, current: float):
        if neuron_id in self.neurons:
            spike = self.neurons[neuron_id].update(self.current_time, current)
            if spike:
                heapq.heappush(self.spike_queue, spike)
                self._propagate_spike(spike)

    def _propagate_spike(self, spike: Spike):
        for synapse in self.synapses:
            if synapse.pre_neuron == spike.neuron_id:
                transmitted_spike = synapse.transmit_spike(spike)
                heapq.heappush(self.spike_queue, transmitted_spike)

    def step(self) -> Dict[str, Any]:
        self.current_time += self.time_step

        spikes_fired = []
        while self.spike_queue and self.spike_queue[0].timestamp <= self.current_time:
            spike = heapq.heappop(self.spike_queue)

            if spike.neuron_id in self.neurons:
                neuron = self.neurons[spike.neuron_id]
                new_spike = neuron.update(self.current_time, spike.amplitude)

                if new_spike:
                    spikes_fired.append(new_spike)
                    self._propagate_spike(new_spike)

        for neuron in self.neurons.values():
            neuron.update(self.current_time)

        activity = {
            "timestamp": self.current_time,
            "spikes_fired": len(spikes_fired),
            "active_neurons": len([n for n in self.neurons.values() if n.membrane_potential > 0.1]),
            "network_energy": sum(n.membrane_potential for n in self.neurons.values()),
        }
        self.network_activity.append(activity)

        return activity

    def run_simulation(
        self, duration_ms: float, inputs: Optional[Dict[int, List[float]]] = None
    ) -> List[Dict[str, Any]]:
        start_time = self.current_time
        results = []

        input_schedule = inputs or {}

        while self.current_time < start_time + duration_ms:
            for neuron_id, input_pattern in input_schedule.items():
                time_index = int((self.current_time - start_time) / self.time_step)
                if time_index < len(input_pattern):
                    self.inject_current(neuron_id, input_pattern[time_index])

            activity = self.step()
            results.append(activity)

        return results

    def get_network_state(self) -> Dict[str, Any]:
        firing_rates = {neuron_id: neuron.get_firing_rate() for neuron_id, neuron in self.neurons.items()}

        return {
            "network_name": self.name,
            "current_time": self.current_time,
            "num_neurons": len(self.neurons),
            "num_synapses": len(self.synapses),
            "pending_spikes": len(self.spike_queue),
            "firing_rates": firing_rates,
            "avg_firing_rate": (np.mean(list(firing_rates.values())) if firing_rates else 0.0),
            "network_synchrony": self._calculate_synchrony(),
        }

    def _calculate_synchrony(self) -> float:
        recent_spikes = []
        current_time = self.current_time

        for neuron in self.neurons.values():
            recent_spikes.extend([t for t in neuron.spike_history if t > current_time - 50.0])

        if len(recent_spikes) < 2:
            return 0.0

        spike_variance = np.var(recent_spikes)
        return float(1.0 / (1.0 + spike_variance))  # Higher synchrony = lower variance


class RecoveryNeuromorphicProcessor:
    def __init__(self):
        self.networks: Dict[str, SpikingNeuralNetwork] = {}
        self.processing_history: List[Dict[str, Any]] = []
        self._initialize_recovery_networks()

    def _initialize_recovery_networks(self):
        emotion_net = SpikingNeuralNetwork("emotion_processor")

        emotion_neurons = {
            "stress_detector": (0, NeuronType.SENSORY, 0.8),
            "anxiety_processor": (1, NeuronType.EXCITATORY, 1.0),
            "calm_generator": (2, NeuronType.INHIBITORY, 1.2),
            "mood_integrator": (3, NeuronType.EXCITATORY, 0.9),
            "emotional_memory": (4, NeuronType.EXCITATORY, 1.1),
        }

        for name, (neuron_id, neuron_type, threshold) in emotion_neurons.items():
            neuron = SpikingNeuron(neuron_id, neuron_type, threshold)
            emotion_net.add_neuron(neuron)

        emotion_synapses = [
            Synapse(0, 1, 0.8, 1.0),  # stress -> anxiety
            Synapse(1, 2, -0.6, 2.0),  # anxiety -> calm (inhibitory)
            Synapse(2, 3, 0.7, 1.5),  # calm -> mood integration
            Synapse(0, 4, 0.5, 3.0),  # stress -> emotional memory
            Synapse(4, 1, 0.4, 2.5),  # emotional memory -> anxiety
        ]

        for synapse in emotion_synapses:
            emotion_net.add_synapse(synapse)

        self.networks["emotion"] = emotion_net

        risk_net = SpikingNeuralNetwork("risk_assessor")

        risk_neurons = {
            "craving_sensor": (10, NeuronType.SENSORY, 0.7),
            "trigger_detector": (11, NeuronType.SENSORY, 0.8),
            "coping_evaluator": (12, NeuronType.EXCITATORY, 1.0),
            "risk_integrator": (13, NeuronType.EXCITATORY, 1.2),
            "alert_generator": (14, NeuronType.MOTOR, 1.5),
        }

        for name, (neuron_id, neuron_type, threshold) in risk_neurons.items():
            neuron = SpikingNeuron(neuron_id, neuron_type, threshold)
            risk_net.add_neuron(neuron)

        risk_synapses = [
            Synapse(10, 13, 0.9, 1.0),  # craving -> risk integration
            Synapse(11, 13, 0.8, 1.5),  # triggers -> risk integration
            Synapse(12, 13, -0.7, 2.0),  # coping -> risk (protective)
            Synapse(13, 14, 1.0, 1.0),  # risk -> alert
            Synapse(10, 12, 0.3, 2.5),  # craving -> coping evaluation
        ]

        for synapse in risk_synapses:
            risk_net.add_synapse(synapse)

        self.networks["risk"] = risk_net

        logger.info("Initialized neuromorphic recovery networks")

    def process_emotional_state(self, emotional_inputs: Dict[str, float]) -> Dict[str, Any]:
        emotion_net = self.networks["emotion"]

        input_mapping = {"stress_level": 0, "anxiety_level": 1, "mood_state": 3}

        inputs = {}
        for emotion, value in emotional_inputs.items():
            if emotion in input_mapping:
                neuron_id = input_mapping[emotion]
                inputs[neuron_id] = [value * 2.0] * 100  # 10ms of stimulation

        results = emotion_net.run_simulation(50.0, inputs)  # 50ms simulation

        final_state = emotion_net.get_network_state()

        processing_result = {
            "emotional_inputs": emotional_inputs,
            "network_response": final_state,
            "emotional_stability": 1.0 - final_state["network_synchrony"],  # Lower synchrony = more stability
            "processing_efficiency": final_state["avg_firing_rate"],
            "emotional_regulation": self._assess_emotional_regulation(results),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        self.processing_history.append(processing_result)
        return processing_result

    def assess_relapse_risk(self, risk_factors: Dict[str, float]) -> Dict[str, Any]:
        risk_net = self.networks["risk"]

        input_mapping = {
            "craving_intensity": 10,
            "trigger_exposure": 11,
            "coping_availability": 12,
        }

        inputs = {}
        for factor, value in risk_factors.items():
            if factor in input_mapping:
                neuron_id = input_mapping[factor]
                if factor == "coping_availability":
                    value = 1.0 - value
                inputs[neuron_id] = [value * 3.0] * 80  # Stronger, longer stimulation

        risk_net.run_simulation(40.0, inputs)

        final_state = risk_net.get_network_state()

        alert_neuron = risk_net.neurons[14]
        alert_fired = len(alert_neuron.spike_history) > 0

        risk_assessment = {
            "risk_factors": risk_factors,
            "network_response": final_state,
            "alert_triggered": alert_fired,
            "risk_level": self._calculate_risk_level(final_state, alert_fired),
            "neuromorphic_confidence": final_state["avg_firing_rate"] / 10.0,  # Normalize
            "processing_latency_ms": 40.0,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        self.processing_history.append(risk_assessment)
        return risk_assessment

    def _assess_emotional_regulation(self, simulation_results: List[Dict[str, Any]]) -> float:
        if not simulation_results:
            return 0.5

        activities = [r["network_energy"] for r in simulation_results]

        if len(activities) < 10:
            return 0.5

        latter_half = activities[len(activities) // 2 :]
        stability = 1.0 / (1.0 + np.var(latter_half))

        return min(1.0, float(stability))

    def _calculate_risk_level(self, network_state: Dict[str, Any], alert_fired: bool) -> str:
        if alert_fired:
            return "high"

        avg_firing = network_state["avg_firing_rate"]

        if avg_firing > 15.0:
            return "moderate"
        elif avg_firing > 5.0:
            return "low"
        else:
            return "minimal"

    def get_processing_insights(self) -> Dict[str, Any]:
        if not self.processing_history:
            return {"message": "No processing history available"}

        recent_processing = self.processing_history[-10:]

        emotional_stability = []
        risk_assessments = []

        for record in recent_processing:
            if "emotional_stability" in record:
                emotional_stability.append(record["emotional_stability"])
            if "risk_level" in record:
                risk_assessments.append(record["risk_level"])

        risk_distribution = {level: risk_assessments.count(level) for level in set(risk_assessments)}

        return {
            "total_processing_events": len(self.processing_history),
            "recent_events": len(recent_processing),
            "avg_emotional_stability": (np.mean(emotional_stability) if emotional_stability else 0.5),
            "risk_level_distribution": risk_distribution,
            "neuromorphic_efficiency": "high_efficiency",  # Spiking networks are inherently efficient
            "processing_paradigm": "event_driven_spiking",
            "networks_active": len(self.networks),
            "insights": self._generate_neuromorphic_insights(recent_processing),
        }

    def _generate_neuromorphic_insights(self, recent_processing: List[Dict[str, Any]]) -> List[str]:
        insights = []

        if len(recent_processing) > 5:
            insights.append("Neuromorphic processing shows consistent event-driven pattern recognition")

        emotional_records = [r for r in recent_processing if "emotional_stability" in r]
        if emotional_records:
            avg_stability = np.mean([r["emotional_stability"] for r in emotional_records])
            if avg_stability > 0.7:
                insights.append("Spiking neural networks indicate strong emotional regulation patterns")
            elif avg_stability < 0.3:
                insights.append("Neuromorphic analysis suggests need for emotional stability interventions")

        risk_records = [r for r in recent_processing if "alert_triggered" in r]
        if risk_records:
            alert_rate = sum(r["alert_triggered"] for r in risk_records) / len(risk_records)
            if alert_rate > 0.5:
                insights.append("High alert frequency in neuromorphic risk assessment network")

        return insights


class EventDrivenProcessor:
    def __init__(self):
        self.event_queue: List[Tuple[float, str, Dict[str, Any]]] = []
        self.processors: Dict[str, Callable] = {}
        self.processing_stats: Dict[str, int] = defaultdict(int)

    def register_processor(self, event_type: str, processor: Callable):
        self.processors[event_type] = processor
        logger.info(f"Registered event processor | Type={event_type}")

    def schedule_event(self, delay_ms: float, event_type: str, event_data: Dict[str, Any]):
        timestamp = datetime.utcnow().timestamp() * 1000 + delay_ms
        heapq.heappush(self.event_queue, (timestamp, event_type, event_data))

    def process_events(self, max_events: int = 100) -> List[Dict[str, Any]]:
        current_time = datetime.utcnow().timestamp() * 1000
        processed = []
        events_processed = 0

        while self.event_queue and self.event_queue[0][0] <= current_time and events_processed < max_events:
            timestamp, event_type, event_data = heapq.heappop(self.event_queue)

            if event_type in self.processors:
                try:
                    result = self.processors[event_type](event_data)
                    processed.append(
                        {
                            "event_type": event_type,
                            "timestamp": timestamp,
                            "result": result,
                            "processing_latency": current_time - timestamp,
                        }
                    )
                    self.processing_stats[event_type] += 1
                except Exception as e:
                    logger.error(f"Event processing failed | Type={event_type} | Error={str(e)}")

            events_processed += 1

        return processed


def create_neuromorphic_processor() -> RecoveryNeuromorphicProcessor:
    return RecoveryNeuromorphicProcessor()


def process_emotional_state_neuromorphic(
    emotional_inputs: Dict[str, float],
) -> Dict[str, Any]:
    processor = create_neuromorphic_processor()
    return processor.process_emotional_state(emotional_inputs)


def assess_risk_neuromorphic(risk_factors: Dict[str, float]) -> Dict[str, Any]:
    processor = create_neuromorphic_processor()
    return processor.assess_relapse_risk(risk_factors)
