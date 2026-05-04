import os
import requests
import json
import time
import threading
from django.conf import settings


class AIService:
    """Singleton AI Service using Groq API with OpenAI-compatible endpoints."""
    _instance = None
    _lock = threading.Lock()
    MAX_RETRIES = 3
    BASE_DELAY = 2
    _last_failure_time = 0
    _cooldown_seconds = 120
    _cache = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.available = False
        self.api_key = os.getenv('GROQ_API_KEY', '').strip()
        self.model_name = 'openai/gpt-oss-120b'
        self.api_url = 'https://api.groq.com/openai/v1/chat/completions'

        if self.api_key:
            self.available = True
            print(f"AI Service initialized with Groq ({self.model_name})")
        else:
            print("No GROQ_API_KEY found, AI Service unavailable.")

    def _is_in_cooldown(self):
        """Check if we're still in cooldown after a rate-limit failure."""
        if self._last_failure_time == 0:
            return False
        elapsed = time.time() - self._last_failure_time
        return elapsed < self._cooldown_seconds

    def _call_api(self, prompt):
        """Call Groq API using OpenAI-compatible chat completions endpoint."""
        if self._is_in_cooldown():
            return self._get_fallback_message()

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a professional business advisor for micro-businesses in Pakistan. Always respond in English. Be concise, actionable, and encouraging."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 500,
            "temperature": 0.7
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json=payload,
                    timeout=15
                )

                if response.status_code == 429:
                    AIService._last_failure_time = time.time()
                    print(f"Groq rate limited (429) on attempt {attempt + 1}. Entering cooldown.")
                    return self._get_fallback_message()

                if response.status_code == 403:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', '')
                    if 'quota' in error_msg.lower() or 'rate' in error_msg.lower():
                        AIService._last_failure_time = time.time()
                        return self._get_fallback_message()
                    return f"AI Service error: {error_msg}"

                response.raise_for_status()
                data = response.json()

                # Reset failure tracking on success
                AIService._last_failure_time = 0

                choices = data.get('choices', [])
                if choices:
                    message = choices[0].get('message', {})
                    return message.get('content', self._get_fallback_message())

                return self._get_fallback_message()

            except Exception as e:
                print(f"Groq API attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    AIService._last_failure_time = time.time()
                    return f"AI Service error: {str(e)}"

        return self._get_fallback_message()

    def _get_fallback_message(self):
        """Return a helpful static message when AI is unavailable."""
        return (
            "<h3>AI Summary Temporarily Unavailable</h3>"
            "<p>The AI analysis service is currently experiencing high demand. "
            "Your business metrics and KPIs are still being tracked accurately above. "
            "Review your alerts panel for any immediate action items.</p>"
            "<p><em>The AI summary will regenerate automatically on your next visit.</em></p>"
        )

    def generate_content(self, prompt, cache_key=None):
        """Unified method for generating content."""
        if not self.available:
            return self._get_fallback_message()

        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]

        if self._is_in_cooldown():
            return self._get_fallback_message()

        result_text = self._call_api(prompt)

        if cache_key and result_text and "Unavailable" not in result_text:
            self._cache[cache_key] = result_text

        return result_text

    def generate_business_summary(self, snapshot, alerts):
        if not snapshot:
            return self._get_fallback_message()

        cache_key = f"summary_{snapshot.id}_{len(alerts)}"

        alert_summary = "\n".join([f"- {a.message}" for a in alerts[:5]])

        prompt = f"""
        As a business advisor for a micro-business in Pakistan, analyze the following performance metrics and provide a concise, actionable summary.
        
        Metrics:
        - Revenue Growth Rate: {snapshot.rgr:.2%}
        - Inventory Turnover: {snapshot.itr:.2f}
        - Expense Ratio: {snapshot.er:.2%}
        - Stock Coverage: {snapshot.scp:.1f} days
        - Business Health Score: {snapshot.bhs}/100
        
        Recent Alerts:
        {alert_summary if alert_summary else "No critical alerts."}
        
        Provide:
        1. A brief assessment of the business health.
        2. Top 2 specific recommendations for improvement.
        3. A motivational closing sentence.
        
        Format your response in beautiful, semantic HTML. Use tags like <h3>, <p>, <ul>, <li>, and <strong>. 
        Do NOT wrap your response in markdown code blocks. Just return raw HTML.
        Keep it professional yet encouraging. Avoid making financial decisions, only provide explanations.
        Keep your response under 150 words. All monetary values should be in PKR.
        """

        return self.generate_content(prompt, cache_key=cache_key)
