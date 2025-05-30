# server/aadf/views/document_views.py

from django.http import FileResponse, Http404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.conf import settings

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

import os
import uuid
import logging
import json

from ..models import (
    User, Tender, TenderDocument, Offer, OfferDocument, Report, AuditLog,
    DocumentVersion
)
from ..serializers import TenderDocumentSerializer, OfferDocumentSerializer
from ..permissions import (
    IsStaffOrAdmin, IsVendor, CanManageOwnOffers, CanViewOwnDocuments
)
from ..utils import (
    validate_file_extension, validate_file_size, 
    generate_secure_document_link, verify_document_signature
)

logger = logging.getLogger('aadf')


class TenderDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for handling tender document uploads with version control"""
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
        """Handle document upload with version control"""
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
            
        # Check if this is a new version of an existing document
        existing_document_id = request.data.get('document_id')
        change_description = request.data.get('change_description', '')
        
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
            
            if existing_document_id:
                # This is a new version of an existing document
                try:
                    existing_document = TenderDocument.objects.get(
                        id=existing_document_id,
                        tender=tender
                    )
                    
                    # Get the current version number
                    current_version = DocumentVersion.objects.filter(
                        document_type='tender',
                        document_id=existing_document.id
                    ).order_by('-version_number').first()
                    
                    version_number = 1
                    if current_version:
                        version_number = current_version.version_number + 1
                    
                    # Create a version record for the previous state if this is the first version
                    if version_number == 1:
                        DocumentVersion.objects.create(
                            document_type='tender',
                            document_id=existing_document.id,
                            original_filename=existing_document.original_filename,
                            filename=existing_document.filename,
                            file_path=existing_document.file_path,
                            file_size=existing_document.file_size,
                            mime_type=existing_document.mime_type,
                            version_number=version_number,
                            created_by=existing_document.uploaded_by,
                            created_at=existing_document.created_at,
                            change_description="Initial version"
                        )
                        version_number = 2
                    
                    # Create new version record
                    DocumentVersion.objects.create(
                        document_type='tender',
                        document_id=existing_document.id,
                        original_filename=file.name,
                        filename=filename,
                        file_path=file_path,
                        file_size=file.size,
                        mime_type=file.content_type,
                        version_number=version_number,
                        created_by=request.user,
                        change_description=change_description
                    )
                    
                    # Update the existing document record
                    existing_document.original_filename = file.name
                    existing_document.filename = filename
                    existing_document.file_path = file_path
                    existing_document.file_size = file.size
                    existing_document.mime_type = file.content_type
                    existing_document.uploaded_by = request.user
                    existing_document.save()
                    
                    # Log the update
                    AuditLog.objects.create(
                        user=request.user,
                        action='update_tender_document',
                        entity_type='tender_document',
                        entity_id=existing_document.id,
                        details={
                            'tender_id': tender.id,
                            'tender_reference': tender.reference_number,
                            'version': version_number,
                            'filename': file.name
                        },
                        ip_address=request.META.get('REMOTE_ADDR', '')
                    )
                    
                    serializer = self.get_serializer(existing_document)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                    
                except TenderDocument.DoesNotExist:
                    return Response(
                        {'error': 'Existing document not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
                # Create new document record
                document = TenderDocument.objects.create(
                    tender=tender,
                    uploaded_by=request.user,
                    original_filename=file.name,
                    filename=filename,
                    file_path=file_path,
                    file_size=file.size,
                    mime_type=file.content_type
                )
                
                # Log the creation
                AuditLog.objects.create(
                    user=request.user,
                    action='create_tender_document',
                    entity_type='tender_document',
                    entity_id=document.id,
                    details={
                        'tender_id': tender.id,
                        'tender_reference': tender.reference_number,
                        'filename': file.name
                    },
                    ip_address=request.META.get('REMOTE_ADDR', '')
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
                
            # Delete all version records
            DocumentVersion.objects.filter(
                document_type='tender',
                document_id=document.id
            ).delete()
                
            # Log the deletion
            AuditLog.objects.create(
                user=request.user,
                action='delete_tender_document',
                entity_type='tender_document',
                entity_id=document.id,
                details={
                    'tender_id': document.tender.id,
                    'tender_reference': document.tender.reference_number,
                    'filename': document.original_filename
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Delete the document record
            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting tender document: {str(e)}")
            return Response(
                {'error': f'Deletion failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get all versions of a document"""
        document = self.get_object()
        
        versions = DocumentVersion.objects.filter(
            document_type='tender',
            document_id=document.id
        ).order_by('-version_number')
        
        return Response([
            {
                'version_number': v.version_number,
                'original_filename': v.original_filename,
                'file_size': v.file_size,
                'created_by': v.created_by.username if v.created_by else None,
                'created_at': v.created_at,
                'change_description': v.change_description
            }
            for v in versions
        ])

    @action(detail=True, methods=['get'])
    def version(self, request, pk=None):
        """Get a specific version of a document"""
        document = self.get_object()
        
        version_number = request.query_params.get('version')
        if not version_number:
            return Response(
                {'error': 'version parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            version = DocumentVersion.objects.get(
                document_type='tender',
                document_id=document.id,
                version_number=version_number
            )
            
            # Create a download URL for this version
            file_path = version.file_path
            if default_storage.exists(file_path):
                file = default_storage.open(file_path, 'rb')
                
                # Create response
                response = FileResponse(
                    file, 
                    content_type=version.mime_type or 'application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{version.original_filename}"'
                
                # Log the download
                AuditLog.objects.create(
                    user=request.user,
                    action='download_tender_document_version',
                    entity_type='tender_document',
                    entity_id=document.id,
                    details={
                        'version_number': version.version_number,
                        'filename': version.original_filename
                    },
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                
                return response
            else:
                return Response(
                    {'error': 'Version file not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except DocumentVersion.DoesNotExist:
            return Response(
                {'error': 'Version not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class OfferDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for handling offer document uploads with version control"""
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
        """Handle document upload with version control"""
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
        
        # Check if this is a new version of an existing document
        existing_document_id = request.data.get('document_id')
        change_description = request.data.get('change_description', '')
        
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
            
            if existing_document_id:
                # This is a new version of an existing document
                try:
                    existing_document = OfferDocument.objects.get(
                        id=existing_document_id,
                        offer=offer
                    )
                    
                    # Get the current version number
                    current_version = DocumentVersion.objects.filter(
                        document_type='offer',
                        document_id=existing_document.id
                    ).order_by('-version_number').first()
                    
                    version_number = 1
                    if current_version:
                        version_number = current_version.version_number + 1
                    
                    # Create a version record for the previous state if this is the first version
                    if version_number == 1:
                        DocumentVersion.objects.create(
                            document_type='offer',
                            document_id=existing_document.id,
                            original_filename=existing_document.original_filename,
                            filename=existing_document.filename,
                            file_path=existing_document.file_path,
                            file_size=existing_document.file_size,
                            mime_type=existing_document.mime_type,
                            version_number=version_number,
                            created_by=request.user,
                            created_at=existing_document.created_at,
                            change_description="Initial version"
                        )
                        version_number = 2
                    
                    # Create new version record
                    DocumentVersion.objects.create(
                        document_type='offer',
                        document_id=existing_document.id,
                        original_filename=file.name,
                        filename=filename,
                        file_path=file_path,
                        file_size=file.size,
                        mime_type=file.content_type,
                        version_number=version_number,
                        created_by=request.user,
                        change_description=change_description
                    )
                    
                    # Update the existing document record
                    existing_document.original_filename = file.name
                    existing_document.filename = filename
                    existing_document.file_path = file_path
                    existing_document.file_size = file.size
                    existing_document.mime_type = file.content_type
                    existing_document.save()
                    
                    # Log the update
                    AuditLog.objects.create(
                        user=request.user,
                        action='update_offer_document',
                        entity_type='offer_document',
                        entity_id=existing_document.id,
                        details={
                            'offer_id': offer.id,
                            'tender_reference': offer.tender.reference_number,
                            'vendor_name': offer.vendor.name,
                            'version': version_number,
                            'filename': file.name
                        },
                        ip_address=request.META.get('REMOTE_ADDR', '')
                    )
                    
                    serializer = self.get_serializer(existing_document)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                    
                except OfferDocument.DoesNotExist:
                    return Response(
                        {'error': 'Existing document not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            else:
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
                
                # Log the creation
                AuditLog.objects.create(
                    user=request.user,
                    action='create_offer_document',
                    entity_type='offer_document',
                    entity_id=document.id,
                    details={
                        'offer_id': offer.id,
                        'tender_reference': offer.tender.reference_number,
                        'vendor_name': offer.vendor.name,
                        'filename': file.name
                    },
                    ip_address=request.META.get('REMOTE_ADDR', '')
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
                
            # Delete all version records
            DocumentVersion.objects.filter(
                document_type='offer',
                document_id=document.id
            ).delete()
            
            # Log the deletion
            AuditLog.objects.create(
                user=request.user,
                action='delete_offer_document',
                entity_type='offer_document',
                entity_id=document.id,
                details={
                    'offer_id': document.offer.id,
                    'tender_reference': document.offer.tender.reference_number,
                    'vendor_name': document.offer.vendor.name,
                    'filename': document.original_filename
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
                
            # Delete the document record
            document.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting offer document: {str(e)}")
            return Response(
                {'error': f'Deletion failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Get all versions of a document"""
        document = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not document.offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to view this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        versions = DocumentVersion.objects.filter(
            document_type='offer',
            document_id=document.id
        ).order_by('-version_number')
        
        return Response([
            {
                'version_number': v.version_number,
                'original_filename': v.original_filename,
                'file_size': v.file_size,
                'created_by': v.created_by.username if v.created_by else None,
                'created_at': v.created_at,
                'change_description': v.change_description
            }
            for v in versions
        ])

    @action(detail=True, methods=['get'])
    def version(self, request, pk=None):
        """Get a specific version of a document"""
        document = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not document.offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to view this document'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        version_number = request.query_params.get('version')
        if not version_number:
            return Response(
                {'error': 'version parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            version = DocumentVersion.objects.get(
                document_type='offer',
                document_id=document.id,
                version_number=version_number
            )
            
            # Create a download URL for this version
            file_path = version.file_path
            if default_storage.exists(file_path):
                file = default_storage.open(file_path, 'rb')
                
                # Create response
                response = FileResponse(
                    file, 
                    content_type=version.mime_type or 'application/octet-stream'
                )
                response['Content-Disposition'] = f'attachment; filename="{version.original_filename}"'
                
                # Log the download
                AuditLog.objects.create(
                    user=request.user,
                    action='download_offer_document_version',
                    entity_type='offer_document',
                    entity_id=document.id,
                    details={
                        'version_number': version.version_number,
                        'filename': version.original_filename,
                        'offer_id': document.offer.id,
                        'vendor_name': document.offer.vendor.name
                    },
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                
                return response
            else:
                return Response(
                    {'error': 'Version file not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except DocumentVersion.DoesNotExist:
            return Response(
                {'error': 'Version not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    @action(detail=True, methods=['post'])
    def compare_versions(self, request, pk=None):
        """Compare two versions of a document"""
        document = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not document.offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to view this document'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        version1 = request.data.get('version1')
        version2 = request.data.get('version2')
        
        if not version1 or not version2:
            return Response(
                {'error': 'Both version1 and version2 are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            v1 = DocumentVersion.objects.get(
                document_type='offer' if hasattr(document, 'offer') else 'tender',
                document_id=document.id,
                version_number=version1
            )
            
            v2 = DocumentVersion.objects.get(
                document_type='offer' if hasattr(document, 'offer') else 'tender',
                document_id=document.id,
                version_number=version2
            )
            
            # Get basic comparison details
            comparison = {
                'version1': {
                    'version_number': v1.version_number,
                    'original_filename': v1.original_filename,
                    'file_size': v1.file_size,
                    'created_by': v1.created_by.username if v1.created_by else None,
                    'created_at': v1.created_at,
                    'change_description': v1.change_description
                },
                'version2': {
                    'version_number': v2.version_number,
                    'original_filename': v2.original_filename,
                    'file_size': v2.file_size,
                    'created_by': v2.created_by.username if v2.created_by else None,
                    'created_at': v2.created_at,
                    'change_description': v2.change_description
                },
                'size_difference': v2.file_size - v1.file_size if v1.file_size and v2.file_size else None
            }
            
            # Log the comparison
            AuditLog.objects.create(
                user=request.user,
                action='compare_document_versions',
                entity_type='offer_document' if hasattr(document, 'offer') else 'tender_document',
                entity_id=document.id,
                details={
                    'version1': v1.version_number,
                    'version2': v2.version_number,
                    'filename': document.original_filename
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response(comparison)
        except DocumentVersion.DoesNotExist:
            return Response(
                {'error': 'One or both versions not found'},
                status=status.HTTP_404_NOT_FOUND
            )


class DocumentDownloadView(APIView):
    """Unified document download handler with enhanced security"""
    permission_classes = []  # Set explicitly in get() method based on authentication type

    def get(self, request, document_type, document_id):
        """
        Handle document download requests with support for both:
        1. Direct authenticated downloads
        2. Secure link downloads with signature verification
        """
        # Check for secure download signature
        expires = request.query_params.get('expires')
        signature = request.query_params.get('signature')
        
        # Determine authentication method
        if expires and signature:
            # Secure link authentication
            if not verify_document_signature(document_type, document_id, expires, signature):
                return Response(
                    {'error': 'Invalid or expired download link'},
                    status=status.HTTP_403_FORBIDDEN
                )
            authenticated_by_signature = True
        else:
            # Standard authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            authenticated_by_signature = False
                
        try:
            # Handle different document types
            if document_type == 'tender':
                document = get_object_or_404(TenderDocument, id=document_id)
                
                # Check permissions for tender documents
                if not authenticated_by_signature:
                    # Staff and admin can access all tender documents
                    if request.user.role in ['staff', 'admin']:
                        pass  # Full access
                    # Vendors can only access documents for published tenders
                    elif request.user.role == 'vendor' and document.tender.status != 'published':
                        return Response(
                            {'error': 'You do not have permission to download this document'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    # Evaluators can only access documents for closed/awarded tenders
                    elif request.user.role == 'evaluator' and document.tender.status not in ['closed', 'awarded']:
                        return Response(
                            {'error': 'You do not have permission to download this document'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    
            elif document_type == 'offer':
                document = get_object_or_404(OfferDocument, id=document_id)
                
                # Check permissions for offer documents
                if not authenticated_by_signature:
                    # Staff and admin can access all offer documents
                    if request.user.role in ['staff', 'admin']:
                        pass  # Full access
                    # Vendors can only access their own offer documents
                    elif request.user.role == 'vendor':
                        if not document.offer.vendor.users.filter(id=request.user.id).exists():
                            return Response(
                                {'error': 'You do not have permission to download this document'},
                                status=status.HTTP_403_FORBIDDEN
                            )
                    # Evaluators can only access documents for closed/awarded tenders
                    elif request.user.role == 'evaluator':
                        if document.offer.tender.status not in ['closed', 'awarded']:
                            return Response(
                                {'error': 'You do not have permission to download this document'},
                                status=status.HTTP_403_FORBIDDEN
                            )
                        
            elif document_type == 'report':
                document = get_object_or_404(Report, id=document_id)
                
                # Check permissions for reports
                if not authenticated_by_signature and request.user.role not in ['staff', 'admin']:
                    return Response(
                        {'error': 'You do not have permission to download this report'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                    
            else:
                return Response(
                    {'error': 'Invalid document type'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Process the file download
            file_path = document.file_path
            if not default_storage.exists(file_path):
                raise Http404("File not found")
                
            file = default_storage.open(file_path, 'rb')
            
            # Determine content type based on file extension or MIME type
            content_type = self._get_content_type(document)
            
            # Create download response
            response = FileResponse(file, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{document.original_filename}"'
            
            # Log the download
            if request.user.is_authenticated:
                # Authenticated download
                AuditLog.objects.create(
                    user=request.user,
                    action='download_document',
                    entity_type=document_type,
                    entity_id=document_id,
                    details={
                        'filename': document.original_filename,
                        'authenticated': True
                    },
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
            else:
                # Anonymous download via secure link
                AuditLog.objects.create(
                    user=None,
                    action='download_document_secure_link',
                    entity_type=document_type,
                    entity_id=document_id,
                    details={
                        'filename': document.original_filename,
                        'authenticated': False,
                        'secure_link': True
                    },
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
            
            return response

        except Http404:
            raise Http404("Document not found")
        except Exception as e:
            logger.error(f"Error downloading document: {str(e)}")
            return Response(
                {'error': f'Download failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_content_type(self, document):
        """Determine the content type based on file extension or MIME type"""
        # Use the document's MIME type if available
        if hasattr(document, 'mime_type') and document.mime_type:
            return document.mime_type
            
        # Otherwise determine from filename
        filename = document.original_filename.lower()
        _, ext = os.path.splitext(filename)
        
        # Map extensions to MIME types
        mime_types = settings.DOCUMENT_MIME_TYPES if hasattr(settings, 'DOCUMENT_MIME_TYPES') else {
            '.pdf': 'application/pdf',
            '.doc': 'application/msword',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xls': 'application/vnd.ms-excel',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.ppt': 'application/vnd.ms-powerpoint',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.csv': 'text/csv',
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.zip': 'application/zip',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif'
        }
        
        # Return the MIME type or a default
        return mime_types.get(ext, 'application/octet-stream')


class SecureDownloadLinkView(APIView):
    """Generate secure download links for documents"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, document_type, document_id):
        """Generate a secure download link"""
        try:
            # Determine document model based on type
            if document_type == 'tender':
                document = get_object_or_404(TenderDocument, id=document_id)
                
                # Check permissions
                if request.user.role not in ['staff', 'admin']:
                    if document.tender.status != 'published':
                        return Response(
                            {'error': 'You do not have permission to access this document'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    
            elif document_type == 'offer':
                document = get_object_or_404(OfferDocument, id=document_id)
                
                # Check permissions
                if request.user.role == 'vendor':
                    if not document.offer.vendor.users.filter(id=request.user.id).exists():
                        return Response(
                            {'error': 'You do not have permission to access this document'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                elif request.user.role == 'evaluator':
                    if document.offer.tender.status not in ['closed', 'awarded']:
                        return Response(
                            {'error': 'You do not have permission to access this document'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                        
            elif document_type == 'report':
                document = get_object_or_404(Report, id=document_id)
                
                # Check permissions
                if request.user.role not in ['staff', 'admin']:
                    return Response(
                        {'error': 'You do not have permission to access this report'},
                        status=status.HTTP_403_FORBIDDEN
                    )
                    
            else:
                return Response(
                    {'error': 'Invalid document type'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get expiration time from query params or use default
            expires_in_minutes = int(request.query_params.get('expires_in', 
                settings.SECURE_DOCUMENT_DOWNLOAD.get('DEFAULT_EXPIRY_MINUTES', 60) 
                if hasattr(settings, 'SECURE_DOCUMENT_DOWNLOAD') else 60))
            
            # Generate download URL
            download_url = generate_secure_document_link(document, expires_in_minutes=expires_in_minutes)
            
            if not download_url:
                return Response(
                    {'error': 'Failed to generate download link'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
            # Log the link generation
            AuditLog.objects.create(
                user=request.user,
                action='generate_download_link',
                entity_type=document_type,
                entity_id=document_id,
                details={
                    'filename': document.original_filename,
                    'expires_in_minutes': expires_in_minutes
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Return the secure download link
            return Response({
                'download_url': download_url,
                'expires_in': f'{expires_in_minutes} minutes',
                'filename': document.original_filename
            })
            
        except Http404:
            return Response(
                {'error': 'Document not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Error generating secure download link: {str(e)}")
            return Response(
                {'error': f'Failed to generate link: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )