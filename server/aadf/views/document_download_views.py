# server/aadf/views/document_download_views.py

from django.http import FileResponse, Http404
from django.core.files.storage import default_storage
from django.shortcuts import get_object_or_404
from django.conf import settings

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action

import os
import logging

from ..models import (
    TenderDocument, OfferDocument, Report, AuditLog
)
from ..utils import generate_secure_document_link, verify_document_signature

logger = logging.getLogger('aadf')

class DocumentDownloadView(APIView):
    """Handle secure file downloads"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_type, document_id):
        """
        Handle document download requests
        
        This view supports two modes:
        1. Direct download with authentication check and permission verification
        2. Secure link download with signature verification
        """
        # Check for secure download if using a signed URL
        expires = request.query_params.get('expires')
        signature = request.query_params.get('signature')
        
        if expires and signature:
            # Verify the signature
            if not verify_document_signature(document_type, document_id, expires, signature):
                return Response(
                    {'error': 'Invalid or expired download link'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # If signature is valid, allow access without permission check
            authenticated_by_signature = True
        else:
            # If no signature provided, require authentication
            if not request.user.is_authenticated:
                return Response(
                    {'error': 'Authentication required'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            authenticated_by_signature = False
                
        try:
            if document_type == 'tender':
                document = get_object_or_404(TenderDocument, id=document_id)
                
                # Check if user has permission to download this tender document
                if not authenticated_by_signature:
                    # Only staff, admin, or vendors for published tenders can download
                    if request.user.role == 'vendor' and document.tender.status != 'published':
                        return Response(
                            {'error': 'You do not have permission to download this document'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    
            elif document_type == 'offer':
                document = get_object_or_404(OfferDocument, id=document_id)
                
                # Check if user has permission to download this offer document
                if not authenticated_by_signature:
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

            file_path = document.file_path
            if not default_storage.exists(file_path):
                raise Http404("File not found")
                
            file = default_storage.open(file_path, 'rb')
            
            # Determine content type based on file extension
            content_type = self._get_content_type(document)
            
            # Create response
            response = FileResponse(file, content_type=content_type)
            response['Content-Disposition'] = f'attachment; filename="{document.original_filename}"'
            
            # Log the download if authenticated
            if request.user.is_authenticated:
                AuditLog.objects.create(
                    user=request.user,
                    action='download',
                    entity_type=document_type,
                    entity_id=document_id,
                    details={'filename': document.original_filename},
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
            else:
                # Anonymous download via secure link
                AuditLog.objects.create(
                    user=None,
                    action='download_secure_link',
                    entity_type=document_type,
                    entity_id=document_id,
                    details={'filename': document.original_filename},
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
        """Determine the content type based on file extension"""
        filename = document.original_filename.lower()
        
        # Get file extension
        _, ext = os.path.splitext(filename)
        
        # Map extensions to MIME types
        mime_types = {
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
    """Create secure download links for documents"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, document_type, document_id):
        """Generate a secure download link"""
        try:
            # Determine document model based on type
            if document_type == 'tender':
                document = get_object_or_404(TenderDocument, id=document_id)
                
                # Check permissions
                if request.user.role == 'vendor' and document.tender.status != 'published':
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
            expires_in_minutes = int(request.query_params.get('expires_in', 60))
            
            # Generate download URL
            base_url = f"{request.scheme}://{request.get_host()}"
            download_url = generate_secure_document_link(
                document, 
                expires_in_minutes=expires_in_minutes,
                base_url=base_url
            )
            
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