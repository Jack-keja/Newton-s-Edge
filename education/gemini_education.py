from __future__ import annotations

import json
import urllib.error
import urllib.request

try:
    from education_function.gemini_config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = ""


GEMINI_MODEL = "gemini-2.5-flash-lite"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def request_gemini_explanation(prompt: str) -> str:
    api_key = GEMINI_API_KEY.strip()
    if not api_key or "PASTE" in api_key.upper():
        raise RuntimeError("Gemini API key is not configured.")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 32598,
        },
    }
    request = urllib.request.Request(
        GEMINI_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini request failed: {exc.code} {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Gemini request failed: {exc.reason}") from exc

    texts: list[str] = []
    for candidate in response_data.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            text = part.get("text")
            if text:
                texts.append(text.strip())
    if not texts:
        raise RuntimeError("Gemini returned no text.")
    return "\n\n".join(texts)
