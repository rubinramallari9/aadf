# server/aadf/views/evaluation_views.py

from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Avg, Max, Min, F, Value, Case, When
from django.db.models.functions import TruncMonth, TruncDate, Coalesce
from django.utils import timezone
from django.conf import settings

import logging
import json
import csv
import io
import datetime
from dateutil.relativedelta import relativedelta

from ..models import (
    Evaluation, EvaluationCriteria, Offer, Tender, User, OfferDocument,
    AuditLog, Notification
)
from ..serializers import (
    EvaluationSerializer, EvaluationCriteriaSerializer
)
from ..permissions import IsStaffOrAdmin, IsEvaluator
from ..utils import (
    calculate_offer_score, create_notification
)
from ..ai_utils import suggest_evaluation_score

logger = logging.getLogger('aadf')


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
            
        # Filter by tender_id if provided
        tender_id = self.request.query_params.get('tender_id')
        if tender_id:
            queryset = queryset.filter(offer__tender_id=tender_id)
            
        # Filter by score range if provided
        min_score = self.request.query_params.get('min_score')
        if min_score:
            queryset = queryset.filter(score__gte=float(min_score))
            
        max_score = self.request.query_params.get('max_score')
        if max_score:
            queryset = queryset.filter(score__lte=float(max_score))
            
        # Apply user role restrictions
        if user.role == 'evaluator':
            # Evaluators can only see their own evaluations
            queryset = queryset.filter(evaluator=user)
        elif user.role == 'vendor':
            # Vendors can see evaluations for their own offers, but only if the tender is awarded
            queryset = queryset.filter(
                offer__vendor__users=user,
                offer__tender__status='awarded'
            )
            
        return queryset

    def perform_create(self, serializer):
        """Auto-assign evaluator to the authenticated user"""
        # Verify user has evaluator role
        if self.request.user.role != 'evaluator' and self.request.user.role not in ['staff', 'admin']:
            raise serializers.ValidationError("Only evaluators, staff, or admins can create evaluations")
            
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
                
            # Check if an evaluation already exists
            existing_evaluation = Evaluation.objects.filter(
                offer=offer,
                criteria=criteria,
                evaluator=self.request.user
            ).first()
            
            if existing_evaluation:
                raise serializers.ValidationError("You have already evaluated this offer for this criteria")
                
            # Save evaluation
            evaluation = serializer.save(evaluator=self.request.user)
            
            # Recalculate offer score
            calculate_offer_score(offer)
            
            # Log the evaluation
            AuditLog.objects.create(
                user=self.request.user,
                action='evaluate',
                entity_type='offer',
                entity_id=offer.id,
                details={
                    'criteria_id': criteria.id,
                    'criteria_name': criteria.name,
                    'score': evaluation.score,
                    'max_score': criteria.max_score
                },
                ip_address=self.request.META.get('REMOTE_ADDR', '')
            )
            
            # Notify vendor if all evaluations are complete
            if offer.tender.status == 'closed':
                # Check if all criteria have been evaluated for this offer
                criteria_count = EvaluationCriteria.objects.filter(tender=offer.tender).count()
                evaluations_count = Evaluation.objects.filter(
                    offer=offer, 
                    evaluator=self.request.user
                ).count()
                
                if criteria_count == evaluations_count:
                    # This evaluator has completed all evaluations for this offer
                    create_notification(
                        user=self.request.user,
                        title='Evaluation Complete',
                        message=f'You have completed all evaluations for the offer from {offer.vendor.name} for tender {offer.tender.reference_number}.',
                        notification_type='success',
                        related_entity=offer
                    )
                    
                    # Check if all evaluators have completed their evaluations
                    # In a real system, this would depend on your evaluation workflow
                    # For simplicity, we'll check if all evaluators have evaluated this offer
                    evaluators = User.objects.filter(role='evaluator')
                    all_complete = True
                    
                    for evaluator in evaluators:
                        evaluator_count = Evaluation.objects.filter(
                            offer=offer,
                            evaluator=evaluator
                        ).count()
                        
                        if evaluator_count < criteria_count:
                            all_complete = False
                            break
                            
                    if all_complete:
                        # All evaluations are complete, notify the tender creator
                        if offer.tender.created_by:
                            create_notification(
                                user=offer.tender.created_by,
                                title='Offer Fully Evaluated',
                                message=f'All evaluations are complete for the offer from {offer.vendor.name} for tender {offer.tender.reference_number}.',
                                notification_type='info',
                                related_entity=offer
                            )
            
            return evaluation
            
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
            
        # Store old score for logging
        old_score = evaluation.score
            
        # Update evaluation
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(evaluation, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Recalculate offer score
        calculate_offer_score(evaluation.offer)
        
        # Log the evaluation update
        AuditLog.objects.create(
            user=request.user,
            action='update_evaluation',
            entity_type='evaluation',
            entity_id=evaluation.id,
            details={
                'offer_id': evaluation.offer.id,
                'criteria_id': evaluation.criteria.id,
                'old_score': old_score,
                'new_score': evaluation.score
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get evaluation summary statistics for a tender"""
        # Check permissions
        if request.user.role not in ['staff', 'admin', 'evaluator']:
            return Response(
                {'error': 'You do not have permission to view the evaluation summary'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get tender ID
        tender_id = request.query_params.get('tender_id')
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
            
        # Get offers for this tender
        offers = Offer.objects.filter(tender=tender, status__in=['submitted', 'evaluated', 'awarded'])
        
        # Get all evaluations for these offers
        evaluations = Evaluation.objects.filter(offer__in=offers)
        
        # Calculate summary statistics
        summary = {
            'tender_id': tender.id,
            'tender_reference': tender.reference_number,
            'tender_title': tender.title,
            'tender_status': tender.status,
            'total_offers': offers.count(),
            'total_evaluations': evaluations.count(),
            'evaluators': evaluations.values('evaluator__username').annotate(count=Count('evaluator')).order_by('-count'),
            'avg_score': evaluations.aggregate(avg=Avg('score'))['avg'],
            'max_score': evaluations.aggregate(max=Max('score'))['max'],
            'min_score': evaluations.aggregate(min=Min('score'))['min'],
            'avg_scores_by_criteria': evaluations.values('criteria__name', 'criteria__category').annotate(avg=Avg('score')).order_by('criteria__category', 'criteria__name'),
            'evaluation_status': self._get_evaluation_status(tender, offers, evaluations),
            'offers_summary': []
        }
        
        # Add offer-level statistics
        for offer in offers:
            offer_evaluations = evaluations.filter(offer=offer)
            
            completed_criteria = offer_evaluations.values('criteria_id').distinct().count()
            total_criteria = EvaluationCriteria.objects.filter(tender=tender).count()
            
            offer_summary = {
                'offer_id': offer.id,
                'vendor_name': offer.vendor.name,
                'price': offer.price,
                'technical_score': offer.technical_score,
                'financial_score': offer.financial_score,
                'total_score': offer.total_score,
                'status': offer.status,
                'evaluation_count': offer_evaluations.count(),
                'evaluation_progress': {
                    'completed': completed_criteria,
                    'total': total_criteria,
                    'percentage': (completed_criteria / total_criteria * 100) if total_criteria > 0 else 0
                },
                'avg_score': offer_evaluations.aggregate(avg=Avg('score'))['avg'],
                'criteria_scores': offer_evaluations.values(
                    'criteria__name', 'criteria__category'
                ).annotate(
                    avg_score=Avg('score')
                ).order_by('criteria__category', 'criteria__name')
            }
            summary['offers_summary'].append(offer_summary)
            
        # Sort offers by total score (descending)
        summary['offers_summary'] = sorted(
            summary['offers_summary'], 
            key=lambda x: (x['total_score'] or 0), 
            reverse=True
        )
        
        # Add evaluation consistency analysis
        if evaluations.exists():
            # Group by criteria and offer to find standard deviation in scores between evaluators
            evaluator_count = evaluations.values('evaluator_id').distinct().count()
            
            if evaluator_count > 1:
                # For each offer and criteria, calculate variance between evaluators
                consistency_analysis = []
                
                for offer in offers:
                    for criteria in EvaluationCriteria.objects.filter(tender=tender):
                        scores = list(evaluations.filter(
                            offer=offer,
                            criteria=criteria
                        ).values_list('score', flat=True))
                        
                        if len(scores) > 1:
                            # Calculate variance
                            avg = sum(scores) / len(scores)
                            variance = sum((x - avg) ** 2 for x in scores) / len(scores)
                            
                            if variance > 400:  # High variance threshold (> 20 points difference)
                                consistency_analysis.append({
                                    'offer_id': offer.id,
                                    'vendor_name': offer.vendor.name,
                                    'criteria_id': criteria.id,
                                    'criteria_name': criteria.name,
                                    'variance': variance,
                                    'scores': scores
                                })
                
                # Sort by variance (descending)
                consistency_analysis.sort(key=lambda x: x['variance'], reverse=True)
                summary['consistency_analysis'] = consistency_analysis[:5]  # Top 5 inconsistencies
        
        return Response(summary)
    
    def _get_evaluation_status(self, tender, offers, evaluations):
        """Helper method to calculate evaluation completeness status"""
        criteria_count = EvaluationCriteria.objects.filter(tender=tender).count()
        evaluator_count = User.objects.filter(role='evaluator').count()
        
        # Calculate total possible evaluations
        total_possible = offers.count() * criteria_count * evaluator_count
        
        # Count completed evaluations
        completed = evaluations.count()
        
        # Calculate percentage
        percentage = (completed / total_possible * 100) if total_possible > 0 else 0
        
        # Get evaluations by evaluator
        evaluator_progress = []
        for evaluator in User.objects.filter(role='evaluator'):
            evaluator_completed = evaluations.filter(evaluator=evaluator).count()
            evaluator_total = offers.count() * criteria_count
            
            evaluator_progress.append({
                'evaluator_id': evaluator.id,
                'evaluator_name': evaluator.username,
                'completed': evaluator_completed,
                'total': evaluator_total,
                'percentage': (evaluator_completed / evaluator_total * 100) if evaluator_total > 0 else 0
            })
            
        # Sort by completion percentage (descending)
        evaluator_progress.sort(key=lambda x: x['percentage'], reverse=True)
        
        return {
            'completed': completed,
            'total': total_possible,
            'percentage': percentage,
            'evaluator_progress': evaluator_progress
        }
    
    @action(detail=False, methods=['get'], permission_classes=[IsStaffOrAdmin | IsEvaluator])
    def pending_tasks(self, request):
        """Get pending evaluation tasks for the current user"""
        user = request.user
        
        # Get all closed or awarded tenders
        tenders = Tender.objects.filter(status__in=['closed', 'awarded'])
        
        # Get all offers for these tenders
        offers = Offer.objects.filter(
            tender__in=tenders,
            status__in=['submitted', 'evaluated', 'awarded']
        )
        
        # Get all criteria for these tenders
        all_criteria = EvaluationCriteria.objects.filter(tender__in=tenders)
        
        # Get all evaluations by this user
        user_evaluations = Evaluation.objects.filter(
            evaluator=user,
            offer__in=offers
        )
        
        # Calculate pending tasks
        pending_tasks = []
        for offer in offers:
            # Get criteria for this offer's tender
            criteria = all_criteria.filter(tender=offer.tender)
            
            # Get evaluations for this offer
            offer_evaluations = user_evaluations.filter(offer=offer)
            
            # Find pending criteria (not yet evaluated)
            evaluated_criteria_ids = offer_evaluations.values_list('criteria_id', flat=True)
            pending_criteria = criteria.exclude(id__in=evaluated_criteria_ids)
            
            if pending_criteria.exists():
                # Group pending criteria by category
                pending_by_category = {}
                for c in pending_criteria:
                    if c.category not in pending_by_category:
                        pending_by_category[c.category] = []
                        
                    pending_by_category[c.category].append({
                        'id': c.id,
                        'name': c.name,
                        'weight': c.weight,
                        'max_score': c.max_score
                    })
                
                pending_tasks.append({
                    'tender_id': offer.tender.id,
                    'tender_reference': offer.tender.reference_number,
                    'offer_id': offer.id,
                    'vendor_name': offer.vendor.name,
                    'pending_criteria': [
                        {
                            'category': category,
                            'criteria': criteria_list
                        } for category, criteria_list in pending_by_category.items()
                    ],
                    'total_pending': pending_criteria.count(),
                    'total_criteria': criteria.count(),
                    'progress': (criteria.count() - pending_criteria.count()) / criteria.count() * 100
                })
        
        # Sort by progress (ascending) so least complete tasks are first
        pending_tasks.sort(key=lambda x: x['progress'])
        
        # Add deadline information
        now = timezone.now()
        for task in pending_tasks:
            tender = Tender.objects.get(id=task['tender_id'])
            # Assume evaluation deadline is 7 days after tender closing
            evaluation_deadline = tender.submission_deadline + timedelta(days=7)
            days_remaining = (evaluation_deadline - now).days
            
            task['deadline'] = {
                'date': evaluation_deadline,
                'days_remaining': days_remaining,
                'is_overdue': days_remaining < 0
            }
        
        return Response({
            'total_pending_offers': len(pending_tasks),
            'total_pending_evaluations': sum(task['total_pending'] for task in pending_tasks),
            'pending_tasks': pending_tasks
        })
    
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin | IsEvaluator])
    def suggest_score(self, request):
        """Suggest an evaluation score for a given offer and criteria using AI"""
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
            
            # Log the suggestion request
            AuditLog.objects.create(
                user=request.user,
                action='suggest_evaluation_score',
                entity_type='offer',
                entity_id=offer.id,
                details={
                    'criteria_id': criteria.id,
                    'criteria_name': criteria.name,
                    'suggested_score': suggested_score,
                    'confidence': confidence
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response({
                'suggested_score': suggested_score,
                'confidence': confidence,
                'max_score': criteria.max_score,
                'criteria_name': criteria.name,
                'criteria_category': criteria.category
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
    
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin | IsEvaluator])
    def bulk_evaluate(self, request):
        """Create multiple evaluations at once"""
        evaluations_data = request.data.get('evaluations')
        if not evaluations_data or not isinstance(evaluations_data, list):
            return Response(
                {'error': 'evaluations list is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        created_evaluations = []
        errors = []
        
        for eval_data in evaluations_data:
            offer_id = eval_data.get('offer_id')
            criteria_id = eval_data.get('criteria_id')
            score = eval_data.get('score')
            comment = eval_data.get('comment', '')
            
            if not offer_id or not criteria_id or score is None:
                errors.append({
                    'data': eval_data,
                    'error': 'offer_id, criteria_id, and score are required'
                })
                continue
                
            try:
                offer = Offer.objects.get(id=offer_id)
                criteria = EvaluationCriteria.objects.get(id=criteria_id)
                
                # Check permissions
                if request.user.role == 'evaluator' and criteria.tender.status not in ['closed', 'awarded']:
                    errors.append({
                        'data': eval_data,
                        'error': 'Cannot evaluate offers for tenders that are not closed or awarded'
                    })
                    continue
                    
                # Check if criteria belongs to the offer's tender
                if criteria.tender_id != offer.tender_id:
                    errors.append({
                        'data': eval_data,
                        'error': 'Criteria does not belong to this offer\'s tender'
                    })
                    continue
                    
                # Check if an evaluation already exists
                existing_evaluation = Evaluation.objects.filter(
                    offer=offer,
                    criteria=criteria,
                    evaluator=request.user
                ).first()
                
                if existing_evaluation:
                    # Update existing evaluation instead of creating a new one
                    existing_evaluation.score = score
                    existing_evaluation.comment = comment
                    existing_evaluation.save()
                    created_evaluations.append(EvaluationSerializer(existing_evaluation).data)
                else:
                    # Create new evaluation
                    evaluation = Evaluation.objects.create(
                        offer=offer,
                        criteria=criteria,
                        evaluator=request.user,
                        score=score,
                        comment=comment
                    )
                    created_evaluations.append(EvaluationSerializer(evaluation).data)
                    
                # Recalculate offer score
                calculate_offer_score(offer)
                
            except Offer.DoesNotExist:
                errors.append({
                    'data': eval_data,
                    'error': 'Offer not found'
                })
            except EvaluationCriteria.DoesNotExist:
                errors.append({
                    'data': eval_data,
                    'error': 'Evaluation criteria not found'
                })
            except Exception as e:
                errors.append({
                    'data': eval_data,
                    'error': str(e)
                })
                
        # Log the bulk evaluation
        AuditLog.objects.create(
            user=request.user,
            action='bulk_evaluate',
            entity_type='evaluation',
            entity_id=0,
            details={
                'created_count': len(created_evaluations),
                'error_count': len(errors)
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({
            'created': len(created_evaluations),
            'errors': len(errors),
            'evaluations': created_evaluations,
            'error_details': errors
        })
    
    @action(detail=False, methods=['get'])
    def my_evaluations(self, request):
        """Get all evaluations by the current user"""
        # Group evaluations by tender and offer
        user_evaluations = Evaluation.objects.filter(evaluator=request.user).select_related(
            'offer', 'offer__tender', 'offer__vendor', 'criteria'
        )
        
        # Organize by tender
        tenders = {}
        for eval in user_evaluations:
            tender_id = eval.offer.tender.id
            offer_id = eval.offer.id
            
            if tender_id not in tenders:
                tenders[tender_id] = {
                    'tender_id': tender_id,
                    'tender_reference': eval.offer.tender.reference_number,
                    'tender_title': eval.offer.tender.title,
                    'tender_status': eval.offer.tender.status,
                    'offers': {}
                }
                
            if offer_id not in tenders[tender_id]['offers']:
                tenders[tender_id]['offers'][offer_id] = {
                    'offer_id': offer_id,
                    'vendor_name': eval.offer.vendor.name,
                    'evaluations': []
                }
                
            tenders[tender_id]['offers'][offer_id]['evaluations'].append({
                'id': eval.id,
                'criteria_name': eval.criteria.name,
                'criteria_category': eval.criteria.category,
                'max_score': eval.criteria.max_score,
                'score': eval.score,
                'comment': eval.comment,
                'created_at': eval.created_at,
                'updated_at': eval.updated_at
            })
        
        # Convert to lists for response
        result = []
        for tender_id, tender_data in tenders.items():
            offers_list = []
            for offer_id, offer_data in tender_data['offers'].items():
                offers_list.append({
                    'offer_id': offer_id,
                    'vendor_name': offer_data['vendor_name'],
                    'evaluations': sorted(offer_data['evaluations'], key=lambda x: x['criteria_name'])
                })
                
            result.append({
                'tender_id': tender_data['tender_id'],
                'tender_reference': tender_data['tender_reference'],
                'tender_title': tender_data['tender_title'],
                'tender_status': tender_data['tender_status'],
                'offers': sorted(offers_list, key=lambda x: x['vendor_name'])
            })
            
        return Response(sorted(result, key=lambda x: x['tender_reference']))
    
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def reassign(self, request):
        """Reassign evaluations from one evaluator to another"""
        from_evaluator_id = request.data.get('from_evaluator_id')
        to_evaluator_id = request.data.get('to_evaluator_id')
        tender_id = request.data.get('tender_id')
        
        if not from_evaluator_id or not to_evaluator_id:
            return Response(
                {'error': 'Both from_evaluator_id and to_evaluator_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            from_evaluator = User.objects.get(id=from_evaluator_id)
            to_evaluator = User.objects.get(id=to_evaluator_id)
            
            # Verify to_evaluator is an evaluator
            if to_evaluator.role != 'evaluator' and to_evaluator.role not in ['staff', 'admin']:
                return Response(
                    {'error': 'Target user must be an evaluator, staff, or admin'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Filter evaluations
            evaluations = Evaluation.objects.filter(evaluator=from_evaluator)
            
            if tender_id:
                try:
                    tender = Tender.objects.get(id=tender_id)
                    evaluations = evaluations.filter(offer__tender=tender)
                except Tender.DoesNotExist:
                    return Response(
                        {'error': 'Tender not found'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                    
            # Check if any evaluations exist
            if not evaluations.exists():
                return Response(
                    {'error': 'No evaluations found to reassign'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Get count before reassignment
            count = evaluations.count()
            affected_offers = set(evaluations.values_list('offer_id', flat=True))
            
            # Reassign evaluations
            evaluations.update(evaluator=to_evaluator)
            
            # Recalculate scores for all affected offers
            for offer_id in affected_offers:
                try:
                    offer = Offer.objects.get(id=offer_id)
                    calculate_offer_score(offer)
                except Offer.DoesNotExist:
                    pass
            
            # Log the reassignment
            # server/aadf/views/evaluation_views.py (continued)

            # Log the reassignment
            AuditLog.objects.create(
                user=request.user,
                action='reassign_evaluations',
                entity_type='evaluation',
                entity_id=0,
                details={
                    'from_evaluator_id': from_evaluator_id,
                    'to_evaluator_id': to_evaluator_id,
                    'tender_id': tender_id,
                    'count': count
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Notify the new evaluator
            create_notification(
                user=to_evaluator,
                title='Evaluations Assigned',
                message=f'You have been assigned {count} evaluations previously assigned to {from_evaluator.username}.',
                notification_type='info'
            )
            
            # Notify the original evaluator
            create_notification(
                user=from_evaluator,
                title='Evaluations Reassigned',
                message=f'{count} of your evaluations have been reassigned to {to_evaluator.username}.',
                notification_type='info'
            )
            
            return Response({
                'status': 'success',
                'count': count,
                'message': f'Successfully reassigned {count} evaluations from {from_evaluator.username} to {to_evaluator.username}'
            })
            
        except User.DoesNotExist:
            return Response(
                {'error': 'One or both users not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def evaluator_performance(self, request):
        """Get performance metrics for evaluators"""
        # Only admin/staff can view evaluator performance
        if request.user.role not in ['admin', 'staff']:
            return Response(
                {'error': 'Only administrators and staff can view evaluator performance'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get all evaluators
        evaluators = User.objects.filter(role='evaluator')
        
        # Calculate metrics for each evaluator
        evaluator_metrics = []
        for evaluator in evaluators:
            # Get all evaluations by this evaluator
            evaluations = Evaluation.objects.filter(evaluator=evaluator)
            
            # Calculate total
            total_evaluations = evaluations.count()
            
            if total_evaluations == 0:
                continue  # Skip evaluators with no evaluations
                
            # Calculate evaluations by tender
            tenders_evaluated = evaluations.values('offer__tender').distinct().count()
            
            # Calculate offers evaluated
            offers_evaluated = evaluations.values('offer').distinct().count()
            
            # Calculate average score given
            avg_score = evaluations.aggregate(avg=Avg('score'))['avg'] or 0
            
            # Calculate average time spent per evaluation
            total_time = timedelta(0)
            count_with_duration = 0
            
            for eval in evaluations:
                if eval.updated_at and eval.created_at:
                    if eval.updated_at > eval.created_at:
                        duration = eval.updated_at - eval.created_at
                        total_time += duration
                        count_with_duration += 1
            
            avg_time = total_time / count_with_duration if count_with_duration > 0 else None
            
            # Calculate consistency (standard deviation of scores)
            scores = list(evaluations.values_list('score', flat=True))
            if len(scores) > 1:
                avg = sum(scores) / len(scores)
                variance = sum((x - avg) ** 2 for x in scores) / len(scores)
                std_dev = variance ** 0.5
            else:
                std_dev = 0
                
            # Calculate activity over time
            last_30_days = timezone.now() - timedelta(days=30)
            recent_evaluations = evaluations.filter(created_at__gte=last_30_days).count()
            
            # Calculate completion rate
            # This would depend on your specific evaluation workflow
            # For simplicity, we'll calculate the percentage of criteria evaluated for each offer
            offers = Offer.objects.filter(evaluations__evaluator=evaluator).distinct()
            completion_rates = []
            
            for offer in offers:
                criteria_count = EvaluationCriteria.objects.filter(tender=offer.tender).count()
                evaluated_count = evaluations.filter(offer=offer).count()
                
                if criteria_count > 0:
                    completion_rates.append(evaluated_count / criteria_count)
                    
            avg_completion_rate = sum(completion_rates) / len(completion_rates) if completion_rates else 0
            
            # Add to metrics
            evaluator_metrics.append({
                'evaluator_id': evaluator.id,
                'evaluator_name': evaluator.username,
                'total_evaluations': total_evaluations,
                'tenders_evaluated': tenders_evaluated,
                'offers_evaluated': offers_evaluated,
                'avg_score': round(avg_score, 2),
                'avg_time_per_evaluation': str(avg_time) if avg_time else None,
                'score_std_dev': round(std_dev, 2),
                'recent_activity': recent_evaluations,
                'avg_completion_rate': round(avg_completion_rate * 100, 2)
            })
            
        # Sort by total evaluations (descending)
        evaluator_metrics.sort(key=lambda x: x['total_evaluations'], reverse=True)
        
        return Response({
            'total_evaluators': len(evaluator_metrics),
            'evaluator_metrics': evaluator_metrics
        })
    
    @action(detail=False, methods=['get'])
    def score_distribution(self, request):
        """Get score distribution for evaluations"""
        # Filter by tender_id if provided
        tender_id = request.query_params.get('tender_id')
        
        # Set up base queryset
        queryset = Evaluation.objects.all()
        
        if tender_id:
            try:
                tender = Tender.objects.get(id=tender_id)
                queryset = queryset.filter(offer__tender=tender)
            except Tender.DoesNotExist:
                return Response(
                    {'error': 'Tender not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        # Apply user role restrictions
        if request.user.role == 'evaluator':
            queryset = queryset.filter(evaluator=request.user)
        elif request.user.role == 'vendor':
            queryset = queryset.filter(
                offer__vendor__users=request.user,
                offer__tender__status='awarded'
            )
            
        # Calculate score ranges
        ranges = [
            {'min': 0, 'max': 20, 'label': '0-20', 'count': 0},
            {'min': 20, 'max': 40, 'label': '20-40', 'count': 0},
            {'min': 40, 'max': 60, 'label': '40-60', 'count': 0},
            {'min': 60, 'max': 80, 'label': '60-80', 'count': 0},
            {'min': 80, 'max': 100, 'label': '80-100', 'count': 0}
        ]
        
        # Count evaluations in each range
        for r in ranges:
            count = queryset.filter(score__gte=r['min'], score__lt=r['max']).count()
            r['count'] = count
            
        # Handle max score edge case
        max_score_count = queryset.filter(score=100).count()
        ranges[-1]['count'] += max_score_count
        
        # Get average score
        avg_score = queryset.aggregate(avg=Avg('score'))['avg'] or 0
        
        # Get distribution by criteria category
        category_distribution = queryset.values('criteria__category').annotate(
            avg_score=Avg('score'),
            count=Count('id')
        ).order_by('criteria__category')
        
        # Get top and bottom scoring criteria
        top_criteria = queryset.values('criteria__name', 'criteria__category').annotate(
            avg_score=Avg('score')
        ).order_by('-avg_score')[:5]
        
        bottom_criteria = queryset.values('criteria__name', 'criteria__category').annotate(
            avg_score=Avg('score')
        ).order_by('avg_score')[:5]
        
        return Response({
            'total_evaluations': queryset.count(),
            'avg_score': round(avg_score, 2),
            'distribution': ranges,
            'category_distribution': list(category_distribution),
            'top_scoring_criteria': list(top_criteria),
            'bottom_scoring_criteria': list(bottom_criteria)
        })
    
    @action(detail=False, methods=['get'])
    def export_evaluations(self, request):
        """Export evaluations to CSV"""
        # Filter by tender_id if provided
        tender_id = request.query_params.get('tender_id')
        
        # Set up base queryset with related objects
        queryset = Evaluation.objects.select_related(
            'offer', 'offer__tender', 'offer__vendor', 'criteria', 'evaluator'
        )
        
        if tender_id:
            try:
                tender = Tender.objects.get(id=tender_id)
                queryset = queryset.filter(offer__tender=tender)
            except Tender.DoesNotExist:
                return Response(
                    {'error': 'Tender not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        # Apply user role restrictions
        if request.user.role == 'evaluator':
            queryset = queryset.filter(evaluator=request.user)
        elif request.user.role == 'vendor':
            queryset = queryset.filter(
                offer__vendor__users=request.user,
                offer__tender__status='awarded'
            )
        elif request.user.role not in ['staff', 'admin']:
            return Response(
                {'error': 'You do not have permission to export evaluations'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Create CSV in memory
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([
            'Tender Reference', 'Tender Title', 'Vendor', 'Criteria Category',
            'Criteria Name', 'Score', 'Max Score', 'Evaluator', 'Date', 'Comment'
        ])
        
        # Write data rows
        for eval in queryset:
            writer.writerow([
                eval.offer.tender.reference_number,
                eval.offer.tender.title,
                eval.offer.vendor.name,
                eval.criteria.category,
                eval.criteria.name,
                eval.score,
                eval.criteria.max_score,
                eval.evaluator.username,
                eval.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                eval.comment or ''
            ])
            
        # Create response with CSV
        buffer.seek(0)
        
        # Generate filename
        filename = f"evaluations_{timezone.now().strftime('%Y%m%d%H%M%S')}.csv"
        if tender_id:
            tender_ref = Tender.objects.get(id=tender_id).reference_number
            filename = f"evaluations_{tender_ref}_{timezone.now().strftime('%Y%m%d%H%M%S')}.csv"
        
        # Log the export
        AuditLog.objects.create(
            user=request.user,
            action='export_evaluations',
            entity_type='evaluation',
            entity_id=0,
            details={
                'tender_id': tender_id,
                'count': queryset.count()
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Create the HTTP response
        response = Response(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    
    @action(detail=False, methods=['get'])
    def evaluation_history(self, request):
        """Get evaluation history and trends"""
        # Only admin/staff and evaluators can view evaluation history
        if request.user.role not in ['admin', 'staff', 'evaluator']:
            return Response(
                {'error': 'You do not have permission to view evaluation history'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Apply user filtering for evaluators
        queryset = Evaluation.objects.all()
        if request.user.role == 'evaluator':
            queryset = queryset.filter(evaluator=request.user)
            
        # Get evaluation count by month
        start_date = timezone.now() - timedelta(days=365)  # Last year
        
        monthly_counts = queryset.filter(
            created_at__gte=start_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        # Get average scores by month
        monthly_scores = queryset.filter(
            created_at__gte=start_date
        ).annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            avg_score=Avg('score')
        ).order_by('month')
        
        # Get evaluation statistics by criteria category
        category_stats = queryset.values('criteria__category').annotate(
            count=Count('id'),
            avg_score=Avg('score')
        ).order_by('criteria__category')
        
        # Get evaluation statistics by evaluator
        evaluator_stats = queryset.values(
            'evaluator__username', 'evaluator_id'
        ).annotate(
            count=Count('id'),
            avg_score=Avg('score')
        ).order_by('-count')
        
        # Get evaluation statistics by tender
        tender_stats = queryset.values(
            'offer__tender__reference_number', 'offer__tender_id'
        ).annotate(
            count=Count('id'),
            avg_score=Avg('score')
        ).order_by('-count')
        
        return Response({
            'total_evaluations': queryset.count(),
            'monthly_counts': list(monthly_counts),
            'monthly_scores': list(monthly_scores),
            'category_stats': list(category_stats),
            'evaluator_stats': list(evaluator_stats),
            'tender_stats': list(tender_stats)
        })


class EvaluationCriteriaViewSet(viewsets.ModelViewSet):
    """ViewSet for managing evaluation criteria"""
    queryset = EvaluationCriteria.objects.all()
    serializer_class = EvaluationCriteriaSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'weight', 'created_at']
    ordering = ['name']

    def get_permissions(self):
        """Return custom permissions based on action"""
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsStaffOrAdmin()]

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
                
            # Verify weight is valid
            weight = self.request.data.get('weight')
            if weight is not None:
                # Check total weight per category
                category = self.request.data.get('category')
                existing_weight = EvaluationCriteria.objects.filter(
                    tender=tender,
                    category=category
                ).aggregate(Sum('weight'))['weight__sum'] or 0
                
                if existing_weight + float(weight) > 100:
                    raise serializers.ValidationError(f"Total weight for {category} criteria cannot exceed 100%")
                
            # Save criteria
            serializer.save(tender=tender)
            
            # Log the creation
            AuditLog.objects.create(
                user=self.request.user,
                action='create_criteria',
                entity_type='evaluation_criteria',
                entity_id=serializer.instance.id,
                details={
                    'tender_id': tender.id,
                    'name': serializer.instance.name,
                    'category': serializer.instance.category,
                    'weight': serializer.instance.weight,
                    'max_score': serializer.instance.max_score
                },
                ip_address=self.request.META.get('REMOTE_ADDR', '')
            )
            
        except Tender.DoesNotExist:
            raise serializers.ValidationError("Tender not found")
    
    def perform_update(self, serializer):
        """Update evaluation criteria"""
        criteria = serializer.instance
        
        # Verify tender status allows updating criteria
        if criteria.tender.status not in ['draft', 'published']:
            raise serializers.ValidationError("Cannot update criteria for closed or awarded tenders")
            
        # Verify weight is valid
        weight = self.request.data.get('weight')
        if weight is not None:
            # Check total weight per category
            category = self.request.data.get('category') or criteria.category
            existing_weight = EvaluationCriteria.objects.filter(
                tender=criteria.tender,
                category=category
            ).exclude(id=criteria.id).aggregate(Sum('weight'))['weight__sum'] or 0
            
            if existing_weight + float(weight) > 100:
                raise serializers.ValidationError(f"Total weight for {category} criteria cannot exceed 100%")
        
        # Save updates
        serializer.save()
        
        # Log the update
        AuditLog.objects.create(
            user=self.request.user,
            action='update_criteria',
            entity_type='evaluation_criteria',
            entity_id=criteria.id,
            details={
                'tender_id': criteria.tender.id,
                'name': criteria.name,
                'category': criteria.category,
                'weight': criteria.weight,
                'max_score': criteria.max_score
            },
            ip_address=self.request.META.get('REMOTE_ADDR', '')
        )
    
    def perform_destroy(self, instance):
        """Delete evaluation criteria"""
        # Verify tender status allows deleting criteria
        if instance.tender.status not in ['draft', 'published']:
            raise serializers.ValidationError("Cannot delete criteria for closed or awarded tenders")
            
        # Check if criteria has evaluations
        if Evaluation.objects.filter(criteria=instance).exists():
            raise serializers.ValidationError("Cannot delete criteria that has evaluations")
            
        # Log before deleting
        AuditLog.objects.create(
            user=self.request.user,
            action='delete_criteria',
            entity_type='evaluation_criteria',
            entity_id=instance.id,
            details={
                'tender_id': instance.tender.id,
                'name': instance.name,
                'category': instance.category
            },
            ip_address=self.request.META.get('REMOTE_ADDR', '')
        )
        
        # Delete
        instance.delete()
    
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def bulk_create(self, request):
        """Create multiple criteria at once"""
        criteria_data = request.data.get('criteria')
        tender_id = request.data.get('tender_id')
        
        if not criteria_data or not isinstance(criteria_data, list) or not tender_id:
            return Response(
                {'error': 'criteria list and tender_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            tender = Tender.objects.get(id=tender_id)
            
            # Verify tender status allows adding criteria
            if tender.status not in ['draft', 'published']:
                return Response(
                    {'error': 'Cannot add criteria to closed or awarded tenders'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Verify total weights per category do not exceed 100%
            category_weights = {}
            for data in criteria_data:
                category = data.get('category')
                weight = float(data.get('weight', 0))
                
                if category not in category_weights:
                    # Get existing weights
                    existing_weight = EvaluationCriteria.objects.filter(
                        tender=tender,
                        category=category
                    ).aggregate(Sum('weight'))['weight__sum'] or 0
                    
                    category_weights[category] = existing_weight
                    
                category_weights[category] += weight
                
                if category_weights[category] > 100:
                    return Response(
                        {'error': f'Total weight for {category} criteria cannot exceed 100%'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
            created_criteria = []
            errors = []
            
            for data in criteria_data:
                try:
                    serializer = self.get_serializer(data=data)
                    if serializer.is_valid():
                        serializer.save(tender=tender)
                        created_criteria.append(serializer.data)
                    else:
                        errors.append({
                            'data': data,
                            'errors': serializer.errors
                        })
                except Exception as e:
                    errors.append({
                        'data': data,
                        'errors': str(e)
                    })
                    
            # Log bulk creation
            AuditLog.objects.create(
                user=request.user,
                action='bulk_create_criteria',
                entity_type='tender',
                entity_id=tender.id,
                details={
                    'created_count': len(created_criteria),
                    'error_count': len(errors)
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response({
                'created': len(created_criteria),
                'errors': len(errors),
                'criteria': created_criteria,
                'error_details': errors
            })
            
        except Tender.DoesNotExist:
            return Response(
                {'error': 'Tender not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def template(self, request):
        """Get template evaluation criteria for a tender"""
        category = request.query_params.get('category', 'technical')
        
        # Default technical criteria templates
        technical_templates = [
            {
                'name': 'Technical Approach',
                'description': 'Overall approach to addressing the requirements',
                'category': 'technical',
                'weight': 25,
                'max_score': 100
            },
            {
                'name': 'Methodology',
                'description': 'Methodology and work plan',
                'category': 'technical',
                'weight': 20,
                'max_score': 100
            },
            {
                'name': 'Experience',
                'description': 'Relevant experience in similar projects',
                'category': 'technical',
                'weight': 15,
                'max_score': 100
            },
            {
                'name': 'Qualifications',
                'description': 'Staff qualifications and expertise',
                'category': 'technical',
                'weight': 15,
                'max_score': 100
            },
            {
                'name': 'Timeline',
                'description': 'Proposed timeline and deliverables',
                'category': 'technical',
                'weight': 15,
                'max_score': 100
            },
            {
                'name': 'Quality Assurance',
                'description': 'Quality assurance and risk management',
                'category': 'technical',
                'weight': 10,
                'max_score': 100
            }
        ]
        
        # Financial criteria templates
        financial_templates = [
            {
                'name': 'Cost Effectiveness',
                'description': 'Overall cost effectiveness of the proposal',
                'category': 'financial',
                'weight': 40,
                'max_score': 100
            },
            {
                'name': 'Budget Clarity',
                'description': 'Clarity and breakdown of budget items',
                'category': 'financial',
                'weight': 30,
                'max_score': 100
            },
            {
                'name': 'Value Added',
                'description': 'Value for money and additional benefits',
                'category': 'financial',
                'weight': 30,
                'max_score': 100
            }
        ]
        
        # Other criteria templates
        other_templates = [
            {
                'name': 'Sustainability',
                'description': 'Environmental and social sustainability',
                'category': 'other',
                'weight': 50,
                'max_score': 100
            },
            {
                'name': 'Innovation',
                'description': 'Innovative elements and approaches',
                'category': 'other',
                'weight': 50,
                'max_score': 100
            }
        ]
        
        if category == 'technical':
            return Response(technical_templates)
        elif category == 'financial':
            return Response(financial_templates)
        elif category == 'other':
            return Response(other_templates)
        else:
            return Response(technical_templates + financial_templates + other_templates)
            
    @action(detail=False, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def copy_from_tender(self, request):
        """Copy evaluation criteria from one tender to another"""
        source_tender_id = request.data.get('source_tender_id')
        target_tender_id = request.data.get('target_tender_id')
        
        if not source_tender_id or not target_tender_id:
            return Response(
                {'error': 'Both source_tender_id and target_tender_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            source_tender = Tender.objects.get(id=source_tender_id)
            target_tender = Tender.objects.get(id=target_tender_id)
            
            # Verify target tender status allows adding criteria
            if target_tender.status not in ['draft', 'published']:
                return Response(
                    {'error': 'Cannot add criteria to closed or awarded tenders'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Get source criteria
            source_criteria = EvaluationCriteria.objects.filter(tender=source_tender)
            
            if not source_criteria.exists():
                return Response(
                    {'error': 'Source tender has no evaluation criteria'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            # Copy criteria to target tender
            copied_criteria = []
            for criteria in source_criteria:
                new_criteria = EvaluationCriteria.objects.create(
                    tender=target_tender,
                    name=criteria.name,
                    description=criteria.description,
                    weight=criteria.weight,
                    max_score=criteria.max_score,
                    category=criteria.category
                )
                copied_criteria.append(EvaluationCriteriaSerializer(new_criteria).data)
                
            # Log the copy action
            AuditLog.objects.create(
                user=request.user,
                action='copy_criteria',
                entity_type='tender',
                entity_id=target_tender.id,
                details={
                    'source_tender_id': source_tender.id,
                    'count': len(copied_criteria)
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response({
                'status': 'success',
                'count': len(copied_criteria),
                'criteria': copied_criteria
            })
            
        except Tender.DoesNotExist:
            return Response(
                {'error': 'One or both tenders not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get statistics about criteria usage across tenders"""
        # Only allow staff and admin
        if request.user.role not in ['staff', 'admin']:
            return Response(
                {'error': 'Only staff and administrators can view criteria statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get all criteria
        all_criteria = EvaluationCriteria.objects.all()
        
        # Calculate average weights by category
        avg_weights = all_criteria.values('category').annotate(
            avg_weight=Avg('weight'),
            count=Count('id')
        ).order_by('category')
        
        # Calculate most common criteria names
        common_names = all_criteria.values('name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Calculate average number of criteria per tender
        tenders_with_criteria = Tender.objects.filter(
            evaluation_criteria__isnull=False
        ).distinct()
        
        criteria_per_tender = 0
        if tenders_with_criteria.exists():
            criteria_count = all_criteria.count()
            tender_count = tenders_with_criteria.count()
            criteria_per_tender = criteria_count / tender_count
            
        # Calculate average scores by criteria name
        avg_scores = Evaluation.objects.values(
            'criteria__name', 'criteria__category'
        ).annotate(
            avg_score=Avg('score'),
            count=Count('id')
        ).order_by('-avg_score')
        
        # Return statistics
        return Response({
            'total_criteria': all_criteria.count(),
            'tenders_with_criteria': tenders_with_criteria.count(),
            'avg_criteria_per_tender': criteria_per_tender,
            'avg_weights_by_category': list(avg_weights),
            'most_common_criteria': list(common_names),
            'avg_scores_by_criteria': list(avg_scores)
        })