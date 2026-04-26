import os
import requests
import json
import time
import threading
from django.conf import settings

# Force pure python implementation for protobuf to avoid C extension issues on Python 3.14
os.environ['PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION'] = 'python'


class AIService:
    """Singleton AI Service that handles Gemini API calls with robust rate-limit handling."""
    _instance = None
    _lock = threading.Lock()
    MAX_RETRIES = 3
    BASE_DELAY = 2  # seconds
    # Track recent failures to avoid hammering a rate-limited API
    _last_failure_time = 0
    _cooldown_seconds = 120  # Wait longer after a rate-limit failure
    _cache = {} # Simple in-memory cache for the session

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
        self.use_sdk = False
        self.api_key = os.getenv('GEMINI_API_KEY', '').strip()
        # Use 2.5-flash as requested
        self.model_name = 'gemini-2.5-flash'
        
        # Try SDK first
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.use_sdk = True
            self.available = True
            print(f"AI Service initialized with SDK ({self.model_name})")
        except Exception as e:
            print(f"AI Service SDK init failed: {e}. Falling back to REST API.")
            if self.api_key:
                self.available = True
            else:
                print("No API key found, AI Service unavailable.")

    def _is_in_cooldown(self):
        """Check if we're still in cooldown after a rate-limit failure."""
        if self._last_failure_time == 0:
            return False
        elapsed = time.time() - self._last_failure_time
        return elapsed < self._cooldown_seconds

    def _call_rest_api(self, prompt):
        """Fallback method using REST API directly to avoid protobuf issues."""
        if self._is_in_cooldown():
            return self._get_fallback_message()

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "maxOutputTokens": 500,
                "temperature": 0.7
            }
        }

        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                
                if response.status_code == 429:
                    # Don't sleep long in a web request, just fail and let the cooldown handle it
                    AIService._last_failure_time = time.time()
                    print(f"AI Service rate limited (429) on attempt {attempt + 1}. Entering cooldown.")
                    return self._get_fallback_message()
                
                if response.status_code == 403:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', '')
                    if 'quota' in error_msg.lower() or 'rate' in error_msg.lower():
                        AIService._last_failure_time = time.time()
                        print(f"AI Service quota exceeded: {error_msg}")
                        return self._get_fallback_message()
                    return f"AI Service error: {error_msg}"
                
                response.raise_for_status()
                data = response.json()
                
                # Reset failure tracking on success
                AIService._last_failure_time = 0
                
                candidates = data.get('candidates', [])
                if candidates:
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if parts:
                        return parts[0].get('text', self._get_fallback_message())
                
                return self._get_fallback_message()
                
            except Exception as e:
                print(f"REST API attempt {attempt + 1} failed: {e}")
                if attempt == self.MAX_RETRIES - 1:
                    AIService._last_failure_time = time.time()
                    return f"AI Service error (REST): {str(e)}"
        
        return self._get_fallback_message()

    def _get_fallback_message(self):
        """Return a helpful static message when AI is unavailable."""
        return (
            "📊 **AI Summary Temporarily Unavailable**\n\n"
            "The AI analysis service is currently experiencing high demand. "
            "Your business metrics and KPIs are still being tracked accurately above. "
            "Review your alerts panel for any immediate action items.\n\n"
            "💡 *The AI summary will regenerate automatically on your next visit.*"
        )

    def generate_content(self, prompt, cache_key=None):
        """Unified method for generating content via SDK or REST."""
        if not self.available:
            return self._get_fallback_message()
        
        if cache_key and cache_key in self._cache:
            return self._cache[cache_key]
        
        if self._is_in_cooldown():
            return self._get_fallback_message()
        
        result_text = ""
        if self.use_sdk:
            try:
                result = self.client.models.generate_content(
                    model=self.model_name,
                    contents=[prompt]
                )
                AIService._last_failure_time = 0
                result_text = result.text
            except Exception as e:
                error_str = str(e).lower()
                if '429' in error_str or 'quota' in error_str or 'rate' in error_str:
                    AIService._last_failure_time = time.time()
                    print(f"SDK rate limited: {e}. Entering cooldown.")
                    return self._get_fallback_message()
                print(f"SDK call failed: {e}. Trying REST fallback.")
                result_text = self._call_rest_api(prompt)
        else:
            result_text = self._call_rest_api(prompt)
        
        if cache_key and result_text and "Unavailable" not in result_text:
            self._cache[cache_key] = result_text
            
        return result_text

    def generate_business_summary(self, snapshot, alerts):
        if not snapshot:
            return self._get_fallback_message()
            
        # Create a cache key based on snapshot ID and alert count to avoid redundant calls
        cache_key = f"summary_{snapshot.id}_{len(alerts)}"
        
        alert_summary = "\n".join([f"- {a.message}" for a in alerts[:5]])
        
        prompt = f"""
        As a business advisor for a micro-business, analyze the following performance metrics and provide a concise, actionable summary.
        
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
        Do NOT wrap your response in markdown code blocks (e.g., no ```html). Just return the raw HTML string.
        Keep it professional yet encouraging. Avoid making financial decisions, only provide explanations.
        Keep your response under 150 words.
        """
        
        return self.generate_content(prompt, cache_key=cache_key)
