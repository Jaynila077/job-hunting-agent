import httpx

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class LLMError(Exception):
    """Base exception for LLM call failures."""
    pass


def call_llm(
    system_prompt: str,
    user_prompt: str,
    api_key: str,
    model: str = "openai/gpt-oss-20b",
    timeout_seconds: float = 90.0,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Sends chat completion prompt to Groq and returns the response text."""
    if not api_key or not api_key.strip():
        raise LLMError("GROQ_API_KEY is not configured.")

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_completion_tokens": 12000,
    }

    try:
        with httpx.Client(timeout=timeout_seconds, transport=transport) as client:
            response = client.post(
                GROQ_CHAT_URL,
                headers=headers,
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise LLMError("LLM request timed out.") from exc
    except httpx.RequestError as exc:
        raise LLMError(f"LLM network connection error: {exc}") from exc

    if response.status_code == 401:
        raise LLMError("LLM authentication failed: invalid GROQ_API_KEY.")
    if response.status_code == 429:
        raise LLMError("LLM rate limit reached. Please retry later.")
    if response.status_code >= 500:
        raise LLMError(f"LLM service error (HTTP {response.status_code}).")
    if response.status_code != 200:
        detail = ""
        try:
            err_json = response.json()
            if "error" in err_json and "message" in err_json["error"]:
                detail = f": {err_json['error']['message']}"
        except Exception:
            pass
        raise LLMError(f"LLM request failed with status code {response.status_code}{detail}")

    try:
        data = response.json()
        return str(data["choices"][0]["message"]["content"])
    except (KeyError, IndexError, ValueError) as exc:
        raise LLMError("LLM returned an invalid response structure.") from exc