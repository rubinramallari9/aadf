from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.http import FileResponse, Http404
import os
import uuid

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
from .permissions import IsStaffOrAdmin, IsVendor, IsEvaluator


class TenderViewSet(viewsets.ModelViewSet):
    """ViewSet for managing tenders"""
    queryset = Tender.objects.all()
    serializer_class = TenderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TenderDetailSerializer
        return TenderSerializer

    def get_queryset(self):
        """Filter tenders based on user role"""
        user = self.request.user
        if user.role == 'vendor':
            return Tender.objects.filter(status='published')
        return Tender.objects.all()

    def perform_create(self, serializer):
        """Auto-assign created_by and generate reference number"""
        serializer.save(
            created_by=self.request.user,
            reference_number=self.generate_reference_number()
        )

    def generate_reference_number(self):
        """Generate unique reference number for tender"""
        return f"TND-{uuid.uuid4().hex[:8].upper()}"

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def publish(self, request, pk=None):
        """Publish a tender"""
        tender = self.get_object()
        if tender.status == 'draft':
            tender.status = 'published'
            tender.published_at = timezone.now()
            tender.save()
            return Response({'status': 'tender published'})
        return Response({'error': 'tender cannot be published'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def close(self, request, pk=None):
        """Close a tender"""
        tender = self.get_object()
        if tender.status == 'published' and tender.submission_deadline < timezone.now():
            tender.status = 'closed'
            tender.save()
            return Response({'status': 'tender closed'})
        return Response({'error': 'tender cannot be closed'},
                        status=status.HTTP_400_BAD_REQUEST)


class OfferViewSet(viewsets.ModelViewSet):
    """ViewSet for managing offers"""
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return OfferDetailSerializer
        return OfferSerializer

    def get_queryset(self):
        """Filter offers based on user role"""
        user = self.request.user
        if user.role == 'vendor':
            return Offer.objects.filter(vendor__users=user)
        return Offer.objects.all()

    def perform_create(self, serializer):
        """Auto-assign submitted_by and vendor"""
        vendor_company = VendorCompany.objects.filter(users=self.request.user).first()
        if not vendor_company and self.request.user.role == 'vendor':
            raise serializers.ValidationError("User must be associated with a vendor company")

        serializer.save(
            submitted_by=self.request.user,
            vendor=vendor_company if self.request.user.role == 'vendor' else None
        )

    @action(detail=True, methods=['post'], permission_classes=[IsVendor])
    def submit(self, request, pk=None):
        """Submit an offer"""
        offer = self.get_object()
        if offer.status == 'draft' and offer.tender.status == 'published':
            offer.status = 'submitted'
            offer.submitted_at = timezone.now()
            offer.save()
            return Response({'status': 'offer submitted'})
        return Response({'error': 'offer cannot be submitted'},
                        status=status.HTTP_400_BAD_REQUEST)


class TenderDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for handling tender document uploads"""
    queryset = TenderDocument.objects.all()
    serializer_class = TenderDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        file = self.request.FILES.get('file')
        if file:
            # Generate a unique filename
            ext = os.path.splitext(file.name)[1]
            filename = f"{uuid.uuid4()}{ext}"

            # Save the file
            file_path = default_storage.save(
                f'tender_documents/{filename}',
                ContentFile(file.read())
            )

            # Save the document record
            serializer.save(
                uploaded_by=self.request.user,
                original_filename=file.name,
                filename=filename,
                file_path=file_path,
                file_size=file.size,
                mime_type=file.content_type
            )


class OfferDocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for handling offer document uploads"""
    queryset = OfferDocument.objects.all()
    serializer_class = OfferDocumentSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter documents based on user role"""
        if self.request.user.role == 'vendor':
            return OfferDocument.objects.filter(offer__vendor__users=self.request.user)
        return OfferDocument.objects.all()

    def perform_create(self, serializer):
        file = self.request.FILES.get('file')
        if file:
            # Generate a unique filename
            ext = os.path.splitext(file.name)[1]
            filename = f"{uuid.uuid4()}{ext}"

            # Save the file
            file_path = default_storage.save(
                f'offer_documents/{filename}',
                ContentFile(file.read())
            )

            # Save the document record
            serializer.save(
                original_filename=file.name,
                filename=filename,
                file_path=file_path,
                file_size=file.size,
                mime_type=file.content_type
            )


class EvaluationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing evaluations"""
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    permission_classes = [permissions.IsAuthenticated, IsEvaluator]

    def perform_create(self, serializer):
        """Auto-assign evaluator to the authenticated user"""
        serializer.save(evaluator=self.request.user)


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

            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'role': user.role,
                'email': user.email
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
            # Delete the user's token
            request.user.auth_token.delete()
            return Response(
                {'message': 'Successfully logged out'},
                status=status.HTTP_200_OK
            )
        except:
            return Response(
                {'error': 'Something went wrong'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RegisterView(APIView):
    """Handle new user registration"""
    permission_classes = []

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Generate token for the new user
            token, _ = Token.objects.get_or_create(user=user)

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

        if not user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        # Update token after password change
        user.auth_token.delete()
        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            'message': 'Password changed successfully',
            'token': token.key
        }, status=status.HTTP_200_OK)


class DocumentDownloadView(APIView):
    """Handle secure file downloads"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_type, document_id):
        try:
            if document_type == 'tender':
                document = TenderDocument.objects.get(id=document_id)
            elif document_type == 'offer':
                document = OfferDocument.objects.get(id=document_id)
                # Check if user has permission to download this offer document
                if request.user.role == 'vendor' and not document.offer.vendor.users.filter(
                        id=request.user.id).exists():
                    return Response(
                        {'error': 'Permission denied'},
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
                response = FileResponse(file, content_type=document.mime_type)
                response['Content-Disposition'] = f'attachment; filename="{document.original_filename}"'
                return response
            else:
                raise Http404("File not found")

        except (TenderDocument.DoesNotExist, OfferDocument.DoesNotExist):
            raise Http404("Document not found")