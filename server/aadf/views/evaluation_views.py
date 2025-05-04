# server/aadf/views/evaluation_views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone

import logging
import json

from ..models import (
    Evaluation, EvaluationCriteria, Offer, Tender, User, AuditLog, Notification
)
from ..serializers import EvaluationSerializer, EvaluationCriteriaSerializer
from ..permissions import IsStaffOrAdmin, IsEvaluator
from ..utils import calculate_offer_score, create_notification
from ..ai_analysis import AIAnalyzer  # Import the AI analyzer module

logger = logging.getLogger('aadf')


class EvaluationCriteriaViewSet(viewsets.ModelViewSet):
    """ViewSet for managing evaluation criteria"""
    queryset = EvaluationCriteria.objects.all()
    serializer_class = EvaluationCriteriaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'name', 'weight']
    ordering = ['tender', 'category', 'weight']

    def get_queryset(self):
        """Filter criteria based on tender_id if provided"""
        queryset = EvaluationCriteria.objects.all()
        
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            queryset = queryset.filter(tender_id=tender_id)
            
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
            
        return queryset

    def perform_create(self, serializer):
        """Check permissions for creation"""
        if self.request.user.role not in ['staff', 'admin']:
            return Response(
                {'error': 'Only staff and admin can create evaluation criteria'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer.save()
        
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def bulk_create(self, request):
        """Create multiple criteria at once"""
        tender_id = request.data.get('tender_id')
        criteria_list = request.data.get('criteria', [])
        
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
            
        created_criteria = []
        for criterion_data in criteria_list:
            criterion_data['tender'] = tender_id
            serializer = self.get_serializer(data=criterion_data)
            
            if serializer.is_valid():
                serializer.save()
                created_criteria.append(serializer.data)
            else:
                return Response(
                    {'error': 'Invalid criteria data', 'details': serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        # Log the creation
        AuditLog.objects.create(
            user=request.user,
            action='bulk_create_criteria',
            entity_type='tender',
            entity_id=tender.id,
            details={'criteria_count': len(created_criteria)},
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
                
        return Response(
            {'message': f'{len(created_criteria)} criteria created successfully', 'criteria': created_criteria},
            status=status.HTTP_201_CREATED
        )


class EvaluationViewSet(viewsets.ModelViewSet):
    """ViewSet for managing evaluations"""
    queryset = Evaluation.objects.all()
    serializer_class = EvaluationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter evaluations based on user role and query parameters"""
        user = self.request.user
        queryset = Evaluation.objects.all()
        
        # Filter by offer if provided
        offer_id = self.request.query_params.get('offer_id')
        if offer_id:
            queryset = queryset.filter(offer_id=offer_id)
            
        # Filter by criteria if provided
        criteria_id = self.request.query_params.get('criteria_id')
        if criteria_id:
            queryset = queryset.filter(criteria_id=criteria_id)
            
        # Filter by evaluator if provided
        evaluator_id = self.request.query_params.get('evaluator_id')
        if evaluator_id:
            queryset = queryset.filter(evaluator_id=evaluator_id)
            
        # Apply user role restrictions
        if user.role == 'evaluator':
            # Evaluators can only see their own evaluations
            queryset = queryset.filter(evaluator=user)
        elif user.role == 'vendor':
            # Vendors can only see evaluations for their own offers
            queryset = queryset.filter(offer__vendor__users=user)
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign evaluator to the authenticated user"""
        serializer.save(evaluator=self.request.user)
        
        # Update offer scores after evaluation
        evaluation = serializer.instance
        calculate_offer_score(evaluation.offer)
        
        # Log the creation
        AuditLog.objects.create(
            user=self.request.user,
            action='create_evaluation',
            entity_type='evaluation',
            entity_id=evaluation.id,
            details={
                'offer_id': evaluation.offer.id,
                'vendor_name': evaluation.offer.vendor.name,
                'criteria_name': evaluation.criteria.name,
                'score': float(evaluation.score)
            },
            ip_address=self.request.META.get('REMOTE_ADDR', '')
        )
        
        # Check if all criteria have been evaluated for this offer by this evaluator
        criteria_count = EvaluationCriteria.objects.filter(tender=evaluation.offer.tender).count()
        user_evaluations = Evaluation.objects.filter(
            offer=evaluation.offer,
            evaluator=self.request.user
        ).count()
        
        if user_evaluations == criteria_count:
            # Create notification for staff/admin that evaluation is complete
            staff_users = User.objects.filter(role__in=['staff', 'admin'])
            for user in staff_users:
                create_notification(
                    user=user,
                    title='Evaluation Completed',
                    message=f'Evaluator {self.request.user.username} has completed evaluation for {evaluation.offer.vendor.name}',
                    notification_type='info',
                    related_entity=evaluation.offer
                )

    def update(self, request, *args, **kwargs):
        """Only allow updating by the original evaluator"""
        evaluation = self.get_object()
        
        if request.user.role not in ['admin', 'staff'] and evaluation.evaluator.id != request.user.id:
            return Response(
                {'error': 'You do not have permission to update this evaluation'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        response = super().update(request, *args, **kwargs)
        
        # Update offer scores after evaluation update
        evaluation = self.get_object()
        calculate_offer_score(evaluation.offer)
        
        # Log the update
        AuditLog.objects.create(
            user=request.user,
            action='update_evaluation',
            entity_type='evaluation',
            entity_id=evaluation.id,
            details={
                'offer_id': evaluation.offer.id,
                'vendor_name': evaluation.offer.vendor.name,
                'criteria_name': evaluation.criteria.name,
                'score': float(evaluation.score)
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return response

    @action(detail=False, methods=['post'])
    def evaluate_offer(self, request):
        """Create or update multiple evaluations for an offer"""
        offer_id = request.data.get('offer_id')
        evaluations = request.data.get('evaluations', [])
        
        if not offer_id:
            return Response(
                {'error': 'offer_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        if not evaluations:
            return Response(
                {'error': 'evaluations data is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            offer = Offer.objects.get(id=offer_id)
        except Offer.DoesNotExist:
            return Response(
                {'error': 'Offer not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Check if user is allowed to evaluate this offer
        if request.user.role not in ['admin', 'staff', 'evaluator']:
            return Response(
                {'error': 'You do not have permission to evaluate offers'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check if offer can be evaluated
        if offer.tender.status not in ['closed', 'awarded']:
            return Response(
                {'error': 'Offers can only be evaluated for closed or awarded tenders'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Process evaluations
        created_count = 0
        updated_count = 0
        
        for eval_data in evaluations:
            criteria_id = eval_data.get('criteria_id')
            score = eval_data.get('score')
            comment = eval_data.get('comment', '')
            
            if not criteria_id or score is None:
                continue
                
            try:
                criteria = EvaluationCriteria.objects.get(id=criteria_id, tender=offer.tender)
            except EvaluationCriteria.DoesNotExist:
                continue
                
            # Validate score
            if score < 0 or score > float(criteria.max_score):
                continue
                
            # Check if evaluation already exists
            existing_eval = Evaluation.objects.filter(
                offer=offer,
                evaluator=request.user,
                criteria=criteria
            ).first()
            
            if existing_eval:
                # Update existing evaluation
                existing_eval.score = score
                existing_eval.comment = comment
                existing_eval.save()
                updated_count += 1
            else:
                # Create new evaluation
                Evaluation.objects.create(
                    offer=offer,
                    evaluator=request.user,
                    criteria=criteria,
                    score=score,
                    comment=comment
                )
                created_count += 1
                
        # Update offer scores
        calculate_offer_score(offer)
        
        # Log the batch evaluation
        AuditLog.objects.create(
            user=request.user,
            action='bulk_evaluate_offer',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'vendor_name': offer.vendor.name,
                'created_count': created_count,
                'updated_count': updated_count
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Check if all criteria have been evaluated for this offer by this evaluator
        criteria_count = EvaluationCriteria.objects.filter(tender=offer.tender).count()
        user_evaluations = Evaluation.objects.filter(
            offer=offer,
            evaluator=request.user
        ).count()
        
        if user_evaluations == criteria_count:
            # Create notification for staff/admin that evaluation is complete
            staff_users = User.objects.filter(role__in=['staff', 'admin'])
            for user in staff_users:
                create_notification(
                    user=user,
                    title='Evaluation Completed',
                    message=f'Evaluator {request.user.username} has completed evaluation for {offer.vendor.name}',
                    notification_type='info',
                    related_entity=offer
                )
                
        return Response({
            'status': 'success',
            'created_count': created_count,
            'updated_count': updated_count,
            'offer_status': offer.status,
            'technical_score': offer.technical_score,
            'financial_score': offer.financial_score,
            'total_score': offer.total_score
        })

    @action(detail=False, methods=['get'])
    def pending_evaluations(self, request):
        """Get offers pending evaluation for the current user"""
        user = request.user
        
        if user.role not in ['admin', 'staff', 'evaluator']:
            return Response(
                {'error': 'Only evaluators, staff, and admins can view pending evaluations'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get tenders that are closed or awarded
        tenders = Tender.objects.filter(status__in=['closed', 'awarded'])
        
        pending_offers = []
        for tender in tenders:
            # Get offers for this tender
            offers = Offer.objects.filter(
                tender=tender, 
                status__in=['submitted', 'evaluated']
            )
            
            for offer in offers:
                # Get criteria for this tender
                criteria = EvaluationCriteria.objects.filter(tender=tender)
                
                # Get evaluations already done by this user for this offer
                evaluations = Evaluation.objects.filter(
                    offer=offer,
                    evaluator=user
                )
                
                # Calculate pending criteria
                evaluated_criteria_ids = [e.criteria_id for e in evaluations]
                pending_criteria = criteria.exclude(id__in=evaluated_criteria_ids)
                
                if pending_criteria.exists():
                    pending_offers.append({
                        'tender_id': tender.id,
                        'tender_reference': tender.reference_number,
                        'tender_title': tender.title,
                        'offer_id': offer.id,
                        'vendor_name': offer.vendor.name,
                        'total_criteria': criteria.count(),
                        'evaluated_criteria': evaluations.count(),
                        'pending_criteria': pending_criteria.count(),
                        'completion_percentage': (evaluations.count() / criteria.count()) * 100 if criteria.count() > 0 else 0
                    })
                    
        # Sort by completion percentage (ascending)
        pending_offers.sort(key=lambda x: x['completion_percentage'])
        
        return Response({
            'pending_offers_count': len(pending_offers),
            'pending_offers': pending_offers
        })

    @action(detail=False, methods=['get'])
    def evaluation_status(self, request):
        """Get overall evaluation status for all tenders"""
        if request.user.role not in ['admin', 'staff']:
            return Response(
                {'error': 'Only staff and admins can view evaluation status'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get closed or awarded tenders
        tenders = Tender.objects.filter(status__in=['closed', 'awarded'])
        
        evaluation_status = []
        for tender in tenders:
            # Get offers for this tender
            offers = Offer.objects.filter(
                tender=tender, 
                status__in=['submitted', 'evaluated', 'awarded']
            )
            
            # Get evaluators who should evaluate this tender
            evaluators = User.objects.filter(role='evaluator', is_active=True)
            
            # Get criteria for this tender
            criteria = EvaluationCriteria.objects.filter(tender=tender)
            
            # Calculate total required evaluations
            total_required = offers.count() * criteria.count() * evaluators.count()
            
            # Get completed evaluations for this tender
            completed_evaluations = Evaluation.objects.filter(
                offer__tender=tender
            ).count()
            
            # Calculate completion percentage
            completion_percentage = (completed_evaluations / total_required) * 100 if total_required > 0 else 0
            
            evaluation_status.append({
                'tender_id': tender.id,
                'tender_reference': tender.reference_number,
                'tender_title': tender.title,
                'tender_status': tender.status,
                'offers_count': offers.count(),
                'criteria_count': criteria.count(),
                'evaluators_count': evaluators.count(),
                'completed_evaluations': completed_evaluations,
                'total_required_evaluations': total_required,
                'completion_percentage': completion_percentage
            })
            
        # Sort by completion percentage (ascending)
        evaluation_status.sort(key=lambda x: x['completion_percentage'])
        
        return Response({
            'evaluation_status': evaluation_status
        })
        
    @action(detail=False, methods=['post'])
    def get_ai_suggestion(self, request):
        """Get AI-assisted evaluation suggestion"""
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
        except (Offer.DoesNotExist, EvaluationCriteria.DoesNotExist):
            return Response(
                {'error': 'Offer or criteria not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Check if user is allowed to evaluate this offer
        if request.user.role not in ['admin', 'staff', 'evaluator']:
            return Response(
                {'error': 'You do not have permission to evaluate offers'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Initialize AI analyzer
        ai_analyzer = AIAnalyzer()
        
        # Get evaluation suggestion
        suggestion = ai_analyzer.generate_evaluation_suggestions(offer_id, criteria_id)
        
        if suggestion.get('status') == 'error':
            return Response(
                {'error': suggestion.get('message', 'Failed to generate suggestion')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Log the AI usage
        AuditLog.objects.create(
            user=request.user,
            action='use_ai_suggestion',
            entity_type='evaluation',
            entity_id=0,  # No evaluation yet
            details={
                'offer_id': offer.id,
                'criteria_id': criteria.id,
                'suggested_score': suggestion.get('suggestion', {}).get('suggested_score')
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(suggestion)
        
    @action(detail=False, methods=['post'])
    def detect_evaluation_anomalies(self, request):
        """Detect anomalies in evaluations using AI"""
        tender_id = request.data.get('tender_id')
        
        if not tender_id:
            return Response(
                {'error': 'tender_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Check permissions
        if request.user.role not in ['admin', 'staff']:
            return Response(
                {'error': 'Only staff and admin can detect evaluation anomalies'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Initialize AI analyzer
        ai_analyzer = AIAnalyzer()
        
        # Detect anomalies
        result = ai_analyzer.detect_evaluation_anomalies(tender_id)
        
        if result.get('status') == 'error':
            return Response(
                {'error': result.get('message', 'Failed to detect anomalies')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Log the AI usage
        AuditLog.objects.create(
            user=request.user,
            action='detect_evaluation_anomalies',
            entity_type='tender',
            entity_id=tender_id,
            details={
                'anomalies_count': len(result.get('anomalies', []))
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(result)