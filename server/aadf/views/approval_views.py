# server/aadf/views/approval_views.py

from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, F
from django.utils import timezone
from django.conf import settings

import logging
import json
from datetime import timedelta

from ..models import (
    Approval, Tender, User, AuditLog, Notification
)
from ..serializers import ApprovalSerializer
from ..permissions import IsStaffOrAdmin, IsAdminUser
from ..utils import create_notification

logger = logging.getLogger('aadf')


class ApprovalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing workflow approvals"""
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter approvals based on user role and query parameters"""
        user = self.request.user
        queryset = Approval.objects.all()
        
        # Filter by tender_id if provided
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
            
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        # Filter by user_id if provided
        approver_id = self.request.query_params.get('user_id')
        if approver_id:
            queryset = queryset.filter(user_id=approver_id)
            
        # Apply user role restrictions
        if user.role not in ['staff', 'admin']:
            # Regular users can only see their own approvals
            queryset = queryset.filter(user=user)
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign user to the authenticated user if not provided"""
        user_id = self.request.data.get('user_id')
        
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                serializer.save(user=user)
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found")
        else:
            serializer.save(user=self.request.user)
            
        # Log the creation
        approval = serializer.instance
        
        AuditLog.objects.create(
            user=self.request.user,
            action='create_approval',
            entity_type='approval',
            entity_id=approval.id,
            details={
                'tender_id': approval.tender.id,
                'tender_reference': approval.tender.reference_number,
                'status': approval.status
            },
            ip_address=self.request.META.get('REMOTE_ADDR', '')
        )
        
        # Notify the approval assignee if different from creator
        if user_id and int(user_id) != self.request.user.id:
            create_notification(
                user=user,
                title='New Approval Required',
                message=f'You have been assigned to approve the tender {approval.tender.reference_number}.',
                notification_type='info',
                related_entity=approval.tender
            )

    def update(self, request, *args, **kwargs):
        """Handle approval update"""
        approval = self.get_object()
        
        # Only the assigned user or admin can update an approval
        if request.user.role != 'admin' and approval.user.id != request.user.id:
            return Response(
                {'error': 'You do not have permission to update this approval'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Can't change a processed approval unless admin
        if approval.status != 'pending' and request.user.role != 'admin':
            return Response(
                {'error': 'Cannot update an already processed approval'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update the approval
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(approval, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Log the update
        AuditLog.objects.create(
            user=request.user,
            action='update_approval',
            entity_type='approval',
            entity_id=approval.id,
            details={
                'tender_id': approval.tender.id,
                'tender_reference': approval.tender.reference_number,
                'status': approval.status
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a tender"""
        approval = self.get_object()
        
        # Verify the user has permission to approve
        if request.user.id != approval.user.id and request.user.role != 'admin':
            return Response(
                {'error': 'You do not have permission to approve this tender'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if approval.status == 'pending':
            # Get comments from request
            comments = request.data.get('comments', '')
            
            # Update status
            approval.status = 'approved'
            approval.comments = comments
            approval.save()
            
            # Log the approval
            AuditLog.objects.create(
                user=request.user,
                action='approve_tender',
                entity_type='approval',
                entity_id=approval.id,
                details={
                    'tender_id': approval.tender.id,
                    'tender_reference': approval.tender.reference_number,
                    'comments': comments
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Notify the tender creator
            if approval.tender.created_by:
                create_notification(
                    user=approval.tender.created_by,
                    title='Tender Approved',
                    message=f'Your tender {approval.tender.reference_number} has been approved by {approval.user.username}.',
                    notification_type='success',
                    related_entity=approval.tender
                )
                
            # Check if this was the final approval in a chain
            # If all approvals are complete, trigger next workflow step
            # (This is a simplified example - real implementation would depend on approval workflow)
            pending_approvals = Approval.objects.filter(
                tender=approval.tender,
                status='pending'
            )
            
            if not pending_approvals.exists():
                # All approvals are complete
                if approval.tender.status == 'draft':
                    # Auto-publish if configured
                    if settings.PROCUREMENT_SETTINGS.get('AUTO_PUBLISH_AFTER_APPROVAL', False):
                        approval.tender.status = 'published'
                        approval.tender.published_at = timezone.now()
                        approval.tender.save()
                        
                        # Notify vendor users
                        vendor_users = User.objects.filter(role='vendor', is_active=True)
                        for user in vendor_users:
                            create_notification(
                                user=user,
                                title='New Tender Published',
                                message=f'A new tender "{approval.tender.title}" has been published.',
                                notification_type='info',
                                related_entity=approval.tender
                            )
                            
                # Notify all approvers that the process is complete
                all_approvers = Approval.objects.filter(
                    tender=approval.tender
                ).exclude(id=approval.id).values_list('user_id', flat=True)
                
                for approver_id in all_approvers:
                    try:
                        approver = User.objects.get(id=approver_id)
                        create_notification(
                            user=approver,
                            title='Approval Process Complete',
                            message=f'All approvals for tender {approval.tender.reference_number} have been completed.',
                            notification_type='info',
                            related_entity=approval.tender
                        )
                    except User.DoesNotExist:
                        pass
                
            return Response({
                'status': 'approved',
                'all_completed': not pending_approvals.exists()
            })
        return Response({'error': 'approval already processed'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a tender"""
        approval = self.get_object()
        
        # Verify the user has permission to reject
        if request.user.id != approval.user.id and request.user.role != 'admin':
            return Response(
                {'error': 'You do not have permission to reject this tender'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if approval.status == 'pending':
            # Get comments from request
            comments = request.data.get('comments', '')
            
            if not comments:
                return Response(
                    {'error': 'Comments are required when rejecting a tender'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Update status
            approval.status = 'rejected'
            approval.comments = comments
            approval.save()
            
            # Log the rejection
            AuditLog.objects.create(
                user=request.user,
                action='reject_tender',
                entity_type='approval',
                entity_id=approval.id,
                details={
                    'tender_id': approval.tender.id,
                    'tender_reference': approval.tender.reference_number,
                    'comments': comments
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Notify the tender creator
            if approval.tender.created_by:
                create_notification(
                    user=approval.tender.created_by,
                    title='Tender Rejected',
                    message=f'Your tender {approval.tender.reference_number} has been rejected by {approval.user.username}. Reason: {comments}',
                    notification_type='warning',
                    related_entity=approval.tender
                )
                
            # Notify all other approvers that the process has been terminated
            other_approvers = Approval.objects.filter(
                tender=approval.tender
            ).exclude(id=approval.id).values_list('user_id', flat=True)
            
            for approver_id in other_approvers:
                try:
                    approver = User.objects.get(id=approver_id)
                    create_notification(
                        user=approver,
                        title='Approval Process Terminated',
                        message=f'The approval process for tender {approval.tender.reference_number} has been terminated due to rejection.',
                        notification_type='info',
                        related_entity=approval.tender
                    )
                except User.DoesNotExist:
                    pass
                
            return Response({'status': 'rejected'})
        return Response({'error': 'approval already processed'},
                        status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reassign(self, request, pk=None):
        """Reassign approval to another user"""
        approval = self.get_object()
        new_user_id = request.data.get('user_id')
        
        # Verify the requester has permission to reassign
        if request.user.role != 'admin' and approval.user.id != request.user.id:
            return Response(
                {'error': 'You do not have permission to reassign this approval'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Can't reassign a processed approval
        if approval.status != 'pending':
            return Response(
                {'error': 'Cannot reassign an already processed approval'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not new_user_id:
            return Response(
                {'error': 'user_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            new_user = User.objects.get(id=new_user_id)
            
            # Can't reassign to the same user
            if new_user.id == approval.user.id:
                return Response(
                    {'error': 'Cannot reassign to the same user'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Store old user for notification
            old_user = approval.user
                
            # Update approval
            approval.user = new_user
            approval.save()
            
            # Log the reassignment
            AuditLog.objects.create(
                user=request.user,
                action='reassign_approval',
                entity_type='approval',
                entity_id=approval.id,
                details={
                    'tender_id': approval.tender.id,
                    'tender_reference': approval.tender.reference_number,
                    'old_user_id': old_user.id,
                    'new_user_id': new_user.id
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Notify the new approver
            create_notification(
                user=new_user,
                title='Approval Assignment',
                message=f'You have been assigned to approve tender {approval.tender.reference_number}.',
                notification_type='info',
                related_entity=approval.tender
            )
            
            # Notify the old approver
            create_notification(
                user=old_user,
                title='Approval Reassigned',
                message=f'Your approval for tender {approval.tender.reference_number} has been reassigned to {new_user.username}.',
                notification_type='info',
                related_entity=approval.tender
            )
            
            return Response({
                'status': 'success',
                'message': f'Approval reassigned from {old_user.username} to {new_user.username}'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def create_approval_chain(self, request):
        """Create an approval chain for a tender with multiple approvers"""
        tender_id = request.data.get('tender_id')
        approver_ids = request.data.get('approver_ids', [])
        
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not approver_ids or not isinstance(approver_ids, list):
            return Response(
                {'error': 'approver_ids must be a non-empty list'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Check if tender already has approvals
            existing_approvals = Approval.objects.filter(tender=tender)
            if existing_approvals.exists():
                return Response(
                    {'error': 'Tender already has approvals. Clear existing approvals first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Create approvals for each approver in the chain
            created_approvals = []
            for approver_id in approver_ids:
                try:
                    approver = User.objects.get(id=approver_id)
                    
                    approval = Approval.objects.create(
                        tender=tender,
                        user=approver,
                        status='pending'
                    )
                    
                    created_approvals.append({
                        'id': approval.id,
                        'user': approver.username,
                        'status': approval.status
                    })
                    
                    # Notify the approver
                    create_notification(
                        user=approver,
                        title='New Approval Required',
                        message=f'You have been assigned to approve the tender {tender.reference_number}.',
                        notification_type='info',
                        related_entity=tender
                    )
                    
                except User.DoesNotExist:
                    # Skip invalid users
                    continue
                    
            # Log the creation of the approval chain
            AuditLog.objects.create(
                user=request.user,
                action='create_approval_chain',
                entity_type='tender',
                entity_id=tender.id,
                details={
                    'tender_reference': tender.reference_number,
                    'approver_count': len(created_approvals),
                    'approver_ids': approver_ids
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Notify the tender creator
            if tender.created_by:
                create_notification(
                    user=tender.created_by,
                    title='Approval Process Started',
                    message=f'An approval process has been initiated for your tender {tender.reference_number}.',
                    notification_type='info',
                    related_entity=tender
                )
                
            return Response({
                'status': 'success',
                'tender_id': tender.id,
                'tender_reference': tender.reference_number,
                'approvals': created_approvals
            })
            
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def clear_approvals(self, request):
        """Clear all approvals for a tender"""
        tender_id = request.data.get('tender_id')
        
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Only admins can clear approvals
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can clear approval chains'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Get existing approvals
            approvals = Approval.objects.filter(tender=tender)
            approval_count = approvals.count()
            
            if approval_count == 0:
                return Response(
                    {'error': 'No approvals found for this tender'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Store approver IDs for notifications
            approver_ids = approvals.values_list('user_id', flat=True)
            
            # Delete all approvals
            approvals.delete()
            
            # Log the clearing of approvals
            AuditLog.objects.create(
                user=request.user,
                action='clear_approvals',
                entity_type='tender',
                entity_id=tender.id,
                details={
                    'tender_reference': tender.reference_number,
                    'approval_count': approval_count
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Notify approvers
            for approver_id in approver_ids:
                try:
                    approver = User.objects.get(id=approver_id)
                    create_notification(
                        user=approver,
                        title='Approval Cancelled',
                        message=f'The approval process for tender {tender.reference_number} has been cancelled by an administrator.',
                        notification_type='info',
                        related_entity=tender
                    )
                except User.DoesNotExist:
                    pass
                
            # Notify the tender creator
            if tender.created_by:
                create_notification(
                    user=tender.created_by,
                    title='Approval Process Cancelled',
                    message=f'The approval process for your tender {tender.reference_number} has been cancelled.',
                    notification_type='info',
                    related_entity=tender
                )
                
            return Response({
                'status': 'success',
                'message': f'Cleared {approval_count} approvals for tender {tender.reference_number}'
            })
            
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def pending_approvals(self, request):
        """Get pending approvals for the current user"""
        user = request.user
        
        # Get pending approvals for this user
        approvals = Approval.objects.filter(
            user=user,
            status='pending'
        ).select_related('tender')
        
        # Calculate deadlines
        now = timezone.now()
        results = []
        
        for approval in approvals:
            # Calculate days since assignment
            days_pending = (now - approval.created_at).days
            
            # Check if overdue (more than 5 days)
            is_overdue = days_pending > 5
            
            results.append({
                'id': approval.id,
                'tender_id': approval.tender.id,
                'tender_reference': approval.tender.reference_number,
                'tender_title': approval.tender.title,
                'created_at': approval.created_at,
                'days_pending': days_pending,
                'is_overdue': is_overdue
            })
            
        # Sort by days pending (descending)
        results.sort(key=lambda x: x['days_pending'], reverse=True)
        
        return Response({
            'total_pending': len(results),
            'approvals': results
        })
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get approval statistics"""
        # Overall statistics
        total_approvals = Approval.objects.count()
        pending_count = Approval.objects.filter(status='pending').count()
        approved_count = Approval.objects.filter(status='approved').count()
        rejected_count = Approval.objects.filter(status='rejected').count()
        
        # Calculate average time to approve
        avg_time = None
        approved_approvals = Approval.objects.filter(status='approved')
        
        if approved_approvals.exists():
            total_hours = 0
            count = 0
            
            for approval in approved_approvals:
                if approval.updated_at and approval.created_at:
                    delta = approval.updated_at - approval.created_at
                    total_hours += delta.total_seconds() / 3600
                    count += 1
                    
            if count > 0:
                avg_time = total_hours / count
                
        # Get top approvers
        top_approvers = User.objects.annotate(
            approval_count=Count('approvals', filter=Q(approvals__status='approved'))
        ).order_by('-approval_count')[:5].values(
            'id', 'username', 'approval_count'
        )
        
        # Get tenders awaiting approval
        tenders_awaiting = Tender.objects.filter(
            approvals__status='pending'
        ).distinct().count()
        
        # Get recent approval activities
        recent_activity = Approval.objects.order_by('-updated_at')[:10].values(
            'id', 'tender__reference_number', 'user__username', 'status', 'updated_at'
        )
        
        return Response({
            'total_approvals': total_approvals,
            'pending_count': pending_count,
            'approved_count': approved_count,
            'rejected_count': rejected_count,
            'approval_rate': (approved_count / total_approvals * 100) if total_approvals > 0 else 0,
            'avg_time_to_approve_hours': avg_time,
            'tenders_awaiting_approval': tenders_awaiting,
            'top_approvers': list(top_approvers),
            'recent_activity': list(recent_activity)
        })
    
    @action(detail=False, methods=['get'])
    def overdue(self, request):
        """Get overdue approvals"""
        # Define overdue threshold (5 days)
        threshold = timezone.now() - timedelta(days=5)
        
        # Find overdue approvals
        overdue_approvals = Approval.objects.filter(
            status='pending',
            created_at__lt=threshold
        ).select_related('tender', 'user')
        
        results = []
        for approval in overdue_approvals:
            days_overdue = (timezone.now() - approval.created_at).days - 5
            
            results.append({
                'id': approval.id,
                'tender_id': approval.tender.id,
                'tender_reference': approval.tender.reference_number,
                'tender_title': approval.tender.title,
                'assignee': approval.user.username,
                'assignee_id': approval.user.id,
                'created_at': approval.created_at,
                'days_overdue': days_overdue
            })
            
        # Sort by days overdue (descending)
        results.sort(key=lambda x: x['days_overdue'], reverse=True)
        
        return Response({
            'total_overdue': len(results),
            'approvals': results
        })
    
    @action(detail=False, methods=['post'])
    def send_reminders(self, request):
        """Send reminders for pending approvals"""
        # Only admins can send reminders
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can send reminders'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Find pending approvals
        pending_approvals = Approval.objects.filter(
            status='pending'
        ).select_related('tender', 'user')
        
        if not pending_approvals.exists():
            return Response(
                {'message': 'No pending approvals found'},
                status=status.HTTP_200_OK
            )
            
        # Send reminders
        reminders_sent = 0
        for approval in pending_approvals:
            days_pending = (timezone.now() - approval.created_at).days
            
            # Create notification with appropriate urgency
            notification_type = 'info'
            if days_pending > 5:
                notification_type = 'warning'
            if days_pending > 10:
                notification_type = 'error'
                
            create_notification(
                user=approval.user,
                title='Approval Reminder',
                message=f'You have a pending approval for tender {approval.tender.reference_number} that has been waiting for {days_pending} days.',
                notification_type=notification_type,
                related_entity=approval
            )
            
            reminders_sent += 1
            
        # Log the reminder sending
        AuditLog.objects.create(
            user=request.user,
            action='send_approval_reminders',
            entity_type='system',
            entity_id=0,
            details={
                'reminders_sent': reminders_sent
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({
            'status': 'success',
            'reminders_sent': reminders_sent
        })