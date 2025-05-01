# server/aadf/views.py

from rest_framework import viewsets, permissions, status, serializers  # Added serializers import
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
from .permissions import IsStaffOrAdmin, IsVendor, IsEvaluator, IsAdminUser  # Added IsAdminUser import


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


class VendorCompanyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor companies"""
    queryset = VendorCompany.objects.all()
    serializer_class = VendorCompanySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter vendor companies based on user role"""
        user = self.request.user
        if user.role == 'vendor':
            return VendorCompany.objects.filter(users=user)
        return VendorCompany.objects.all()

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_user(self, request, pk=None):
        """Assign a user to a vendor company"""
        company = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            if user.role == 'vendor':
                company.users.add(user)
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
            company.users.remove(user)
            return Response({'status': 'user removed'})
        except User.DoesNotExist:
            return Response({'error': 'user not found'},
                            status=status.HTTP_404_NOT_FOUND)


class EvaluationCriteriaViewSet(viewsets.ModelViewSet):
    """ViewSet for managing evaluation criteria"""
    queryset = EvaluationCriteria.objects.all()
    serializer_class = EvaluationCriteriaSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAdmin]

    def get_queryset(self):
        """Filter by tender_id if provided"""
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            return EvaluationCriteria.objects.filter(tender_id=tender_id)
        return EvaluationCriteria.objects.all()


class ApprovalViewSet(viewsets.ModelViewSet):
    """ViewSet for managing approvals"""
    queryset = Approval.objects.all()
    serializer_class = ApprovalSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter approvals based on user role"""
        user = self.request.user
        if user.role in ['staff', 'admin']:
            return Approval.objects.all()
        return Approval.objects.filter(user=user)

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
            return Response({'status': 'approved'})
        return Response({'error': 'approval already processed'},
                        status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def reject(self, request, pk=None):
        """Reject a tender"""
        approval = self.get_object()
        if approval.status == 'pending':
            approval.status = 'rejected'
            approval.comments = request.data.get('comments', '')
            approval.save()
            return Response({'status': 'rejected'})
        return Response({'error': 'approval already processed'},
                        status=status.HTTP_400_BAD_REQUEST)


class ReportViewSet(viewsets.ModelViewSet):
    """ViewSet for managing reports"""
    queryset = Report.objects.all()
    serializer_class = ReportSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAdmin]

    def perform_create(self, serializer):
        """Auto-assign generated_by to the authenticated user"""
        serializer.save(generated_by=self.request.user)

    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def generate_tender_report(self, request):
        """Generate a report for a specific tender"""
        tender_id = request.data.get('tender_id')
        try:
            tender = Tender.objects.get(id=tender_id)
            # Generate report logic here
            report_filename = f"tender_report_{tender.reference_number}.pdf"
            report_filepath = f"reports/{report_filename}"

            report = Report.objects.create(
                tender=tender,
                generated_by=request.user,
                report_type='tender_commission',
                filename=report_filename,
                file_path=report_filepath
            )

            serializer = self.get_serializer(report)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Tender.DoesNotExist:
            return Response({'error': 'tender not found'},
                            status=status.HTTP_404_NOT_FOUND)


class NotificationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notifications"""
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filter notifications for the authenticated user"""
        return Notification.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark a notification as read"""
        notification = self.get_object()
        notification.is_read = True
        notification.save()
        return Response({'status': 'marked as read'})

    @action(detail=False, methods=['post'])
    def mark_all_as_read(self, request):
        """Mark all notifications as read for the authenticated user"""
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'all notifications marked as read'})


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing audit logs"""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

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

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])

        return queryset


class UserProfileView(APIView):
    """Handle user profile operations"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get authenticated user's profile"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        """Update authenticated user's profile"""
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
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
            data.update({
                'total_tenders': Tender.objects.count(),
                'published_tenders': Tender.objects.filter(status='published').count(),
                'total_offers': Offer.objects.count(),
                'pending_approvals': Approval.objects.filter(status='pending').count(),
                'recent_activities': AuditLog.objects.order_by('-created_at')[:10].values()
            })
        elif user.role == 'vendor':
            vendor_companies = VendorCompany.objects.filter(users=user)
            data.update({
                'published_tenders': Tender.objects.filter(status='published').count(),
                'my_offers': Offer.objects.filter(vendor__in=vendor_companies).count(),
                'pending_offers': Offer.objects.filter(vendor__in=vendor_companies, status='draft').count(),
                'unread_notifications': Notification.objects.filter(user=user, is_read=False).count()
            })
        elif user.role == 'evaluator':
            data.update({
                'tenders_to_evaluate': Tender.objects.filter(status='closed').count(),
                'completed_evaluations': Evaluation.objects.filter(evaluator=user).count(),
                'pending_evaluations': Evaluation.objects.filter(evaluator=user, score__isnull=True).count()
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
            from django.db.models import Q
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query)
            )

        # Filter by date range
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            queryset = queryset.filter(created_at__range=[start_date, end_date])

        # Apply user role restrictions
        if request.user.role == 'vendor':
            queryset = queryset.filter(status='published')

        serializer = TenderSerializer(queryset, many=True)
        return Response(serializer.data)