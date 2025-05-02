# server/aadf/views/notification_views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

import logging

from ..models import Notification, User, AuditLog
from ..serializers import NotificationSerializer
from ..permissions import IsStaffOrAdmin

logger = logging.getLogger('aadf')


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notifications with email integration"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'is_read']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter notifications for the authenticated user"""
        queryset = Notification.objects.filter(user=self.request.user)
        
        # Filter by read status if provided
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=(is_read.lower() == 'true'))
            
        # Filter by type if provided
        notification_type = self.request.query_params.get('type')
        if notification_type:
            queryset = queryset.filter(type=notification_type)
            
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
            
        # Search in title or message
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(message__icontains=search)
            )
            
        return queryset

    def perform_create(self, serializer):
        """Ensure user is set to authenticated user"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        
        # Verify ownership
        if notification.user != request.user:
            return Response(
                {'error': 'You do not have permission to mark this notification as read'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        notification.is_read = True
        notification.save()
        
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for the authenticated user"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        
        return Response({'status': 'all notifications marked as read'})

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get the count of unread notifications"""
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        
        return Response({'count': count})
    
    @action(detail=False, methods=['delete'])
    def clear_read(self, request):
        """Delete all read notifications for the user"""
        # Get all read notifications
        read_notifications = Notification.objects.filter(
            user=request.user, 
            is_read=True
        )
        
        # Count before deletion
        count = read_notifications.count()
        
        # Delete them
        read_notifications.delete()
        
        return Response({
            'status': 'success',
            'count': count,
            'message': f'{count} read notifications have been deleted'
        })
    
    @action(detail=True, methods=['post'])
    def send_email(self, request, pk=None):
        """Send notification as email"""
        notification = self.get_object()
        
        # Verify ownership
        if notification.user != request.user and request.user.role not in ['admin', 'staff']:
            return Response(
                {'error': 'You do not have permission to email this notification'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Verify user has an email
        if not notification.user.email:
            return Response(
                {'error': 'The user does not have an email address'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Send email
            self._send_notification_email(notification)
            
            # Log the email
            AuditLog.objects.create(
                user=request.user,
                action='send_notification_email',
                entity_type='notification',
                entity_id=notification.id,
                details={'recipient_email': notification.user.email},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response({'status': 'email sent'})
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return Response(
                {'error': f'Failed to send email: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _send_notification_email(self, notification):
        """Send an email for the notification"""
        context = {
            'user': notification.user,
            'notification': notification,
            'platform_name': settings.PROCUREMENT_SETTINGS.get('PLATFORM_NAME', 'AADF Procurement Platform'),
            'platform_url': settings.PROCUREMENT_SETTINGS.get('PLATFORM_URL', 'http://localhost:3000')
        }
        
        # Render email templates
        html_content = render_to_string('notifications/email.html', context)
        text_content = strip_tags(html_content)
        
        # Fallback to basic text if template is not available
        if not html_content or html_content.startswith("{% extends"):
            text_content = f"""
            Hello {notification.user.first_name or notification.user.username},
            
            {notification.title}
            
            {notification.message}
            
            Best regards,
            AADF Procurement Platform
            """
            html_content = None
        
        # Create email message
        email = EmailMultiAlternatives(
            subject=notification.title,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[notification.user.email]
        )
        
        # Attach HTML content if available
        if html_content:
            email.attach_alternative(html_content, "text/html")
        
        # Send email
        email.send()
    
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def bulk_create(self, request):
        """Create notifications for multiple users"""
        users_ids = request.data.get('user_ids', [])
        role = request.data.get('role')
        title = request.data.get('title')
        message = request.data.get('message')
        notification_type = request.data.get('type', 'info')
        send_email = request.data.get('send_email', False)
        
        if not title or not message:
            return Response(
                {'error': 'Title and message are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get users to notify
        users = []
        if users_ids:
            users = User.objects.filter(id__in=users_ids)
        elif role:
            users = User.objects.filter(role=role)
        else:
            return Response(
                {'error': 'Either user_ids or role must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not users.exists():
            return Response(
                {'error': 'No users found with the specified criteria'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Create notifications
        notifications_created = 0
        emails_sent = 0
        
        for user in users:
            # Create notification
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message,
                type=notification_type
            )
            notifications_created += 1
            
            # Send email if requested and user has email
            if send_email and user.email:
                try:
                    self._send_notification_email(notification)
                    emails_sent += 1
                except Exception as e:
                    logger.error(f"Failed to send email to {user.email}: {e}")
        
        # Log the bulk creation
        AuditLog.objects.create(
            user=request.user,
            action='bulk_create_notifications',
            entity_type='notification',
            entity_id=0,
            details={
                'users_count': users.count(),
                'notifications_created': notifications_created,
                'emails_sent': emails_sent
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({
            'status': 'success',
            'notifications_created': notifications_created,
            'emails_sent': emails_sent
        })
    
    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available notification types"""
        types = [
            {
                'id': 'info',
                'name': 'Information',
                'description': 'General information notifications'
            },
            {
                'id': 'success',
                'name': 'Success',
                'description': 'Success notifications for completed actions'
            },
            {
                'id': 'warning',
                'name': 'Warning',
                'description': 'Warning notifications for potential issues'
            },
            {
                'id': 'error',
                'name': 'Error',
                'description': 'Error notifications for failed actions'
            },
            {
                'id': 'tender',
                'name': 'Tender',
                'description': 'Notifications related to tenders'
            },
            {
                'id': 'offer',
                'name': 'Offer',
                'description': 'Notifications related to offers'
            },
            {
                'id': 'evaluation',
                'name': 'Evaluation',
                'description': 'Notifications related to evaluations'
            },
            {
                'id': 'system',
                'name': 'System',
                'description': 'System notifications'
            }
        ]
        
        return Response(types)
    
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def send_newsletter(self, request):
        """Send a newsletter to all users"""
        subject = request.data.get('subject')
        content = request.data.get('content')
        roles = request.data.get('roles', [])
        
        if not subject or not content:
            return Response(
                {'error': 'Subject and content are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get users to notify
        users_query = User.objects.filter(is_active=True)
        if roles:
            users_query = users_query.filter(role__in=roles)
            
        users_with_email = users_query.exclude(
            Q(email='') | Q(email__isnull=True)
        )
        
        if not users_with_email.exists():
            return Response(
                {'error': 'No users found with valid email addresses'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Prepare email
        recipients = list(users_with_email.values_list('email', flat=True))
        
        # Try to use HTML template if available
        try:
            html_content = render_to_string('email/newsletter.html', {
                'subject': subject,
                'content': content,
                'platform_name': settings.PROCUREMENT_SETTINGS.get('PLATFORM_NAME', 'AADF Procurement Platform'),
                'platform_url': settings.PROCUREMENT_SETTINGS.get('PLATFORM_URL', 'http://localhost:3000')
            })
            text_content = strip_tags(html_content)
        except:
            text_content = content
            html_content = None
        
        # Send email
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[settings.DEFAULT_FROM_EMAIL],  # Send to self
            bcc=recipients  # BCC all recipients for privacy
        )
        
        if html_content:
            email.attach_alternative(html_content, "text/html")
            
        email.send()
        
        # Log the newsletter
        AuditLog.objects.create(
            user=request.user,
            action='send_newsletter',
            entity_type='notification',
            entity_id=0,
            details={
                'subject': subject,
                'recipients_count': len(recipients),
                'roles': roles or 'all'
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({
            'status': 'success',
            'recipients_count': len(recipients)
        })