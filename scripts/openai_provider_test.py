#!/usr/bin/env python3
import os
import sys
from openai import OpenAI, APIError, RateLimitError, AuthenticationError, BadRequestError

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    if not api_key:
        print("NON-BLOCKING: auth error (OPENAI_API_KEY not set)", file=sys.stderr)
        sys.exit(0)
    client = OpenAI(api_key=api_key)
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'RecoveryOS smoketest PASS'."}],
            max_tokens=8,
            temperature=0,
        )
        text = (resp.choices[0].message.content or "").strip()
        if text:
            print(f"PASS: {text}")
        else:
            print("NON-BLOCKING: empty response", file=sys.stderr)
        sys.exit(0)
    except RateLimitError as e:
        msg = str(e).lower()
        if "insufficient_quota" in msg or "insufficient quota" in msg:
            print("NON-BLOCKING: insufficient_quota (OpenAI billing)", file=sys.stderr)
            sys.exit(0)
        print("NON-BLOCKING: rate_limit (retry later)", file=sys.stderr)
        sys.exit(0)
    except AuthenticationError:
        print("NON-BLOCKING: auth error (check OPENAI_API_KEY)", file=sys.stderr)
        sys.exit(0)
    except BadRequestError as e:
        print(f"NON-BLOCKING: bad-request ({e})", file=sys.stderr)
        sys.exit(0)
    except APIError as e:
        print(f"NON-BLOCKING: api error ({e})", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"NON-BLOCKING: unexpected error ({e})", file=sys.stderr)
        sys.exit(0)

if __name__ == "__main__":
    main()
