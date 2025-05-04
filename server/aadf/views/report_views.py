# server/aadf/views/report_views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.http import FileResponse
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

import logging
import os
import io
import uuid
import csv
import json

from ..models import (
    Report, Tender, Offer, Evaluation, User, AuditLog
)
from ..serializers import ReportSerializer
from ..permissions import IsStaffOrAdmin
from ..utils import (
    generate_tender_report, export_tender_data, generate_offer_audit_trail,
    get_dashboard_statistics
)

logger = logging.getLogger('aadf')


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for generating and managing reports"""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter reports based on query parameters"""
        queryset = Report.objects.all()
        
        # Filter by tender_id if provided
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
            
        # Filter by report_type if provided
        report_type = self.request.query_params.get('report_type')
        if report_type:
            queryset = queryset.filter(report_type=report_type)
            
        # Filter by generated_by if provided
        generated_by = self.request.query_params.get('generated_by')
        if generated_by:
            queryset = queryset.filter(generated_by__username=generated_by)
            
        return queryset

    def perform_create(self, serializer):
        """Set the generator to the current user"""
        serializer.save(generated_by=self.request.user)

    @action(detail=False, methods=['post'])
    def generate_tender_report(self, request):
        """Generate a PDF report for a tender"""
        tender_id = request.data.get('tender_id')
        report_type = request.data.get('report_type', 'tender_commission')
        
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Generate the report
        report_buffer = generate_tender_report(tender)
        
        if not report_buffer:
            return Response(
                {'error': 'Failed to generate report'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Save the report file
        filename = f"tender_report_{tender.reference_number}_{uuid.uuid4().hex[:8]}.pdf"
        file_path = f"reports/{filename}"
        
        # Save to storage
        default_storage.save(
            file_path,
            ContentFile(report_buffer.getvalue())
        )
        
        # Create report record
        report = Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type=report_type,
            filename=filename,
            file_path=file_path
        )
        
        # Log the report generation
        AuditLog.objects.create(
            user=request.user,
            action='generate_tender_report',
            entity_type='tender',
            entity_id=tender.id,
            details={
                'report_id': report.id,
                'report_type': report_type,
                'tender_reference': tender.reference_number
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return the report info
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def export_tender_data(self, request):
        """Export tender data to CSV"""
        tender_id = request.data.get('tender_id')
        
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Generate CSV data
        csv_buffer = export_tender_data(tender)
        
        if not csv_buffer:
            return Response(
                {'error': 'Failed to generate CSV data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Save the CSV file
        filename = f"tender_data_{tender.reference_number}_{uuid.uuid4().hex[:8]}.csv"
        file_path = f"reports/{filename}"
        
        # Save to storage
        default_storage.save(
            file_path,
            ContentFile(csv_buffer.getvalue())
        )
        
        # Create report record
        report = Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type='tender_data',
            filename=filename,
            file_path=file_path
        )
        
        # Log the export
        AuditLog.objects.create(
            user=request.user,
            action='export_tender_data',
            entity_type='tender',
            entity_id=tender.id,
            details={
                'report_id': report.id,
                'tender_reference': tender.reference_number
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return the report info
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def export_evaluation_matrix(self, request):
        """Export evaluation matrix for a tender"""
        tender_id = request.data.get('tender_id')
        
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get offers and evaluations
        offers = Offer.objects.filter(
            tender=tender,
            status__in=['submitted', 'evaluated', 'awarded', 'rejected']
        )
        
        # Get criteria
        criteria = tender.evaluation_criteria.all().order_by('category', 'name')
        
        # Prepare CSV data
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        
        # Write header row
        header = ['Vendor Name', 'Offer Status', 'Price']
        for criterion in criteria:
            header.append(f"{criterion.name} (max: {criterion.max_score})")
        header.extend(['Technical Score', 'Financial Score', 'Total Score'])
        
        writer.writerow(header)
        
        # Write data for each offer
        for offer in offers:
            row = [offer.vendor.name, offer.status, offer.price or 'N/A']
            
            # Get evaluations for this offer
            evaluations = Evaluation.objects.filter(offer=offer)
            evaluation_dict = {}
            for eval_item in evaluations:
                criterion_id = eval_item.criteria.id
                if criterion_id not in evaluation_dict:
                    evaluation_dict[criterion_id] = []
                evaluation_dict[criterion_id].append(float(eval_item.score))
            
            # Add scores for each criterion
            for criterion in criteria:
                scores = evaluation_dict.get(criterion.id, [])
                if scores:
                    avg_score = sum(scores) / len(scores)
                    row.append(f"{avg_score:.2f}")
                else:
                    row.append('N/A')
            
            # Add final scores
            row.extend([
                f"{offer.technical_score:.2f}" if offer.technical_score is not None else 'N/A',
                f"{offer.financial_score:.2f}" if offer.financial_score is not None else 'N/A',
                f"{offer.total_score:.2f}" if offer.total_score is not None else 'N/A'
            ])
            
            writer.writerow(row)
            
        # Save the CSV file
        filename = f"evaluation_matrix_{tender.reference_number}_{uuid.uuid4().hex[:8]}.csv"
        file_path = f"reports/{filename}"
        
        # Save to storage
        buffer.seek(0)
        default_storage.save(
            file_path,
            ContentFile(buffer.getvalue())
        )
        
        # Create report record
        report = Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type='evaluation_matrix',
            filename=filename,
            file_path=file_path
        )
        
        # Log the export
        AuditLog.objects.create(
            user=request.user,
            action='export_evaluation_matrix',
            entity_type='tender',
            entity_id=tender.id,
            details={
                'report_id': report.id,
                'tender_reference': tender.reference_number
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return the report info
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def generate_offer_audit(self, request):
        """Generate audit trail for an offer"""
        offer_id = request.data.get('offer_id')
        
        if not offer_id:
            return Response(
                {'error': 'offer_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            offer = Offer.objects.get(id=offer_id)
        except Offer.DoesNotExist:
            return Response(
                {'error': 'Offer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Generate audit trail
        audit_trail = generate_offer_audit_trail(offer)
        
        # Create JSON file
        buffer = io.StringIO()
        json.dump(audit_trail, buffer, indent=2, default=str)
        
        # Save the file
        filename = f"offer_audit_{offer.tender.reference_number}_{offer.vendor.name}_{uuid.uuid4().hex[:8]}.json"
        file_path = f"reports/{filename}"
        
        # Save to storage
        buffer.seek(0)
        default_storage.save(
            file_path,
            ContentFile(buffer.getvalue())
        )
        
        # Create report record
        report = Report.objects.create(
            tender=offer.tender,
            generated_by=request.user,
            report_type='offer_audit',
            filename=filename,
            file_path=file_path
        )
        
        # Log the export
        AuditLog.objects.create(
            user=request.user,
            action='generate_offer_audit',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'report_id': report.id,
                'tender_reference': offer.tender.reference_number,
                'vendor_name': offer.vendor.name
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return the report info
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def generate_dashboard_report(self, request):
        """Generate a dashboard statistics report"""
        # Get dashboard statistics
        stats = get_dashboard_statistics()
        
        # Create JSON file
        buffer = io.StringIO()
        json.dump(stats, buffer, indent=2, default=str)
        
        # Save the file
        timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
        filename = f"dashboard_report_{timestamp}.json"
        file_path = f"reports/{filename}"
        
        # Save to storage
        buffer.seek(0)
        default_storage.save(
            file_path,
            ContentFile(buffer.getvalue())
        )
        
        # Create report record (without associating with a specific tender)
        report = Report.objects.create(
            generated_by=request.user,
            report_type='dashboard',
            filename=filename,
            file_path=file_path
        )
        
        # Log the export
        AuditLog.objects.create(
            user=request.user,
            action='generate_dashboard_report',
            entity_type='system',
            entity_id=0,
            details={
                'report_id': report.id
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return the report info
        serializer = self.get_serializer(report)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a report file"""
        report = self.get_object()
        
        # Check if file exists
        if not default_storage.exists(report.file_path):
            return Response(
                {'error': 'Report file not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Open the file
        file = default_storage.open(report.file_path, 'rb')
        
        # Determine content type based on filename
        filename = report.filename.lower()
        if filename.endswith('.pdf'):
            content_type = 'application/pdf'
        elif filename.endswith('.csv'):
            content_type = 'text/csv'
        elif filename.endswith('.json'):
            content_type = 'application/json'
        else:
            content_type = 'application/octet-stream'
            
        # Create response
        response = FileResponse(file, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{report.filename}"'
        
        # Log the download
        AuditLog.objects.create(
            user=request.user,
            action='download_report',
            entity_type='report',
            entity_id=report.id,
            details={
                'report_type': report.report_type,
                'filename': report.filename
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return response