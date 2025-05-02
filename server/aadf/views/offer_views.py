# server/aadf/views/offer_views.py

from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.conf import settings
from django.db.models import Q, Count, Avg, Sum
from django.http import FileResponse

import logging
import os
import uuid

from ..models import (
    Offer, Tender, VendorCompany, OfferDocument, TenderRequirement, User,
    EvaluationCriteria, Evaluation
)
from ..serializers import (
    OfferSerializer, OfferDetailSerializer, OfferDocumentSerializer
)
from ..permissions import CanManageOwnOffers, IsStaffOrAdmin, IsEvaluator 
from ..utils import (
    create_notification, calculate_offer_score, generate_offer_audit_trail,
    get_vendor_statistics
)
from ..ai_utils import (
    check_missing_requirements, analyze_document_completeness, 
    analyze_offer_competitiveness, suggest_evaluation_score
)

logger = logging.getLogger('aadf')


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
        """Filter offers based on user role and hide offers until deadline"""
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
        elif user.role in ['staff', 'admin']:
            # Staff/Admin can see all offers, but if OFFERS_HIDDEN_UNTIL_DEADLINE is enabled,
            # hide offers for ongoing tenders until the deadline has passed
            if settings.PROCUREMENT_SETTINGS.get('OFFERS_HIDDEN_UNTIL_DEADLINE', True):
                now = timezone.now()
                
                # Get all tenders where deadline has not passed yet
                ongoing_tenders = Tender.objects.filter(
                    status='published',
                    submission_deadline__gt=now
                ).values_list('id', flat=True)
                
                # Exclude offers for ongoing tenders, unless it's the user's own tender
                if ongoing_tenders.exists():
                    own_tenders = Offer.objects.filter(
                        tender_id__in=ongoing_tenders,
                        tender__created_by=user
                    )
                    
                    other_tenders = queryset.exclude(tender_id__in=ongoing_tenders)
                    
                    # Combine the querysets
                    queryset = other_tenders | own_tenders
        
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

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin | IsEvaluator])
    def evaluate(self, request, pk=None):
        """Mark offer as evaluated"""
        offer = self.get_object()
        
        if offer.status == 'submitted' and offer.tender.status in ['closed', 'awarded']:
            # Calculate and update scores
            calculate_offer_score(offer)
            
            # Update status
            offer.status = 'evaluated'
            offer.save()
            
            # Notify the vendor
            for user in offer.vendor.users.all():
                create_notification(
                    user=user,
                    title='Offer Evaluated',
                    message=f'Your offer for tender {offer.tender.reference_number} has been evaluated.',
                    notification_type='info',
                    related_entity=offer
                )
            
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
            
    @action(detail=True, methods=['get'])
    def ai_analysis(self, request, pk=None):
        """Perform AI analysis on an offer"""
        offer = self.get_object()
        
        # Check permissions (only staff, admin, evaluators, or the offer's vendor)
        if request.user.role == 'vendor' and not offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to analyze this offer'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check if tender is closed (AI analysis is only available for closed tenders)
        if offer.tender.status not in ['closed', 'awarded'] and request.user.role == 'vendor':
            return Response(
                {'error': 'AI analysis is only available for offers on closed or awarded tenders'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get missing requirements
        missing_requirements = check_missing_requirements(offer)
        
        # Get document completeness analysis
        documents = OfferDocument.objects.filter(offer=offer)
        document_analysis = []
        
        for doc in documents:
            score, missing_elements = analyze_document_completeness(doc)
            document_analysis.append({
                'document_id': doc.id,
                'filename': doc.original_filename,
                'document_type': doc.document_type,
                'completeness_score': score,
                'missing_elements': missing_elements
            })
        
        # Get offer competitiveness analysis
        competitiveness_score, strengths, weaknesses = analyze_offer_competitiveness(offer)
        
        # Compile analysis results
        analysis_results = {
            'missing_requirements': missing_requirements,
            'document_analysis': document_analysis,
            'competitiveness': {
                'score': competitiveness_score,
                'strengths': strengths,
                'weaknesses': weaknesses
            }
        }
        
        return Response(analysis_results)
    
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin | IsEvaluator])
    def suggest_score(self, request):
        """Suggest an evaluation score for a given offer and criteria"""
        offer_id = request.data.get('offer_id')
        criteria_id = request.data.get('criteria_id')
        
        if not offer_id or not criteria_id:
            return Response(
                {'error': 'Both offer_id and criteria_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            offer = Offer.objects.get(id=offer_id)
            criteria = EvaluationCriteria.objects.get(id=criteria_id)
            
            # Check permissions
            if request.user.role == 'vendor':
                return Response(
                    {'error': 'Vendors cannot use this feature'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Check if criteria belongs to the offer's tender
            if criteria.tender_id != offer.tender_id:
                return Response(
                    {'error': 'Criteria does not belong to this offer\'s tender'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get suggested score
            suggested_score, confidence = suggest_evaluation_score(offer, criteria)
            
            return Response({
                'suggested_score': suggested_score,
                'confidence': confidence,
                'max_score': criteria.max_score
            })
            
        except Offer.DoesNotExist:
            return Response(
                {'error': 'Offer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except EvaluationCriteria.DoesNotExist:
            return Response(
                {'error': 'Evaluation criteria not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    @action(detail=True, methods=['get'])
    def audit_trail(self, request, pk=None):
        """Get audit trail for an offer"""
        offer = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to view this audit trail'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        audit_trail = generate_offer_audit_trail(offer)
        
        return Response(audit_trail)
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for an offer"""
        offer = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to view these statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get evaluations
        evaluations = Evaluation.objects.filter(offer=offer)
        evaluation_stats = evaluations.values('criteria__category').annotate(
            avg_score=Avg('score'),
            count=Count('id')
        )
        
        # Get document stats
        documents = OfferDocument.objects.filter(offer=offer)
        document_count = documents.count()
        document_total_size = documents.aggregate(sum=Sum('file_size'))['sum'] or 0
        
        # Compile statistics
        stats = {
            'evaluation_stats': evaluation_stats,
            'document_stats': {
                'count': document_count,
                'total_size': document_total_size
            },
            'technical_score': offer.technical_score,
            'financial_score': offer.financial_score,
            'total_score': offer.total_score,
            'submission_date': offer.submitted_at,
            'last_updated': offer.updated_at
        }
        
        return Response(stats)
    
    @action(detail=True, methods=['post'])
    def add_note(self, request, pk=None):
        """Add a note to an offer"""
        offer = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not offer.vendor.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to add notes to this offer'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        note = request.data.get('note')
        if not note:
            return Response(
                {'error': 'Note content is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Append note with timestamp and username
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        note_with_meta = f"[{timestamp} - {request.user.username}] {note}"
        
        if offer.notes:
            offer.notes = f"{offer.notes}\n\n{note_with_meta}"
        else:
            offer.notes = note_with_meta
            
        offer.save(update_fields=['notes'])
        
        return Response({'status': 'note added'})
    
    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def adjust_score(self, request, pk=None):
        """Manually adjust an offer's score"""
        offer = self.get_object()
        
        technical_score = request.data.get('technical_score')
        financial_score = request.data.get('financial_score')
        reason = request.data.get('reason')
        
        if not reason:
            return Response(
                {'error': 'A reason for the manual adjustment is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update scores
        if technical_score is not None:
            try:
                offer.technical_score = float(technical_score)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Technical score must be a number'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        if financial_score is not None:
            try:
                offer.financial_score = float(financial_score)
            except (ValueError, TypeError):
                return Response(
                    {'error': 'Financial score must be a number'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        # Recalculate total score
        if offer.technical_score is not None and offer.financial_score is not None:
            technical_weight = settings.PROCUREMENT_SETTINGS.get('DEFAULT_EVALUATION_WEIGHT_TECHNICAL', 70)
            financial_weight = settings.PROCUREMENT_SETTINGS.get('DEFAULT_EVALUATION_WEIGHT_FINANCIAL', 30)
            
            offer.total_score = (
                (offer.technical_score * technical_weight / 100) +
                (offer.financial_score * financial_weight / 100)
            )
            
        # Save the offer
        offer.save()
        
        # Add a note about the adjustment
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        note_with_meta = f"[{timestamp} - {request.user.username}] Score manually adjusted. Reason: {reason}"
        
        if offer.notes:
            offer.notes = f"{offer.notes}\n\n{note_with_meta}"
        else:
            offer.notes = note_with_meta
            
        offer.save(update_fields=['notes'])
        
        # Log the adjustment
        from ..models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action='adjust_score',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'technical_score': technical_score,
                'financial_score': financial_score,
                'reason': reason
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({
            'status': 'score adjusted',
            'technical_score': offer.technical_score,
            'financial_score': offer.financial_score,
            'total_score': offer.total_score
        })
    
    @action(detail=True, methods=['get'], permission_classes=[IsStaffOrAdmin | IsEvaluator])
    def compare(self, request, pk=None):
        """Compare this offer with others in the same tender"""
        offer = self.get_object()
        
        # Get other offers in the same tender
        other_offers = Offer.objects.filter(
            tender=offer.tender,
            status__in=['submitted', 'evaluated', 'awarded']
        ).exclude(id=offer.id)
        
        if not other_offers.exists():
            return Response({
                'message': 'No other offers to compare with',
                'comparison': []
            })
            
        # Prepare comparison data
        comparison = []
        for other in other_offers:
            price_diff = None
            if offer.price and other.price and offer.price > 0 and other.price > 0:
                price_diff = round((other.price - offer.price) / offer.price * 100, 2)
                
            technical_diff = None
            if offer.technical_score and other.technical_score:
                technical_diff = round(other.technical_score - offer.technical_score, 2)
                
            total_diff = None
            if offer.total_score and other.total_score:
                total_diff = round(other.total_score - offer.total_score, 2)
                
            comparison.append({
                'offer_id': other.id,
                'vendor_name': other.vendor.name,
                'price': other.price,
                'price_difference_percent': price_diff,
                'technical_score': other.technical_score,
                'technical_score_difference': technical_diff,
                'total_score': other.total_score,
                'total_score_difference': total_diff,
                'status': other.status
            })
            
        return Response({
            'main_offer': {
                'offer_id': offer.id,
                'vendor_name': offer.vendor.name,
                'price': offer.price,
                'technical_score': offer.technical_score,
                'total_score': offer.total_score,
                'status': offer.status
            },
            'comparison': comparison
        })
    
    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def revert_to_draft(self, request, pk=None):
        """Revert a submitted offer back to draft status"""
        offer = self.get_object()
        
        # Only allow reverting if tender is still published and offer is submitted
        if offer.tender.status != 'published' or offer.status != 'submitted':
            return Response(
                {'error': 'Can only revert offers that are submitted for published tenders'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        reason = request.data.get('reason')
        if not reason:
            return Response(
                {'error': 'A reason for reverting is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Revert to draft
        offer.status = 'draft'
        offer.submitted_at = None
        offer.save()
        
        # Add a note about the reversion
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        note_with_meta = f"[{timestamp} - {request.user.username}] Reverted from submitted to draft. Reason: {reason}"
        
        if offer.notes:
            offer.notes = f"{offer.notes}\n\n{note_with_meta}"
        else:
            offer.notes = note_with_meta
            
        offer.save(update_fields=['notes'])
        
        # Notify the vendor
        for user in offer.vendor.users.all():
            create_notification(
                user=user,
                title='Offer Reverted to Draft',
                message=f'Your offer for tender {offer.tender.reference_number} has been reverted to draft status. Reason: {reason}',
                notification_type='warning',
                related_entity=offer
            )
            
        # Log the action
        from ..models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action='revert_to_draft',
            entity_type='offer',
            entity_id=offer.id,
            details={'reason': reason},
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({'status': 'offer reverted to draft'})