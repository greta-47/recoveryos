import os
from typing import Dict, Any, List
from openai import OpenAI

# Requires env var OPENAI_API_KEY set in Render
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM = (
    "You are a coordinated multi-agent team for RecoveryOS (BC, Canada). "
    "Agents: Researcher, Analyst, Critic (BC compliance), Strategist, Advisor. "
    "Trauma-informed, professional, decision-ready. No clinical diagnosis or crisis advice. "
    "Cite sources when possible, note assumptions, and keep outputs concise."
)

PROMPTS = {
    "researcher": lambda topic, horizon: f"""ROLE: Researcher
TASK: Compile high-signal sources on "{topic}" for the next {horizon}.
Include papers, patents, regulatory pages (BC/Canada), earnings calls, pricing pages, reviews.
Return:
1) Findings list: [{{source, date, claim, metric, reliability, excerpt}}] (concise, 8–15 items)
2) 10-bullet executive summary.""",

    "analyst": """ROLE: Analyst
From the Researcher findings, extract:
(1) 3–5 trends, (2) buyer/funding patterns, (3) TAM/SAM + unit economics,
(4) 3 bottlenecks, (5) opportunity map with ROI ranges (note sensitivity to regulation/rates).""",

    "critic": """ROLE: Critic (Compliance + Red Team)
Challenge assumptions and feasibility. Flag hidden costs (support load, returns), platform risk, data handling.
BC/Canada guardrails: informed consent before sharing, data minimization, no PHI in email, crisis disclaimers,
export/delete rights, encryption in transit/at rest. Provide risks, kill-criteria, escalation triggers.""",

    "strategist": """ROLE: Strategist
Produce a 90-day GTM plan with 3 budget variants (Lean / Standard / Aggressive).
Include: ICP, offer, channels, budget, KPIs (leading/lagging), 30/60/90 milestones,
and clear stop/scale thresholds."""
}

def _chat(content: str, model: str = "gpt-4o-mini") -> str:
    """Small helper to call OpenAI Chat Completions."""
    resp = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[{"role": "system", "content": SYSTEM},
                  {"role": "user", "content": content}],
    )
    return resp.choices[0].message.content

def run_multi_agent(topic: str, horizon: str, okrs: str) -> Dict[str, Any]:
    """Main pipeline: Researcher -> Analyst -> Critic -> Strategist -> Advisor memo."""
    # 1) Researcher
    researcher = _chat(PROMPTS["researcher"](topic, horizon))

    # 2) Analyst
    analyst = _chat(f"Researcher findings:\n{researcher}\n\n{PROMPTS['analyst']}")

    # 3) Critic (with BC guardrails)
    critic = _chat(f"Researcher + Analyst:\n{researcher}\n\n{analyst}\n\n{PROMPTS['critic']}")

    # 4) Strategist
    strategist = _chat(
        f"Use the prior outputs to build the plan.\n"
        f"Researcher:\n{researcher}\n\nAnalyst:\n{analyst}\n\nCritic:\n{critic}\n\n{PROMPTS['strategist']}"
    )

    # 5) Advisor memo (higher quality model)
    advisor_memo = client.chat.completions.create(
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

    return {
        "topic": topic,
        "horizon": horizon,
        "okrs": okrs,
        "researcher": researcher,
        "analyst": analyst,
        "critic": critic,
        "strategist": strategist,
        "advisor_memo": advisor_memo,
    }
