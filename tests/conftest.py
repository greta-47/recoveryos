import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def _no_openai_network(monkeypatch):
    """
    Prevent real OpenAI calls in unit tests.
    Adjust import path to where your client is created (e.g., agents.py module path).
    """

    patches = []
    for target in [
        "agents.OpenAI",  # main agents module
        "clinical_agents.OpenAI",  # clinical agents module
        "emotion_ai.OpenAI",  # emotion AI module
    ]:
        try:
            p = patch(target)
            mocked_cls = p.start()
            mocked_client = AsyncMock()
            mocked_client.chat.completions.create = AsyncMock(
                return_value={"choices": [{"message": {"content": "ok"}}]}
            )
            mocked_client.responses.create = AsyncMock(
                return_value={"output_text": "ok"}
            )
            mocked_cls.return_value = mocked_client
            patches.append(p)
        except Exception:
            pass

    yield

    for p in patches:
        try:
            p.stop()
        except Exception:
            pass
