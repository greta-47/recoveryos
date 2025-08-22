#!/usr/bin/env python3
import os
import sys
from openai import OpenAI, APIError, RateLimitError

def main():
    provider = "openai"
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is not set in environment", file=sys.stderr)
        sys.exit(1)

    model = os.getenv("OPENAI_MODEL", "gpt-5")

    print(f"Provider: {provider}")
    print(f"Model: {model}")

    client = OpenAI(api_key=api_key)

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": "Reply with one short sentence confirming connectivity."},
            ],
            timeout=20,
        )
    except RateLimitError as e:
        print(f"Rate limited: {e}", file=sys.stderr)
        sys.exit(2)
    except APIError as e:
        print(f"OpenAI API error: {e}", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(4)

    content = resp.choices[0].message.content if resp and resp.choices else ""
    usage = getattr(resp, "usage", None)
    if usage:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        print("Test response:", content.strip())
        print(f"Token usage: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")
    else:
        print("Test response:", content.strip())
        print("Token usage: unavailable")

if __name__ == "__main__":
    main()
