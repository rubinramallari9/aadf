# server/aadf/views/audit_views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, F
from django.utils import timezone
from django.conf import settings
from datetime import datetime, timedelta

import logging
import json
import csv
import io

from ..models import AuditLog, User, Tender, Offer, VendorCompany
from ..serializers import AuditLogSerializer
from ..permissions import IsStaffOrAdmin, IsAdminUser

logger = logging.getLogger('aadf')


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing audit logs with enhanced filtering and analysis"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'action', 'entity_type']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter audit logs by query parameters"""
        queryset = AuditLog.objects.all()

        # Filter by user_id
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        # Filter by username
        username = self.request.query_params.get('username')
        if username:
            queryset = queryset.filter(user__username__icontains=username)

        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)

        # Filter by entity_type
        entity_type = self.request.query_params.get('entity_type')
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        # Filter by entity_id
        entity_id = self.request.query_params.get('entity_id')
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)

        # Filter by IP address
        ip_address = self.request.query_params.get('ip_address')
        if ip_address:
            queryset = queryset.filter(ip_address__icontains=ip_address)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        elif end_date:
            queryset = queryset.filter(created_at__lte=end_date)
            
        # Filter by time period (last X days/hours)
        period = self.request.query_params.get('period')
        if period:
            if period.endswith('d'):  # days
                try:
                    days = int(period[:-1])
                    start_time = timezone.now() - timedelta(days=days)
                    queryset = queryset.filter(created_at__gte=start_time)
                except ValueError:
                    pass
            elif period.endswith('h'):  # hours
                try:
                    hours = int(period[:-1])
                    start_time = timezone.now() - timedelta(hours=hours)
                    queryset = queryset.filter(created_at__gte=start_time)
                except ValueError:
                    pass
        
        # Full-text search in details
        search = self.request.query_params.get('search')
        if search:
            # Convert details to string for search (this is a simplification, 
            # in a production environment you might want a more sophisticated search)
            queryset = queryset.filter(
                Q(details__icontains=search) |
                Q(action__icontains=search) |
                Q(entity_type__icontains=search) |
                Q(user__username__icontains=search) |
                Q(ip_address__icontains=search)
            )
            
        return queryset

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get audit log statistics"""
        # Count by entity type
        entity_stats = AuditLog.objects.values('entity_type').annotate(count=Count('entity_type')).order_by('-count')
        
        # Count by action
        action_stats = AuditLog.objects.values('action').annotate(count=Count('action')).order_by('-count')
        
        # Count by user
        user_stats = AuditLog.objects.values('user__username', 'user_id').annotate(count=Count('user')).order_by('-count')[:10]
        
        # Count by IP address
        ip_stats = AuditLog.objects.values('ip_address').annotate(count=Count('ip_address')).order_by('-count')[:10]
        
        # Activity by hour of day
        hour_stats = AuditLog.objects.extra(
            select={'hour': "EXTRACT(hour FROM created_at)"}
        ).values('hour').annotate(count=Count('id')).order_by('hour')
        
        # Activity by day of week
        day_stats = AuditLog.objects.extra(
            select={'day': "EXTRACT(dow FROM created_at)"}
        ).values('day').annotate(count=Count('id')).order_by('day')
        
        # Recent activity trend (daily counts for last 30 days)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=30)
        
        # Get daily counts
        daily_counts = []
        current_date = start_date
        while current_date <= end_date:
            next_date = current_date + timedelta(days=1)
            count = AuditLog.objects.filter(
                created_at__gte=current_date,
                created_at__lt=next_date
            ).count()
            daily_counts.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
            current_date = next_date
        
        return Response({
            'total_logs': AuditLog.objects.count(),
            'entity_stats': list(entity_stats),
            'action_stats': list(action_stats),
            'user_stats': list(user_stats),
            'ip_stats': list(ip_stats),
            'hour_stats': list(hour_stats),
            'day_stats': list(day_stats),
            'daily_counts': daily_counts
        })
    
    @action(detail=False, methods=['get'])
    def user_activity(self, request):
        """Get activity statistics for a specific user"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            user = User.objects.get(id=user_id)
            
            # Get logs for this user
            logs = AuditLog.objects.filter(user=user)
            
            # Activity by entity type
            entity_stats = logs.values('entity_type').annotate(count=Count('entity_type')).order_by('-count')
            
            # Activity by action
            action_stats = logs.values('action').annotate(count=Count('action')).order_by('-count')
            
            # Activity by hour of day
            hour_stats = logs.extra(
                select={'hour': "EXTRACT(hour FROM created_at)"}
            ).values('hour').annotate(count=Count('id')).order_by('hour')
            
            # Recent activity trend (daily counts for last 30 days)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=30)
            
            # Get daily counts
            daily_counts = []
            current_date = start_date
            while current_date <= end_date:
                next_date = current_date + timedelta(days=1)
                count = logs.filter(
                    created_at__gte=current_date,
                    created_at__lt=next_date
                ).count()
                daily_counts.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'count': count
                })
                current_date = next_date
                
            # Last login time
            last_login = logs.filter(action='login').order_by('-created_at').first()
            
            # IP addresses used
            ip_addresses = logs.values('ip_address').distinct()
            
            # Count of actions by entity
            entity_actions = {}
            for entity_type in logs.values_list('entity_type', flat=True).distinct():
                entity_actions[entity_type] = logs.filter(
                    entity_type=entity_type
                ).values('action').annotate(count=Count('action'))
            
            return Response({
                'username': user.username,
                'total_logs': logs.count(),
                'entity_stats': list(entity_stats),
                'action_stats': list(action_stats),
                'hour_stats': list(hour_stats),
                'daily_counts': daily_counts,
                'last_login': last_login.created_at if last_login else None,
                'ip_addresses': [ip['ip_address'] for ip in ip_addresses],
                'entity_actions': entity_actions
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def entity_history(self, request):
        """Get audit history for a specific entity"""
        entity_type = request.query_params.get('entity_type')
        entity_id = request.query_params.get('entity_id')
        
        if not entity_type or not entity_id:
            return Response(
                {'error': 'Both entity_type and entity_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get logs for this entity
        logs = AuditLog.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id
        ).order_by('created_at')
        
        if not logs.exists():
            return Response(
                {'error': 'No audit logs found for this entity'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get entity details if available
        entity_details = None
        entity_name = None
        
        if entity_type == 'tender':
            try:
                tender = Tender.objects.get(id=entity_id)
                entity_details = {
                    'reference_number': tender.reference_number,
                    'title': tender.title,
                    'status': tender.status,
                    'created_at': tender.created_at
                }
                entity_name = tender.reference_number
            except Tender.DoesNotExist:
                pass
        elif entity_type == 'offer':
            try:
                offer = Offer.objects.get(id=entity_id)
                entity_details = {
                    'tender_reference': offer.tender.reference_number,
                    'vendor_name': offer.vendor.name,
                    'status': offer.status,
                    'created_at': offer.created_at
                }
                entity_name = f"Offer from {offer.vendor.name} for {offer.tender.reference_number}"
            except Offer.DoesNotExist:
                pass
        elif entity_type == 'user':
            try:
                user = User.objects.get(id=entity_id)
                entity_details = {
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'is_active': user.is_active,
                    'date_joined': user.date_joined
                }
                entity_name = user.username
            except User.DoesNotExist:
                pass
                
        # Format the history as a timeline
        timeline = []
        for log in logs:
            timeline.append({
                'timestamp': log.created_at,
                'user': log.user.username if log.user else 'System',
                'action': log.action,
                'details': log.details or {},
                'ip_address': log.ip_address
            })
            
        # Count actions
        action_counts = logs.values('action').annotate(count=Count('action'))
        
        # Count users involved
        user_counts = logs.exclude(user__isnull=True).values(
            'user__username', 'user_id'
        ).annotate(count=Count('user'))
        
        return Response({
            'entity_type': entity_type,
            'entity_id': entity_id,
            'entity_name': entity_name,
            'entity_details': entity_details,
            'total_logs': logs.count(),
            'timeline': timeline,
            'action_counts': list(action_counts),
            'user_counts': list(user_counts)
        })
    
    @action(detail=False, methods=['post'])
    def export_logs(self, request):
        """Export audit logs to CSV"""
        # Get filter parameters from request
        user_id = request.data.get('user_id')
        action = request.data.get('action')
        entity_type = request.data.get('entity_type')
        entity_id = request.data.get('entity_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        # Build queryset with filters
        queryset = AuditLog.objects.all()
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            
        if action:
            queryset = queryset.filter(action=action)
            
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)
            
        if entity_id:
            queryset = queryset.filter(entity_id=entity_id)
            
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
        elif start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        elif end_date:
            queryset = queryset.filter(created_at__lte=end_date)
            
        # Order by timestamp
        queryset = queryset.order_by('created_at')
        
        # Create CSV in memory
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([
            'Timestamp', 'User', 'Action', 'Entity Type', 'Entity ID', 
            'IP Address', 'Details'
        ])
        
        # Write data rows
        for log in queryset:
            # Format details as JSON string
            details_str = json.dumps(log.details) if log.details else ''
            
            writer.writerow([
                log.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                log.user.username if log.user else 'System',
                log.action,
                log.entity_type,
                log.entity_id,
                log.ip_address or '',
                details_str
            ])
            
        # Create response with CSV
        buffer.seek(0)
        
        # Generate filename
        filename = f"audit_logs_{timezone.now().strftime('%Y%m%d%H%M%S')}.csv"
        
        # Create the HTTP response
        response = Response(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @action(detail=False, methods=['get'])
    def security_alerts(self, request):
        """Get security alerts based on audit logs"""
        # Define time periods for detection
        last_day = timezone.now() - timedelta(days=1)
        last_week = timezone.now() - timedelta(days=7)
        
        alerts = []
        
        # 1. Multiple failed login attempts
        failed_logins = AuditLog.objects.filter(
            action='login_failed',
            created_at__gte=last_day
        )
        
        # Group by user and IP
        login_attempts = {}
        for log in failed_logins:
            user_id = log.details.get('username') if log.details else None
            ip = log.ip_address
            
            if not user_id or not ip:
                continue
                
            key = f"{user_id}|{ip}"
            if key not in login_attempts:
                login_attempts[key] = []
            login_attempts[key].append(log)
            
        # Check for suspicious patterns
        for key, logs in login_attempts.items():
            if len(logs) >= 5:  # 5+ failed attempts
                user_id, ip = key.split('|')
                alerts.append({
                    'type': 'failed_login_attempts',
                    'severity': 'high' if len(logs) >= 10 else 'medium',
                    'details': {
                        'username': user_id,
                        'ip_address': ip,
                        'attempts': len(logs),
                        'timestamps': [log.created_at for log in logs]
                    }
                })
                
        # 2. Unusual access times
        business_hours_start = 8  # 8 AM
        business_hours_end = 18   # 6 PM
        
        non_business_hours_access = AuditLog.objects.extra(
            where=["EXTRACT(hour FROM created_at) < %s OR EXTRACT(hour FROM created_at) >= %s"],
            params=[business_hours_start, business_hours_end]
        ).filter(
            created_at__gte=last_week
        ).exclude(
            action='system'
        )
        
        # Group by user
        unusual_access = {}
        for log in non_business_hours_access:
            if not log.user_id:
                continue
                
            if log.user_id not in unusual_access:
                unusual_access[log.user_id] = []
            unusual_access[log.user_id].append(log)
            
        # Check for patterns
        for user_id, logs in unusual_access.items():
            if len(logs) >= 10:  # Significant non-business hours activity
                try:
                    user = User.objects.get(id=user_id)
                    alerts.append({
                        'type': 'unusual_access_times',
                        'severity': 'medium',
                        'details': {
                            'username': user.username,
                            'count': len(logs),
                            'sample_times': [log.created_at for log in logs[:5]]
                        }
                    })
                except User.DoesNotExist:
                    pass
                    
        # 3. Multiple IP addresses for same user
        # Group logs by user
        user_ips = {}
        recent_logs = AuditLog.objects.filter(
            created_at__gte=last_day
        ).exclude(
            user__isnull=True
        ).exclude(
            ip_address__isnull=True
        ).exclude(
            ip_address=''
        )
        
        for log in recent_logs:
            if log.user_id not in user_ips:
                user_ips[log.user_id] = set()
            user_ips[log.user_id].add(log.ip_address)
            
        # Check for users with multiple IPs
        for user_id, ips in user_ips.items():
            if len(ips) >= 3:  # 3+ different IPs in 24 hours
                try:
                    user = User.objects.get(id=user_id)
                    alerts.append({
                        'type': 'multiple_ip_addresses',
                        'severity': 'medium',
                        'details': {
                            'username': user.username,
                            'ip_count': len(ips),
                            'ip_addresses': list(ips)
                        }
                    })
                except User.DoesNotExist:
                    pass
                    
        # 4. Sensitive operations
        sensitive_actions = [
            'reset_password', 'change_role', 'deactivate_user', 
            'system', 'delete'
        ]
        
        sensitive_logs = AuditLog.objects.filter(
            action__in=sensitive_actions,
            created_at__gte=last_week
        )
        
        for log in sensitive_logs:
            alerts.append({
                'type': 'sensitive_operation',
                'severity': 'low',
                'details': {
                    'username': log.user.username if log.user else 'System',
                    'action': log.action,
                    'timestamp': log.created_at,
                    'entity_type': log.entity_type,
                    'entity_id': log.entity_id,
                    'details': log.details or {}
                }
            })
            
        # Sort alerts by severity
        severity_order = {'high': 0, 'medium': 1, 'low': 2}
        alerts.sort(key=lambda x: severity_order[x['severity']])
        
        return Response({
            'total_alerts': len(alerts),
            'alerts': alerts
        })
    
    @action(detail=False, methods=['get'])
    def action_types(self, request):
        """Get all action types in the audit log"""
        actions = AuditLog.objects.values('action').distinct().order_by('action')
        return Response([a['action'] for a in actions])
    
    @action(detail=False, methods=['get'])
    def entity_types(self, request):
        """Get all entity types in the audit log"""
        entities = AuditLog.objects.values('entity_type').distinct().order_by('entity_type')
        return Response([e['entity_type'] for e in entities])