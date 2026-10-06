import httpx
import pytest

from jobagent.llm import LLMError, call_llm


def test_call_llm_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test_secret_key"
        content = '{"choices": [{"message": {"content": "{\\"result\\": true}"}}]}'
        return httpx.Response(200, content=content.encode("utf-8"))

    transport = httpx.MockTransport(handler)
    res = call_llm(
        system_prompt="sys",
        user_prompt="usr",
        api_key="test_secret_key",
        transport=transport,
    )
    assert res == '{"result": true}'


def test_call_llm_missing_key():
    with pytest.raises(LLMError, match="GROQ_API_KEY is not configured"):
        call_llm(system_prompt="sys", user_prompt="usr", api_key="")


def test_call_llm_401():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, content=b'{"error": "unauthorized"}')

    transport = httpx.MockTransport(handler)
    with pytest.raises(LLMError, match="LLM authentication failed"):
        call_llm(system_prompt="sys", user_prompt="usr", api_key="secret", transport=transport)


def test_call_llm_429():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, content=b'{"error": "rate limit"}')

    transport = httpx.MockTransport(handler)
    with pytest.raises(LLMError, match="rate limit"):
        call_llm(system_prompt="sys", user_prompt="usr", api_key="secret", transport=transport)


def test_call_llm_timeout():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Connection timed out")

    transport = httpx.MockTransport(handler)
    with pytest.raises(LLMError, match="timed out"):
        call_llm(system_prompt="sys", user_prompt="usr", api_key="secret", transport=transport)