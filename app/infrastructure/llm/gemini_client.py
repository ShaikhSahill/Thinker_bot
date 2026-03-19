from __future__ import annotations

import json
from typing import Any

import google.generativeai as genai

from app.settings import Settings


class GeminiClient:
    def __init__(self) -> None:
        settings = Settings()
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set")

        genai.configure(api_key=settings.gemini_api_key)
        self._model_name = settings.gemini_model

    def generate_text(self, prompt: str) -> str:
        model = genai.GenerativeModel(self._model_name)
        resp = model.generate_content(prompt)
        return (resp.text or "").strip()

    def generate_json(self, prompt: str) -> dict[str, Any]:
        text = self.generate_text(prompt)
        # Try strict JSON first; fall back to extracting first JSON object.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
        raise ValueError("Gemini did not return valid JSON")
