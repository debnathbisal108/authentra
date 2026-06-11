import httpx
import json
import re
from abc import ABC, abstractmethod
from typing import Optional
from app.core.config import settings


class LLMProvider(ABC):
    @abstractmethod
    async def complete(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        pass


class GeminiProvider(LLMProvider):
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    async def complete(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        if not settings.GEMINI_API_KEY:
            raise ValueError("Gemini API key not configured")

        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 4096},
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.BASE_URL}?key={settings.GEMINI_API_KEY}",
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]


class OpenRouterProvider(LLMProvider):
    BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
    MODEL = "google/gemma-3-12b-it:free"

    async def complete(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OpenRouter API key not configured")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {"model": self.MODEL, "messages": messages, "max_tokens": 4096, "temperature": 0.2}

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                self.BASE_URL,
                headers={"Authorization": f"Bearer {settings.OPENROUTER_API_KEY}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


class LLMService:
    def __init__(self):
        self._providers = []
        if settings.GEMINI_API_KEY:
            self._providers.append(GeminiProvider())
        if settings.OPENROUTER_API_KEY:
            self._providers.append(OpenRouterProvider())

    async def complete(self, prompt: str, system: Optional[str] = None, json_mode: bool = False) -> str:
        last_error = None
        for provider in self._providers:
            try:
                return await provider.complete(prompt, system=system, json_mode=json_mode)
            except Exception as e:
                last_error = e
                continue

        # If no providers configured, return a structured mock for development
        if json_mode:
            return json.dumps({
                "full_name": "Unknown Candidate",
                "email": "",
                "phone": "",
                "linkedin": "",
                "employment": [],
                "education": [],
                "skills": [],
                "note": "LLM not configured - configure GEMINI_API_KEY or OPENROUTER_API_KEY"
            })
        return "LLM provider not configured. Please set GEMINI_API_KEY or OPENROUTER_API_KEY."

    def clean_json_response(self, text: str) -> str:
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        return text.strip()

    async def complete_json(self, prompt: str, system: Optional[str] = None) -> dict:
        result = await self.complete(prompt, system=system, json_mode=True)
        cleaned = self.clean_json_response(result)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(cleaned[start:end])
            return {}


llm_service = LLMService()


# ─── Prompts ──────────────────────────────────────────────────────────────────

RESUME_PARSE_SYSTEM = """You are an expert HR data extractor. Extract structured information from resume text.
Return ONLY valid JSON, no markdown, no explanation."""

RESUME_PARSE_PROMPT = """Extract all information from this resume and return a JSON object with these exact fields:
{{
  "full_name": "string",
  "email": "string or null",
  "phone": "string or null",
  "linkedin": "string or null",
  "employment": [
    {{
      "company_name": "string",
      "job_title": "string or null",
      "start_date": "string or null",
      "end_date": "string or null",
      "is_current": false,
      "location": "string or null",
      "description": "string or null"
    }}
  ],
  "education": [
    {{
      "institution_name": "string",
      "degree": "string or null",
      "field_of_study": "string or null",
      "start_year": "string or null",
      "end_year": "string or null",
      "gpa": "string or null"
    }}
  ],
  "skills": ["string"]
}}

Resume text:
{resume_text}"""

FRAUD_ANALYSIS_SYSTEM = """You are an expert background verification fraud analyst.
Analyze resumes for potential fraud, inconsistencies, and red flags.
Return ONLY valid JSON."""

FRAUD_ANALYSIS_PROMPT = """Analyze this candidate profile for fraud indicators and return JSON:
{
  "flags": [
    {
      "flag_type": "string (e.g., OVERLAPPING_DATES, SUSPICIOUS_GAP, FAKE_COMPANY, KEYWORD_STUFFING, IMPOSSIBLE_TIMELINE)",
      "description": "string",
      "severity": "low|medium|high|critical",
      "details": {}
    }
  ],
  "summary": "string"
}

Candidate data:
{candidate_data}"""


RISK_SCORING_SYSTEM = """You are an AI risk assessment expert for employee background verification.
Generate a comprehensive risk score and recommendation.
Return ONLY valid JSON."""

RISK_SCORING_PROMPT = """Generate risk assessment for this candidate verification data and return JSON:
{
  "total_score": 0-100,
  "risk_level": "low|moderate|high|critical",
  "employment_score": 0-100,
  "education_score": 0-100,
  "fraud_score": 0-100,
  "public_check_score": 0-100,
  "explanation": "string",
  "final_verdict": "clear|review_required|reject",
  "ai_recommendation": "detailed string recommendation"
}

Score guide: 0-25=Low, 26-50=Moderate, 51-75=High, 76-100=Critical risk

Verification data:
{verification_data}"""


VERIFICATION_EMAIL_PROMPT = """Generate a professional verification email for employment verification.
Return JSON with subject and body fields.
{
  "subject": "string",
  "body": "string (plain text)"
}

Details:
- Candidate name: {candidate_name}
- Company: {company_name}
- Job title claimed: {job_title}
- Employment dates claimed: {dates}
- Verification link: {verification_link}"""
