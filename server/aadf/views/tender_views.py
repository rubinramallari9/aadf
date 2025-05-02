# server/aadf/views/tender_views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg

import logging
import uuid

from ..models import (
    User, Tender, TenderRequirement, Offer, EvaluationCriteria, Report
)
from ..serializers import (
    TenderSerializer, TenderDetailSerializer, TenderRequirementSerializer, 
    EvaluationCriteriaSerializer
)
from ..permissions import IsStaffOrAdmin
from ..utils import (
    generate_reference_number, create_notification, generate_tender_report, 
    export_tender_data
)

logger = logging.getLogger('aadf')


class TenderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing tenders"""
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'reference_number', 'category']
    ordering_fields = ['created_at', 'submission_deadline', 'title']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TenderDetailSerializer
        return TenderSerializer

    def get_queryset(self):
        """Filter tenders based on user role"""
        user = self.request.user
        queryset = Tender.objects.all()
        
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        # Filter by category if provided
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
            
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
            
        # Apply user role restrictions
        if user.role == 'vendor':
            queryset = queryset.filter(status='published')
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign created_by and generate reference number"""
        ref_number = generate_reference_number()
        serializer.save(
            created_by=self.request.user,
            reference_number=ref_number
        )

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def publish(self, request, pk=None):
        """Publish a tender"""
        tender = self.get_object()
        if tender.status == 'draft':
            # Check if tender has all required information
            if not tender.submission_deadline:
                return Response(
                    {'error': 'Submission deadline is required before publishing'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            tender.status = 'published'
            tender.published_at = timezone.now()
            tender.save()
            
            # Notify vendor users
            vendor_users = User.objects.filter(role='vendor', is_active=True)
            for user in vendor_users:
                create_notification(
                    user=user,
                    title='New Tender Published',
                    message=f'A new tender "{tender.title}" has been published.',
                    notification_type='info',
                    related_entity=tender
                )
                
            return Response({'status': 'tender published'})
        return Response({'error': 'tender cannot be published'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def close(self, request, pk=None):
        """Close a tender"""
        tender = self.get_object()
        if tender.status == 'published':
            tender.status = 'closed'
            tender.save()
            
            # Notify evaluators
            evaluator_users = User.objects.filter(role='evaluator', is_active=True)
            for user in evaluator_users:
                create_notification(
                    user=user,
                    title='Tender Closed for Evaluation',
                    message=f'Tender "{tender.title}" has been closed and is ready for evaluation.',
                    notification_type='info',
                    related_entity=tender
                )
                
            return Response({'status': 'tender closed'})
        return Response({'error': 'tender cannot be closed'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def award(self, request, pk=None):
        """Award a tender"""
        tender = self.get_object()
        offer_id = request.data.get('offer_id')
        
        if not offer_id:
            return Response(
                {'error': 'offer_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            offer = Offer.objects.get(id=offer_id, tender=tender)
        except Offer.DoesNotExist:
            return Response(
                {'error': 'Offer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        if tender.status == 'closed':
            tender.status = 'awarded'
            tender.save()
            
            # Update the awarded offer
            offer.status = 'awarded'
            offer.save()
            
            # Update all other offers to rejected
            Offer.objects.filter(tender=tender).exclude(id=offer_id).update(status='rejected')
            
            # Notify the awarded vendor
            for user in offer.vendor.users.all():
                create_notification(
                    user=user,
                    title='Tender Awarded to Your Company',
                    message=f'Your offer for "{tender.title}" has been accepted.',
                    notification_type='success',
                    related_entity=offer
                )
                
            # Notify other vendors
            for rejected_offer in Offer.objects.filter(tender=tender).exclude(id=offer_id):
                for user in rejected_offer.vendor.users.all():
                    create_notification(
                        user=user,
                        title='Tender Award Result',
                        message=f'Your offer for "{tender.title}" was not selected.',
                        notification_type='info',
                        related_entity=rejected_offer
                    )
                    
            return Response({'status': 'tender awarded'})
        return Response({'error': 'tender cannot be awarded'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a tender"""
        tender = self.get_object()
        
        # Count offers by status
        offer_stats = Offer.objects.filter(tender=tender).values('status').annotate(count=Count('status'))
        offer_stats_dict = {item['status']: item['count'] for item in offer_stats}
        
        # Calculate average scores
        avg_scores = Offer.objects.filter(
            tender=tender,
            technical_score__isnull=False,
            financial_score__isnull=False
        ).aggregate(
            avg_technical=Avg('technical_score'),
            avg_financial=Avg('financial_score'),
            avg_total=Avg('total_score')
        )
        
        stats = {
            'total_offers': Offer.objects.filter(tender=tender).count(),
            'offer_statuses': offer_stats_dict,
            'average_scores': avg_scores,
            'total_documents': tender.documents.count(),
            'total_requirements': tender.requirements.count(),
            'total_criteria': tender.evaluation_criteria.count(),
        }
        
        return Response(stats)

    @action(detail=True, methods=['get'], permission_classes=[IsStaffOrAdmin])
    def export_report(self, request, pk=None):
        """Export tender report as PDF"""
        tender = self.get_object()
        report_buffer = generate_tender_report(tender)
        
        if not report_buffer:
            return Response(
                {'error': 'Failed to generate report'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Create a report record
        filename = f"tender_report_{tender.reference_number}.pdf"
        file_path = f"reports/{filename}"
        
        Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type='tender_commission',
            filename=filename,
            file_path=file_path
        )
        
        # Return the PDF
        report_buffer.seek(0)
        response = FileResponse(
            report_buffer,
            content_type='application/pdf',
            as_attachment=True,
            filename=filename
        )
        
        return response

    @action(detail=True, methods=['get'], permission_classes=[IsStaffOrAdmin])
    def export_csv(self, request, pk=None):
        """Export tender data as CSV"""
        tender = self.get_object()
        csv_buffer = export_tender_data(tender)
        
        if not csv_buffer:
            return Response(
                {'error': 'Failed to generate CSV'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Create a report record
        filename = f"tender_data_{tender.reference_number}.csv"
        file_path = f"reports/{filename}"
        
        Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type='tender_data',
            filename=filename,
            file_path=file_path
        )
        
        # Return the CSV
        csv_buffer.seek(0)
        response = FileResponse(
            csv_buffer,
            content_type='text/csv',
            as_attachment=True,
            filename=filename
        )
        
        return response

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def add_requirement(self, request, pk=None):
        """Add a requirement to a tender"""
        tender = self.get_object()
        
        serializer = TenderRequirementSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(tender=tender)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def add_evaluation_criteria(self, request, pk=None):
        """Add evaluation criteria to a tender"""
        tender = self.get_object()
        
        serializer = EvaluationCriteriaSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(tender=tender)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)