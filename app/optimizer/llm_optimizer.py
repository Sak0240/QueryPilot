import json
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from app.config import settings
from app.optimizer.prompts import SYSTEM_PROMPT, build_user_prompt


class LLMError(RuntimeError):
    """Raised when the model call fails or its answer can't be used."""


def _make_client() -> OpenAI:
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=60,
        max_retries=0,   # we do our own retry below
    )


def _parse_answer(text: str) -> dict:
    """Turn the model's reply into a dict with the 3 expected keys."""
    text = (text or "").strip()
    # Some models wrap JSON in ```json fences even when told not to
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"Model did not return valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise LLMError("Model answer must be a JSON object")

    candidate = data.get("candidate_sql")
    indexes = data.get("index_suggestions") or []
    if candidate is not None and not isinstance(candidate, str):
        raise LLMError("candidate_sql must be a string or null")
    if not isinstance(indexes, list) or not all(isinstance(i, str) for i in indexes):
        raise LLMError("index_suggestions must be a list of strings")

    return {
        "explanation": str(data.get("explanation", "")),
        "candidate_sql": candidate,
        "index_suggestions": indexes,
    }


def get_suggestions(analysis: dict, client: OpenAI | None = None) -> dict:
    """Ask the model for optimization suggestions.

    Returns {"explanation", "candidate_sql", "index_suggestions"}.
    Nothing in the result is trusted yet: Layer 5 must validate it.
    `client` can be a fake in tests.
    """
    client = client or _make_client()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(analysis)},
    ]

    last_error: Exception | None = None
    for attempt in range(2):                      # first try + one retry
        try:
            reply = client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            return _parse_answer(reply.choices[0].message.content)
        except AuthenticationError as e:
            raise LLMError("401: the API key is invalid. Check LLM_API_KEY in .env") from e
        except RateLimitError as e:               # 429
            last_error = e
        except APIConnectionError as e:           # network hiccup
            last_error = e
        except APIStatusError as e:
            if e.status_code == 402:
                raise LLMError("402: insufficient balance. Top up the provider account") from e
            if e.status_code >= 500:              # provider-side problem
                last_error = e
            else:
                raise LLMError(f"Model API error {e.status_code}") from e
        if attempt == 0:
            time.sleep(5)
    raise LLMError(f"Model call failed after retry: {last_error}") from last_error