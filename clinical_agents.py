import logging
from typing import Dict, Any
from datetime import datetime
import openai

logger = logging.getLogger("recoveryos")

DUAL_DIAGNOSIS_PROMPT = """You are a specialized clinical AI agent for dual diagnosis cases (mental health + addiction).

EXPERTISE:
- Comorbid conditions: depression+substance use, anxiety+alcohol, PTSD+opioids, bipolar+stimulants
- Evidence-based integrated treatment approaches
- Trauma-informed care for complex presentations
- Medication-assisted treatment considerations

CLINICAL REASONING:
1. Assess both mental health and substance use patterns
2. Identify interaction effects and treatment priorities
3. Suggest integrated, evidence-based interventions
4. Consider safety and stabilization first

SAFETY GUARDRAILS:
- No diagnosis - only clinical observations and suggestions
- Always recommend professional clinical consultation
- Flag high-risk presentations immediately
- Maintain trauma-informed, non-shaming approach

Analyze the case and provide clinical reasoning with evidence-based pathway suggestions."""

POLY_SUBSTANCE_PROMPT = """You are a specialized clinical AI agent for poly-substance use cases.

EXPERTISE:
- Multiple substance use patterns and interactions
- Cross-tolerance and withdrawal considerations
- Harm reduction and staged treatment approaches
- Evidence-based interventions for complex use patterns

CLINICAL REASONING:
1. Map substance use patterns and interactions
2. Assess withdrawal and safety considerations
3. Prioritize substances by risk and impact
4. Suggest staged, evidence-based treatment approach

SAFETY GUARDRAILS:
- No medical advice - clinical observations only
- Always recommend medical supervision for withdrawal
- Flag dangerous combinations immediately
- Focus on harm reduction and safety first

Analyze the poly-substance pattern and suggest evidence-based treatment pathways."""

TRAUMA_INFORMED_PROMPT = """You are a specialized clinical AI agent for trauma + addiction cases.

EXPERTISE:
- Trauma-informed addiction treatment
- PTSD and complex trauma presentations
- Safety and stabilization approaches
- Evidence-based trauma therapies in recovery context

CLINICAL REASONING:
1. Assess trauma history impact on substance use
2. Identify trauma triggers and coping patterns
3. Suggest trauma-informed treatment sequencing
4. Consider safety and stabilization needs

SAFETY GUARDRAILS:
- Never re-traumatize through questioning
- Focus on safety and empowerment
- No trauma processing without professional support
- Maintain therapeutic presence and validation

Provide trauma-informed clinical reasoning and evidence-based pathway suggestions."""


class ClinicalAgent:
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.prompts = {
            "dual_diagnosis": DUAL_DIAGNOSIS_PROMPT,
            "poly_substance": POLY_SUBSTANCE_PROMPT,
            "trauma_informed": TRAUMA_INFORMED_PROMPT,
        }

    def analyze_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            prompt = self.prompts.get(self.agent_type, "")
            if not prompt:
                raise ValueError(f"Unknown agent type: {self.agent_type}")

            case_summary = self._format_case_data(case_data)

            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": case_summary},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            analysis = response.choices[0].message.content

            return {
                "agent_type": self.agent_type,
                "analysis": analysis,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "case_id": case_data.get("case_id", "unknown"),
            }

        except Exception as e:
            logger.error(
                f"Clinical agent analysis failed | Agent={self.agent_type} | Error={str(e)}"
            )
            return {
                "agent_type": self.agent_type,
                "analysis": "Clinical analysis unavailable - please consult with healthcare provider",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }

    def _format_case_data(self, case_data: Dict[str, Any]) -> str:
        formatted = []

        if "demographics" in case_data:
            formatted.append(f"Demographics: {case_data['demographics']}")

        if "substance_use" in case_data:
            formatted.append(f"Substance Use: {case_data['substance_use']}")

        if "mental_health" in case_data:
            formatted.append(f"Mental Health: {case_data['mental_health']}")

        if "trauma_history" in case_data:
            formatted.append(f"Trauma History: {case_data['trauma_history']}")

        if "current_symptoms" in case_data:
            formatted.append(f"Current Symptoms: {case_data['current_symptoms']}")

        if "risk_factors" in case_data:
            formatted.append(f"Risk Factors: {case_data['risk_factors']}")

        return "\n".join(formatted) if formatted else "Limited case data available"


def analyze_complex_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
    results = {}

    if case_data.get("has_dual_diagnosis"):
        agent = ClinicalAgent("dual_diagnosis")
        results["dual_diagnosis"] = agent.analyze_case(case_data)

    if case_data.get("has_poly_substance"):
        agent = ClinicalAgent("poly_substance")
        results["poly_substance"] = agent.analyze_case(case_data)

    if case_data.get("has_trauma"):
        agent = ClinicalAgent("trauma_informed")
        results["trauma_informed"] = agent.analyze_case(case_data)

    return {
        "complex_case_analysis": results,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "case_id": case_data.get("case_id", "unknown"),
    }
