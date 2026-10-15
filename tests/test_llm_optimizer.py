import json
from types import SimpleNamespace

import pytest

from app.optimizer import llm_optimizer
from app.optimizer.llm_optimizer import LLMError, get_suggestions, _parse_answer

ANALYSIS = {
    "sql": "SELECT * FROM t WHERE a = 1",
    "plan": {"Node Type": "Seq Scan", "Relation Name": "t",
             "Total Cost": 10.0, "Plan Rows": 5, "Filter": "(a = 1)"},
    "bottlenecks": [],
    "schema": {"t": {"columns": [{"name": "a", "type": "integer", "nullable": False}],
                     "indexes": []}},
}


class FakeClient:
    """Pretends to be the OpenAI client. `outcomes` are returned or raised in order."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        message = SimpleNamespace(content=outcome)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


GOOD = json.dumps({
    "explanation": "Add an index on a.",
    "candidate_sql": None,
    "index_suggestions": ["CREATE INDEX ON t (a)"],
})


def test_good_answer_is_parsed():
    result = get_suggestions(ANALYSIS, client=FakeClient([GOOD]))
    assert result["index_suggestions"] == ["CREATE INDEX ON t (a)"]
    assert result["candidate_sql"] is None


def test_fenced_json_is_accepted():
    assert _parse_answer("```json\n" + GOOD + "\n```")["explanation"]


def test_broken_json_raises():
    with pytest.raises(LLMError):
        _parse_answer("this is not json")


def test_wrong_types_raise():
    bad = json.dumps({"explanation": "x", "candidate_sql": 5, "index_suggestions": []})
    with pytest.raises(LLMError):
        _parse_answer(bad)


def test_retries_once_on_connection_error(monkeypatch):
    from openai import APIConnectionError
    import httpx

    monkeypatch.setattr(llm_optimizer.time, "sleep", lambda s: None)
    err = APIConnectionError(request=httpx.Request("POST", "http://x"))
    client = FakeClient([err, GOOD])
    assert get_suggestions(ANALYSIS, client=client)["explanation"]
    assert client.calls == 2


def test_gives_up_after_second_failure(monkeypatch):
    from openai import APIConnectionError
    import httpx

    monkeypatch.setattr(llm_optimizer.time, "sleep", lambda s: None)
    err = APIConnectionError(request=httpx.Request("POST", "http://x"))
    client = FakeClient([err, err])
    with pytest.raises(LLMError):
        get_suggestions(ANALYSIS, client=client)
    assert client.calls == 2