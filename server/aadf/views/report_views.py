# server/aadf/views/report_views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.db.models import Q, Sum, Avg, Count, Max, Min, F
from django.utils import timezone
from django.conf import settings
from reportlab.graphics.shapes import Circle, Drawing
from reportlab.lib import colors
from ..models import TenderDocument, OfferDocument

import logging
import os
import uuid
import io
import json
import csv
import datetime
from dateutil.relativedelta import relativedelta

from ..models import (
    Report, Tender, Offer, User, EvaluationCriteria, Evaluation, AuditLog,
    VendorCompany
)
from ..serializers import ReportSerializer
from ..permissions import IsStaffOrAdmin
from ..utils import (
    generate_tender_report, export_tender_data, generate_offer_audit_trail
)

logger = logging.getLogger('aadf')


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing reports with enhanced features"""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'report_type']
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
            
        # Filter by date range if provided
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
            
        # Filter by creator
        generated_by = self.request.query_params.get('generated_by')
        if generated_by:
            queryset = queryset.filter(generated_by__username=generated_by)
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign generated_by to the authenticated user"""
        serializer.save(generated_by=self.request.user)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """Download a report"""
        report = self.get_object()
        
        try:
            # Check if file exists
            if not default_storage.exists(report.file_path):
                return Response(
                    {'error': 'Report file not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Open the file
            file = default_storage.open(report.file_path, 'rb')
            
            # Determine content type
            content_type = 'application/pdf'
            if report.filename.endswith('.csv'):
                content_type = 'text/csv'
            elif report.filename.endswith('.xlsx'):
                content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            elif report.filename.endswith('.json'):
                content_type = 'application/json'
                
            # Return the file
            response = FileResponse(
                file,
                content_type=content_type,
                as_attachment=True,
                filename=report.filename
            )
            
            # server/aadf/views/report_views.py (continued)

            # Log the download
            AuditLog.objects.create(
                user=request.user,
                action='download_report',
                entity_type='report',
                entity_id=report.id,
                details={'filename': report.filename},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return response
        except Exception as e:
            logger.error(f"Error downloading report: {str(e)}")
            return Response(
                {'error': f'Download failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'])
    def generate_tender_report(self, request):
        """Generate a comprehensive report for a tender"""
        tender_id = request.data.get('tender_id')
        report_type = request.data.get('report_type', 'tender_commission')
        include_evaluations = request.data.get('include_evaluations', True)
        include_offers = request.data.get('include_offers', True)
        include_audit_trail = request.data.get('include_audit_trail', False)
        
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Generate the report with enhanced features
            report_buffer = self._generate_enhanced_tender_report(
                tender, 
                include_evaluations=include_evaluations,
                include_offers=include_offers,
                include_audit_trail=include_audit_trail
            )
            
            if not report_buffer:
                return Response(
                    {'error': 'Failed to generate report'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
            # Create a report record
            filename = f"tender_report_{tender.reference_number}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
            file_path = f"reports/{filename}"
            
            # Save the report to storage
            default_storage.save(file_path, ContentFile(report_buffer.getvalue()))
                
            # Create the report record
            report = Report.objects.create(
                tender=tender,
                generated_by=request.user,
                report_type=report_type,
                filename=filename,
                file_path=file_path
            )
            
            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating tender report: {str(e)}")
            return Response(
                {'error': f'Report generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_enhanced_tender_report(self, tender, **options):
        """
        Generate an enhanced tender report with detailed sections
        Returns a PDF buffer
        """
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
                PageBreak, ListFlowable, ListItem, Flowable
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics.charts.barcharts import VerticalBarChart
            from reportlab.graphics.charts.piecharts import Pie
            import io
            
            # Create a buffer to receive the PDF data
            buffer = io.BytesIO()
            
            # Create the PDF object
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72, leftMargin=72,
                topMargin=72, bottomMargin=72
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='Heading1',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=12
            ))
            styles.add(ParagraphStyle(
                name='Heading2',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=8
            ))
            styles.add(ParagraphStyle(
                name='Heading3',
                parent=styles['Heading3'],
                fontSize=12,
                spaceAfter=6
            ))
            styles.add(ParagraphStyle(
                name='Normal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            ))
            styles.add(ParagraphStyle(
                name='NormalIndent',
                parent=styles['Normal'],
                leftIndent=20,
                fontSize=10,
                spaceAfter=6
            ))
            
            # Build the document
            elements = []
            
            # Cover page
            elements.append(Paragraph(f"Tender Report", styles['Heading1']))
            elements.append(Paragraph(f"Reference: {tender.reference_number}", styles['Heading2']))
            elements.append(Paragraph(f"Title: {tender.title}", styles['Normal']))
            elements.append(Paragraph(f"Status: {tender.status}", styles['Normal']))
            elements.append(Paragraph(f"Report generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            elements.append(Paragraph(f"Generated by: {self.request.user.username}", styles['Normal']))
            elements.append(PageBreak())
            
            # Table of contents placeholder
            elements.append(Paragraph("Table of Contents", styles['Heading1']))
            elements.append(Paragraph("1. Tender Information", styles['Normal']))
            elements.append(Paragraph("2. Offers Summary", styles['Normal']))
            if options.get('include_evaluations', True):
                elements.append(Paragraph("3. Evaluation Results", styles['Normal']))
            if options.get('include_offers', True):
                elements.append(Paragraph("4. Detailed Offers", styles['Normal']))
            if options.get('include_audit_trail', False):
                elements.append(Paragraph("5. Audit Trail", styles['Normal']))
            elements.append(PageBreak())
            
            # 1. Tender Information section
            elements.append(Paragraph("1. Tender Information", styles['Heading1']))
            
            # Tender details
            tender_data = [
                ["Reference Number:", tender.reference_number],
                ["Title:", tender.title],
                ["Status:", tender.status],
                ["Category:", tender.category or "N/A"],
                ["Created By:", tender.created_by.username if tender.created_by else "N/A"],
                ["Created On:", tender.created_at.strftime('%Y-%m-%d')],
                ["Published On:", tender.published_at.strftime('%Y-%m-%d') if tender.published_at else "N/A"],
                ["Submission Deadline:", tender.submission_deadline.strftime('%Y-%m-%d %H:%M')],
                ["Estimated Value:", f"{tender.estimated_value}" if tender.estimated_value else "N/A"]
            ]
            
            tender_table = Table(tender_data, colWidths=[150, 300])
            tender_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(tender_table)
            elements.append(Spacer(1, 0.2*inch))
            
            # Tender description
            elements.append(Paragraph("Description:", styles['Heading3']))
            elements.append(Paragraph(tender.description, styles['Normal']))
            elements.append(Spacer(1, 0.2*inch))
            
            # Tender requirements
            requirements = tender.requirements.all()
            if requirements.exists():
                elements.append(Paragraph("Requirements:", styles['Heading3']))
                req_data = [["Requirement", "Type", "Mandatory"]]
                
                for req in requirements:
                    req_data.append([
                        req.description,
                        req.document_type or "N/A",
                        "Yes" if req.is_mandatory else "No"
                    ])
                
                req_table = Table(req_data, colWidths=[250, 100, 100])
                req_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(req_table)
            
            # Add a page break
            elements.append(PageBreak())
            
            # 2. Offers Summary section
            elements.append(Paragraph("2. Offers Summary", styles['Heading1']))
            
            # Count offers by status
            offers = tender.offers.all()
            if not offers.exists():
                elements.append(Paragraph("No offers received for this tender.", styles['Normal']))
            else:
                status_counts = offers.values('status').annotate(count=Count('status'))
                status_data = {item['status']: item['count'] for item in status_counts}
                
                # Create a summary paragraph
                summary_text = f"Total Offers: {offers.count()}<br/>"
                for status, count in status_data.items():
                    summary_text += f"{status.capitalize()}: {count}<br/>"
                
                elements.append(Paragraph(summary_text, styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
                
                # Add offers table
                elements.append(Paragraph("Offers Overview:", styles['Heading3']))
                
                offer_data = [["Vendor", "Status", "Price", "Technical Score", "Financial Score", "Total Score"]]
                for offer in offers:
                    offer_data.append([
                        offer.vendor.name,
                        offer.status.capitalize(),
                        f"{offer.price}" if offer.price else "N/A",
                        f"{offer.technical_score}" if offer.technical_score is not None else "N/A",
                        f"{offer.financial_score}" if offer.financial_score is not None else "N/A",
                        f"{offer.total_score}" if offer.total_score is not None else "N/A"
                    ])
                
                # Add awarded flag to winning offer if applicable
                if tender.status == 'awarded':
                    awarded_offer = offers.filter(status='awarded').first()
                    if awarded_offer:
                        for i, row in enumerate(offer_data):
                            if i > 0 and row[0] == awarded_offer.vendor.name:
                                offer_data[i][1] = "AWARDED"
                
                offer_table = Table(offer_data, colWidths=[150, 70, 70, 70, 70, 70])
                offer_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ]))
                
                # Highlight awarded row if exists
                if tender.status == 'awarded':
                    for i, row in enumerate(offer_data):
                        if i > 0 and row[1] == "AWARDED":
                            offer_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, i), (-1, i), colors.lightgreen),
                            ]))
                
                elements.append(offer_table)
                
                # Add visualization if possible
                # Create a chart for score comparison
                if any(offer.total_score is not None for offer in offers):
                    elements.append(Spacer(1, 0.3*inch))
                    elements.append(Paragraph("Offer Score Comparison:", styles['Heading3']))
                    
                    # Only include offers with scores
                    scored_offers = [offer for offer in offers if offer.total_score is not None]
                    if scored_offers:
                        # Sort by total score
                        scored_offers.sort(key=lambda x: x.total_score or 0, reverse=True)
                        
                        # Bar chart for scores
                        drawing = Drawing(400, 200)
                        bc = VerticalBarChart()
                        bc.x = 50
                        bc.y = 50
                        bc.height = 125
                        bc.width = 300
                        bc.data = [[offer.total_score for offer in scored_offers[:5]]]
                        bc.strokeColor = colors.black
                        bc.valueAxis.valueMin = 0
                        bc.valueAxis.valueMax = 100
                        bc.valueAxis.valueStep = 10
                        bc.categoryAxis.labels.boxAnchor = 'ne'
                        bc.categoryAxis.labels.dx = -8
                        bc.categoryAxis.labels.dy = -2
                        bc.categoryAxis.labels.angle = 30
                        bc.categoryAxis.categoryNames = [offer.vendor.name[:20] for offer in scored_offers[:5]]
                        drawing.add(bc)
                        
                        elements.append(drawing)
            
            # Add a page break
            elements.append(PageBreak())
            
            # 3. Evaluation Results section (if included)
            if options.get('include_evaluations', True):
                elements.append(Paragraph("3. Evaluation Results", styles['Heading1']))
                
                # Get evaluation criteria
                criteria = EvaluationCriteria.objects.filter(tender=tender)
                
                if not criteria.exists():
                    elements.append(Paragraph("No evaluation criteria defined for this tender.", styles['Normal']))
                else:
                    # Criteria table
                    elements.append(Paragraph("Evaluation Criteria:", styles['Heading3']))
                    
                    criteria_data = [["Name", "Category", "Weight", "Max Score"]]
                    for criterion in criteria:
                        criteria_data.append([
                            criterion.name,
                            criterion.category.capitalize(),
                            f"{criterion.weight}%",
                            str(criterion.max_score)
                        ])
                    
                    criteria_table = Table(criteria_data, colWidths=[200, 100, 70, 70])
                    criteria_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                    ]))
                    elements.append(criteria_table)
                    elements.append(Spacer(1, 0.2*inch))
                    
                    # Evaluation results
                    evaluations = Evaluation.objects.filter(offer__tender=tender)
                    if evaluations.exists():
                        elements.append(Paragraph("Evaluation Summary by Criteria:", styles['Heading3']))
                        
                        # Get average scores by criteria
                        avg_scores = evaluations.values(
                            'criteria__name',
                            'criteria__category'
                        ).annotate(
                            avg_score=Avg('score')
                        ).order_by('criteria__category', 'criteria__name')
                        
                        # Create table
                        avg_data = [["Criteria", "Category", "Average Score"]]
                        for item in avg_scores:
                            avg_data.append([
                                item['criteria__name'],
                                item['criteria__category'].capitalize(),
                                f"{item['avg_score']:.2f}"
                            ])
                        
                        avg_table = Table(avg_data, colWidths=[200, 100, 140])
                        avg_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                            ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                        ]))
                        elements.append(avg_table)
                        
                        # Detailed evaluations by offer
                        elements.append(Spacer(1, 0.3*inch))
                        elements.append(Paragraph("Detailed Evaluations by Offer:", styles['Heading3']))
                        
                        for offer in offers.filter(status__in=['submitted', 'evaluated', 'awarded']):
                            elements.append(Paragraph(f"Offer from {offer.vendor.name}:", styles['Heading3']))
                            
                            offer_evals = evaluations.filter(offer=offer)
                            if not offer_evals.exists():
                                elements.append(Paragraph("No evaluations recorded.", styles['NormalIndent']))
                                continue
                                
                            # Create table
                            eval_data = [["Criteria", "Score", "Evaluator", "Comment"]]
                            for eval in offer_evals:
                                comment = eval.comment if eval.comment else ""
                                if len(comment) > 50:
                                    comment = comment[:47] + "..."
                                    
                                eval_data.append([
                                    eval.criteria.name,
                                    f"{eval.score}",
                                    eval.evaluator.username,
                                    comment
                                ])
                            
                            eval_table = Table(eval_data, colWidths=[150, 60, 100, 130])
                            eval_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                            ]))
                            elements.append(eval_table)
                            elements.append(Spacer(1, 0.2*inch))
                    else:
                        elements.append(Paragraph("No evaluations have been recorded for this tender.", styles['Normal']))
                
                # Add a page break
                elements.append(PageBreak())
            
            # 4. Detailed Offers section (if included)
            if options.get('include_offers', True):
                elements.append(Paragraph("4. Detailed Offers", styles['Heading1']))
                
                if not offers.exists():
                    elements.append(Paragraph("No offers received for this tender.", styles['Normal']))
                else:
                    for i, offer in enumerate(offers):
                        elements.append(Paragraph(f"Offer {i+1}: {offer.vendor.name}", styles['Heading2']))
                        
                        # Offer details
                        offer_details = [
                            ["Status:", offer.status.capitalize()],
                            ["Submitted By:", offer.submitted_by.username if offer.submitted_by else "N/A"],
                            ["Submitted On:", offer.submitted_at.strftime('%Y-%m-%d %H:%M') if offer.submitted_at else "N/A"],
                            ["Price:", f"{offer.price}" if offer.price else "N/A"],
                            ["Technical Score:", f"{offer.technical_score}" if offer.technical_score is not None else "N/A"],
                            ["Financial Score:", f"{offer.financial_score}" if offer.financial_score is not None else "N/A"],
                            ["Total Score:", f"{offer.total_score}" if offer.total_score is not None else "N/A"]
                        ]
                        
                        offer_details_table = Table(offer_details, colWidths=[120, 300])
                        offer_details_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ]))
                        elements.append(offer_details_table)
                        elements.append(Spacer(1, 0.2*inch))
                        
                        # Offer documents
                        documents = offer.documents.all()
                        if documents.exists():
                            elements.append(Paragraph("Documents:", styles['Heading3']))
                            
                            doc_data = [["Filename", "Type", "Size (KB)"]]
                            for doc in documents:
                                doc_data.append([
                                    doc.original_filename,
                                    doc.document_type or "N/A",
                                    f"{(doc.file_size or 0) / 1024:.1f}"
                                ])
                            
                            doc_table = Table(doc_data, colWidths=[250, 120, 70])
                            doc_table.setStyle(TableStyle([
                                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                                ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                            ]))
                            elements.append(doc_table)
                        else:
                            elements.append(Paragraph("No documents attached to this offer.", styles['Normal']))
                        
                        # Notes
                        if offer.notes:
                            elements.append(Spacer(1, 0.2*inch))
                            elements.append(Paragraph("Notes:", styles['Heading3']))
                            elements.append(Paragraph(offer.notes, styles['Normal']))
                        
                        # Add page break between offers
                        if i < len(offers) - 1:
                            elements.append(PageBreak())
                
                # Add a page break
                elements.append(PageBreak())
            
            # 5. Audit Trail section (if included)
            if options.get('include_audit_trail', False):
                elements.append(Paragraph("5. Audit Trail", styles['Heading1']))
                
                # Get audit logs for this tender
                audit_logs = AuditLog.objects.filter(
                    entity_type='tender',
                    entity_id=tender.id
                ).order_by('created_at')
                
                if not audit_logs.exists():
                    elements.append(Paragraph("No audit records found for this tender.", styles['Normal']))
                else:
                    elements.append(Paragraph("Tender Audit Trail:", styles['Heading3']))
                    
                    # Create table
                    audit_data = [["Timestamp", "User", "Action", "Details"]]
                    for log in audit_logs:
                        details = log.details or {}
                        detail_str = ", ".join(f"{k}: {v}" for k, v in details.items())
                        if len(detail_str) > 50:
                            detail_str = detail_str[:47] + "..."
                            
                        audit_data.append([
                            log.created_at.strftime('%Y-%m-%d %H:%M'),
                            log.user.username if log.user else "System",
                            log.action,
                            detail_str
                        ])
                    
                    audit_table = Table(audit_data, colWidths=[100, 100, 100, 140])
                    audit_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ]))
                    elements.append(audit_table)
                    elements.append(Spacer(1, 0.2*inch))
                    
                    # Get audit logs for related offers
                    offer_audit_logs = AuditLog.objects.filter(
                        entity_type='offer',
                        entity_id__in=offers.values_list('id', flat=True)
                    ).order_by('created_at')
                    
                    if offer_audit_logs.exists():
                        elements.append(Paragraph("Offers Audit Trail:", styles['Heading3']))
                        
                        # Create table
                        offer_audit_data = [["Timestamp", "User", "Action", "Offer", "Details"]]
                        for log in offer_audit_logs:
                            try:
                                offer = Offer.objects.get(id=log.entity_id)
                                offer_name = offer.vendor.name
                            except:
                                offer_name = f"ID: {log.entity_id}"
                                
                            details = log.details or {}
                            detail_str = ", ".join(f"{k}: {v}" for k, v in details.items())
                            if len(detail_str) > 40:
                                detail_str = detail_str[:37] + "..."
                                
                            offer_audit_data.append([
                                log.created_at.strftime('%Y-%m-%d %H:%M'),
                                log.user.username if log.user else "System",
                                log.action,
                                offer_name,
                                detail_str
                            ])
                        
                        offer_audit_table = Table(offer_audit_data, colWidths=[90, 90, 80, 90, 90])
                        offer_audit_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                            ('GRID', (0, 0), (-1, -1), 1, colors.black),
                            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ]))
                        elements.append(offer_audit_table)
            
            # Build the document
            doc.build(elements)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Error in _generate_enhanced_tender_report: {str(e)}")
            return None

    # server/aadf/views/report_views.py (continued)

    @action(detail=False, methods=['post'])
    def generate_comparative_report(self, request):
        """Generate a comparative report for multiple tenders"""
        tender_ids = request.data.get('tender_ids', [])
        report_type = request.data.get('report_type', 'comparative_analysis')
        format_type = request.data.get('format', 'pdf')  # pdf or csv
        
        if not tender_ids or len(tender_ids) < 2:
            return Response(
                {'error': 'At least two tender_ids are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            # Get tenders
            tenders = Tender.objects.filter(id__in=tender_ids)
            
            if tenders.count() < 2:
                return Response(
                    {'error': 'At least two valid tenders are required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Generate the report based on format
            if format_type == 'pdf':
                report_buffer = self._generate_comparative_pdf_report(tenders)
                filename = f"comparative_report_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
                content_type = 'application/pdf'
            else:  # csv
                report_buffer = self._generate_comparative_csv_report(tenders)
                filename = f"comparative_report_{timezone.now().strftime('%Y%m%d%H%M%S')}.csv"
                content_type = 'text/csv'
                
            if not report_buffer:
                return Response(
                    {'error': 'Failed to generate report'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
            # Create a report record (just use the first tender as the parent)
            file_path = f"reports/{filename}"
            
            # Save the report to storage
            default_storage.save(file_path, ContentFile(report_buffer.getvalue()))
                
            # Create the report record
            report = Report.objects.create(
                tender=tenders.first(),
                generated_by=request.user,
                report_type=report_type,
                filename=filename,
                file_path=file_path
            )
            
            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error generating comparative report: {str(e)}")
            return Response(
                {'error': f'Report generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_comparative_pdf_report(self, tenders):
        """Generate a PDF report comparing multiple tenders"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
                PageBreak, ListFlowable, ListItem
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics.charts.barcharts import VerticalBarChart
            from reportlab.graphics.charts.linecharts import HorizontalLineChart
            import io
            
            # Create a buffer to receive the PDF data
            buffer = io.BytesIO()
            
            # Create the PDF object
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72, leftMargin=72,
                topMargin=72, bottomMargin=72
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='Heading1',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=12
            ))
            styles.add(ParagraphStyle(
                name='Heading2',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=8
            ))
            styles.add(ParagraphStyle(
                name='Heading3',
                parent=styles['Heading3'],
                fontSize=12,
                spaceAfter=6
            ))
            styles.add(ParagraphStyle(
                name='Normal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            ))
            
            # Build the document
            elements = []
            
            # Cover page
            elements.append(Paragraph(f"Comparative Tender Analysis", styles['Heading1']))
            elements.append(Paragraph(f"Report Date: {timezone.now().strftime('%Y-%m-%d')}", styles['Normal']))
            elements.append(Paragraph(f"Generated by: {self.request.user.username}", styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
            
            # Add tenders being compared
            elements.append(Paragraph(f"Tenders Included in This Analysis:", styles['Heading3']))
            for tender in tenders:
                elements.append(Paragraph(f"• {tender.reference_number}: {tender.title}", styles['Normal']))
            
            elements.append(PageBreak())
            
            # 1. Tender Overview Comparison
            elements.append(Paragraph("1. Tender Overview Comparison", styles['Heading1']))
            
            # Create comparison table
            tender_comparison = [
                ["Parameter"] + [f"Tender {i+1}: {t.reference_number}" for i, t in enumerate(tenders)]
            ]
            
            # Add rows for different parameters
            tender_comparison.append(
                ["Title"] + [t.title for t in tenders]
            )
            tender_comparison.append(
                ["Status"] + [t.status.capitalize() for t in tenders]
            )
            tender_comparison.append(
                ["Category"] + [(t.category or "N/A") for t in tenders]
            )
            tender_comparison.append(
                ["Created On"] + [t.created_at.strftime('%Y-%m-%d') for t in tenders]
            )
            tender_comparison.append(
                ["Published On"] + [(t.published_at.strftime('%Y-%m-%d') if t.published_at else "N/A") for t in tenders]
            )
            tender_comparison.append(
                ["Deadline"] + [t.submission_deadline.strftime('%Y-%m-%d') for t in tenders]
            )
            tender_comparison.append(
                ["Estimated Value"] + [(f"{t.estimated_value}" if t.estimated_value else "N/A") for t in tenders]
            )
            tender_comparison.append(
                ["# of Offers"] + [str(t.offers.count()) for t in tenders]
            )
            tender_comparison.append(
                ["# of Requirements"] + [str(t.requirements.count()) for t in tenders]
            )
            
            # Calculate column widths
            n_tenders = len(tenders)
            col_width = 400 / (n_tenders + 1)
            col_widths = [150] + [col_width] * n_tenders
            
            # Create the table
            table = Table(tender_comparison, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))
            
            # 2. Requirements Comparison
            elements.append(Paragraph("2. Requirements Comparison", styles['Heading2']))
            
            # Collect all unique requirement types
            all_requirement_types = set()
            for tender in tenders:
                types = tender.requirements.values_list('document_type', flat=True).distinct()
                all_requirement_types.update([t for t in types if t])
            
            if all_requirement_types:
                # Create a matrix of requirement types by tender
                req_comparison = [
                    ["Requirement Type"] + [f"Tender {i+1}" for i in range(len(tenders))]
                ]
                
                for req_type in sorted(all_requirement_types):
                    row = [req_type]
                    for tender in tenders:
                        has_req = tender.requirements.filter(document_type=req_type).exists()
                        row.append("✓" if has_req else "✗")
                    req_comparison.append(row)
                
                # Create the table
                req_table = Table(req_comparison, colWidths=col_widths)
                req_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(req_table)
            else:
                elements.append(Paragraph("No standard requirement types found across these tenders.", styles['Normal']))
            
            elements.append(PageBreak())
            
            # 3. Offer Analysis
            elements.append(Paragraph("3. Offer Analysis", styles['Heading1']))
            
            # Create a bar chart comparing number of offers
            offer_counts = [tender.offers.count() for tender in tenders]
            
            elements.append(Paragraph("3.1 Number of Offers by Tender", styles['Heading2']))
            
            # Only create chart if there are offers
            if any(offer_counts):
                drawing = Drawing(400, 200)
                bc = VerticalBarChart()
                bc.x = 50
                bc.y = 50
                bc.height = 125
                bc.width = 300
                bc.data = [offer_counts]
                bc.strokeColor = colors.black
                bc.valueAxis.valueMin = 0
                bc.valueAxis.valueMax = max(offer_counts) + 1
                bc.valueAxis.valueStep = 1
                bc.categoryAxis.labels.boxAnchor = 'ne'
                bc.categoryAxis.labels.dx = -8
                bc.categoryAxis.labels.dy = -2
                bc.categoryAxis.labels.angle = 30
                bc.categoryAxis.categoryNames = [t.reference_number for t in tenders]
                drawing.add(bc)
                
                elements.append(drawing)
                elements.append(Spacer(1, 0.2*inch))
            
            # Status breakdown for all offers
            elements.append(Paragraph("3.2 Offer Status Breakdown", styles['Heading2']))
            
            status_data = [
                ["Status"] + [f"Tender {i+1}" for i in range(len(tenders))]
            ]
            
            # Get all possible statuses
            all_statuses = list(Offer.STATUS_CHOICES)
            status_dict = dict(all_statuses)
            
            # Add a row for each status
            for status_code, status_name in all_statuses:
                row = [status_name.capitalize()]
                for tender in tenders:
                    count = tender.offers.filter(status=status_code).count()
                    row.append(str(count))
                status_data.append(row)
                
            # Add total row
            status_data.append(
                ["TOTAL"] + [str(tender.offers.count()) for tender in tenders]
            )
            
            # Create the table
            status_table = Table(status_data, colWidths=col_widths)
            status_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(status_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Average prices comparison
            elements.append(Paragraph("3.3 Price Analysis", styles['Heading2']))
            
            price_data = [
                ["Metric"] + [f"Tender {i+1}" for i in range(len(tenders))]
            ]
            
            for tender in tenders:
                tender.avg_price = tender.offers.filter(price__isnull=False).aggregate(avg=Avg('price'))['avg']
                tender.min_price = tender.offers.filter(price__isnull=False).aggregate(min=Min('price'))['min']
                tender.max_price = tender.offers.filter(price__isnull=False).aggregate(max=Max('price'))['max']
            
            # Add rows for different price metrics
            price_data.append(
                ["Average Price"] + [(f"{t.avg_price:.2f}" if t.avg_price else "N/A") for t in tenders]
            )
            price_data.append(
                ["Minimum Price"] + [(f"{t.min_price:.2f}" if t.min_price else "N/A") for t in tenders]
            )
            price_data.append(
                ["Maximum Price"] + [(f"{t.max_price:.2f}" if t.max_price else "N/A") for t in tenders]
            )
            price_data.append(
                ["Price Range"] + [(f"{t.max_price - t.min_price:.2f}" if t.min_price and t.max_price else "N/A") for t in tenders]
            )
            
            # Create the table
            price_table = Table(price_data, colWidths=col_widths)
            price_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(price_table)
            
            elements.append(PageBreak())
            
            # 4. Vendor Participation
            elements.append(Paragraph("4. Vendor Participation", styles['Heading1']))
            
            # Find all vendors who participated in any of these tenders
            vendor_ids = Offer.objects.filter(
                tender__in=tenders
            ).values_list('vendor_id', flat=True).distinct()
            
            vendors = VendorCompany.objects.filter(id__in=vendor_ids)
            
            if not vendors.exists():
                elements.append(Paragraph("No vendors have submitted offers for these tenders.", styles['Normal']))
            else:
                # Create a matrix of vendor participation by tender
                vendor_matrix = [
                    ["Vendor"] + [f"Tender {i+1}" for i in range(len(tenders))]
                ]
                
                for vendor in vendors:
                    row = [vendor.name]
                    for tender in tenders:
                        has_offer = tender.offers.filter(vendor=vendor).exists()
                        row.append("✓" if has_offer else "✗")
                    vendor_matrix.append(row)
                
                # Create the table
                vendor_table = Table(vendor_matrix, colWidths=col_widths)
                vendor_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(vendor_table)
                elements.append(Spacer(1, 0.3*inch))
                
                # Aggregate participation metrics
                elements.append(Paragraph("4.1 Vendor Participation Metrics", styles['Heading2']))
                
                participation_data = []
                for vendor in vendors:
                    vendor_data = {
                        'name': vendor.name,
                        'tenders_count': sum(1 for t in tenders if t.offers.filter(vendor=vendor).exists()),
                        'total_offers': Offer.objects.filter(vendor=vendor, tender__in=tenders).count(),
                        'awards': Offer.objects.filter(vendor=vendor, tender__in=tenders, status='awarded').count()
                    }
                    participation_data.append(vendor_data)
                
                # Sort by participation count (descending)
                participation_data.sort(key=lambda x: x['tenders_count'], reverse=True)
                
                part_matrix = [
                    ["Vendor", "Tenders Participated", "Total Offers", "Awards"]
                ]
                
                for data in participation_data:
                    part_matrix.append([
                        data['name'],
                        str(data['tenders_count']),
                        str(data['total_offers']),
                        str(data['awards'])
                    ])
                
                # Create the table
                part_table = Table(part_matrix, colWidths=[200, 100, 100, 100])
                part_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ]))
                elements.append(part_table)
            
            elements.append(PageBreak())
            
            # 5. Evaluation Criteria Comparison (if applicable)
            elements.append(Paragraph("5. Evaluation Criteria Comparison", styles['Heading1']))
            
            # Check if there are evaluation criteria for these tenders
            has_criteria = False
            for tender in tenders:
                if EvaluationCriteria.objects.filter(tender=tender).exists():
                    has_criteria = True
                    break
            
            if not has_criteria:
                elements.append(Paragraph("No evaluation criteria defined for these tenders.", styles['Normal']))
            else:
                # Create comparison table for evaluation criteria
                elements.append(Paragraph("5.1 Technical Criteria Weights", styles['Heading2']))
                
                # Get technical criteria for each tender
                tech_comparison = [
                    ["Tender", "# of Technical Criteria", "Total Weight", "Avg Weight per Criterion"]
                ]
                
                for i, tender in enumerate(tenders):
                    criteria = EvaluationCriteria.objects.filter(tender=tender, category='technical')
                    count = criteria.count()
                    total_weight = criteria.aggregate(sum=Sum('weight'))['sum'] or 0
                    avg_weight = total_weight / count if count > 0 else 0
                    
                    tech_comparison.append([
                        f"Tender {i+1}: {tender.reference_number}",
                        str(count),
                        f"{total_weight}%",
                        f"{avg_weight:.1f}%"
                    ])
                
                # Create the table
                tech_table = Table(tech_comparison, colWidths=[200, 100, 100, 100])
                tech_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ]))
                elements.append(tech_table)
                elements.append(Spacer(1, 0.3*inch))
                
                # Create comparison table for financial criteria
                elements.append(Paragraph("5.2 Financial Criteria Weights", styles['Heading2']))
                
                # Get financial criteria for each tender
                fin_comparison = [
                    ["Tender", "# of Financial Criteria", "Total Weight", "Avg Weight per Criterion"]
                ]
                
                for i, tender in enumerate(tenders):
                    criteria = EvaluationCriteria.objects.filter(tender=tender, category='financial')
                    count = criteria.count()
                    total_weight = criteria.aggregate(sum=Sum('weight'))['sum'] or 0
                    avg_weight = total_weight / count if count > 0 else 0
                    
                    fin_comparison.append([
                        f"Tender {i+1}: {tender.reference_number}",
                        str(count),
                        f"{total_weight}%",
                        f"{avg_weight:.1f}%"
                    ])
                
                # Create the table
                fin_table = Table(fin_comparison, colWidths=[200, 100, 100, 100])
                fin_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                ]))
                elements.append(fin_table)
            
            # 6. Conclusions and Recommendations
            elements.append(PageBreak())
            elements.append(Paragraph("6. Conclusions and Recommendations", styles['Heading1']))
            elements.append(Paragraph("This section can be filled with analysis and recommendations based on the data presented in this report.", styles['Normal']))
            
            # Build the document
            doc.build(elements)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Error in _generate_comparative_pdf_report: {str(e)}")
            return None
    
    def _generate_comparative_csv_report(self, tenders):
        """Generate a CSV report comparing multiple tenders"""
        try:
            import csv
            from io import StringIO
            
            # Create a buffer for the CSV data
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            # Write header
            writer.writerow(["Comparative Tender Analysis", timezone.now().strftime('%Y-%m-%d')])
            writer.writerow(["Generated by", self.request.user.username])
            writer.writerow([])  # Empty row
            
            # Write tender IDs
            writer.writerow(["Tender ID"] + [t.id for t in tenders])
            writer.writerow(["Reference Number"] + [t.reference_number for t in tenders])
            writer.writerow([])  # Empty row
            
            # Basic tender information
            writer.writerow(["Tender Information"])
            writer.writerow(["Title"] + [t.title for t in tenders])
            writer.writerow(["Status"] + [t.status for t in tenders])
            writer.writerow(["Category"] + [(t.category or "N/A") for t in tenders])
            writer.writerow(["Created Date"] + [t.created_at.strftime('%Y-%m-%d') for t in tenders])
            writer.writerow(["Published Date"] + [(t.published_at.strftime('%Y-%m-%d') if t.published_at else "N/A") for t in tenders])
            writer.writerow(["Submission Deadline"] + [t.submission_deadline.strftime('%Y-%m-%d') for t in tenders])
            writer.writerow(["Estimated Value"] + [(f"{t.estimated_value}" if t.estimated_value else "N/A") for t in tenders])
            writer.writerow([])  # Empty row
            
            # Offer statistics
            writer.writerow(["Offer Statistics"])
            writer.writerow(["Total Offers"] + [str(t.offers.count()) for t in tenders])
            
            # Offer status counts
            all_statuses = dict(Offer.STATUS_CHOICES)
            for status_code, status_name in all_statuses.items():
                writer.writerow([f"Status: {status_name}"] + [str(t.offers.filter(status=status_code).count()) for t in tenders])
            
            writer.writerow([])  # Empty row
            
            # Price information
            writer.writerow(["Price Information"])
            
            # Calculate price statistics
            for tender in tenders:
                tender.avg_price = tender.offers.filter(price__isnull=False).aggregate(avg=Avg('price'))['avg']
                tender.min_price = tender.offers.filter(price__isnull=False).aggregate(min=Min('price'))['min']
                tender.max_price = tender.offers.filter(price__isnull=False).aggregate(max=Max('price'))['max']
            
            writer.writerow(["Average Price"] + [(f"{t.avg_price:.2f}" if t.avg_price else "N/A") for t in tenders])
            writer.writerow(["Minimum Price"] + [(f"{t.min_price:.2f}" if t.min_price else "N/A") for t in tenders])
            writer.writerow(["Maximum Price"] + [(f"{t.max_price:.2f}" if t.max_price else "N/A") for t in tenders])
            writer.writerow([])  # Empty row
            
            # Requirements information
            # server/aadf/views/report_views.py (continued)

            # Requirements information
            writer.writerow(["Requirements Information"])
            writer.writerow(["Total Requirements"] + [str(t.requirements.count()) for t in tenders])
            
            # Collect all unique requirement types
            all_requirement_types = set()
            for tender in tenders:
                types = tender.requirements.values_list('document_type', flat=True).distinct()
                all_requirement_types.update([t for t in types if t])
            
            # Write requirement types by tender
            for req_type in sorted(all_requirement_types):
                row = [f"Requirement: {req_type}"]
                for tender in tenders:
                    has_req = tender.requirements.filter(document_type=req_type).exists()
                    row.append("Yes" if has_req else "No")
                writer.writerow(row)
            
            writer.writerow([])  # Empty row
            
            # Evaluation criteria information
            writer.writerow(["Evaluation Criteria Information"])
            writer.writerow(["Total Criteria"] + [str(EvaluationCriteria.objects.filter(tender=t).count()) for t in tenders])
            
            # Technical criteria
            writer.writerow(["Technical Criteria"] + [str(EvaluationCriteria.objects.filter(tender=t, category='technical').count()) for t in tenders])
            writer.writerow(["Technical Weight"] + [f"{EvaluationCriteria.objects.filter(tender=t, category='technical').aggregate(sum=Sum('weight'))['sum'] or 0}%" for t in tenders])
            
            # Financial criteria
            writer.writerow(["Financial Criteria"] + [str(EvaluationCriteria.objects.filter(tender=t, category='financial').count()) for t in tenders])
            writer.writerow(["Financial Weight"] + [f"{EvaluationCriteria.objects.filter(tender=t, category='financial').aggregate(sum=Sum('weight'))['sum'] or 0}%" for t in tenders])
            
            writer.writerow([])  # Empty row
            
            # Vendor participation
            writer.writerow(["Vendor Participation"])
            
            # Find all vendors who participated in any of these tenders
            vendor_ids = Offer.objects.filter(
                tender__in=tenders
            ).values_list('vendor_id', flat=True).distinct()
            
            vendors = VendorCompany.objects.filter(id__in=vendor_ids)
            
            # Write header row with tender references
            writer.writerow(["Vendor"] + [t.reference_number for t in tenders])
            
            # Write vendor participation
            for vendor in vendors:
                row = [vendor.name]
                for tender in tenders:
                    has_offer = tender.offers.filter(vendor=vendor).exists()
                    row.append("Yes" if has_offer else "No")
                writer.writerow(row)
            
            writer.writerow([])  # Empty row
            
            # Vendor statistics
            writer.writerow(["Vendor Statistics"])
            writer.writerow(["Vendor", "Tenders Participated", "Total Offers", "Awards"])
            
            for vendor in vendors:
                row = [
                    vendor.name,
                    str(sum(1 for t in tenders if t.offers.filter(vendor=vendor).exists())),
                    str(Offer.objects.filter(vendor=vendor, tender__in=tenders).count()),
                    str(Offer.objects.filter(vendor=vendor, tender__in=tenders, status='awarded').count())
                ]
                writer.writerow(row)
            
            # Return the buffer value
            buffer_value = io.StringIO()
            buffer_value.write(buffer.getvalue())
            buffer_value.seek(0)
            return buffer_value
            
        except Exception as e:
            logger.error(f"Error in _generate_comparative_csv_report: {str(e)}")
            return None

    @action(detail=False, methods=['post'])
    def generate_vendor_report(self, request):
        """Generate a report for a specific vendor"""
        vendor_id = request.data.get('vendor_id')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        format_type = request.data.get('format', 'pdf')  # pdf or csv
        
        if not vendor_id:
            return Response(
                {'error': 'vendor_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            vendor = VendorCompany.objects.get(id=vendor_id)
            
            # Set default date range if not provided
            if not start_date:
                start_date = (timezone.now() - datetime.timedelta(days=365)).strftime('%Y-%m-%d')
            if not end_date:
                end_date = timezone.now().strftime('%Y-%m-%d')
                
            # Generate the report based on format
            if format_type == 'pdf':
                report_buffer = self._generate_vendor_pdf_report(vendor, start_date, end_date)
                filename = f"vendor_report_{vendor.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
                content_type = 'application/pdf'
            else:  # csv
                report_buffer = self._generate_vendor_csv_report(vendor, start_date, end_date)
                filename = f"vendor_report_{vendor.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}.csv"
                content_type = 'text/csv'
                
            if not report_buffer:
                return Response(
                    {'error': 'Failed to generate report'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
            # Create a report record (use the most recent tender by this vendor as parent)
            recent_tender = Tender.objects.filter(
                offers__vendor=vendor
            ).order_by('-created_at').first()
            
            if not recent_tender:
                return Response(
                    {'error': 'No tenders found for this vendor'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Save the report to storage
            file_path = f"reports/{filename}"
            default_storage.save(file_path, ContentFile(report_buffer.getvalue()))
                
            # Create the report record
            report = Report.objects.create(
                tender=recent_tender,
                generated_by=request.user,
                report_type='vendor_analysis',
                filename=filename,
                file_path=file_path
            )
            
            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except VendorCompany.DoesNotExist:
            return Response(
                {'error': 'Vendor not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating vendor report: {str(e)}")
            return Response(
                {'error': f'Report generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_vendor_pdf_report(self, vendor, start_date, end_date):
        """Generate a PDF report for a vendor"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib import colors
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
                PageBreak, ListFlowable, ListItem
            )
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.graphics.shapes import Drawing
            from reportlab.graphics.charts.barcharts import VerticalBarChart
            from reportlab.graphics.charts.piecharts import Pie
            from reportlab.graphics.charts.linecharts import HorizontalLineChart
            import io
            import datetime
            
            # Parse dates
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Create a buffer to receive the PDF data
            buffer = io.BytesIO()
            
            # Create the PDF object
            doc = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=72, leftMargin=72,
                topMargin=72, bottomMargin=72
            )
            
            # Get styles
            styles = getSampleStyleSheet()
            styles.add(ParagraphStyle(
                name='Heading1',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=12
            ))
            styles.add(ParagraphStyle(
                name='Heading2',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=8
            ))
            styles.add(ParagraphStyle(
                name='Heading3',
                parent=styles['Heading3'],
                fontSize=12,
                spaceAfter=6
            ))
            styles.add(ParagraphStyle(
                name='Normal',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=6
            ))
            styles.add(ParagraphStyle(
                name='NormalIndent',
                parent=styles['Normal'],
                leftIndent=20,
                fontSize=10,
                spaceAfter=6
            ))
            
            # Build the document
            elements = []
            
            # Cover page
            elements.append(Paragraph(f"Vendor Performance Report", styles['Heading1']))
            elements.append(Paragraph(f"{vendor.name}", styles['Heading2']))
            elements.append(Paragraph(f"Period: {start_date} to {end_date}", styles['Normal']))
            elements.append(Paragraph(f"Report generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            elements.append(Paragraph(f"Generated by: {self.request.user.username}", styles['Normal']))
            elements.append(PageBreak())
            
            # 1. Vendor Information
            elements.append(Paragraph("1. Vendor Information", styles['Heading1']))
            
            # Vendor details table
            vendor_details = [
                ["Company Name:", vendor.name],
                ["Registration Number:", vendor.registration_number or "N/A"],
                ["Address:", vendor.address or "N/A"],
                ["Phone:", vendor.phone or "N/A"],
                ["Email:", vendor.email or "N/A"],
                ["Registered Since:", vendor.created_at.strftime('%Y-%m-%d')],
                ["Number of Users:", str(vendor.users.count())]
            ]
            
            vendor_table = Table(vendor_details, colWidths=[150, 300])
            vendor_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(vendor_table)
            elements.append(PageBreak())
            
            # 2. Participation Summary
            elements.append(Paragraph("2. Participation Summary", styles['Heading1']))
            
            # Get offers within date range
            offers = Offer.objects.filter(
                vendor=vendor,
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            # Participation statistics
            elements.append(Paragraph("2.1 Tender Participation", styles['Heading2']))
            
            # Calculate participation metrics
            total_tenders = Tender.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).count()
            
            participated_tenders = offers.values('tender_id').distinct().count()
            
            participation_rate = participated_tenders / total_tenders * 100 if total_tenders > 0 else 0
            
            # Create table with participation metrics
            participation_stats = [
                ["Metric", "Value"],
                ["Total Tenders in Period:", str(total_tenders)],
                ["Tenders Participated:", str(participated_tenders)],
                ["Participation Rate:", f"{participation_rate:.1f}%"],
                ["Total Offers Submitted:", str(offers.count())],
                ["Offers per Tender:", f"{offers.count() / participated_tenders:.1f}" if participated_tenders > 0 else "N/A"]
            ]
            
            part_table = Table(participation_stats, colWidths=[200, 200])
            part_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ]))
            elements.append(part_table)
            elements.append(Spacer(1, 0.3*inch))
            
            # Offer status breakdown
            elements.append(Paragraph("2.2 Offer Status Breakdown", styles['Heading2']))
            
            # Get offers by status
            status_counts = offers.values('status').annotate(count=Count('status'))
            status_dict = dict(Offer.STATUS_CHOICES)
            
            # Prepare data for pie chart and table
            status_data = []
            for status_item in status_counts:
                status_code = status_item['status']
                count = status_item['count']
                status_name = status_dict.get(status_code, status_code).capitalize()
                status_data.append((status_name, count))
            
            # Add any missing statuses with count 0
            existing_codes = [item['status'] for item in status_counts]
            for code, name in Offer.STATUS_CHOICES:
                if code not in existing_codes:
                    status_data.append((name.capitalize(), 0))
            
            # Sort by status name
            status_data.sort(key=lambda x: x[0])
            
            # Create pie chart if there are offers
            if offers.exists():
                drawing = Drawing(300, 200)
                pie = Pie()
                pie.x = 150
                pie.y = 100
                pie.width = 100
                pie.height = 100
                pie.data = [item[1] for item in status_data]
                pie.labels = [f"{item[0]}: {item[1]}" for item in status_data]
                pie.slices.strokeWidth = 0.5
                
                # Assign colors to slices
                colors_list = [colors.red, colors.green, colors.blue, colors.yellow, colors.pink]
                for i, (status_name, _) in enumerate(status_data):
                    if status_name.lower() == 'awarded':
                        pie.slices[i].fillColor = colors.green
                    elif status_name.lower() == 'rejected':
                        pie.slices[i].fillColor = colors.red
                    else:
                        pie.slices[i].fillColor = colors_list[i % len(colors_list)]
                
                drawing.add(pie)
                elements.append(drawing)
            
            # Create status table
            status_table_data = [["Status", "Count", "Percentage"]]
            total_offers = offers.count()
            
            for status_name, count in status_data:
                percentage = count / total_offers * 100 if total_offers > 0 else 0
                status_table_data.append([status_name, str(count), f"{percentage:.1f}%"])
            
            # Add totals row
            status_table_data.append(["TOTAL", str(total_offers), "100.0%"])
            
            status_table = Table(status_table_data, colWidths=[150, 100, 100])
            status_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'CENTER'),
                ('ALIGN', (2, 1), (2, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(status_table)
            elements.append(PageBreak())
            
            # 3. Performance Analysis
            elements.append(Paragraph("3. Performance Analysis", styles['Heading1']))
            
            # Get evaluated offers
            evaluated_offers = offers.filter(
                Q(technical_score__isnull=False) | 
                Q(financial_score__isnull=False) | 
                Q(total_score__isnull=False)
            )
            
            if not evaluated_offers.exists():
                elements.append(Paragraph("No evaluated offers in the selected period.", styles['Normal']))
            else:
                # Create scores summary
                elements.append(Paragraph("3.1 Evaluation Scores Summary", styles['Heading2']))
                
                # Calculate score metrics
                avg_technical = evaluated_offers.aggregate(avg=Avg('technical_score'))['avg']
                avg_financial = evaluated_offers.aggregate(avg=Avg('financial_score'))['avg']
                avg_total = evaluated_offers.aggregate(avg=Avg('total_score'))['avg']
                
                # Create scores table
                scores_data = [
                    ["Score Type", "Average", "Minimum", "Maximum"],
                    ["Technical Score", 
                     f"{avg_technical:.2f}" if avg_technical else "N/A",
                     f"{evaluated_offers.aggregate(min=Min('technical_score'))['min']:.2f}" if evaluated_offers.filter(technical_score__isnull=False).exists() else "N/A",
                     f"{evaluated_offers.aggregate(max=Max('technical_score'))['max']:.2f}" if evaluated_offers.filter(technical_score__isnull=False).exists() else "N/A"
                    ],
                    ["Financial Score", 
                     f"{avg_financial:.2f}" if avg_financial else "N/A",
                     f"{evaluated_offers.aggregate(min=Min('financial_score'))['min']:.2f}" if evaluated_offers.filter(financial_score__isnull=False).exists() else "N/A",
                     f"{evaluated_offers.aggregate(max=Max('financial_score'))['max']:.2f}" if evaluated_offers.filter(financial_score__isnull=False).exists() else "N/A"
                    ],
                    ["Total Score", 
                     f"{avg_total:.2f}" if avg_total else "N/A",
                     f"{evaluated_offers.aggregate(min=Min('total_score'))['min']:.2f}" if evaluated_offers.filter(total_score__isnull=False).exists() else "N/A",
                     f"{evaluated_offers.aggregate(max=Max('total_score'))['max']:.2f}" if evaluated_offers.filter(total_score__isnull=False).exists() else "N/A"
                    ]
                ]
                
                scores_table = Table(scores_data, colWidths=[120, 100, 100, 100])
                scores_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ]))
                elements.append(scores_table)
                elements.append(Spacer(1, 0.3*inch))
                
                # Create score trend chart if multiple evaluated offers
                if evaluated_offers.count() > 1:
                    elements.append(Paragraph("3.2 Score Trends", styles['Heading2']))
                    elements.append(Paragraph("Performance trend over time (by offer submission date):", styles['Normal']))
                    
                    # Get offers with total score, ordered by submission date
                    trend_offers = evaluated_offers.filter(
                        total_score__isnull=False,
                        submitted_at__isnull=False
                    ).order_by('submitted_at')
                    
                    if trend_offers.count() > 1:
                        # Prepare data for line chart
                        dates = [o.submitted_at.strftime('%Y-%m-%d') for o in trend_offers]
                        scores = [o.total_score for o in trend_offers]
                        
                        # Create line chart
                        drawing = Drawing(500, 200)
                        lc = HorizontalLineChart()
                        lc.x = 50
                        lc.y = 50
                        lc.height = 125
                        lc.width = 400
                        lc.data = [scores]
                        lc.joinedLines = 1
                        lc.lines[0].symbol = Circle(r=2, fillColor=colors.blue)
                        lc.lines[0].strokeWidth = 2
                        lc.lines[0].strokeColor = colors.blue
                        
                        # Configure axes
                        lc.valueAxis.valueMin = 0
                        lc.valueAxis.valueMax = 100
                        lc.valueAxis.valueStep = 10
                        lc.categoryAxis.categoryNames = dates
                        lc.categoryAxis.labels.boxAnchor = 'ne'
                        lc.categoryAxis.labels.angle = 30
                        lc.categoryAxis.labels.dx = -8
                        lc.categoryAxis.labels.dy = -2
                        
                        drawing.add(lc)
                        elements.append(drawing)
                        elements.append(Spacer(1, 0.2*inch))
                    
                # List of evaluated tenders with scores
                elements.append(Paragraph("3.3 Detailed Evaluation Results", styles['Heading2']))
                
                # Create table with tender details and scores
                eval_data = [
                    ["Tender Ref.", "Tender Title", "Technical", "Financial", "Total", "Status"]
                ]
                
                for offer in evaluated_offers:
                    eval_data.append([
                        offer.tender.reference_number,
                        offer.tender.title[:30] + "..." if len(offer.tender.title) > 30 else offer.tender.title,
                        f"{offer.technical_score:.1f}" if offer.technical_score is not None else "N/A",
                        f"{offer.financial_score:.1f}" if offer.financial_score is not None else "N/A",
                        f"{offer.total_score:.1f}" if offer.total_score is not None else "N/A",
                        offer.status.capitalize()
                    ])
                
                eval_table = Table(eval_data, colWidths=[80, 160, 70, 70, 70, 70])
                eval_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (2, 1), (-1, -1), 'CENTER'),
                ]))
                
                # Highlight awarded offers
                for i, row in enumerate(eval_data):
                    if i > 0 and row[5] == 'Awarded':
                        eval_table.setStyle(TableStyle([
                            ('BACKGROUND', (0, i), (-1, i), colors.lightgreen),
                        ]))
                
                elements.append(eval_table)
            
            elements.append(PageBreak())
            
            # 4. Price Analysis
            elements.append(Paragraph("4. Price Analysis", styles['Heading1']))
            
            # Get offers with prices
            priced_offers = offers.filter(price__isnull=False)
            
            if not priced_offers.exists():
                elements.append(Paragraph("No price information available for this period.", styles['Normal']))
            else:
                # Price statistics
                avg_price = priced_offers.aggregate(avg=Avg('price'))['avg']
                min_price = priced_offers.aggregate(min=Min('price'))['min']
                max_price = priced_offers.aggregate(max=Max('price'))['max']
                
                elements.append(Paragraph(f"Average Price: {avg_price:.2f}", styles['Normal']))
                elements.append(Paragraph(f"Price Range: {min_price:.2f} - {max_price:.2f}", styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
                
                # Price competitiveness analysis
                elements.append(Paragraph("4.1 Price Competitiveness", styles['Heading2']))
                
                # Compare prices to average prices for the same tenders
                price_comp_data = [
                    ["Tender Ref.", "Vendor Price", "Avg. Market Price", "Difference", "% Difference"]
                ]
                
                for offer in priced_offers:
                    # Get average price for this tender (excluding this vendor)
                    market_avg = Offer.objects.filter(
                        tender=offer.tender,
                        price__isnull=False
                    ).exclude(
                        vendor=vendor
                    ).aggregate(avg=Avg('price'))['avg']
                    
                    if market_avg:
                        diff = offer.price - market_avg
                        pct_diff = (diff / market_avg) * 100
                        
                        price_comp_data.append([
                            offer.tender.reference_number,
                            f"{offer.price:.2f}",
                            f"{market_avg:.2f}",
                            f"{diff:.2f}",
                            f"{pct_diff:.1f}%"
                        ])
                
                if len(price_comp_data) > 1:
                    price_comp_table = Table(price_comp_data, colWidths=[80, 90, 110, 90, 90])
                    price_comp_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ]))
                    
                    # Color code the percentage difference column
                    for i in range(1, len(price_comp_data)):
                        pct_str = price_comp_data[i][4]
                        try:
                            pct = float(pct_str.replace('%', ''))
                            if pct < -5:  # More than 5% below average (good)
                                price_comp_table.setStyle(TableStyle([
                                    ('TEXTCOLOR', (4, i), (4, i), colors.green),
                                ]))
                            elif pct > 10:  # More than 10% above average (bad)
                                price_comp_table.setStyle(TableStyle([
                                    ('TEXTCOLOR', (4, i), (4, i), colors.red),
                                ]))
                        except:
                            pass
                    
                    elements.append(price_comp_table)
                else:
                    elements.append(Paragraph("No comparative price data available.", styles['Normal']))
            
            elements.append(PageBreak())
            
            # 5. Recommendations
            # server/aadf/views/report_views.py (continued)

            # 5. Recommendations
            elements.append(Paragraph("5. Conclusions and Recommendations", styles['Heading1']))
            elements.append(Paragraph("Based on the analysis of this vendor's performance, the following conclusions and recommendations can be made:", styles['Normal']))
            
            # Add performance notes based on actual data
            success_rate = offers.filter(status='awarded').count() / offers.count() * 100 if offers.count() > 0 else 0
            
            # Generate appropriate recommendations based on data
            recommendations = []
            
            if success_rate < 10:
                recommendations.append("The vendor has a low success rate of awarded tenders. Recommend providing feedback on areas for improvement.")
            elif success_rate > 50:
                recommendations.append("The vendor has a high success rate. Consider for preferred vendor status.")
                
            if evaluated_offers.exists():
                avg_tech = evaluated_offers.aggregate(avg=Avg('technical_score'))['avg'] or 0
                avg_fin = evaluated_offers.aggregate(avg=Avg('financial_score'))['avg'] or 0
                
                if avg_tech < 50:
                    recommendations.append("Technical scores are below average. Recommend technical capability review.")
                if avg_fin < 50:
                    recommendations.append("Financial scores are below average. Consider price competitiveness review.")
                    
            # Add recommendations to document
            if recommendations:
                recommendations_list = []
                for rec in recommendations:
                    recommendations_list.append(Paragraph(f"• {rec}", styles['NormalIndent']))
                    
                for item in recommendations_list:
                    elements.append(item)
            else:
                elements.append(Paragraph("No specific recommendations at this time.", styles['Normal']))
            
            # Add placeholder for manual notes
            elements.append(Spacer(1, 0.3*inch))
            elements.append(Paragraph("Additional Notes:", styles['Heading3']))
            elements.append(Paragraph("_______________________________________________________", styles['Normal']))
            elements.append(Paragraph("_______________________________________________________", styles['Normal']))
            elements.append(Paragraph("_______________________________________________________", styles['Normal']))
            elements.append(Paragraph("_______________________________________________________", styles['Normal']))
            
            # Build the document
            doc.build(elements)
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Error in _generate_vendor_pdf_report: {str(e)}")
            return None
    
    def _generate_vendor_csv_report(self, vendor, start_date, end_date):
        """Generate a CSV report for a vendor"""
        try:
            import csv
            from io import StringIO
            import datetime
            
            # Parse dates
            start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()
            
            # Create a buffer for the CSV data
            buffer = StringIO()
            writer = csv.writer(buffer)
            
            # Write header
            writer.writerow(["Vendor Performance Report", vendor.name])
            writer.writerow(["Period", f"{start_date} to {end_date}"])
            writer.writerow(["Generated On", timezone.now().strftime('%Y-%m-%d %H:%M')])
            writer.writerow(["Generated By", self.request.user.username])
            writer.writerow([])  # Empty row
            
            # Vendor Information
            writer.writerow(["Vendor Information"])
            writer.writerow(["Company Name", vendor.name])
            writer.writerow(["Registration Number", vendor.registration_number or "N/A"])
            writer.writerow(["Address", vendor.address or "N/A"])
            writer.writerow(["Phone", vendor.phone or "N/A"])
            writer.writerow(["Email", vendor.email or "N/A"])
            writer.writerow(["Registered Since", vendor.created_at.strftime('%Y-%m-%d')])
            writer.writerow(["Number of Users", str(vendor.users.count())])
            writer.writerow([])  # Empty row
            
            # Get offers within date range
            offers = Offer.objects.filter(
                vendor=vendor,
                created_at__gte=start_date,
                created_at__lte=end_date
            )
            
            # Participation Summary
            writer.writerow(["Participation Summary"])
            
            # Calculate participation metrics
            total_tenders = Tender.objects.filter(
                created_at__gte=start_date,
                created_at__lte=end_date
            ).count()
            
            participated_tenders = offers.values('tender_id').distinct().count()
            
            participation_rate = participated_tenders / total_tenders * 100 if total_tenders > 0 else 0
            
            writer.writerow(["Total Tenders in Period", str(total_tenders)])
            writer.writerow(["Tenders Participated", str(participated_tenders)])
            writer.writerow(["Participation Rate", f"{participation_rate:.1f}%"])
            writer.writerow(["Total Offers Submitted", str(offers.count())])
            writer.writerow(["Offers per Tender", f"{offers.count() / participated_tenders:.1f}" if participated_tenders > 0 else "N/A"])
            writer.writerow([])  # Empty row
            
            # Offer Status Breakdown
            writer.writerow(["Offer Status Breakdown"])
            
            status_counts = offers.values('status').annotate(count=Count('status'))
            status_dict = dict(Offer.STATUS_CHOICES)
            writer.writerow(["Status", "Count", "Percentage"])
            
            total_offers = offers.count()
            for status_item in status_counts:
                status_code = status_item['status']
                count = status_item['count']
                status_name = status_dict.get(status_code, status_code).capitalize()
                percentage = count / total_offers * 100 if total_offers > 0 else 0
                writer.writerow([status_name, str(count), f"{percentage:.1f}%"])
                
            writer.writerow(["TOTAL", str(total_offers), "100.0%"])
            writer.writerow([])  # Empty row
            
            # Performance Analysis
            writer.writerow(["Performance Analysis"])
            
            # Get evaluated offers
            evaluated_offers = offers.filter(
                Q(technical_score__isnull=False) | 
                Q(financial_score__isnull=False) | 
                Q(total_score__isnull=False)
            )
            
            if evaluated_offers.exists():
                # Calculate score metrics
                avg_technical = evaluated_offers.aggregate(avg=Avg('technical_score'))['avg']
                avg_financial = evaluated_offers.aggregate(avg=Avg('financial_score'))['avg']
                avg_total = evaluated_offers.aggregate(avg=Avg('total_score'))['avg']
                
                writer.writerow(["Evaluation Scores Summary"])
                writer.writerow(["Score Type", "Average", "Minimum", "Maximum"])
                writer.writerow([
                    "Technical Score", 
                    f"{avg_technical:.2f}" if avg_technical else "N/A",
                    f"{evaluated_offers.aggregate(min=Min('technical_score'))['min']:.2f}" if evaluated_offers.filter(technical_score__isnull=False).exists() else "N/A",
                    f"{evaluated_offers.aggregate(max=Max('technical_score'))['max']:.2f}" if evaluated_offers.filter(technical_score__isnull=False).exists() else "N/A"
                ])
                writer.writerow([
                    "Financial Score", 
                    f"{avg_financial:.2f}" if avg_financial else "N/A",
                    f"{evaluated_offers.aggregate(min=Min('financial_score'))['min']:.2f}" if evaluated_offers.filter(financial_score__isnull=False).exists() else "N/A",
                    f"{evaluated_offers.aggregate(max=Max('financial_score'))['max']:.2f}" if evaluated_offers.filter(financial_score__isnull=False).exists() else "N/A"
                ])
                writer.writerow([
                    "Total Score", 
                    f"{avg_total:.2f}" if avg_total else "N/A",
                    f"{evaluated_offers.aggregate(min=Min('total_score'))['min']:.2f}" if evaluated_offers.filter(total_score__isnull=False).exists() else "N/A",
                    f"{evaluated_offers.aggregate(max=Max('total_score'))['max']:.2f}" if evaluated_offers.filter(total_score__isnull=False).exists() else "N/A"
                ])
                writer.writerow([])  # Empty row
                
                # Detailed Evaluation Results
                writer.writerow(["Detailed Evaluation Results"])
                writer.writerow(["Tender Ref.", "Tender Title", "Technical", "Financial", "Total", "Status"])
                
                for offer in evaluated_offers:
                    writer.writerow([
                        offer.tender.reference_number,
                        offer.tender.title,
                        f"{offer.technical_score:.1f}" if offer.technical_score is not None else "N/A",
                        f"{offer.financial_score:.1f}" if offer.financial_score is not None else "N/A",
                        f"{offer.total_score:.1f}" if offer.total_score is not None else "N/A",
                        offer.status.capitalize()
                    ])
            else:
                writer.writerow(["No evaluated offers in the selected period."])
                
            writer.writerow([])  # Empty row
            
            # Price Analysis
            writer.writerow(["Price Analysis"])
            
            # Get offers with prices
            priced_offers = offers.filter(price__isnull=False)
            
            if priced_offers.exists():
                # Price statistics
                avg_price = priced_offers.aggregate(avg=Avg('price'))['avg']
                min_price = priced_offers.aggregate(min=Min('price'))['min']
                max_price = priced_offers.aggregate(max=Max('price'))['max']
                
                writer.writerow(["Average Price", f"{avg_price:.2f}"])
                writer.writerow(["Minimum Price", f"{min_price:.2f}"])
                writer.writerow(["Maximum Price", f"{max_price:.2f}"])
                writer.writerow(["Price Range", f"{max_price - min_price:.2f}"])
                writer.writerow([])  # Empty row
                
                # Price Competitiveness
                writer.writerow(["Price Competitiveness"])
                writer.writerow(["Tender Ref.", "Vendor Price", "Avg. Market Price", "Difference", "% Difference"])
                
                for offer in priced_offers:
                    # Get average price for this tender (excluding this vendor)
                    market_avg = Offer.objects.filter(
                        tender=offer.tender,
                        price__isnull=False
                    ).exclude(
                        vendor=vendor
                    ).aggregate(avg=Avg('price'))['avg']
                    
                    if market_avg:
                        diff = offer.price - market_avg
                        pct_diff = (diff / market_avg) * 100
                        
                        writer.writerow([
                            offer.tender.reference_number,
                            f"{offer.price:.2f}",
                            f"{market_avg:.2f}",
                            f"{diff:.2f}",
                            f"{pct_diff:.1f}%"
                        ])
            else:
                writer.writerow(["No price information available for this period."])
                
            # Return the buffer value
            buffer_value = io.StringIO()
            buffer_value.write(buffer.getvalue())
            buffer_value.seek(0)
            return buffer_value
            
        except Exception as e:
            logger.error(f"Error in _generate_vendor_csv_report: {str(e)}")
            return None

    @action(detail=False, methods=['post'])
    def generate_archive(self, request):
        """Generate a ZIP archive of all documents for a tender"""
        from zipfile import ZipFile
        import io
        
        tender_id = request.data.get('tender_id')
        include_offers = request.data.get('include_offers', True)
        
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Create a buffer for the ZIP file
            buffer = io.BytesIO()
            
            # Create the ZIP file
            with ZipFile(buffer, 'w') as zip_file:
                # Add tender documents
                tender_docs = TenderDocument.objects.filter(tender=tender)
                for doc in tender_docs:
                    file_path = os.path.join(settings.MEDIA_ROOT, doc.file_path)
                    if os.path.exists(file_path):
                        zip_path = f"tender_documents/{doc.original_filename}"
                        zip_file.write(file_path, zip_path)
                
                # Add offer documents if requested
                if include_offers:
                    offers = Offer.objects.filter(tender=tender)
                    for offer in offers:
                        offer_docs = OfferDocument.objects.filter(offer=offer)
                        for doc in offer_docs:
                            file_path = os.path.join(settings.MEDIA_ROOT, doc.file_path)
                            if os.path.exists(file_path):
                                zip_path = f"offer_documents/{offer.vendor.name}/{doc.original_filename}"
                                zip_file.write(file_path, zip_path)
                
                # Add reports for this tender
                reports = Report.objects.filter(tender=tender)
                for report in reports:
                    file_path = os.path.join(settings.MEDIA_ROOT, report.file_path)
                    if os.path.exists(file_path):
                        zip_path = f"reports/{report.filename}"
                        zip_file.write(file_path, zip_path)
                        
            # Create filename and file path
            filename = f"tender_archive_{tender.reference_number}_{timezone.now().strftime('%Y%m%d%H%M%S')}.zip"
            file_path = f"archives/{filename}"
            
            # Save the archive to storage
            default_storage.save(file_path, ContentFile(buffer.getvalue()))
            
            # Create a report record
            report = Report.objects.create(
                tender=tender,
                generated_by=request.user,
                report_type='archive',
                filename=filename,
                file_path=file_path
            )
            
            # Log the archive creation
            AuditLog.objects.create(
                user=request.user,
                action='create_archive',
                entity_type='tender',
                entity_id=tender.id,
                details={
                    'filename': filename,
                    'include_offers': include_offers
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating archive: {str(e)}")
            return Response(
                {'error': f'Archive generation failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def report_types(self, request):
        """Get available report types"""
        report_types = [
            {
                'id': 'tender_commission',
                'name': 'Tender Commission Report',
                'description': 'Detailed report for the tender commission'
            },
            {
                'id': 'tender_data',
                'name': 'Tender Data Export',
                'description': 'Export of tender data in CSV format'
            },
            {
                'id': 'comparative_analysis',
                'name': 'Comparative Analysis',
                'description': 'Comparison of multiple tenders'
            },
            {
                'id': 'vendor_analysis',
                'name': 'Vendor Analysis',
                'description': 'Analysis of a vendor\'s performance'
            },
            {
                'id': 'archive',
                'name': 'Document Archive',
                'description': 'ZIP archive of all documents for a tender'
            }
        ]
        
        return Response(report_types)