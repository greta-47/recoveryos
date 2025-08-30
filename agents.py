import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import APIError, OpenAI, RateLimitError

# ----------------------
# Logging
# ----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("recoveryos")

# ----------------------
# OpenAI client
# ----------------------
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    if os.getenv("TESTING") or "test" in sys.argv[0] or any("test" in arg for arg in sys.argv):
        api_key = "test-key-for-testing"
        logger.warning("Using mock API key for testing environment")
    else:
        raise RuntimeError("OPENAI_API_KEY is not set in environment")
client = OpenAI(api_key=api_key)

# Allow env overrides for models - using GPT-5 as requested
MODEL_FAST = os.getenv("OPENAI_MODEL_FAST", "gpt-5")
MODEL_HIGH = os.getenv("OPENAI_MODEL_HIGH", "gpt-5")

# ----------------------
# System message
# ----------------------
SYSTEM = """You are a coordinated multi-agent team for RecoveryOS (BC, Canada).
Agents: Researcher, Analyst, Critic (BC compliance), Strategist, Advisor.
Core principles:
- Trauma-informed, professional, decision-ready
- Deep clinical reasoning for complex cases (dual diagnosis, poly-substance, trauma)
- Evidence-based pathways and interventions
- No clinical diagnosis or crisis advice
- Cite sources, note assumptions, keep concise
- Never include PHI or patient identifiers
- Personalized responses based on user profile and history
- All outputs must be de-identified and audit-safe
"""


# ----------------------
# Prompts
# ----------------------
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
- Low: Case reports, anecdotal/forum posts, non–peer-reviewed preprints without corroboration.

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


def analyst_prompt(okrs: str) -> str:
    return f"""ROLE: Analyst + Test Designer (RecoveryOS)

CONTEXT
Use the Researcher’s findings to extract patterns and design **Top 5 real-world validation tests** that most directly advance these OKRs:
{okrs}

OUTPUT SECTIONS (IN ORDER)

1) TRENDS & PATTERNS (3–5 items)
- Validated trends only (no guesses). Each one references evidence by [Fi].
- Include buyer/funding patterns (who pays?), TAM/SAM and unit economics (CAC/LTV if known).
- Call out bottlenecks: regulatory, clinical, tech, trust.

2) TOP 5 VALIDATION TESTS (JSON ARRAY ONLY — NO MARKDOWN FENCES)
Return exactly 5 objects, fields below, ordered by **Priority** (P1 highest). Keep costs small and timeframes fast.

[
  {{
    "id": "T1",
    "hypothesis": "Clear, falsifiable statement tied to OKRs",
    "test_method": "e.g., landing page A/B test, 10 patient interviews, fake door test",
    "metric": "Success threshold (e.g., ≥30% click-through; ≥7/10 would pay)",
    "timeframe_days": 7,
    "budget_max_usd": 500,
    "owner": "Product | Clinical Lead | AI | Growth",
    "priority": "P1 | P2 | P3",
    "rationale": "Why this test now; reference evidence [F#] and key risks reduced"
  }}
]

Constraints:
- **Fast** (<14 days), **Lean** (≤ $500), **Risk-reducing** (biggest unknowns first).
- Prefer tests that can run asynchronously and de-identified.

3) PRIORITIZATION RATIONALE (2–4 bullets)
- Why the ordering (impact × confidence × cost × time), referencing [T#] and [F#].

STYLE
- Be concise. No fluff. Only actionable insights.
"""


CRITIC_PROMPT = """ROLE: Critic (Compliance + Red Team)
Challenge assumptions and feasibility. Flag hidden costs (support load, returns), platform risk, data handling.
BC/Canada guardrails: informed consent before sharing, data minimization, no PHI in email, crisis disclaimers,
export/delete rights, encryption in transit/at rest. Provide risks, kill-criteria, escalation triggers.
"""

STRATEGIST_PROMPT = """ROLE: Strategist
Produce a 90-day GTM plan with 3 budget variants (Lean / Standard / Aggressive).
Include: ICP, offer, channels, budget, KPIs (leading/lagging), 30/60/90 milestones,
and clear stop/scale thresholds.
"""


def advisor_prompt(okrs: str) -> str:
    return f"""You are the final Advisor in the RecoveryOS multi-agent pipeline.
Your job is not to summarize — it is to **decide, align, and reveal trade-offs**.

## OKRs to Align With:
{okrs}

## Task:
1. **Evaluate**: Does the Strategist's plan clearly advance these OKRs?
   - If YES: refine for clarity and actionability.
   - If NO: **rewrite the core strategy** to align.

2. **Explain Trade-offs**:
   - What must we sacrifice (time, budget, scope) to hit each OKR?
   - What happens if we don't invest in X?
   - What are the hidden costs (e.g., clinician burnout, patient trust)?

3. **Flag Gaps**:
   - Missing data? Unproven assumptions? Over-reliance on AI?
   - Is this ethical, trauma-informed, and safe for BC/Canada?

4. **Output Structure**:
   - Decision: [Go / No-Go / Pivot]
   - Rationale: 3–5 sentences
   - Top 3 Trade-offs
   - Next Actions (owner + deadline)
   - Risks if we proceed / if we delay

Be concise. Be courageous. Be clinical.
"""


# ----------------------
# Helpers
# ----------------------
def _contains_phi(text: str) -> bool:
    patterns = [
        r"\b\d{3}-\d{3}-\d{4}\b",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        r"\b\d{3}-\d{2}-\d{4}\b",
        r"\bDOB[:\s]*\d{1,2}/\d{1,2}/\d{4}\b",
    ]
    return any(re.search(p, text, re.I) for p in patterns)


def _chat(content: str, model: str = MODEL_FAST, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": content},
                ],
                timeout=15,
            )
            return resp.choices[0].message.content or ""
        except RateLimitError:
            wait = 2**attempt
            time.sleep(wait)
        except APIError as e:
            if attempt == max_retries - 1:
                raise RuntimeError(f"OpenAI API error after {max_retries} attempts: {e}")
            time.sleep(2)
    raise RuntimeError("Max retries exceeded")


# --- JSON extraction for Analyst's Top 5 tests ---
_JSON_ARRAY_RE = re.compile(r"\[\s*(?:\{[\s\S]*?\})(?:\s*,\s*\{[\s\S]*?\}\s*)*\s*\]")


def _fix_json_like(s: str) -> str:
    """Best-effort: normalize curly quotes and remove trailing commas."""
    if not s:
        return s
    s = s.replace("“", '"').replace("”", '"').replace("’", "'").replace("‘", "'")
    s = re.sub(r",(\s*[}\]])", r"\1", s)
    return s


def _parse_analyst_tests(text: str) -> List[Dict[str, Any]]:
    """
    Extract the JSON array from the Analyst section and return up to 5 test dicts.
    We look for the first valid JSON array; filter for dicts with expected keys.
    """
    if not text:
        return []
    candidates = _JSON_ARRAY_RE.findall(text)
    for raw in candidates:
        fixed = _fix_json_like(raw)
        try:
            arr = json.loads(fixed)
        except Exception:
            continue
        if isinstance(arr, list):
            required = {"hypothesis", "test_method", "metric"}
            objs = [o for o in arr if isinstance(o, dict) and required.issubset(o.keys())]
            if objs:
                out: List[Dict[str, Any]] = []
                for o in objs[:5]:
                    item = dict(o)
                    if "timeframe_days" in item:
                        try:
                            item["timeframe_days"] = int(item["timeframe_days"])
                        except Exception:
                            pass
                    if "budget_max_usd" in item:
                        try:
                            item["budget_max_usd"] = float(item["budget_max_usd"])
                        except Exception:
                            pass
                    out.append(item)
                return out
    return []


# ----------------------
# Pipeline
# ----------------------
def run_multi_agent(
    topic: str, horizon: str, okrs: str, user_context: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    request_id = str(uuid.uuid4())
    logger.info(f"Agent pipeline started | ID={request_id} | Topic='{topic}'")

    # Input validation
    if not topic or len(topic.strip()) < 5:
        raise ValueError("Topic must be at least 5 characters")
    if not horizon or not okrs:
        raise ValueError("Horizon and OKRs are required")

    try:
        context_info = ""
        if user_context:
            profile = user_context.get("user_profile", {})
            if profile:
                context_info = (
                    "\nUser Context: "
                    f"Communication style: {profile.get('communication_style', 'supportive')}, "
                    f"Recovery goals: {profile.get('recovery_goals', 'general')}"
                )
        # 1) Researcher
        researcher = _chat(researcher_prompt(topic, horizon) + context_info)

        # 2) Analyst (Top 5 tests)
        analyst = _chat(f"Researcher findings:\n{researcher}\n\n{analyst_prompt(okrs)}")
        analyst_tests = _parse_analyst_tests(analyst)

        # 3) Critic
        critic = _chat(f"Researcher + Analyst:\n{researcher}\n\n{analyst}\n\n{CRITIC_PROMPT}")

        # 4) Strategist
        strategist = _chat(
            "Use the prior outputs to build the plan.\n"
            f"Researcher:\n{researcher}\n\nAnalyst:\n{analyst}\n\nCritic:\n{critic}\n\n{STRATEGIST_PROMPT}"
        )

        # 5) Advisor (decision + trade-offs, aligned to OKRs) — higher quality model
        advisor_input = (
            advisor_prompt(okrs)
            + "\n\nContext:\n"
            + f"Researcher:\n{researcher}\n\nAnalyst:\n{analyst}\n\nCritic:\n{critic}\n\nStrategist:\n{strategist}"
        )
        raw_memo = (
            client.chat.completions.create(
                model=MODEL_HIGH,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": advisor_input},
                ],
            )
            .choices[0]
            .message.content
            or ""
        )

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
            "analyst_tests": analyst_tests,
            "critic": critic,
            "strategist": strategist,
            "advisor_memo": advisor_memo,
        }

    except Exception as e:
        logger.error("Agent pipeline failed | ID=%s | Error=%s", request_id, str(e))
        raise
