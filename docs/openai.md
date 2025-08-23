OpenAI smoketest

Overview
- A lightweight smoketest runs in CI to verify API access. It is non-blocking (continue-on-error) so quota/auth issues don’t fail CI.
- Default model: gpt-5-mini. Override with OPENAI_MODEL.

CI workflow
- File: .github/workflows/openai-smoketest.yml
- Environment:
  - OPENAI_API_KEY is read from GitHub Actions repo secret.
  - OPENAI_MODEL can be set as a repo variable to override (optional).
- Behavior:
  - PASS: Prints a line beginning with "PASS:".
  - NON-BLOCKING cases:
    - insufficient_quota (billing)
    - rate_limit (transient 429)
    - auth error (missing/invalid key)
    - bad-request (invalid params/model)
    - unexpected/api error

Run locally
1) pip install "openai>=1.40.0"
2) export OPENAI_API_KEY=your_key
3) Optional: export OPENAI_MODEL=gpt-5-mini
4) python scripts/openai_provider_test.py

Expected outputs
- PASS: RecoveryOS smoketest PASS
- NON-BLOCKING: insufficient_quota (OpenAI billing)
- NON-BLOCKING: rate_limit (retry later)
- NON-BLOCKING: auth error (check OPENAI_API_KEY)
- NON-BLOCKING: bad-request (...)
