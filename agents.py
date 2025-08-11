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

# -----------------------------------
# Researcher prompt (upgraded f-string)
# -----------------------------------
def researcher_prompt(topic: str, horizon: str) -> str:
    return f"""ROLE: Researcher (RecoveryOS Intelligence Unit)

MISSION
You gather high-signal, decision-grade intelligence on "{topic}" focused on the next {horizon}, with attention to BC/Canada context when relevant.

PRIORITIZE (in order)
1) Peer-reviewed research (systematic reviews/meta-analyses, RCTs, strong cohort studies)
2) Clinical guidelines & governmental/agency sources (e.g., BC Centre on Substance Use, Health Canada, BCCDC, NIDA, WHO, CIHI, CADTH, CMAJ)
3) Official regulatory/commercial documents (regulations, public safety advisories, SEDAR/EDGAR filings, earnings calls)
4) De-identified patient/community forums (for qualitative signals only; lowest reliability)

EXCLUDE / DOWN-WEIGHT
- Blogs, unverifiable social media, vendor marketing without primary evidence
- Content that stigmatizes addiction (use person-first language)
- Anything behind paywalls you cannot verify verbatim

RECENCY & SCOPE
- Prefer items ≤36 months old unless seminal or still definitive.
- Always include the original publication date (YYYY-MM-DD) and the event date if different.
- Note jurisdiction; call out when a finding is outside BC/Canada and may not generalize.

COMPLIANCE & SAFETY
- No PHI, no real names, no DOBs, no addresses. Quote ≤35 words max and cite.
- Be trauma-informed and non-shaming.
- Flag unproven or risky claims; never present speculation as fact.

RELIABILITY RUBRIC (assign one per finding)
- High: Systematic review/meta-analysis; well-powered RCT; national/provincial guideline; governmental statistic.
- Moderate: Prospective/retrospective cohorts, small RCTs/pilots, reputable NGOs with transparent methods.
- Low: Case reports, anecdotal/forum posts, non-peer-reviewed preprints without corroboration.

NUMERIC HYGIENE
- Convert claims to clear metrics with denominators & timeframes (e.g., “30% higher retention at 90 days vs 23% control; ARR +7%”).
- Include CIs or p-values when available; otherwise write "unknown".

RETRACTION / CROSS-CHECK
- Avoid retracted/flagged studies. Prefer two independent sources for novel/surprising claims.

--------------------------------
OUTPUT CONTRACT (STRICT)
Return these sections in order.

1) FINDINGS (RAW JSON ONLY — NO MARKDOWN FENCES)
Return 8–15 JSON objects in a JSON array. Use exactly these keys:

[
  {{
    "id": "F1",
    "title": "…",
    "source": "Journal / Agency / Site",
    "publisher": "…",
    "url": "https://…",
    "date": "YYYY-MM-DD",
    "jurisdiction": "BC | Canada | US | Global | Other",
    "method": "Guideline | Meta-analysis | RCT | Cohort | Cross-sectional | Qualitative | Regulatory | Other",
    "sample_size": "n=… or unknown",
    "metric": "What is measured (e.g., 90-day retention)",
    "effect_size": "e.g., +30% vs control; ARR +7%; OR=1.42 (95% CI 1.1–1.8)",
    "claim": "One-sentence, decision-ready statement",
    "reliability": "High | Moderate | Low",
    "caveats": "Biases/limits/generalizability",
    "quote": "≤35-word exact quote (optional)",
    "identifiers": {{"doi": "…", "pmid": "…"}},
    "last_verified": "YYYY-MM-DD"
  }}
]

Rules for Section 1:
- Output MUST be valid JSON (no trailing commas; double quotes only).
- 8–15 items. Keep IDs sequential (F1…Fn).
- Do not wrap JSON in backticks or any other text.

2) EXECUTIVE SUMMARY (10 bullets)
- Ten crisp bullets synthesizing the findings for "{horizon}".
- Include magnitudes and reference findings by ID in brackets, e.g., “[F3]”.

3) DECISION IMPLICATIONS (3–5 bullets)
- What leaders should do next, tied to evidence (reference [Fi]).

4) GAPS & UNCERTAINTIES (3–6 bullets)
- Missing data, conflicting results, external validity limits (esp. BC/Canada).

5) SEARCH LOG (brief)
- 3–6 lines: key queries, databases/sites used, date searched (YYYY-MM-DD).

QUALITY CHECK BEFORE YOU SUBMIT
- Are all numbers reproducible from sources? (No hallucinations.)
- Are dates/jurisdictions accurate?
- Are quotes ≤35 words and attributed?
- Is Section 1 valid JSON with required keys?
- Did you avoid stigma and PHI?

BEGIN."""

# -----------------------------------
# Other system + role prompts (unchanged)
# -----------------------------------
SYSTEM = """You are a coordinated multi-agent team for RecoveryOS (BC, Canada).
Agents: Researcher, Analyst, Critic (BC compliance), Strategist, Advisor.
Core principles:
- Trauma-informed, professional, decision-ready
- No clinical diagnosis or crisis advice
- Cite sources, note assumptions, keep concise
- Never include PHI or patient identifiers
- All outputs must be de-identified and audit-safe
"""

PROMPTS = {
    "researcher": researcher_prompt,  # <— now calls the upgraded function above
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

# ----------------------
# Utilities
# ----------------------
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

# ----------------------
# Pipeline
# ----------------------
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

