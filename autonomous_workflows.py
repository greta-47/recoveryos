import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("recoveryos")


class WorkflowType(Enum):
    DAILY_CHECKIN = "daily_checkin"
    RISK_MONITORING = "risk_monitoring"
    RELAPSE_ALERT = "relapse_alert"
    MEDICATION_REMINDER = "medication_reminder"
    THERAPY_FOLLOWUP = "therapy_followup"


class WorkflowStatus(Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ESCALATED = "escalated"


class ClinicalGuardrail:
    def __init__(self, name: str, condition: str, action: str, escalation_level: str):
        self.name = name
        self.condition = condition
        self.action = action
        self.escalation_level = escalation_level


CLINICAL_GUARDRAILS = [
    ClinicalGuardrail(
        name="high_risk_score",
        condition="risk_score >= 8.0",
        action="immediate_clinician_alert",
        escalation_level="urgent",
    ),
    ClinicalGuardrail(
        name="suicide_ideation",
        condition="contains_suicide_keywords",
        action="crisis_protocol",
        escalation_level="emergency",
    ),
    ClinicalGuardrail(
        name="relapse_indicator",
        condition="relapse_keywords_detected",
        action="enhanced_support",
        escalation_level="high",
    ),
    ClinicalGuardrail(
        name="missed_checkins",
        condition="missed_checkins >= 3",
        action="wellness_check",
        escalation_level="moderate",
    ),
]


class AutonomousWorkflow:
    def __init__(self, workflow_id: str, user_id: int, workflow_type: WorkflowType):
        self.workflow_id = workflow_id
        self.user_id = user_id
        self.workflow_type = workflow_type
        self.status = WorkflowStatus.ACTIVE
        self.created_at = datetime.utcnow()
        self.last_executed: Optional[datetime] = None
        self.execution_count = 0
        self.guardrails = CLINICAL_GUARDRAILS

    def should_execute(self) -> bool:
        if self.status != WorkflowStatus.ACTIVE:
            return False

        now = datetime.utcnow()

        if self.workflow_type == WorkflowType.DAILY_CHECKIN:
            if not self.last_executed:
                return True
            return (now - self.last_executed) >= timedelta(hours=20)

        elif self.workflow_type == WorkflowType.RISK_MONITORING:
            if not self.last_executed:
                return True
            return (now - self.last_executed) >= timedelta(hours=4)

        elif self.workflow_type == WorkflowType.RELAPSE_ALERT:
            return True

        return False

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            self.last_executed = datetime.utcnow()
            self.execution_count += 1

            guardrail_results = self._check_guardrails(context)

            if guardrail_results.get("escalation_required"):
                self.status = WorkflowStatus.ESCALATED
                return self._handle_escalation(guardrail_results, context)

            if self.workflow_type == WorkflowType.DAILY_CHECKIN:
                return self._execute_daily_checkin(context)
            elif self.workflow_type == WorkflowType.RISK_MONITORING:
                return self._execute_risk_monitoring(context)
            elif self.workflow_type == WorkflowType.RELAPSE_ALERT:
                return self._execute_relapse_alert(context)

            return {"status": "completed", "message": "Workflow executed successfully"}

        except Exception as e:
            logger.error(f"Workflow execution failed | ID={self.workflow_id} | Error={str(e)}")
            return {"status": "error", "message": str(e)}

    def _check_guardrails(self, context: Dict[str, Any]) -> Dict[str, Any]:
        results: Dict[str, Any] = {
            "escalation_required": False,
            "triggered_guardrails": [],
            "escalation_level": "none",
        }

        for guardrail in self.guardrails:
            if self._evaluate_guardrail_condition(guardrail, context):
                results["triggered_guardrails"].append(guardrail.name)

                if guardrail.escalation_level in ["urgent", "emergency"]:
                    results["escalation_required"] = True
                    results["escalation_level"] = guardrail.escalation_level

        return results

    def _evaluate_guardrail_condition(self, guardrail: ClinicalGuardrail, context: Dict[str, Any]) -> bool:
        condition = guardrail.condition

        if condition == "risk_score >= 8.0":
            return context.get("risk_score", 0) >= 8.0

        elif condition == "contains_suicide_keywords":
            text = context.get("user_input", "").lower()
            suicide_keywords = [
                "suicide",
                "kill myself",
                "end it all",
                "not worth living",
            ]
            return any(keyword in text for keyword in suicide_keywords)

        elif condition == "relapse_keywords_detected":
            text = context.get("user_input", "").lower()
            relapse_keywords = [
                "used again",
                "drank again",
                "relapsed",
                "couldn't resist",
            ]
            return any(keyword in text for keyword in relapse_keywords)

        elif condition == "missed_checkins >= 3":
            return context.get("missed_checkins", 0) >= 3

        return False

    def _handle_escalation(self, guardrail_results: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        escalation_level = guardrail_results["escalation_level"]
        triggered_guardrails = guardrail_results["triggered_guardrails"]

        logger.warning(
            "Workflow escalation | ID=%s | Level=%s | Guardrails=%s",
            self.workflow_id,
            escalation_level,
            triggered_guardrails,
        )

        if escalation_level == "emergency":
            return {
                "status": "escalated",
                "escalation_level": "emergency",
                "message": "Emergency protocols activated. Crisis intervention team notified.",
                "actions": ["crisis_protocol", "immediate_clinical_contact"],
                "triggered_guardrails": triggered_guardrails,
            }

        elif escalation_level == "urgent":
            return {
                "status": "escalated",
                "escalation_level": "urgent",
                "message": "High-risk situation detected. Clinical team alerted.",
                "actions": ["clinician_alert", "enhanced_monitoring"],
                "triggered_guardrails": triggered_guardrails,
            }

        return {
            "status": "escalated",
            "escalation_level": escalation_level,
            "message": "Clinical oversight requested.",
            "triggered_guardrails": triggered_guardrails,
        }

    def _execute_daily_checkin(self, context: Dict[str, Any]) -> Dict[str, Any]:
        user_profile = context.get("user_profile", {})
        preferred_time = user_profile.get("checkin_time", "09:00")

        return {
            "status": "completed",
            "workflow_type": "daily_checkin",
            "message": f"Daily check-in reminder sent for {preferred_time}",
            "actions": ["send_checkin_reminder", "prepare_personalized_questions"],
            "personalization": {
                "communication_style": user_profile.get("communication_style", "supportive"),
                "preferred_coping_tools": user_profile.get("coping_preferences", []),
            },
        }

    def _execute_risk_monitoring(self, context: Dict[str, Any]) -> Dict[str, Any]:
        risk_score = context.get("risk_score", 0)
        risk_factors = context.get("risk_factors", [])

        if risk_score >= 6.0:
            return {
                "status": "completed",
                "workflow_type": "risk_monitoring",
                "message": "Elevated risk detected - enhanced monitoring activated",
                "risk_score": risk_score,
                "risk_factors": risk_factors,
                "actions": [
                    "increase_checkin_frequency",
                    "suggest_coping_tools",
                    "prepare_support_resources",
                ],
            }

        return {
            "status": "completed",
            "workflow_type": "risk_monitoring",
            "message": "Risk monitoring completed - levels normal",
            "risk_score": risk_score,
            "actions": ["continue_standard_monitoring"],
        }

    def _execute_relapse_alert(self, context: Dict[str, Any]) -> Dict[str, Any]:
        alert_triggers = context.get("alert_triggers", [])

        return {
            "status": "completed",
            "workflow_type": "relapse_alert",
            "message": "Relapse prevention protocols activated",
            "alert_triggers": alert_triggers,
            "actions": [
                "activate_support_network",
                "provide_immediate_coping_tools",
                "schedule_urgent_checkin",
            ],
        }


class WorkflowManager:
    def __init__(self):
        self.active_workflows: Dict[str, AutonomousWorkflow] = {}

    def create_workflow(self, user_id: int, workflow_type: WorkflowType) -> str:
        workflow_id = f"{workflow_type.value}_{user_id}_{int(datetime.utcnow().timestamp())}"
        workflow = AutonomousWorkflow(workflow_id, user_id, workflow_type)
        self.active_workflows[workflow_id] = workflow

        logger.info(f"Workflow created | ID={workflow_id} | Type={workflow_type.value} | User={user_id}")
        return workflow_id

    def execute_workflows(self, user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []

        for workflow_id, workflow in self.active_workflows.items():
            if workflow.should_execute():
                result = workflow.execute(user_context)
                result["workflow_id"] = workflow_id
                results.append(result)

        return results

    def pause_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].status = WorkflowStatus.PAUSED
            return True
        return False

    def resume_workflow(self, workflow_id: str) -> bool:
        if workflow_id in self.active_workflows:
            self.active_workflows[workflow_id].status = WorkflowStatus.ACTIVE
            return True
        return False


workflow_manager = WorkflowManager()


def setup_user_workflows(user_id: int, preferences: Dict[str, Any]) -> List[str]:
    workflow_ids = []

    if preferences.get("daily_checkins", True):
        workflow_id = workflow_manager.create_workflow(user_id, WorkflowType.DAILY_CHECKIN)
        workflow_ids.append(workflow_id)

    if preferences.get("risk_monitoring", True):
        workflow_id = workflow_manager.create_workflow(user_id, WorkflowType.RISK_MONITORING)
        workflow_ids.append(workflow_id)

    if preferences.get("relapse_alerts", True):
        workflow_id = workflow_manager.create_workflow(user_id, WorkflowType.RELAPSE_ALERT)
        workflow_ids.append(workflow_id)

    return workflow_ids


def execute_user_workflows(user_id: int, context: Dict[str, Any]) -> List[Dict[str, Any]]:
    user_context = {**context, "user_id": user_id}
    return workflow_manager.execute_workflows(user_context)
