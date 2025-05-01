# server/aadf/middleware.py

import json
from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog


class AuditLoggingMiddleware(MiddlewareMixin):
    """Middleware to log user actions for audit purposes"""

    def process_response(self, request, response):
        """Log user actions after processing the request"""

        # Only log successful requests that modify data
        if response.status_code not in [200, 201, 204]:
            return response

        # Skip logging for certain URLs
        skip_paths = ['/admin/', '/static/', '/media/', '/favicon.ico']
        if any(request.path.startswith(path) for path in skip_paths):
            return response

        # Only log authenticated users
        if not request.user.is_authenticated:
            return response

        # Determine action based on HTTP method
        action_map = {
            'GET': 'view',
            'POST': 'create',
            'PUT': 'update',
            'PATCH': 'update',
            'DELETE': 'delete'
        }
        action = action_map.get(request.method, 'unknown')

        # Extract entity type and ID from URL if available
        entity_type = 'unknown'
        entity_id = None

        # Parse path to extract entity info
        path_parts = request.path.strip('/').split('/')
        if len(path_parts) >= 2:
            entity_type = path_parts[1].replace('-', '_')
            if len(path_parts) >= 3 and path_parts[2].isdigit():
                entity_id = int(path_parts[2])

        # Get request details for logging
        details = {
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
        }

        # Add request body for POST/PUT/PATCH requests
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                if request.content_type == 'application/json':
                    body = json.loads(request.body.decode('utf-8'))
                else:
                    body = request.POST.dict()
                details['request_body'] = body
            except:
                pass

        # Get client IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # Create audit log entry
        try:
            AuditLog.objects.create(
                user=request.user,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                ip_address=ip_address
            )
        except:
            # Don't fail the request if audit logging fails
            pass

        return response


class TenderAccessMiddleware(MiddlewareMixin):
    """Middleware to control tender access based on status"""

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Check tender access permissions before processing view"""

        # Skip for non-tender URLs
        if not request.path.startswith('/tenders/'):
            return None

        # Skip for staff and admin
        if hasattr(request.user, 'role') and request.user.role in ['staff', 'admin']:
            return None

        # For vendors, only allow access to published tenders
        if hasattr(request.user, 'role') and request.user.role == 'vendor':
            if 'pk' in view_kwargs:
                try:
                    from .models import Tender
                    tender = Tender.objects.get(pk=view_kwargs['pk'])
                    if tender.status != 'published':
                        from django.http import HttpResponseForbidden
                        return HttpResponseForbidden("Access denied: Tender not published")
                except Tender.DoesNotExist:
                    pass

        return None