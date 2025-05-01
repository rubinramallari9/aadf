# server/aadf/views.py (Part 1)

from rest_framework import viewsets, permissions, status, serializers, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404, JsonResponse
from django.db.models import Q, Count, Sum, Avg
from django.shortcuts import get_object_or_404
import os
import uuid
import logging
import json

from .models import (
    User, VendorCompany, Tender, TenderRequirement, TenderDocument,
    Offer, OfferDocument, EvaluationCriteria, Evaluation, Approval,
    Report, Notification, AuditLog
)
from .serializers import (
    UserSerializer, VendorCompanySerializer, TenderSerializer, TenderDetailSerializer,
    TenderRequirementSerializer, TenderDocumentSerializer, OfferSerializer, OfferDetailSerializer,
    OfferDocumentSerializer, EvaluationCriteriaSerializer, EvaluationSerializer,
    ApprovalSerializer, ReportSerializer, NotificationSerializer, AuditLogSerializer
)
from .permissions import (
    IsStaffOrAdmin, IsVendor, IsEvaluator, IsAdminUser, CanManageOwnOffers, CanViewOwnDocuments
)
from .utils import (
    generate_reference_number, save_uploaded_file, validate_file_extension, 
    validate_file_size, calculate_offer_score, create_notification, 
    generate_tender_report, export_tender_data, generate_secure_document_link,
    verify_document_signature, get_dashboard_statistics, get_vendor_statistics
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
            'total_documents': TenderDocument.objects.filter(tender=tender).count(),
            'total_requirements': TenderRequirement.objects.filter(tender=tender).count(),
            'total_criteria': EvaluationCriteria.objects.filter(tender=tender).count(),
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


class OfferViewSet(viewsets.ModelViewSet):
    """ViewSet for managing offers"""
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['vendor__name', 'tender__reference_number', 'tender__title']
    ordering_fields = ['created_at', 'total_score', 'price']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OfferDetailSerializer
        return OfferSerializer

    def get_queryset(self):
        """Filter offers based on user role"""
        user = self.request.user
        queryset = Offer.objects.all()
        
        # Filter by tender if provided
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
        
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        # Apply user role restrictions
        if user.role == 'vendor':
            # Vendors can only see their own offers
            queryset = queryset.filter(vendor__users=user)
        elif user.role == 'evaluator':
            # Evaluators can only see offers for closed or awarded tenders
            queryset = queryset.filter(tender__status__in=['closed', 'awarded'])
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign submitted_by and vendor"""
        if self.request.user.role == 'vendor':
            # Get the vendor company associated with this user
            try:
                vendor_company = VendorCompany.objects.filter(users=self.request.user).first()
                if not vendor_company:
                    raise serializers.ValidationError("User must be associated with a vendor company")
                
                serializer.save(
                    submitted_by=self.request.user,
                    vendor=vendor_company,
                    status='draft'
                )
            except Exception as e:
                logger.error(f"Error creating offer: {str(e)}")
                raise serializers.ValidationError(f"Error creating offer: {str(e)}")
        else:
            # For staff/admin, use the provided vendor
            serializer.save(submitted_by=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit an offer"""
        offer = self.get_object()
        
        # Check permissions - only vendor who owns the offer or staff/admin can submit
        if request.user.role == 'vendor' and not offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to submit this offer'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if offer.status == 'draft' and offer.tender.status == 'published':
            # Check if tender submission deadline has passed
            if offer.tender.submission_deadline < timezone.now():
                return Response(
                    {'error': 'Submission deadline has passed'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Check if all mandatory requirements have documents
            mandatory_requirements = TenderRequirement.objects.filter(
                tender=offer.tender,
                is_mandatory=True
            )
            
            for requirement in mandatory_requirements:
                if not OfferDocument.objects.filter(
                    offer=offer,
                    document_type=requirement.document_type
                ).exists():
                    return Response(
                        {'error': f'Missing required document: {requirement.description}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # Submit the offer
            offer.status = 'submitted'
            offer.submitted_at = timezone.now()
            offer.save()
            
            # Notify tender creator
            if offer.tender.created_by:
                create_notification(
                    user=offer.tender.created_by,
                    title='New Offer Submitted',
                    message=f'A new offer from {offer.vendor.name} has been submitted for tender {offer.tender.reference_number}.',
                    notification_type='info',
                    related_entity=offer
                )
                
            return Response({'status': 'offer submitted'})
        return Response({'error': 'offer cannot be submitted'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def evaluate(self, request, pk=None):
        """Mark offer as evaluated"""
        offer = self.get_object()
        
        if offer.status == 'submitted' and offer.tender.status in ['closed', 'awarded']:
            # Calculate and update scores
            calculate_offer_score(offer)
            
            # Update status
            offer.status = 'evaluated'
            offer.save()
            
            return Response({'status': 'offer evaluated'})
        return Response({'error': 'offer cannot be evaluated'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Get all documents for an offer"""
        offer = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to view these documents'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        documents = OfferDocument.objects.filter(offer=offer)
        serializer = OfferDocumentSerializer(documents, many=True)
        
        return Response(serializer.data)


class TenderDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for handling tender document uploads"""
    queryset = TenderDocument.objects.all()
    serializer_class = TenderDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'original_filename']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter documents based on tender_id if provided"""
        queryset = TenderDocument.objects.all()
        
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
            
        return queryset

    def create(self, request, *args, **kwargs):
        """Handle document upload"""
        # Validate permission (only staff and admin can upload tender documents)
        if request.user.role not in ['staff', 'admin']:
            return Response(
                {'error': 'You do not have permission to upload tender documents'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get tender ID from request
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
            
        # Get file from request
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate file extension
        if not validate_file_extension(file.name):
            return Response(
                {'error': 'Invalid file extension'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate file size
        if not validate_file_size(file):
            return Response(
                {'error': 'File size exceeds the limit'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Save the file
        try:
            # Generate a unique filename
            ext = os.path.splitext(file.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            
            # Save to storage
            file_path = default_storage.save(
                f'tender_documents/{filename}',
                ContentFile(file.read())
            )
            
            # Create
            # server/aadf/views.py (Part 2) - Continued from previous part

# (TenderDocumentViewSet - create method continued)
            # Create document record
            document = TenderDocument.objects.create(
                tender=tender,
                uploaded_by=request.user,
                original_filename=file.name,
                filename=filename,
                file_path=file_path,
                file_size=file.size,
                mime_type=file.content_type
            )
            
            serializer = self.get_serializer(document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error uploading tender document: {str(e)}")
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Handle document deletion"""
        document = self.get_object()
        
        # Check permissions (only staff/admin, and only if tender is in draft)
        if request.user.role not in ['staff', 'admin']:
            return Response(
                {'error': 'You do not have permission to delete tender documents'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        if document.tender.status != 'draft':
            return Response(
                {'error': 'Cannot delete documents from published tenders'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Delete the file
        try:
            if default_storage.exists(document.file_path):
                default_storage.delete(document.file_path)
                
            # Delete the document record
            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting tender document: {str(e)}")
            return Response(
                {'error': f'Deletion failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OfferDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for handling offer document uploads"""
    queryset = OfferDocument.objects.all()
    serializer_class = OfferDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'original_filename']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter documents based on user role and offer_id if provided"""
        user = self.request.user
        queryset = OfferDocument.objects.all()
        
        # Filter by offer_id if provided
        offer_id = self.request.query_params.get('offer_id')
        if offer_id:
            queryset = queryset.filter(offer_id=offer_id)
            
        # Apply user role restrictions
        if user.role == 'vendor':
            # Vendors can only see their own documents
            queryset = queryset.filter(offer__vendor__users=user)
            
        return queryset

    def create(self, request, *args, **kwargs):
        """Handle document upload"""
        # Get offer ID from request
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
            
        # Check permissions (only owner vendor or staff/admin)
        if request.user.role == 'vendor' and not offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to upload documents for this offer'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check if offer can be modified
        if offer.status != 'draft':
            return Response(
                {'error': 'Cannot add documents to submitted offers'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get file from request
        file = request.FILES.get('file')
        if not file:
            return Response(
                {'error': 'file is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate file extension
        if not validate_file_extension(file.name):
            return Response(
                {'error': 'Invalid file extension'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate file size
        if not validate_file_size(file):
            return Response(
                {'error': 'File size exceeds the limit'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get document type
        document_type = request.data.get('document_type')
        
        # Save the file
        try:
            # Generate a unique filename
            ext = os.path.splitext(file.name)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            
            # Save to storage
            file_path = default_storage.save(
                f'offer_documents/{filename}',
                ContentFile(file.read())
            )
            
            # Create document record
            document = OfferDocument.objects.create(
                offer=offer,
                original_filename=file.name,
                filename=filename,
                file_path=file_path,
                file_size=file.size,
                mime_type=file.content_type,
                document_type=document_type
            )
            
            serializer = self.get_serializer(document)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            logger.error(f"Error uploading offer document: {str(e)}")
            return Response(
                {'error': f'Upload failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        """Handle document deletion"""
        document = self.get_object()
        
        # Check permissions (only owner vendor or staff/admin)
        if request.user.role == 'vendor' and not document.offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to delete this document'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check if offer can be modified
        if document.offer.status != 'draft':
            return Response(
                {'error': 'Cannot delete documents from submitted offers'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Delete the file
        try:
            if default_storage.exists(document.file_path):
                default_storage.delete(document.file_path)
                
            # Delete the document record
            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting offer document: {str(e)}")
            return Response(
                {'error': f'Deletion failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EvaluationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing evaluations"""
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'score']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter evaluations based on user role and query parameters"""
        user = self.request.user
        queryset = Evaluation.objects.all()
        
        # Filter by offer_id if provided
        offer_id = self.request.query_params.get('offer_id')
        if offer_id:
            queryset = queryset.filter(offer_id=offer_id)
            
        # Filter by criteria_id if provided
        criteria_id = self.request.query_params.get('criteria_id')
        if criteria_id:
            queryset = queryset.filter(criteria_id=criteria_id)
            
        # Filter by evaluator_id if provided
        evaluator_id = self.request.query_params.get('evaluator_id')
        if evaluator_id:
            queryset = queryset.filter(evaluator_id=evaluator_id)
            
        # Apply user role restrictions
        if user.role == 'evaluator':
            # Evaluators can only see their own evaluations
            queryset = queryset.filter(evaluator=user)
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign evaluator to the authenticated user"""
        # Verify user has evaluator role
        if self.request.user.role != 'evaluator' and self.request.user.role not in ['staff', 'admin']:
            raise serializers.ValidationError("Only evaluators can create evaluations")
            
        # Get offer and criteria
        offer_id = self.request.data.get('offer_id')
        criteria_id = self.request.data.get('criteria_id')
        
        try:
            offer = Offer.objects.get(id=offer_id)
            criteria = EvaluationCriteria.objects.get(id=criteria_id)
            
            # Verify offer and criteria belong to the same tender
            if offer.tender_id != criteria.tender_id:
                raise serializers.ValidationError("Offer and criteria must belong to the same tender")
                
            # Verify offer status allows evaluation
            if offer.tender.status not in ['closed', 'awarded']:
                raise serializers.ValidationError("Cannot evaluate offers for tenders that are not closed or awarded")
                
            # Save evaluation
            serializer.save(evaluator=self.request.user)
            
            # Recalculate offer score
            calculate_offer_score(offer)
            
        except (Offer.DoesNotExist, EvaluationCriteria.DoesNotExist) as e:
            raise serializers.ValidationError(str(e))

    def update(self, request, *args, **kwargs):
        """Handle evaluation update"""
        evaluation = self.get_object()
        
        # Check permissions (only the evaluator or staff/admin)
        if request.user.role == 'evaluator' and evaluation.evaluator.id != request.user.id:
            return Response(
                {'error': 'You do not have permission to update this evaluation'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Verify offer status allows evaluation update
        if evaluation.offer.tender.status not in ['closed', 'awarded']:
            return Response(
                {'error': 'Cannot update evaluations for tenders that are not closed or awarded'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update evaluation
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(evaluation, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Recalculate offer score
        calculate_offer_score(evaluation.offer)
        
        return Response(serializer.data)


class VendorCompanyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor companies"""
    queryset = VendorCompany.objects.all()
    serializer_class = VendorCompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'registration_number', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Filter vendor companies based on user role"""
        user = self.request.user
        queryset = VendorCompany.objects.all()
        
        # Apply user role restrictions
        if user.role == 'vendor':
            # Vendors can only see their own companies
            queryset = queryset.filter(users=user)
            
        return queryset

    def perform_create(self, serializer):
        """Handle creation of vendor company"""
        # Only staff/admin can create vendor companies
        if self.request.user.role not in ['staff', 'admin']:
            raise serializers.ValidationError("Only staff/admin can create vendor companies")
            
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_user(self, request, pk=None):
        """Assign a user to a vendor company"""
        company = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            if user.role == 'vendor':
                company.users.add(user)
                
                # Create notification for the user
                create_notification(
                    user=user,
                    title='Assigned to Vendor Company',
                    message=f'You have been assigned to the vendor company: {company.name}',
                    notification_type='info',
                    related_entity=company
                )
                
                return Response({'status': 'user assigned'})
            return Response({'error': 'user must have vendor role'},
                            status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'user not found'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def remove_user(self, request, pk=None):
        """Remove a user from a vendor company"""
        company = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            if company.users.filter(id=user_id).exists():
                company.users.remove(user)
                
                # Create notification for the user
                create_notification(
                    user=user,
                    title='Removed from Vendor Company',
                    message=f'You have been removed from the vendor company: {company.name}',
                    notification_type='info',
                    related_entity=company
                )
                
                return Response({'status': 'user removed'})
            return Response({'error': 'user is not assigned to this company'},
                            status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'user not found'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a vendor company"""
        company = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not company.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to view these statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get statistics
        stats = get_vendor_statistics(company)
        
        return Response(stats)


class EvaluationCriteriaViewSet(viewsets.ModelViewSet):
    """ViewSet for managing evaluation criteria"""
    queryset = EvaluationCriteria.objects.all()
    serializer_class = EvaluationCriteriaSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAdmin]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'weight', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Filter by tender_id if provided"""
        queryset = EvaluationCriteria.objects.all()
        
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
            
        # Filter by category if provided
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
            
        return queryset

    def perform_create(self, serializer):
        """Create evaluation criteria for a tender"""
        # Get tender from request
        tender_id = self.request.data.get('tender_id')
        if not tender_id:
            raise serializers.ValidationError("tender_id is required")
            
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Verify tender status allows adding criteria
            if tender.status not in ['draft', 'published']:
                raise serializers.ValidationError("Cannot add criteria to closed or awarded tenders")
                
            # Save criteria
            serializer.save(tender=tender)
            
        except Tender.DoesNotExist:
            raise serializers.ValidationError("Tender not found")


class ApprovalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing approvals"""
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter approvals based on user role"""
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
            
        # Apply user role restrictions
        if user.role not in ['staff', 'admin']:
            # Regular users can only see their own approvals
            queryset = queryset.filter(user=user)
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign user to the authenticated user"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def approve(self, request, pk=None):
        """Approve a tender"""
        approval = self.get_object()
        if approval.status == 'pending':
            approval.status = 'approved'
            approval.save()
            
            # Notify the tender creator
            if approval.tender.created_by:
                create_notification(
                    user=approval.tender.created_by,
                    title='Tender Approved',
                    message=f'Your tender {approval.tender.reference_number} has been approved by {approval.user.username}.',
                    notification_type='success',
                    related_entity=approval.tender
                )
                
            return Response({'status': 'approved'})
        return Response({'error': 'approval already processed'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def reject(self, request, pk=None):
        """Reject a tender"""
        approval = self.get_object()
        if approval.status == 'pending':
            # Get comments from request
            comments = request.data.get('comments', '')
            
            approval.status = 'rejected'
            approval.comments = comments
            approval.save()
            
            # Notify the tender creator
            if approval.tender.created_by:
                create_notification(
                    user=approval.tender.created_by,
                    title='Tender Rejected',
                    message=f'Your tender {approval.tender.reference_number} has been rejected by {approval.user.username}. Comments: {comments}',
                    notification_type='warning',
                    related_entity=approval.tender
                )
                
            return Response({'status': 'rejected'})
        return Response({'error': 'approval already processed'},
                        status=status.HTTP_400_BAD_REQUEST)
        # server/aadf/views.py (Part 3) - Continued from previous part

class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing reports"""
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
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign generated_by to the authenticated user"""
        serializer.save(generated_by=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def generate_tender_report(self, request):
        """Generate a report for a specific tender"""
        tender_id = request.data.get('tender_id')
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Generate the report
            report_buffer = generate_tender_report(tender)
            if not report_buffer:
                return Response(
                    {'error': 'Failed to generate report'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
            # Create a report record
            filename = f"tender_report_{tender.reference_number}_{timezone.now().strftime('%Y%m%d%H%M%S')}.pdf"
            file_path = f"reports/{filename}"
            
            # Save the report to storage
            with default_storage.open(file_path, 'wb') as f:
                f.write(report_buffer.read())
                
            # Create the report record
            report = Report.objects.create(
                tender=tender,
                generated_by=request.user,
                report_type='tender_commission',
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
                
            # Return the file
            response = FileResponse(
                file,
                content_type=content_type,
                as_attachment=True,
                filename=report.filename
            )
            
            return response
        except Exception as e:
            logger.error(f"Error downloading report: {str(e)}")
            return Response(
                {'error': f'Download failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notifications"""
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
            
        return queryset

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


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing audit logs"""
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

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])

        return queryset

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get audit log statistics"""
        # Count by entity type
        entity_stats = AuditLog.objects.values('entity_type').annotate(count=Count('entity_type'))
        
        # Count by action
        action_stats = AuditLog.objects.values('action').annotate(count=Count('action'))
        
        # Count by user
        user_stats = AuditLog.objects.values('user__username').annotate(count=Count('user'))
        
        # Recent activity
        recent_activity = AuditLog.objects.select_related('user').order_by('-created_at')[:10].values(
            'id', 'user__username', 'action', 'entity_type', 'entity_id', 'created_at'
        )
        
        stats = {
            'entity_stats': entity_stats,
            'action_stats': action_stats,
            'user_stats': user_stats,
            'recent_activity': recent_activity,
            'total_logs': AuditLog.objects.count()
        }
        
        return Response(stats)


class LoginView(APIView):
    """Handle user login and token generation"""
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'error': 'Please provide both username and password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user:
            if not user.is_active:
                return Response(
                    {'error': 'Account is disabled'},
                    status=status.HTTP_401_UNAUTHORIZED
                )

            # Delete any existing tokens for this user
            Token.objects.filter(user=user).delete()
            
            # Create a new token
            token = Token.objects.create(user=user)
            
            # Log the login action
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
                
            AuditLog.objects.create(
                user=user,
                action='login',
                entity_type='auth',
                entity_id=0,
                details={'method': 'token'},
                ip_address=ip_address
            )
            
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'role': user.role,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            })

        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


class LogoutView(APIView):
    """Handle user logout and token deletion"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            # Log the logout action
            AuditLog.objects.create(
                user=request.user,
                action='logout',
                entity_type='auth',
                entity_id=0,
                details={'method': 'token'},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Delete the user's token
            request.user.auth_token.delete()
            return Response(
                {'message': 'Successfully logged out'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return Response(
                {'error': 'Something went wrong'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RegisterView(APIView):
    """Handle new user registration"""
    permission_classes = []

    def post(self, request):
        # Check if registrations are allowed for this role
        role = request.data.get('role', 'vendor')
        
        # Only vendor registration is allowed without admin approval
        if role != 'vendor' and not request.user.is_authenticated:
            return Response(
                {'error': 'Only vendor registration is allowed without admin approval'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # If staff/admin registration, check if request is from an admin
        if role in ['staff', 'admin'] and (not request.user.is_authenticated or request.user.role != 'admin'):
            return Response(
                {'error': 'Only administrators can create staff or admin accounts'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            # Create the user
            user = serializer.save()
            
            # Generate token for the new user
            token = Token.objects.create(user=user)
            
            # If role is vendor, create a vendor company if requested
            company_name = request.data.get('company_name')
            if role == 'vendor' and company_name:
                company_data = {
                    'name': company_name,
                    'registration_number': request.data.get('registration_number', ''),
                    'email': user.email,
                    'phone': request.data.get('phone', ''),
                    'address': request.data.get('address', '')
                }
                
                vendor_company = VendorCompany.objects.create(**company_data)
                vendor_company.users.add(user)
                
            # Log the registration
            AuditLog.objects.create(
                user=user,
                action='register',
                entity_type='user',
                entity_id=user.id,
                details={'role': role},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Create welcome notification
            create_notification(
                user=user,
                title='Welcome to AADF Procurement Platform',
                message='Thank you for registering. Your account has been created successfully.',
                notification_type='info'
            )
            
            # Notify admins about new vendor registration
            if role == 'vendor':
                admin_users = User.objects.filter(role='admin', is_active=True)
                for admin_user in admin_users:
                    create_notification(
                        user=admin_user,
                        title='New Vendor Registration',
                        message=f'A new vendor user {user.username} has registered.',
                        notification_type='info',
                        related_entity=user
                    )

            return Response({
                'user': serializer.data,
                'token': token.key
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """Handle password change for authenticated users"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'error': 'Both old and new passwords are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate new password
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        # Update token after password change
        user.auth_token.delete()
        token = Token.objects.create(user=user)
        
        # Log the password change
        AuditLog.objects.create(
            user=user,
            action='change_password',
            entity_type='user',
            entity_id=user.id,
            details={},
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Create notification
        create_notification(
            user=user,
            title='Password Changed',
            message='Your password has been changed successfully.',
            notification_type='info'
        )

        return Response({
            'message': 'Password changed successfully',
            'token': token.key
        }, status=status.HTTP_200_OK)


class DocumentDownloadView(APIView):
    """Handle secure file downloads"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_type, document_id):
        # Check for secure download if using a signed URL
        expires = request.query_params.get('expires')
        signature = request.query_params.get('signature')
        
        if expires and signature:
            from .utils import verify_document_signature
            
            if not verify_document_signature(document_type, document_id, expires, signature):
                return Response(
                    {'error': 'Invalid or expired download link'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
        try:
            if document_type == 'tender':
                document = get_object_or_404(TenderDocument, id=document_id)
                
                # Check if user has permission to download this tender document
                # Only staff, admin, or vendors for published tenders can download
                if request.user.role == 'vendor' and document.tender.status != 'published':
                    return Response(
                        {'error': 'You do not have permission to download this document'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                    
            elif document_type == 'offer':
                document = get_object_or_404(OfferDocument, id=document_id)
                
                # Check if user has permission to download this offer document
                if request.user.role == 'vendor':
                    # Vendors can only download their own offer documents
                    if not document.offer.vendor.users.filter(id=request.user.id).exists():
                        return Response(
                            {'error': 'You do not have permission to download this document'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                elif request.user.role == 'evaluator':
                    # Evaluators can only download documents for closed or awarded tenders
                    if document.offer.tender.status not in ['closed', 'awarded']:
                        return Response(
                            {'error': 'You do not have permission to download this document'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                        
            elif document_type == 'report':
                document = get_object_or_404(Report, id=document_id)
                
                # Only staff and admin can download reports
                if request.user.role not in ['staff', 'admin']:
                    return Response(
                        {'error': 'You do not have permission to download this report'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                    
            else:
                return Response(
                    {'error': 'Invalid document type'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_path = document.file_path
            if default_storage.exists(file_path):
                file = default_storage.open(file_path, 'rb')
                
                # Determine content type
                content_type = document.mime_type if hasattr(document, 'mime_type') else 'application/octet-stream'
                
                # Create response
                response = FileResponse(file, content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename="{document.original_filename}"'
                
                # Log the download
                AuditLog.objects.create(
                    user=request.user,
                    action='download',
                    entity_type=document_type,
                    entity_id=document_id,
                    details={'filename': document.original_filename},
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                
                return response
            else:
                raise Http404("File not found")

        except (TenderDocument.DoesNotExist, OfferDocument.DoesNotExist, Report.DoesNotExist):
            raise Http404("Document not found")
        except Exception as e:
            logger.error(f"Error downloading document: {str(e)}")
            return Response(
                {'error': f'Download failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserProfileView(APIView):
    """Handle user profile operations"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get authenticated user's profile"""
        user = request.user
        serializer = UserSerializer(user)
        
        # Add extra information based on user role
        data = serializer.data
        
        if user.role == 'vendor':
            # Get vendor companies for this user
            companies = VendorCompany.objects.filter(users=user)
            data['companies'] = VendorCompanySerializer(companies, many=True).data
            
        # Get notification counts
        data['unread_notifications'] = Notification.objects.filter(user=user, is_read=False).count()
        
        return Response(data)

    def put(self, request):
        """Update authenticated user's profile"""
        user = request.user
        
        # Prevent role change through profile update unless by admin
        if 'role' in request.data and user.role != 'admin':
            return Response(
                {'error': 'Role cannot be changed through profile update'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Log the profile update
            AuditLog.objects.create(
                user=user,
                action='update_profile',
                entity_type='user',
                entity_id=user.id,
                details={},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardView(APIView):
    """Dashboard data endpoint"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get dashboard statistics based on user role"""
        user = request.user
        data = {}

        if user.role in ['admin', 'staff']:
            # Get comprehensive dashboard data for staff/admin
            data = get_dashboard_statistics()
            
            # Add user-specific information
            data['user'] = {
                'created_tenders': Tender.objects.filter(created_by=user).count(),
                'unread_notifications': Notification.objects.filter(user=user, is_read=False).count(),
                'recent_activity': AuditLog.objects.filter(user=user).order_by('-created_at')[:5].values(
                    'action', 'entity_type', 'entity_id', 'created_at'
                )
            }
            
        elif user.role == 'vendor':
            # Get vendor companies for this user
            vendor_companies = VendorCompany.objects.filter(users=user)
            
            if vendor_companies.exists():
                # Get offers for all companies
                offers = Offer.objects.filter(vendor__in=vendor_companies)
                
                data.update({
                    'offers': {
                        'total': offers.count(),
                        'draft': offers.filter(status='draft').count(),
                        'submitted': offers.filter(status='submitted').count(),
                        'evaluated': offers.filter(status='evaluated').count(),
                        'awarded': offers.filter(status='awarded').count(),
                        'rejected': offers.filter(status='rejected').count(),
                    },
                    'tenders': {
                        'published': Tender.objects.filter(status='published').count(),
                        'participated': Tender.objects.filter(offers__vendor__in=vendor_companies).distinct().count(),
                        'won': Tender.objects.filter(offers__vendor__in=vendor_companies, offers__status='awarded').distinct().count()
                    },
                    'companies': VendorCompanySerializer(vendor_companies, many=True).data,
                    'recent_offers': offers.order_by('-created_at')[:5].values(
                        'id', 'tender__reference_number', 'tender__title', 'status', 'submitted_at'
                    ),
                    'recent_tenders': Tender.objects.filter(status='published').order_by('-published_at')[:5].values(
                        'id', 'reference_number', 'title', 'submission_deadline'
                    ),
                    'unread_notifications': Notification.objects.filter(user=user, is_read=False).count()
                })
            else:
                # No company associated with this vendor
                data.update({
                    'offers': {
                        'total': 0,
                        'draft': 0,
                        'submitted': 0,
                        'evaluated': 0,
                        'awarded': 0,
                        'rejected': 0,
                    },
                    'tenders': {
                        'published': Tender.objects.filter(status='published').count(),
                        'participated': 0,
                        'won': 0
                    },
                    'companies': [],
                    'recent_tenders': Tender.objects.filter(status='published').order_by('-published_at')[:5].values(
                        'id', 'reference_number', 'title', 'submission_deadline'
                    ),
                    'unread_notifications': Notification.objects.filter(user=user, is_read=False).count(),
                    'warning': 'No vendor company associated with your account. Please contact an administrator.'
                })
                
        elif user.role == 'evaluator':
            # Get data for evaluator
            data.update({
                'tenders': {
                    'total_to_evaluate': Tender.objects.filter(status__in=['closed', 'awarded']).count(),
                    'evaluated': Tender.objects.filter(
                        status__in=['closed', 'awarded'],
                        offers__evaluations__evaluator=user
                    ).distinct().count()
                },
                'evaluations': {
                    'completed': Evaluation.objects.filter(evaluator=user).count(),
                    'recent': Evaluation.objects.filter(evaluator=user).order_by('-created_at')[:5].values(
                        'id', 'offer__tender__reference_number', 'criteria__name', 'score', 'created_at'
                    )
                },
                'pending_evaluations': Offer.objects.filter(
                    tender__status__in=['closed', 'awarded']
                ).exclude(
                    evaluations__evaluator=user
                ).count(),
                'recent_tenders': Tender.objects.filter(status__in=['closed', 'awarded']).order_by('-updated_at')[:5].values(
                    'id', 'reference_number', 'title', 'status'
                ),
                'unread_notifications': Notification.objects.filter(user=user, is_read=False).count()
            })

        return Response(data)


class TenderSearchView(APIView):
    """Search tenders endpoint"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Search tenders with various filters"""
        queryset = Tender.objects.all()

        # Filter by status
        status_param = request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        # Filter by category
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)

        # Search in title and description
        search_query = request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(reference_number__icontains=search_query)
            )

        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])
            
        # Filter by deadline - before or after a date
        deadline_before = request.query_params.get('deadline_before')
        if deadline_before:
            queryset = queryset.filter(submission_deadline__lte=deadline_before)
            
        deadline_after = request.query_params.get('deadline_after')
        if deadline_after:
            queryset = queryset.filter(submission_deadline__gte=deadline_after)

        # Apply user role restrictions
        if request.user.role == 'vendor':
            queryset = queryset.filter(status='published')
            
        # Get participation status for vendor
        if request.user.role == 'vendor':
            # Get vendor companies for this user
            vendor_companies = VendorCompany.objects.filter(users=request.user)
            
            # Get tenders where the vendor has submitted offers
            participated_tenders = Tender.objects.filter(offers__vendor__in=vendor_companies).values_list('id', flat=True)
            
            # Add participation flag to each tender
            results = []
            for tender in queryset:
                tender_data = TenderSerializer(tender).data
                tender_data['has_participated'] = tender.id in participated_tenders
                results.append(tender_data)
        else:
            # For other roles, just return the serialized tenders
            results = TenderSerializer(queryset, many=True).data

        return Response(results)


class UserManagementView(APIView):
    """User management endpoints for admins"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        """Get all users"""
        users = User.objects.all()
        
        # Filter by role if provided
        role = request.query_params.get('role')
        if role:
            users = users.filter(role=role)
            
        # Filter by active status if provided
        is_active = request.query_params.get('is_active')
        if is_active is not None:
            users = users.filter(is_active=(is_active.lower() == 'true'))
            
        # Search by username or email
        search = request.query_params.get('search')
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
            
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        """Create a new user"""
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Log the user creation
            AuditLog.objects.create(
                user=request.user,
                action='create_user',
                entity_type='user',
                entity_id=user.id,
                details={'role': user.role},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, user_id):
        """Update a user"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Log the user update
            AuditLog.objects.create(
                user=request.user,
                action='update_user',
                entity_type='user',
                entity_id=user.id,
                details={},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id):
        """Deactivate a user (not hard delete)"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Don't allow deactivating yourself
        if user.id == request.user.id:
            return Response(
                {'error': 'You cannot deactivate your own account'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Deactivate user instead of deleting
        user.is_active = False
        user.save()
        
        # Log the user deactivation
        AuditLog.objects.create(
            user=request.user,
            action='deactivate_user',
            entity_type='user',
            entity_id=user.id,
            details={},
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def reset_password(self, request, user_id):
        """Reset a user's password"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        new_password = request.data.get('new_password')
        if not new_password:
            return Response(
                {'error': 'New password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate new password
        if len(new_password) < 8:
            return Response(
                {'error': 'Password must be at least 8 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        user.set_password(new_password)
        user.save()
        
        # Log the password reset
        AuditLog.objects.create(
            user=request.user,
            action='reset_password',
            entity_type='user',
            entity_id=user.id,
            details={},
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Create notification for the user
        create_notification(
            user=user,
            title='Password Reset',
            message='Your password has been reset by an administrator. Please login with your new password.',
            notification_type='warning'
        )
        
        return Response({'message': 'Password reset successful'})