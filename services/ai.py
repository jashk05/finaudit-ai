import os
import json
import asyncio
from google import genai


class AISummarizer:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
        self.enabled = bool(self.api_key)

        self.client = (
            genai.Client(api_key=self.api_key)
            if self.enabled
            else None
        )

    async def __call__(self, analysis):
        if not self.enabled:
            return None

        payload = {
            "company": analysis["company_name"],
            "ticker": analysis["ticker"],
            "risk_score": analysis["risk_score"],
            "risk_band": analysis["risk_band"],
            "data_coverage": analysis["data_coverage"],
            "metrics": analysis["metrics"],
            "signals": analysis["signals"],
        }

        prompt = f"""
You are the explanatory layer of a forensic accounting analytics product.

Use only the supplied structured financial facts.

Do not accuse the company of fraud, manipulation, misconduct,
or wrongdoing, do mention if it seems to be likely the case.

A financial reporting risk signal is not proof of manipulation.

Return concise plain text with:

1. A two sentence executive assessment.
2. The three most important signals and why they matter.
3. Two plausible legitimate business explanations that an analyst should investigate.
4. Three next documents or disclosures to inspect.

Structured data:

{json.dumps(payload, indent=2)}
"""

        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model,
            contents=prompt,
        )

        usage = response.usage_metadata

        input_tokens = (
            usage.prompt_token_count
            if usage and usage.prompt_token_count
            else 0
        )

        output_tokens = (
            usage.candidates_token_count
            if usage and usage.candidates_token_count
            else 0
        )

        cached_tokens = (
            usage.cached_content_token_count
            if usage and usage.cached_content_token_count
            else 0
        )

        total_tokens = (
            usage.total_token_count
            if usage and usage.total_token_count
            else input_tokens + output_tokens
        )

        thinking_tokens = (
            usage.thoughts_token_count
            if usage and usage.thoughts_token_count
            else 0
        )

        return {
            "summary": response.text,
            "provider": "Google Gemini",
            "model": self.model,

            "usage": {
                "input_tokens": input_tokens,
                "cached_input_tokens": cached_tokens,
                "output_tokens": output_tokens,
                "thinking_tokens": thinking_tokens,
                "total_tokens": total_tokens,
            },

            # Gemini 3.6 Flash input/output is free on the Gemini API free tier.
            "estimated_cost_usd": 0.0,
        }


summarize_analysis = AISummarizer()