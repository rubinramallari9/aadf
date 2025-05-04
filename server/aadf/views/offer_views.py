# server/aadf/views/offer_views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Avg, Sum, Min, Max
from django.utils import timezone

import logging
import json

from ..models import (
    Offer, OfferDocument, Tender, User, AuditLog, Notification,
    Evaluation, EvaluationCriteria, Report
)
from ..serializers import OfferSerializer, OfferDetailSerializer
from ..permissions import IsStaffOrAdmin, IsVendor, CanManageOwnOffers
from ..utils import create_notification, calculate_offer_score, generate_offer_audit_trail
from ..ai_analysis import AIAnalyzer  # Import the AI analyzer module

logger = logging.getLogger('aadf')


class OfferViewSet(viewsets.ModelViewSet):
    """ViewSet for managing offers"""
    queryset = Offer.objects.all()
    serializer_class = OfferSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['tender__reference_number', 'vendor__name']
    ordering_fields = ['created_at', 'submitted_at', 'price', 'total_score']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return detailed serializer for retrieve action"""
        if self.action == 'retrieve':
            return OfferDetailSerializer
        return OfferSerializer

    def get_queryset(self):
        """Filter offers based on user role and query parameters"""
        user = self.request.user
        queryset = Offer.objects.all()
        
        # Filter by tender_id if provided
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
            
        # Filter by vendor_id if provided
        vendor_id = self.request.query_params.get('vendor_id')
        if vendor_id:
            queryset = queryset.filter(vendor_id=vendor_id)
            
        # Filter by status if provided
        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)
            
        # Apply user role restrictions
        if user.role == 'vendor':
            # Vendors can only see their own offers
            queryset = queryset.filter(vendor__users=user)
        elif user.role == 'evaluator':
            # Evaluators can only see offers for tenders in closed or awarded status
            queryset = queryset.filter(tender__status__in=['closed', 'awarded'])
            
        # Apply special conditions
        if user.role not in ['staff', 'admin']:
            # Special case: Hide other offers until tender closes
            closed_tenders = Tender.objects.filter(
                Q(status__in=['closed', 'awarded']) |
                Q(submission_deadline__lt=timezone.now())
            ).values_list('id', flat=True)
            
            # Display all offers for closed tenders, but only own offers for open tenders
            if user.role == 'vendor':
                queryset = queryset.filter(
                    Q(tender_id__in=closed_tenders) |
                    Q(vendor__users=user)
                )
            
        return queryset

    def perform_create(self, serializer):
        """Set the submitter to the current user"""
        # Ensure vendor can create offers
        user = self.request.user
        if user.role == 'vendor':
            # Check if the user belongs to the vendor company
            vendor = serializer.validated_data.get('vendor')
            if not vendor.users.filter(id=user.id).exists():
                raise permissions.PermissionDenied(
                    "You can only create offers for your own company"
                )
        
        serializer.save(submitted_by=user)
        
        # Log the creation
        offer = serializer.instance
        AuditLog.objects.create(
            user=user,
            action='create_offer',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'tender_id': offer.tender.id,
                'tender_reference': offer.tender.reference_number,
                'vendor_name': offer.vendor.name
            },
            ip_address=self.request.META.get('REMOTE_ADDR', '')
        )

    def update(self, request, *args, **kwargs):
        """Restrict updates based on role and offer status"""
        offer = self.get_object()
        user = request.user
        
        # Only staff/admin or the vendor who submitted can update
        if user.role == 'vendor':
            if not offer.vendor.users.filter(id=user.id).exists():
                return Response(
                    {'error': 'You can only update your own offers'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Vendors can only update draft offers
            if offer.status != 'draft':
                return Response(
                    {'error': 'You can only update offers in draft status'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        response = super().update(request, *args, **kwargs)
        
        # Log the update
        AuditLog.objects.create(
            user=user,
            action='update_offer',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'tender_id': offer.tender.id,
                'tender_reference': offer.tender.reference_number,
                'vendor_name': offer.vendor.name
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return response

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Submit an offer"""
        offer = self.get_object()
        user = request.user
        
        # Check permissions
        if user.role == 'vendor' and not offer.vendor.users.filter(id=user.id).exists():
            return Response(
                {'error': 'You can only submit your own offers'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check if offer can be submitted
        if offer.status != 'draft':
            return Response(
                {'error': 'Only draft offers can be submitted'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if tender is still accepting submissions
        if offer.tender.status != 'published' or offer.tender.submission_deadline < timezone.now():
            return Response(
                {'error': 'Tender is not accepting submissions at this time'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check for mandatory requirements
        mandatory_requirements = offer.tender.requirements.filter(is_mandatory=True)
        documents = OfferDocument.objects.filter(offer=offer)
        
        missing_documents = []
        for req in mandatory_requirements:
            if not documents.filter(document_type=req.document_type).exists():
                missing_documents.append(req.document_type)
                
        if missing_documents:
            return Response(
                {
                    'error': 'Missing mandatory documents',
                    'missing_documents': missing_documents
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if price is provided
        if offer.price is None:
            return Response(
                {'error': 'Price is required for submission'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update offer status
        offer.status = 'submitted'
        offer.submitted_at = timezone.now()
        offer.submitted_by = user
        offer.save()
        
        # Log the submission
        AuditLog.objects.create(
            user=user,
            action='submit_offer',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'tender_id': offer.tender.id,
                'tender_reference': offer.tender.reference_number,
                'vendor_name': offer.vendor.name,
                'price': float(offer.price)
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Notify staff/admin
        staff_users = User.objects.filter(role__in=['staff', 'admin'])
        for staff_user in staff_users:
            create_notification(
                user=staff_user,
                title='New Offer Submitted',
                message=f'Vendor {offer.vendor.name} has submitted an offer for tender {offer.tender.reference_number}',
                notification_type='info',
                related_entity=offer
            )
            
        # Return updated offer
        serializer = self.get_serializer(offer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def evaluate(self, request, pk=None):
        """Mark an offer as evaluated"""
        offer = self.get_object()
        
        # Check if offer can be evaluated
        if offer.status not in ['submitted', 'evaluated']:
            return Response(
                {'error': 'Only submitted or previously evaluated offers can be evaluated'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check if tender is in the right status
        if offer.tender.status not in ['closed', 'awarded']:
            return Response(
                {'error': 'Tender must be closed or awarded for evaluation'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update offer status
        offer.status = 'evaluated'
        offer.save()
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='mark_offer_evaluated',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'tender_id': offer.tender.id,
                'tender_reference': offer.tender.reference_number,
                'vendor_name': offer.vendor.name
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return updated offer
        serializer = self.get_serializer(offer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def award(self, request, pk=None):
        """Award this offer"""
        offer = self.get_object()
        
        # Check if offer can be awarded
        if offer.status not in ['submitted', 'evaluated']:
            return Response(
                {'error': 'Only submitted or evaluated offers can be awarded'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update offer status
        offer.status = 'awarded'
        offer.save()
        
        # Update tender status
        tender = offer.tender
        if tender.status != 'awarded':
            tender.status = 'awarded'
            tender.save()
            
        # Reject all other offers for this tender
        other_offers = Offer.objects.filter(tender=tender).exclude(id=offer.id)
        other_offers.update(status='rejected')
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='award_offer',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'tender_id': tender.id,
                'tender_reference': tender.reference_number,
                'vendor_name': offer.vendor.name
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Notify the awarded vendor
        for user in offer.vendor.users.all():
            create_notification(
                user=user,
                title='Tender Awarded',
                message=f'Your offer for {tender.reference_number} has been awarded',
                notification_type='success',
                related_entity=offer
            )
            
        # Notify rejected vendors
        for rejected_offer in other_offers:
            for user in rejected_offer.vendor.users.all():
                create_notification(
                    user=user,
                    title='Tender Result',
                    message=f'Your offer for {tender.reference_number} was not selected',
                    notification_type='info',
                    related_entity=rejected_offer
                )
                
        # Return updated offer
        serializer = self.get_serializer(offer)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def reject(self, request, pk=None):
        """Reject this offer"""
        offer = self.get_object()
        
        # Check if offer can be rejected
        if offer.status not in ['submitted', 'evaluated']:
            return Response(
                {'error': 'Only submitted or evaluated offers can be rejected'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Update offer status
        offer.status = 'rejected'
        offer.save()
        
        # Log the action
        AuditLog.objects.create(
            user=request.user,
            action='reject_offer',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'tender_id': offer.tender.id,
                'tender_reference': offer.tender.reference_number,
                'vendor_name': offer.vendor.name
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Notify the vendor
        for user in offer.vendor.users.all():
            create_notification(
                user=user,
                title='Offer Rejected',
                message=f'Your offer for {offer.tender.reference_number} has been rejected',
                notification_type='info',
                related_entity=offer
            )
            
        # Return updated offer
        serializer = self.get_serializer(offer)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get statistics on offers"""
        user = request.user
        
        # Base queryset - apply user restrictions
        if user.role == 'vendor':
            queryset = Offer.objects.filter(vendor__users=user)
        else:
            queryset = Offer.objects.all()
            
        # Overall statistics
        total_offers = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('status'))
        
        # Price statistics
        price_stats = queryset.filter(price__isnull=False).aggregate(
            avg_price=Avg('price'),
            min_price=Min('price'),
            max_price=Max('price'),
            total_value=Sum('price')
        )
        
        # Score statistics
        score_stats = queryset.filter(total_score__isnull=False).aggregate(
            avg_score=Avg('total_score'),
            min_score=Min('total_score'),
            max_score=Max('total_score')
        )
        
        # Recent activity
        recent_offers = queryset.order_by('-created_at')[:5].values(
            'id', 'tender__reference_number', 'vendor__name', 'status', 'created_at'
        )
        
        # By tender statistics
        tender_stats = []
        if user.role in ['staff', 'admin']:
            tender_counts = queryset.values('tender__id', 'tender__reference_number', 'tender__title').annotate(
                count=Count('id')
            ).order_by('-count')[:10]
            
            for item in tender_counts:
                tender_stats.append({
                    'tender_id': item['tender__id'],
                    'tender_reference': item['tender__reference_number'],
                    'tender_title': item['tender__title'],
                    'offer_count': item['count']
                })
                
        # By vendor statistics
        vendor_stats = []
        if user.role in ['staff', 'admin']:
            vendor_counts = queryset.values('vendor__id', 'vendor__name').annotate(
                count=Count('id'),
                awarded=Count('id', filter=Q(status='awarded')),
                rejected=Count('id', filter=Q(status='rejected')),
                submitted=Count('id', filter=Q(status='submitted'))
            ).order_by('-count')[:10]
            
            for item in vendor_counts:
                vendor_stats.append({
                    'vendor_id': item['vendor__id'],
                    'vendor_name': item['vendor__name'],
                    'offer_count': item['count'],
                    'awarded_count': item['awarded'],
                    'rejected_count': item['rejected'],
                    'submitted_count': item['submitted']
                })
                
        return Response({
            'total_offers': total_offers,
            'status_counts': status_counts,
            'price_statistics': price_stats,
            'score_statistics': score_stats,
            'recent_offers': recent_offers,
            'tender_statistics': tender_stats,
            'vendor_statistics': vendor_stats
        })

    @action(detail=True, methods=['get'])
    def evaluation_summary(self, request, pk=None):
        """Get a summary of evaluations for this offer"""
        offer = self.get_object()
        
        # Get all evaluations for this offer
        evaluations = Evaluation.objects.filter(offer=offer)
        
        if not evaluations.exists():
            return Response({
                'status': 'No evaluations found',
                'offer_id': offer.id,
                'vendor_name': offer.vendor.name,
                'tender_reference': offer.tender.reference_number
            })
            
        # Group evaluations by criteria
        criteria_evaluations = {}
        for evaluation in evaluations:
            criteria_id = evaluation.criteria.id
            
            if criteria_id not in criteria_evaluations:
                criteria_evaluations[criteria_id] = {
                    'criteria_id': criteria_id,
                    'criteria_name': evaluation.criteria.name,
                    'criteria_category': evaluation.criteria.category,
                    'criteria_weight': float(evaluation.criteria.weight),
                    'max_score': float(evaluation.criteria.max_score),
                    'evaluations': []
                }
                
            criteria_evaluations[criteria_id]['evaluations'].append({
                'evaluation_id': evaluation.id,
                'evaluator': evaluation.evaluator.username,
                'score': float(evaluation.score),
                'comment': evaluation.comment,
                'created_at': evaluation.created_at.isoformat()
            })
            
        # Calculate average scores for each criteria
        for criteria_id, data in criteria_evaluations.items():
            scores = [e['score'] for e in data['evaluations']]
            avg_score = sum(scores) / len(scores) if scores else 0
            
            data['average_score'] = avg_score
            data['normalized_score'] = (avg_score / data['max_score']) * 100 if data['max_score'] > 0 else 0
            
        # Sort by criteria category and weight
        criteria_list = list(criteria_evaluations.values())
        criteria_list.sort(key=lambda x: (x['criteria_category'], -x['criteria_weight']))
        
        # Calculate overall statistics
        technical_scores = [data['normalized_score'] for data in criteria_list if data['criteria_category'] == 'technical']
        financial_scores = [data['normalized_score'] for data in criteria_list if data['criteria_category'] == 'financial']
        
        technical_avg = sum(technical_scores) / len(technical_scores) if technical_scores else 0
        financial_avg = sum(financial_scores) / len(financial_scores) if financial_scores else 0
        
        return Response({
            'offer_id': offer.id,
            'vendor_name': offer.vendor.name,
            'tender_reference': offer.tender.reference_number,
            'criteria_evaluations': criteria_list,
            'technical_score': float(offer.technical_score) if offer.technical_score else technical_avg,
            'financial_score': float(offer.financial_score) if offer.financial_score else financial_avg,
            'total_score': float(offer.total_score) if offer.total_score else None,
            'evaluator_count': evaluations.values('evaluator').distinct().count(),
            'evaluation_count': evaluations.count()
        })

    @action(detail=True, methods=['get'])
    def compare(self, request, pk=None):
        """Compare this offer with others in the same tender"""
        offer = self.get_object()
        user = request.user
        
        # Get other offers for this tender
        other_offers = Offer.objects.filter(
            tender=offer.tender
        ).exclude(id=offer.id)
        
        # Apply visibility restrictions
        if user.role == 'vendor':
            # Vendors can only see other offers after tender closing
            if offer.tender.status not in ['closed', 'awarded'] and offer.tender.submission_deadline > timezone.now():
                return Response(
                    {'error': 'Offers can only be compared after tender closing'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
            # Vendors can only compare if they have a submitted offer
            if not offer.vendor.users.filter(id=user.id).exists():
                return Response(
                    {'error': 'You can only compare your own offers'},
                    status=status.HTTP_403_FORBIDDEN
                )
                
        # Price comparison
        price_comparison = {}
        if offer.price is not None:
            other_prices = [float(o.price) for o in other_offers if o.price is not None]
            
            if other_prices:
                avg_price = sum(other_prices) / len(other_prices)
                min_price = min(other_prices)
                max_price = max(other_prices)
                
                offer_price = float(offer.price)
                price_diff = ((offer_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                
                price_comparison = {
                    'offer_price': offer_price,
                    'avg_price': avg_price,
                    'min_price': min_price,
                    'max_price': max_price,
                    'price_difference': price_diff,
                    'is_lowest': offer_price <= min_price,
                    'is_highest': offer_price >= max_price,
                    'price_position': sorted([offer_price] + other_prices).index(offer_price) + 1,
                    'total_offers': len(other_prices) + 1
                }
                
        # Score comparison (if evaluated)
        score_comparison = {}
        if offer.total_score is not None:
            other_scores = [float(o.total_score) for o in other_offers if o.total_score is not None]
            
            if other_scores:
                avg_score = sum(other_scores) / len(other_scores)
                min_score = min(other_scores)
                max_score = max(other_scores)
                
                offer_score = float(offer.total_score)
                score_diff = offer_score - avg_score
                
                score_comparison = {
                    'offer_score': offer_score,
                    'avg_score': avg_score,
                    'min_score': min_score,
                    'max_score': max_score,
                    'score_difference': score_diff,
                    'is_lowest': offer_score <= min_score,
                    'is_highest': offer_score >= max_score,
                    'score_position': sorted([offer_score] + other_scores, reverse=True).index(offer_score) + 1,
                    'total_offers': len(other_scores) + 1
                }
                
        # Technical score comparison
        tech_comparison = {}
        if offer.technical_score is not None:
            other_tech_scores = [float(o.technical_score) for o in other_offers if o.technical_score is not None]
            
            if other_tech_scores:
                avg_tech = sum(other_tech_scores) / len(other_tech_scores)
                tech_diff = float(offer.technical_score) - avg_tech
                
                tech_comparison = {
                    'offer_score': float(offer.technical_score),
                    'avg_score': avg_tech,
                    'difference': tech_diff
                }
                
        # Financial score comparison
        fin_comparison = {}
        if offer.financial_score is not None:
            other_fin_scores = [float(o.financial_score) for o in other_offers if o.financial_score is not None]
            
            if other_fin_scores:
                avg_fin = sum(other_fin_scores) / len(other_fin_scores)
                fin_diff = float(offer.financial_score) - avg_fin
                
                fin_comparison = {
                    'offer_score': float(offer.financial_score),
                    'avg_score': avg_fin,
                    'difference': fin_diff
                }
                
        return Response({
            'offer_id': offer.id,
            'vendor_name': offer.vendor.name,
            'tender_reference': offer.tender.reference_number,
            'price_comparison': price_comparison,
            'score_comparison': score_comparison,
            'technical_comparison': tech_comparison,
            'financial_comparison': fin_comparison,
            'total_offers': other_offers.count() + 1
        })
        
    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def analyze_offer(self, request, pk=None):
        """Perform AI analysis of an offer"""
        offer = self.get_object()
        
        # Initialize AI analyzer
        ai_analyzer = AIAnalyzer()
        
        # Analyze offer
        analysis_result = ai_analyzer.analyze_offer(offer.id)
        
        if analysis_result.get('status') == 'error':
            return Response(
                {'error': analysis_result.get('message', 'Analysis failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Log the AI usage
        AuditLog.objects.create(
            user=request.user,
            action='analyze_offer',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'tender_reference': offer.tender.reference_number,
                'vendor_name': offer.vendor.name,
                'analysis_timestamp': analysis_result.get('analysis_timestamp')
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(analysis_result)