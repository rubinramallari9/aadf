# server/aadf/middleware.py

import json
import logging
from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from rest_framework.authtoken.models import Token
from django.http import JsonResponse
from .models import AuditLog

logger = logging.getLogger('aadf')

class TokenExpirationMiddleware(MiddlewareMixin):
    """Middleware to check token expiration"""
    
    def process_request(self, request):
        """Check if token is expired"""
        try:
            # Skip for unauthenticated requests or non-token authentication
            if not hasattr(request, 'auth') or not isinstance(request.auth, Token):
                return None
                
            # Get token creation time and check if expired
            token = request.auth
            token_creation = token.created
            expiration_time = token_creation + timedelta(days=settings.TOKEN_EXPIRY_DAYS)
            
            if timezone.now() > expiration_time:
                # Token expired, delete it and return 401
                token.delete()
                return JsonResponse({'error': 'Token expired'}, status=401)
                
            return None
        except Exception as e:
            # Log error but let the request continue
            logger.error(f"Error in token expiration middleware: {str(e)}")
            return None


class AuditLoggingMiddleware(MiddlewareMixin):
    """Middleware to log user actions for audit purposes"""

    def process_response(self, request, response):
        """Log user actions after processing the request"""
        try:
            # Only log successful requests that modify data
            if response.status_code not in [200, 201, 204]:
                return response

            # Skip logging for certain URLs
            skip_paths = ['/admin/', '/static/', '/media/', '/favicon.ico']
            if any(request.path.startswith(path) for path in skip_paths):
                return response

            # Only log authenticated users
            if not request.user or not request.user.is_authenticated:
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
                        # Remove sensitive data
                        if 'password' in body:
                            body['password'] = '********'
                        details['request_body'] = body
                    else:
                        body = request.POST.dict()
                        # Remove sensitive data
                        if 'password' in body:
                            body['password'] = '********'
                        details['request_body'] = body
                except Exception as e:
                    logger.warning(f"Failed to parse request body: {str(e)}")

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
                    entity_id=entity_id or 0,
                    details=details,
                    ip_address=ip_address
                )
            except Exception as e:
                logger.error(f"Failed to create audit log: {str(e)}")
                
        except Exception as e:
            # Catch all exception to prevent middleware from breaking the application
            logger.error(f"Error in audit logging middleware: {str(e)}")
            
        return response


class TenderAccessMiddleware(MiddlewareMixin):
    """Middleware to control tender access based on status"""

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Check tender access permissions before processing view"""
        try:
            # Skip for non-tender URLs
            if not request.path.startswith('/api/tenders/'):
                return None

            # Skip for admin, staff, and unauthenticated users
            if not hasattr(request.user, 'role') or not request.user.is_authenticated:
                return None
                
            if request.user.role in ['staff', 'admin']:
                return None

            # For vendors, only allow access to published tenders
            if request.user.role == 'vendor':
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
        except Exception as e:
            # Log error but let the request continue
            logger.error(f"Error in tender access middleware: {str(e)}")
            return None