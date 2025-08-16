# main.py — RecoveryOS API (conflict-free, merged)
from datetime import datetime
import logging
import re
from typing import Dict, Any, Optional, Union, List

from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Import your multi-agent pipeline
from agents import run_multi_agent

# Optional routers (only if present)
try:
    from coping import router as coping_router
except Exception:
    coping_router = None  # type: ignore[assignment]

try:
    from briefing import router as briefing_router
except Exception:
    briefing_router = None  # type: ignore[assignment]

# ----------------------
# Logging Setup
# ----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("recoveryos")

# ----------------------
# Advanced modules (optional; provide safe fallbacks)
# ----------------------
try:
    from multimodal import process_multimodal_input
    from emotion_ai import analyze_emotion_and_respond
    from clinical_agents import analyze_complex_case
    from autonomous_workflows import setup_user_workflows, execute_user_workflows
    from federated_learning import create_federated_manager
    from differential_privacy import create_clinical_privacy_protector
    from causal_ai import create_causal_inference_engine
    from edge_ai import create_edge_ai_manager
    from neuromorphic import create_neuromorphic_processor
    from graph_neural_networks import create_recovery_graph_analyzer
    from quantum_crypto import create_quantum_crypto
    from explainable_ai import create_explainable_ai_engine
    from elite_config import get_elite_config, is_elite_feature_enabled, EliteFeature
    from observability_enhanced import (
        track_elite_endpoint_enhanced,
        enhanced_observability,
    )
    from feature_flags import feature_flags
except Exception as e:
    logger.warning(f"Advanced AI modules not available: {e}")

    # functions used in non-elite routes
    process_multimodal_input = None  # type: ignore[assignment]
    analyze_emotion_and_respond = None  # type: ignore[assignment]
    analyze_complex_case = None  # type: ignore[assignment]
    setup_user_workflows = None  # type: ignore[assignment]
    execute_user_workflows = None  # type: ignore[assignment]

    # elite/observability fallbacks (no-ops to avoid NameErrors)
    def track_elite_endpoint_enhanced(_name: str):
        def _decorator(func):
            return func
        return _decorator  # type: ignore[misc]

    class _NoObs:
        def get_metrics_summary(self):  # pragma: no cover - safe noop
            return {"message": "Enhanced observability not enabled"}
        def get_prometheus_metrics(self):  # pragma: no cover - safe noop
            return ""

    enhanced_observability = _NoObs()  # type: ignore[assignment]

    def is_elite_feature_enabled(_feature) -> bool:  # type: ignore[unused-argument]
        return False

    class EliteFeature:  # type: ignore[no-redef]
        FEDERATED_LEARNING = "federated_learning"
        CAUSAL_AI = "causal_ai"
        EDGE_AI = "edge_ai"
        NEUROMORPHIC = "neuromorphic"
        GRAPH_NEURAL_NETWORKS = "graph_neural_networks"
        QUANTUM_CRYPTO = "quantum_crypto"
        EXPLAINABLE_AI = "explainable_ai"
        DIFFERENTIAL_PRIVACY = "differential_privacy"
        CONTINUAL_LEARNING = "continual_learning"
        HOMOMORPHIC_ENCRYPTION = "homomorphic_encryption"

    class _Flags:
        @staticmethod
        def is_enabled(_name: str) -> bool:
            return False
    feature_flags = _Flags()  # type: ignore[assignment]

    # elite factories referenced later (won’t be called if feature disabled)
    def create_federated_manager():  # pragma: no cover
        raise RuntimeError("Federated manager unavailable")
    def create_clinical_privacy_protector():  # pragma: no cover
        raise RuntimeError("Privacy protector unavailable")
    def create_causal_inference_engine():  # pragma: no cover
        raise RuntimeError("Causal engine unavailable")
    def create_edge_ai_manager():  # pragma: no cover
        raise RuntimeError("Edge AI manager unavailable")
    def create_neuromorphic_processor():  # pragma: no cover
        raise RuntimeError("Neuromorphic processor unavailable")
    def create_recovery_graph_analyzer():  # pragma: no cover
        raise RuntimeError("Graph analyzer unavailable")
    def create_quantum_crypto():  # pragma: no cover
        raise RuntimeError("Quantum crypto unavailable")
    def create_explainable_ai_engine():  # pragma: no cover
        raise RuntimeError("Explainable AI engine unavailable")
    def get_elite_config():  # pragma: no cover
        class _Cfg:
            @staticmethod
            def get_system_status():
                return {"status": "elite_config_unavailable"}
        return _Cfg()

# ----------------------
# App & Middleware
# ----------------------
app = FastAPI(
    title="RecoveryOS API",
    version="0.1.0",
    description="AI-powered relapse prevention platform for addiction recovery",
)

# Secure CORS (tight)
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://recoveryos.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# Serve static UI (e.g., /ui/agents.html)
app.mount("/ui", StaticFiles(directory="ui", html=True), name="ui")

# ----------------------
# Models
# ----------------------
class Checkin(BaseModel):
    mood: int = Field(..., ge=1, le=5, description="Mood level: 1 (struggling) to 5 (strong)")
    urge: int = Field(..., ge=1, le=5, description="Urge to use: 1 (low) to 5 (high)")
    sleep_hours: float = Field(0, ge=0, le=24, description="Hours slept last night")
    isolation_score: int = Field(0, ge=0, le=5, description="Social connection: 1 (isolated) to 5 (connected)")

class AgentsIn(BaseModel):
    topic: str = Field(..., min_length=5, max_length=200)
    horizon: str = Field(default="90 days", max_length=50)
    okrs: str = Field(default="1) Cash-flow positive 2) Consistent scaling 3) CSAT 85%", max_length=500)

class EmotionalAnalysisIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    user_id: Optional[int] = None

class ClinicalCaseIn(BaseModel):
    case_data: Dict[str, Any]
    case_type: str = Field(..., description="dual_diagnosis, poly_substance, or trauma_informed")

# ----------------------
# Routes
# ----------------------
@app.get("/", response_class=JSONResponse)
def root():
    return {
        "ok": True,
        "service": "RecoveryOS",
        "version": app.version,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": "production",
    }

@app.get("/healthz", response_class=JSONResponse)
def health():
    return {"status": "ok", "app": "RecoveryOS", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.post("/checkins")
def create_checkin(checkin: Checkin, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    request_id = f"req-{hash(f'{client_ip}-{datetime.utcnow().timestamp()}') % 10**8}"
    logger.info(f"Check-in received | ID={request_id} | Urge={checkin.urge} | Mood={checkin.mood}")

    # Safety guardrail
    if checkin.urge >= 4:
        tool = "Urge Surfing — 5-minute guided wave visualization"
    elif checkin.mood <= 2:
        tool = "Grounding — 5-4-3-2-1 sensory exercise"
    elif checkin.sleep_hours < 5:
        tool = "Sleep Hygiene Tip: Try a 10-minute body scan"
    else:
        tool = "Breathing — Box breathing 4x4"

    logger.info(f"Tool suggested | ID={request_id} | Tool='{tool}'")
    return {
        "message": "Check-in received",
        "tool": tool,
        "data": checkin.dict(),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
    }

@app.post("/agents/run")
def agents_run(body: AgentsIn, request: Request):
    # (MERGE RESOLVED) unified variant using consistent f-strings
    client_host = request.client.host if request.client else "unknown"
    request_id = f"agent-{hash(f'{client_host}-{datetime.utcnow().timestamp()}') % 10**8}"
    logger.info(f"Agent pipeline started | ID={request_id} | Topic='{body.topic}'")
    try:
        # Prompt injection safety
        if re.search(r"password|token|secret|PHI", body.topic, re.I):
            raise HTTPException(status_code=400, detail="Invalid topic — restricted keywords detected")

        user_context = {"user_id": "anonymous"}
        result = run_multi_agent(body.topic, body.horizon, body.okrs, user_context)

        # De-identification scan
        for key in ["researcher", "analyst", "critic", "strategist", "advisor_memo"]:
            if key in result and result[key]:
                if re.search(r"patient \d+|name:|DOB:", result[key], re.I):
                    logger.warning(f"Potential PHI detected in {key} output — redacting")
                    result[key] = "[REDACTED] Output may contain sensitive data."

        logger.info(f"Agent pipeline completed | ID={request_id}")
        return {**result, "request_id": request_id, "timestamp": datetime.utcnow().isoformat() + "Z"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent pipeline failed | ID={request_id} | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Internal agent error — please try again")

@app.post("/ai/emotion-analysis")
def emotion_analysis(body: EmotionalAnalysisIn):
    if analyze_emotion_and_respond is None:
        raise HTTPException(status_code=503, detail="Emotional AI not available")
    try:
        user_context = {"user_id": body.user_id} if body.user_id else {}
        result = analyze_emotion_and_respond(body.text, user_context)
        return {**result, "timestamp": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        logger.error(f"Emotion analysis failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Emotion analysis failed")

@app.post("/ai/clinical-analysis")
def clinical_analysis(body: ClinicalCaseIn):
    if analyze_complex_case is None:
        raise HTTPException(status_code=503, detail="Clinical AI not available")
    try:
        result = analyze_complex_case(body.case_data)
        return {**result, "timestamp": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        logger.error(f"Clinical analysis failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Clinical analysis failed")

@app.post("/ai/multimodal-upload")
async def multimodal_upload(file: UploadFile = File(...)):
    if process_multimodal_input is None:
        raise HTTPException(status_code=503, detail="Multimodal processing not available")
    try:
        file_data = await file.read()
        result = process_multimodal_input(
            file_data,
            file.filename or "unknown",
            file.content_type or "application/octet-stream",
        )
        return {**result, "timestamp": datetime.utcnow().isoformat() + "Z"}
    except Exception as e:
        logger.error(f"Multimodal processing failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Multimodal processing failed")

@app.post("/workflows/setup/{user_id}")
def setup_workflows(user_id: int, preferences: Dict[str, Any]):
    if setup_user_workflows is None:
        raise HTTPException(status_code=503, detail="Autonomous workflows not available")
    try:
        workflow_ids = setup_user_workflows(user_id, preferences)
        return {
            "user_id": user_id,
            "workflow_ids": workflow_ids,
            "message": f"Set up {len(workflow_ids)} workflows",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Workflow setup failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Workflow setup failed")

@app.post("/workflows/execute/{user_id}")
def execute_workflows(user_id: int, context: Dict[str, Any]):
    if execute_user_workflows is None:
        raise HTTPException(status_code=503, detail="Autonomous workflows not available")
    try:
        results = execute_user_workflows(user_id, context)
        return {
            "user_id": user_id,
            "workflow_results": results,
            "executed_count": len(results),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Workflow execution failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Workflow execution failed")

@app.post("/elite/federated-learning/train")
@track_elite_endpoint_enhanced("federated_learning")
def federated_learning_train(client_data: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.FEDERATED_LEARNING):
        raise HTTPException(status_code=503, detail="Federated learning not enabled")
    try:
        manager = create_federated_manager()
        client_id = client_data.get("client_id", "anonymous_client")
        client_weights = client_data.get("client_weights", [])
        if client_id not in manager.clients:
            manager.register_client(client_id)
        formatted_data = {client_id: {"weights": client_weights}}
        results = manager.federated_round(formatted_data)
        return {
            "global_weights_updated": results is not None,
            "training_metrics": manager.get_training_metrics(),
            "client_id": client_id,
            "federated_round": manager.aggregator.round_number,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Federated learning failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Federated learning failed")

@app.post("/elite/causal-analysis/analyze")
@track_elite_endpoint_enhanced("causal_analysis")
def causal_analysis(user_state: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.CAUSAL_AI):
        raise HTTPException(status_code=503, detail="Causal AI not enabled")
    try:
        engine = create_causal_inference_engine()
        analysis = engine.analyze_causal_factors(user_state)
        return analysis
    except Exception as e:
        logger.error(f"Causal analysis failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Causal analysis failed")

@app.post("/elite/edge-ai/deploy")
@track_elite_endpoint_enhanced("edge_ai")
def deploy_edge_model(request_data: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.EDGE_AI):
        raise HTTPException(status_code=503, detail="Edge AI not enabled")
    try:
        manager = create_edge_ai_manager()
        model_type = request_data.get("model_type", "emotion")
        model_type_mapping = {
            "emotion_classifier": "emotion",
            "risk_predictor": "risk",
            "emotion": "emotion",
            "risk": "risk",
        }
        mapped_model_type = model_type_mapping.get(model_type, "emotion")
        deployment_id = manager.deploy_model(mapped_model_type)
        if deployment_id:
            client_code = manager.get_client_deployment_code(deployment_id)
            return {
                "deployment_id": deployment_id,
                "model_type": mapped_model_type,
                "original_request": model_type,
                "client_code": client_code,
                "deployment_status": "deployed",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        else:
            raise HTTPException(status_code=500, detail="Model deployment failed")
    except Exception as e:
        logger.error(f"Edge AI deployment failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Edge AI deployment failed")

@app.post("/elite/neuromorphic/process")
@track_elite_endpoint_enhanced("neuromorphic")
def neuromorphic_processing(emotional_inputs: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.NEUROMORPHIC):
        raise HTTPException(status_code=503, detail="Neuromorphic processing not enabled")
    try:
        processor = create_neuromorphic_processor()
        results = processor.process_emotional_state(emotional_inputs)
        return results
    except Exception as e:
        logger.error(f"Neuromorphic processing failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Neuromorphic processing failed")

@app.post("/elite/graph-neural/analyze")
@track_elite_endpoint_enhanced("graph_neural")
def graph_neural_analysis(request_data: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.GRAPH_NEURAL_NETWORKS):
        raise HTTPException(status_code=503, detail="Graph neural networks not enabled")
    try:
        analyzer = create_recovery_graph_analyzer()
        user_id = request_data.get("user_id", "anonymous")
        user_state = request_data.get("user_state", {})
        analysis = analyzer.analyze_user_recovery_network(user_id, user_state)
        return analysis
    except Exception as e:
        logger.error(f"Graph analysis failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Graph analysis failed")

@app.post("/elite/quantum-crypto/encrypt")
@track_elite_endpoint_enhanced("quantum_crypto")
def quantum_encrypt(request_data: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.QUANTUM_CRYPTO):
        raise HTTPException(status_code=503, detail="Quantum cryptography not enabled")
    try:
        crypto = create_quantum_crypto()
        key_id = crypto.generate_keypair()
        plaintext = request_data.get("plaintext", "")
        result = crypto.encrypt(key_id, plaintext)
        if result:
            return result
        else:
            raise HTTPException(status_code=500, detail="Quantum encryption failed")
    except Exception as e:
        logger.error(f"Quantum encryption failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Quantum encryption failed")

@app.post("/elite/explainable-ai/predict")
@track_elite_endpoint_enhanced("explainable_ai")
def explainable_prediction(prediction_request: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.EXPLAINABLE_AI):
        raise HTTPException(status_code=503, detail="Explainable AI not enabled")
    try:
        engine = create_explainable_ai_engine()
        input_data = prediction_request.get("input_data", {})
        prediction = prediction_request.get("prediction", {})
        explanation = engine.explain_prediction(input_data, prediction)
        return explanation
    except Exception as e:
        logger.error(f"Explainable AI failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Explainable AI failed")

@app.post("/elite/differential-privacy/analyze")
@track_elite_endpoint_enhanced("differential_privacy")
def differential_privacy_analyze(request_data: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.DIFFERENTIAL_PRIVACY):
        raise HTTPException(status_code=503, detail="Differential privacy not enabled")
    try:
        protector = create_clinical_privacy_protector()
        analysis_type = request_data.get("analysis_type", "emotion_analysis")
        epsilon = request_data.get("epsilon", 1.0)
        input_data = request_data.get("data", [])
        result: Union[Dict[str, float], List[Dict[str, Any]], Dict[str, str]] = {}

        if analysis_type == "emotion_analysis":
            if isinstance(input_data, list):
                emotion_dict: Dict[str, float] = {}
                for i, val in enumerate(input_data):
                    if isinstance(val, str):
                        positive_words = ["happy", "good", "great", "excellent", "wonderful", "amazing"]
                        negative_words = ["sad", "bad", "terrible", "awful", "horrible", "stressed"]
                        val_lower = val.lower()
                        score = 0.5
                        if any(word in val_lower for word in positive_words):
                            score = 0.8
                        elif any(word in val_lower for word in negative_words):
                            score = 0.2
                        emotion_dict[f"emotion_{i}"] = score
                    else:
                        emotion_dict[f"emotion_{i}"] = float(val)
                result = protector.privatize_emotion_analysis(emotion_dict, "anonymous", epsilon)
            else:
                result = protector.privatize_emotion_analysis(input_data, "anonymous", epsilon)

        elif analysis_type == "risk_assessment":
            if isinstance(input_data, list):
                risk_factors = [{"name": f"factor_{i}", "score": float(val)} for i, val in enumerate(input_data)]
                result = protector.privatize_risk_assessment(risk_factors, "anonymous", epsilon)
            else:
                result = protector.privatize_risk_assessment(input_data, "anonymous", epsilon)

        else:
            if isinstance(input_data, dict):
                result = protector.privatize_aggregated_stats(input_data, epsilon)
            else:
                result = {"error": "Unsupported data type for privacy analysis"}

        return {
            "analysis_type": analysis_type,
            "privacy_epsilon": float(epsilon),
            "result": result,
            "privacy_guaranteed": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Differential privacy analysis failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Differential privacy analysis failed")

@app.post("/elite/continual-learning/train")
@track_elite_endpoint_enhanced("continual_learning")
def continual_learning_train(task_data: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.CONTINUAL_LEARNING):
        raise HTTPException(status_code=503, detail="Continual learning not enabled")
    try:
        from continual_learning import create_continual_learner  # type: ignore
        learner = create_continual_learner()
        task_id = task_data.get("task_id", "default_task")
        training_data = task_data.get("task_data", {})
        if isinstance(training_data, dict):
            training_data = [training_data]
        elif not isinstance(training_data, list):
            training_data = [{"data": training_data}]
        result = learner.learn_new_task(task_id, training_data)
        performance = learner._evaluate_performance(training_data)
        return {
            "task_id": task_id,
            "training_result": result,
            "knowledge_retention": performance,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Continual learning failed | Error={str(e)} | TaskData={task_data}")
        raise HTTPException(status_code=500, detail=f"Continual learning failed: {str(e)}")

@app.post("/elite/homomorphic/compute")
@track_elite_endpoint_enhanced("homomorphic")
def homomorphic_compute(computation_request: Dict[str, Any]):
    if not is_elite_feature_enabled(EliteFeature.HOMOMORPHIC_ENCRYPTION):
        raise HTTPException(status_code=503, detail="Homomorphic encryption not enabled")
    try:
        from homomorphic_encryption import create_homomorphic_processor  # type: ignore
        processor = create_homomorphic_processor()
        operation = computation_request.get("operation", "secure_sum")
        data = computation_request.get("data", [])
        if operation == "secure_sum":
            result = processor.secure_risk_aggregation(data)
        elif operation == "secure_aggregation":
            result = processor.secure_risk_aggregation(data)
        elif operation == "outcome_comparison":
            group_a = computation_request.get("group_a", [])
            group_b = computation_request.get("group_b", [])
            result = processor.secure_outcome_comparison(group_a, group_b)
        else:
            result = {"error": f"Unknown operation: {operation}"}
        return {
            "operation": operation,
            "result": result,
            "privacy_guaranteed": True,
            "computation_summary": processor.get_computation_summary(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Homomorphic encryption failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Homomorphic encryption failed")

@app.get("/elite/system-status")
@track_elite_endpoint_enhanced("system_status")
def elite_system_status():
    try:
        config = get_elite_config()
        return config.get_system_status()
    except Exception as e:
        logger.error(f"Elite system status failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="System status unavailable")

@app.get("/elite/metrics")
@track_elite_endpoint_enhanced("elite_metrics")
def elite_metrics():
    """Get elite AI system metrics"""
    try:
        if feature_flags.is_enabled("enhanced_observability"):
            return enhanced_observability.get_metrics_summary()
        else:
            return {"message": "Enhanced observability not enabled"}
    except Exception as e:
        logger.error(f"Elite metrics failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")

@app.get("/metrics")
def prometheus_metrics():
    """Prometheus metrics endpoint for monitoring"""
    try:
        from fastapi.responses import Response
        return Response(enhanced_observability.get_prometheus_metrics(), media_type="text/plain")
    except Exception as e:
        logger.error(f"Prometheus metrics failed | Error={str(e)}")
        raise HTTPException(status_code=500, detail="Metrics unavailable")

# Optional routers
if coping_router:
    app.include_router(coping_router)
if briefing_router:
    app.include_router(briefing_router)
