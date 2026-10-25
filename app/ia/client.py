import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai

load_dotenv()

class GoogleGenAIClient:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY não encontrada nas variáveis de ambiente")

        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-3.8-flash"

    def generate_content(self, prompt: str) -> str:
        """Gera conteúdo usando o Gemini AI."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt
        )
        return response.text

    def generate_structured_content(self, prompt: str) -> dict[str, Any]:
        """Gera conteúdo estruturado (JSON) usando o Gemini AI."""
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt + ". Retorne apenas JSON válido."
        )

        try:
            return json.loads(response.text)
        except json.JSONDecodeError:
            raise ValueError(f"Resposta inválida do Gemini: {response.text}")
