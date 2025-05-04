# server/aadf/views/report_views.py

import re
from django.http import FileResponse, Http404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.db.models import Q

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

import os
import uuid
import logging
import json
import io
import csv
from datetime import datetime, timedelta, timezone

from ..models import (
    Report, Tender, Offer, Evaluation, User, AuditLog, VendorCompany
)
from ..serializers import ReportSerializer
from ..permissions import IsStaffOrAdmin
from ..utils import (
    generate_tender_report, export_tender_data, generate_offer_audit_trail,
    get_dashboard_statistics
)
from ..ai_analysis import AIAnalyzer  # Import AIAnalyzer

logger = logging.getLogger('aadf')


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for generating and managing reports with AI-enhanced analytics"""
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
    def generate_ai_enhanced_report(self, request):
        """Generate an AI-enhanced report for a tender"""
        tender_id = request.data.get('tender_id')
        report_type = request.data.get('report_type', 'comprehensive')
        
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
            
        # Initialize AI analyzer
        ai_analyzer = AIAnalyzer()
        
        # Generate analytics report
        report_result = ai_analyzer.generate_analytics_report(tender_id, report_type)
        
        if report_result.get('status') == 'error':
            return Response(
                {'error': report_result.get('message', 'Report generation failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Save the report data as JSON
        report_data = report_result.get('report_data', {})
        filename = f"ai_report_{tender.reference_number}_{report_type}_{uuid.uuid4().hex[:8]}.json"
        file_path = f"reports/{filename}"
        
        # Save to storage
        default_storage.save(
            file_path,
            ContentFile(json.dumps(report_data, indent=2, default=str))
        )
        
        # Create report record
        report = Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type=f"ai_{report_type}",
            filename=filename,
            file_path=file_path
        )
        
        # Log the AI report generation
        AuditLog.objects.create(
            user=request.user,
            action='generate_ai_report',
            entity_type='tender',
            entity_id=tender.id,
            details={
                'report_id': report.id,
                'report_type': report_type,
                'tender_reference': tender.reference_number
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return the report info with the analysis data
        serializer = self.get_serializer(report)
        data = serializer.data
        data['ai_analysis'] = report_data
        
        return Response(data)

    @action(detail=False, methods=['post'])
    def analyze_bidding_package(self, request):
        """Analyze tender bidding package with AI"""
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
            
        # Initialize AI analyzer
        ai_analyzer = AIAnalyzer()
        
        # Analyze tender
        analysis_result = ai_analyzer.analyze_tender(tender_id)
        
        if analysis_result.get('status') == 'error':
            return Response(
                {'error': analysis_result.get('message', 'Analysis failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Extract bidding-specific information
        bidding_analysis = {
            'tender_info': analysis_result.get('tender_info', {}),
            'competition_level': self._get_competition_level(analysis_result),
            'price_analysis': analysis_result.get('price_analysis', {}),
            'document_analysis': analysis_result.get('document_analysis', {}),
            'bidding_recommendations': self._extract_bidding_recommendations(analysis_result)
        }
        
        # Add team evaluation if available
        team_evaluation = self._analyze_team_requirements(tender)
        if team_evaluation:
            bidding_analysis['team_evaluation'] = team_evaluation
            
        # Add bidding requirements analysis
        bidding_analysis['requirements_analysis'] = self._analyze_bidding_requirements(tender)
        
        # Save the analysis as a report
        filename = f"bidding_analysis_{tender.reference_number}_{uuid.uuid4().hex[:8]}.json"
        file_path = f"reports/{filename}"
        
        # Save to storage
        default_storage.save(
            file_path,
            ContentFile(json.dumps(bidding_analysis, indent=2, default=str))
        )
        
        # Create report record
        report = Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type='bidding_analysis',
            filename=filename,
            file_path=file_path
        )
        
        # Log the analysis
        AuditLog.objects.create(
            user=request.user,
            action='analyze_bidding_package',
            entity_type='tender',
            entity_id=tender.id,
            details={
                'report_id': report.id,
                'tender_reference': tender.reference_number
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return the analysis
        return Response({
            'report_id': report.id,
            'tender_reference': tender.reference_number,
            'bidding_analysis': bidding_analysis
        })
        
    def _get_competition_level(self, analysis_result):
        """Extract competition level from analysis"""
        basic_stats = analysis_result.get('basic_stats', {})
        submitted_offers = basic_stats.get('submitted_offers', 0)
        
        if submitted_offers >= 5:
            return {'level': 'High', 'description': 'Strong competition with multiple qualified bidders'}
        elif submitted_offers >= 3:
            return {'level': 'Medium', 'description': 'Adequate competition with several qualified bidders'}
        else:
            return {'level': 'Low', 'description': 'Limited competition which may affect value for money'}
    
    def _extract_bidding_recommendations(self, analysis_result):
        """Extract bidding-relevant recommendations"""
        all_recommendations = analysis_result.get('recommendations', [])
        bidding_recommendations = [r for r in all_recommendations if r.get('type') in ['warning', 'info']]
        return bidding_recommendations
        
    def _analyze_team_requirements(self, tender):
        """Analyze team requirements for the tender"""
        # Extract team requirements from tender description or documents
        requirements = tender.requirements.filter(
            Q(description__icontains='team') | 
            Q(description__icontains='expert') | 
            Q(description__icontains='personnel')
        )
        
        if not requirements.exists():
            return None
            
        team_analysis = {
            'required_roles': [],
            'qualifications_needed': [],
            'licensing_requirements': []
        }
        
        # Extract team requirements using regex patterns
        for req in requirements:
            description = req.description
            
            # Look for roles
            role_pattern = r'(architect|engineer|planner|expert|specialist|manager|consultant|lead)'
            roles = re.findall(role_pattern, description, re.IGNORECASE)
            if roles:
                for role in roles:
                    team_analysis['required_roles'].append({
                        'role': role.capitalize(),
                        'requirement_id': req.id,
                        'is_mandatory': req.is_mandatory
                    })
            
            # Look for qualifications
            qual_pattern = r'(degree|qualification|experience|years|certified)'
            quals = re.findall(qual_pattern, description, re.IGNORECASE)
            if quals:
                team_analysis['qualifications_needed'].append({
                    'qualification_type': 'Education/Experience',
                    'description': description,
                    'requirement_id': req.id,
                    'is_mandatory': req.is_mandatory
                })
            
            # Look for licenses
            license_pattern = r'(license|certification|accreditation)'
            licenses = re.findall(license_pattern, description, re.IGNORECASE)
            if licenses:
                team_analysis['licensing_requirements'].append({
                    'license_type': 'Professional License',
                    'description': description,
                    'requirement_id': req.id,
                    'is_mandatory': req.is_mandatory
                })
        
        return team_analysis
    
    def _analyze_bidding_requirements(self, tender):
        """Analyze bidding requirements for the tender"""
        requirements = tender.requirements.all()
        documents = tender.documents.all()
        
        # Categorize requirements
        categorized_requirements = {
            'technical': [],
            'financial': [],
            'administrative': [],
            'legal': [],
            'other': []
        }
        
        for req in requirements:
            description = req.description.lower()
            
            if any(word in description for word in ['technical', 'specification', 'functional']):
                category = 'technical'
            elif any(word in description for word in ['financial', 'price', 'cost', 'budget']):
                category = 'financial'
            elif any(word in description for word in ['administrative', 'form', 'certificate']):
                category = 'administrative'
            elif any(word in description for word in ['legal', 'law', 'regulation']):
                category = 'legal'
            else:
                category = 'other'
                
            categorized_requirements[category].append({
                'id': req.id,
                'description': req.description,
                'document_type': req.document_type,
                'is_mandatory': req.is_mandatory
            })
            
        # Check for form requirements in documents
        forms_found = []
        for doc in documents:
            filename = doc.original_filename.lower()
            if 'form' in filename:
                forms_found.append({
                    'document_id': doc.id,
                    'filename': doc.original_filename
                })
                
        # Prepare the analysis
        return {
            'categorized_requirements': categorized_requirements,
            'total_requirements': requirements.count(),
            'mandatory_requirements': requirements.filter(is_mandatory=True).count(),
            'forms_required': forms_found,
            'has_financial_requirements': len(categorized_requirements['financial']) > 0,
            'has_technical_requirements': len(categorized_requirements['technical']) > 0
        }

    @action(detail=False, methods=['post'])
    def export_tender_data(self, request):
        """Export tender data to CSV with AI-enhanced insights"""
        tender_id = request.data.get('tender_id')
        include_ai_insights = request.data.get('include_ai_insights', False)
        
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
            
        # Get AI insights if requested
        ai_insights = None
        if include_ai_insights:
            ai_analyzer = AIAnalyzer()
            analysis_result = ai_analyzer.analyze_tender(tender_id)
            
            if analysis_result.get('status') == 'success':
                ai_insights = {
                    'price_insights': analysis_result.get('price_analysis', {}),
                    'evaluation_insights': analysis_result.get('evaluation_consistency', {}),
                    'recommendations': analysis_result.get('recommendations', [])
                }
                
                # Append AI insights to CSV
                if ai_insights:
                    insights_buffer = io.StringIO()
                    writer = csv.writer(insights_buffer)
                    
                    writer.writerow([])
                    writer.writerow(['AI INSIGHTS'])
                    writer.writerow(['Price Analysis'])
                    
                    price_analysis = ai_insights.get('price_insights', {})
                    if price_analysis.get('analysis_performed', False):
                        writer.writerow(['Average Price', price_analysis.get('avg_price', 'N/A')])
                        writer.writerow(['Price Range', price_analysis.get('price_range', 'N/A')])
                        writer.writerow(['Price Variance', price_analysis.get('price_variance', 'N/A')])
                    
                    writer.writerow([])
                    writer.writerow(['Recommendations'])
                    
                    for rec in ai_insights.get('recommendations', []):
                        writer.writerow([rec.get('issue', ''), rec.get('description', '')])
                    
                    # Combine the buffers
                    combined_buffer = io.StringIO()
                    csv_buffer.seek(0)
                    combined_buffer.write(csv_buffer.getvalue())
                    insights_buffer.seek(0)
                    combined_buffer.write(insights_buffer.getvalue())
                    csv_buffer = combined_buffer
            
        # Save the file
        filename = f"tender_data_{tender.reference_number}_{uuid.uuid4().hex[:8]}.csv"
        file_path = f"reports/{filename}"
        
        # Save to storage
        csv_buffer.seek(0)
        default_storage.save(
            file_path,
            ContentFile(csv_buffer.getvalue())
        )
        
        # Create report record
        report = Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type='tender_data' + ('_with_ai' if include_ai_insights else ''),
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
                'tender_reference': tender.reference_number,
                'include_ai_insights': include_ai_insights
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