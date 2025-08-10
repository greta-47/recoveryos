# agents.py
import os
import time
import uuid
import re
from typing import Dict, Any
from datetime import datetime
from openai import OpenAI, APIError, RateLimitError
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("recoveryos")

# Validate API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY is not set in environment")
client = OpenAI(api_key=api_key)

# System message
SYSTEM = """You are a coordinated multi-agent team for RecoveryOS (BC, Canada).
Agents: Researcher, Analyst, Critic (BC compliance), Strategist, Advisor.
Core principles:
- Trauma-informed, professional, decision-ready
- No clinical diagnosis or crisis advice
- Cite sources, note assumptions, keep concise
- Never include PHI or patient identifiers
- All outputs must be de-identified and audit-safe
"""

# Prompts
PROMPTS = {
    "researcher": lambda topic, horizon: f'''ROLE: Researcher
TASK: Compile high-signal sources on "{topic}" for the next {horizon}.
Prioritize: peer-reviewed journals, government health sites (BC/CDC/WHO), clinical guidelines.

Include:
- Papers, patents, regulatory pages (BC/Canada)
- Earnings calls (if commercial)
- Pricing pages, patient reviews (de-identified)

Return:
1) Findings list: [{{source, date, claim, metric, reliability, excerpt}}] (8–15 items)
2) 10-bullet executive summary.
''',

    "analyst": '''ROLE: Analyst
From the Researcher findings, extract:
(1) 3–5 trends, (2) buyer/funding patterns, (3) TAM/SAM + unit economics,
(4) 3 bottlenecks, (5) opportunity map with ROI ranges (note sensitivity to regulation/rates).''',

    "critic": '''ROLE: Critic (Compliance + Red Team)
Challenge assumptions and feasibility. Flag hidden costs (support load, returns), platform risk, data handling.
BC/Canada guardrails: informed consent before sharing, data minimization, no PHI in email, crisis disclaimers,
export/delete rights, encryption in transit/at rest. Provide risks, kill-criteria, escalation triggers.''',

    "strategist": '''ROLE: Strategist
Produce a 90-day GTM plan with 3 budget variants (Lean / Standard / Aggressive).
Include: ICP, offer, channels, budget, KPIs (leading/lagging), 30/60/90 milestones,
and clear stop/scale thresholds.'''
}

def _contains_phi(text: str) -> bool:
    patterns = [
        r"\b\d{3}-\d{3}-\d{4}\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\bDOB[:\s]*\d{1,2}/\d{1,2}/\d{4}\b",
    ]
    return any(re.search(p, text, re.I) for p in patterns)

def _chat(content: str, model: str = "gpt-4o-mini", max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": content}
                ],
                timeout=15
            )
            return resp.choices[0].message.content
        except RateLimitError:
            wait = 2 ** attempt
            time.sleep(wait)
        except APIError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"OpenAI API error after {max_retries} attempts: {e}")
            time.sleep(2)
    raise RuntimeError("Max retries exceeded")

def run_multi_agent(topic: str, horizon: str, okrs: str) -> Dict[str, Any]:
    request_id = str(uuid.uuid4())
    logger.info(f"Agent pipeline started | ID={request_id} | Topic='{topic}'")

    # Input validation
    if not topic or len(topic.strip()) < 5:
        raise ValueError("Topic must be at least 5 characters")
    if not horizon or not okrs:
        raise ValueError("Horizon and OKRs are required")

    try:
        # 1) Researcher
        researcher = _chat(PROMPTS["researcher"](topic, horizon))

        # 2) Analyst
        analyst = _chat(f"Researcher findings:\n{researcher}\n\n{PROMPTS['analyst']}")

        # 3) Critic
        critic = _chat(f"Researcher + Analyst:\n{researcher}\n\n{analyst}\n\n{PROMPTS['critic']}")

        # 4) Strategist
        strategist = _chat(
            f"Use the prior outputs to build the plan.\n"
            f"Researcher:\n{researcher}\n\nAnalyst:\n{analyst}\n\nCritic:\n{critic}\n\n{PROMPTS['strategist']}"
        )

        # 5) Advisor memo (higher quality model)
        raw_memo = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content":
                    f"Create a decision memo aligned to OKRs: {okrs}.\n"
                    "Sections: Top Opportunities, Risks/Kill-Criteria, 90-day GTM (3 variants), "
                    "KPIs, Decision & Rationale, Next Actions. Keep it concise and actionable.\n\n"
                    f"Researcher:\n{researcher}\n\nAnalyst:\n{analyst}\n\nCritic:\n{critic}\n\nStrategist:\n{strategist}"
                }
            ],
        ).choices[0].message.content

        # PHI check
        advisor_memo = "[REDACTED] Potential PHI detected." if _contains_phi(raw_memo) else raw_memo

        logger.info(f"Agent pipeline completed | ID={request_id}")
        return {
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "topic": topic,
            "horizon": horizon,
            "okrs": okrs,
            "researcher": researcher,
            "analyst": analyst,
            "critic": critic,
            "strategist": strategist,
            "advisor_memo": advisor_memo,
        }

    except Exception as e:
        logger.error(f"Agent pipeline failed | ID={request_id} | Error={str(e)}")
        raise
