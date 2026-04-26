from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .services import AIService
import json

@csrf_exempt
def chat_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            query = data.get('query')
            if not query:
                return JsonResponse({'error': 'No query provided'}, status=400)
            
            ai_service = AIService()
            if not ai_service.available:
                return JsonResponse({'response': "AI Chat is currently unavailable. Please check your API configuration."})
            
            # We can pass context here if needed, e.g., current KPIs
            # For FAQ, we'll use a specific prompt
            prompt = f"""
            You are Biz-ight Assistant, a specialized AI for micro-business management.
            Help the user with business advice, dashboard navigation, or general FAQs.
            User query: {query}
            
            Guidelines:
            - Be professional yet supportive.
            - Focus on micro and home-based business contexts.
            - Keep answers concise and actionable.
            - USE RICH FORMATTING: Use markdown headings (##), bullet points (-), and bold text (**word**) to make your response easy to read.
            - If suggesting steps, use numbered lists.
            """
            
            response_text = ai_service.generate_content(prompt)
            return JsonResponse({'response': response_text})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Invalid request'}, status=405)
