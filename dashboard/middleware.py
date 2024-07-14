# your_app/middleware.py

from django.utils import timezone
from .models import PageVisit, SiteVisit
from knox.models import AuthToken

# Page Traffic
class TrafficMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not request.path.startswith('/admin/'):
            # Determine if it's an API call
            is_api_call = request.path.startswith('/api/')

            # Get Knox token if present
            token_key = None
            if is_api_call:
                auth_header = request.META.get('HTTP_AUTHORIZATION')
                if auth_header and auth_header.startswith('Token '):
                    token_key = auth_header.split(' ')[1][:8]  # Knox uses first 8 chars as key

            # Ensure session for non-API calls
            if not is_api_call and not request.session.session_key:
                request.session.save()

            PageVisit.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key if not is_api_call else None,
                token_key=token_key,
                ip_address=self.get_client_ip(request),
                path=request.path,
                method=request.method,
                is_api_call=is_api_call,
                referer=request.META.get('HTTP_REFERER'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                timestamp=timezone.now()
            )

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

# Site Visit
class SiteVisitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Don't track admin pages
        if not request.path.startswith('/admin/'):
            SiteVisit.objects.create(
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                path=request.path,
            )

        return response

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip