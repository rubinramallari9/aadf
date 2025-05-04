# server/aadf/views/evaluation_views.py

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Avg
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

import logging
import json
import uuid
import math
import re

from ..models import (
    Evaluation, EvaluationCriteria, Offer, Tender, User, AuditLog, Notification,
    TenderDocument, OfferDocument, Report
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
    def auto_generate_criteria(self, request):
        """Auto-generate evaluation criteria for a tender using AI"""
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
            
        # Check if tender already has criteria
        existing_criteria = EvaluationCriteria.objects.filter(tender=tender).count()
        if existing_criteria > 0:
            return Response(
                {'error': 'Tender already has evaluation criteria. Clear existing criteria first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Generate criteria based on tender documents and description
        generated_criteria = self._generate_criteria_from_tender(tender)
        
        # Create the criteria
        created_criteria = []
        for criterion in generated_criteria:
            serializer = self.get_serializer(data=criterion)
            
            if serializer.is_valid():
                serializer.save()
                created_criteria.append(serializer.data)
            else:
                # Continue with other criteria even if one fails
                logger.warning(f"Failed to create criterion: {serializer.errors}")
        
        # Log the criteria generation
        AuditLog.objects.create(
            user=request.user,
            action='auto_generate_criteria',
            entity_type='tender',
            entity_id=tender.id,
            details={
                'criteria_count': len(created_criteria),
                'tender_reference': tender.reference_number
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({
            'message': f'Successfully generated {len(created_criteria)} criteria',
            'criteria': created_criteria
        })
    
    def _generate_criteria_from_tender(self, tender):
        """Generate evaluation criteria based on tender content"""
        criteria = []
        
        # Extract requirements from tender description
        description = tender.description
        
        # Common criteria categories and keywords
        criteria_templates = {
            'technical': [
                {'name': 'Technical Approach', 'description': 'Evaluation of the proposed technical approach and methodology', 'weight': 25, 'max_score': 10},
                {'name': 'Quality Assurance', 'description': 'Quality assurance and control methodology', 'weight': 15, 'max_score': 10},
                {'name': 'Innovation', 'description': 'Innovative approaches and solutions proposed', 'weight': 10, 'max_score': 10}
            ],
            'financial': [
                {'name': 'Price Competitiveness', 'description': 'Competitiveness of the proposed price', 'weight': 30, 'max_score': 10},
                {'name': 'Cost Breakdown', 'description': 'Clarity and reasonableness of cost breakdown', 'weight': 10, 'max_score': 10}
            ],
            'qualification': [
                {'name': 'Experience', 'description': 'Relevant experience in similar projects', 'weight': 15, 'max_score': 10},
                {'name': 'Team Qualifications', 'description': 'Qualifications and expertise of the proposed team', 'weight': 20, 'max_score': 10},
                {'name': 'Project References', 'description': 'Quality and relevance of provided references', 'weight': 10, 'max_score': 10}
            ],
            'management': [
                {'name': 'Project Management', 'description': 'Project management methodology and approach', 'weight': 15, 'max_score': 10},
                {'name': 'Risk Management', 'description': 'Risk identification and mitigation strategy', 'weight': 10, 'max_score': 10},
                {'name': 'Timeline', 'description': 'Feasibility of proposed timeline', 'weight': 10, 'max_score': 10}
            ]
        }
        
        # Check tender documents for clues
        documents = TenderDocument.objects.filter(tender=tender)
        has_tech_docs = any('technical' in doc.original_filename.lower() for doc in documents)
        has_finance_docs = any('financial' in doc.original_filename.lower() for doc in documents)
        
        # Add technical criteria if appropriate
        if has_tech_docs or 'technical' in description.lower():
            for template in criteria_templates['technical']:
                criteria.append({
                    'tender': tender.id,
                    'name': template['name'],
                    'description': template['description'],
                    'weight': template['weight'],
                    'max_score': template['max_score'],
                    'category': 'technical'
                })
                
        # Add financial criteria
        for template in criteria_templates['financial']:
            criteria.append({
                'tender': tender.id,
                'name': template['name'],
                'description': template['description'],
                'weight': template['weight'],
                'max_score': template['max_score'],
                'category': 'financial'
            })
            
        # Add qualification criteria
        qualification_weight = 0
        for template in criteria_templates['qualification']:
            # Check if specific qualification criteria apply
            if 'team' in description.lower() and 'Team' in template['name']:
                qualification_weight += template['weight']
                criteria.append({
                    'tender': tender.id,
                    'name': template['name'],
                    'description': template['description'],
                    'weight': template['weight'],
                    'max_score': template['max_score'],
                    'category': 'technical'
                })
            elif 'experience' in description.lower() and 'Experience' in template['name']:
                qualification_weight += template['weight']
                criteria.append({
                    'tender': tender.id,
                    'name': template['name'],
                    'description': template['description'],
                    'weight': template['weight'],
                    'max_score': template['max_score'],
                    'category': 'technical'
                })
            elif 'reference' in description.lower() and 'Reference' in template['name']:
                qualification_weight += template['weight']
                criteria.append({
                    'tender': tender.id,
                    'name': template['name'],
                    'description': template['description'],
                    'weight': template['weight'],
                    'max_score': template['max_score'],
                    'category': 'technical'
                })
                
        # Add management criteria if appropriate
        if 'timeline' in description.lower() or 'project management' in description.lower():
            for template in criteria_templates['management']:
                criteria.append({
                    'tender': tender.id,
                    'name': template['name'],
                    'description': template['description'],
                    'weight': template['weight'],
                    'max_score': template['max_score'],
                    'category': 'technical'
                })
                
        # Check for specific bidding package requirements mentioned in documents
        # Look for team composition requirements
        team_required = False
        for doc in documents:
            filename = doc.original_filename.lower()
            if 'team' in filename or 'personnel' in filename or 'staff' in filename:
                team_required = True
                break
                
        if team_required:
            criteria.append({
                'tender': tender.id,
                'name': 'Team Composition',
                'description': 'Evaluation of the proposed team composition and expertise distribution',
                'weight': 15,
                'max_score': 10,
                'category': 'technical'
            })
        
        # Look for specific expertise areas required 
        expertise_keywords = ['architect', 'engineer', 'planner', 'expert']
        for keyword in expertise_keywords:
            if keyword in description.lower():
                criteria.append({
                    'tender': tender.id,
                    'name': f'{keyword.capitalize()} Expertise',
                    'description': f'Evaluation of the {keyword} expertise and qualifications',
                    'weight': 10,
                    'max_score': 10,
                    'category': 'technical'
                })
        
        # Normalize weights if we have many criteria
        if len(criteria) > 0:
            total_weight = sum(c['weight'] for c in criteria)
            if total_weight != 100:
                # Adjust weights to sum to 100
                adjustment_factor = 100 / total_weight
                for criterion in criteria:
                    criterion['weight'] = round(criterion['weight'] * adjustment_factor)
                
                # Ensure weights sum to exactly 100 by adjusting the first criterion
                current_sum = sum(c['weight'] for c in criteria)
                if current_sum != 100:
                    criteria[0]['weight'] += (100 - current_sum)
        
        return criteria
        
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
    """ViewSet for managing evaluations with AI assistance"""
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
        
    @action(detail=False, methods=['post'])
    def ai_recommend_evaluations(self, request):
        """Get AI-assisted evaluation recommendations for all pending criteria in an offer"""
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
            
        # Check if user is allowed to evaluate this offer
        if request.user.role not in ['admin', 'staff', 'evaluator']:
            return Response(
                {'error': 'You do not have permission to evaluate offers'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get all criteria for this tender
        criteria = EvaluationCriteria.objects.filter(tender=offer.tender)
        
        # Get evaluations already done by this user
        evaluations = Evaluation.objects.filter(
            offer=offer,
            evaluator=request.user
        )
        
        # Find pending criteria
        evaluated_criteria_ids = [e.criteria_id for e in evaluations]
        pending_criteria = criteria.exclude(id__in=evaluated_criteria_ids)
        
        if not pending_criteria.exists():
            return Response(
                {'message': 'No pending criteria found for this offer'},
                status=status.HTTP_200_OK
            )
            
        # Initialize AI analyzer
        ai_analyzer = AIAnalyzer()
        
        # Get evaluation suggestions for each pending criteria
        recommendations = []
        
        for criterion in pending_criteria:
            # Get suggestion
            suggestion = ai_analyzer.generate_evaluation_suggestions(offer.id, criterion.id)
            
            if suggestion.get('status') == 'success':
                recommendations.append({
                    'criteria_id': criterion.id,
                    'criteria_name': criterion.name,
                    'criteria_category': criterion.category,
                    'max_score': float(criterion.max_score),
                    'weight': float(criterion.weight),
                    'suggested_score': suggestion.get('suggestion', {}).get('suggested_score'),
                    'confidence': suggestion.get('suggestion', {}).get('confidence'),
                    'explanation': suggestion.get('suggestion', {}).get('explanation'),
                    'factors': suggestion.get('suggestion', {}).get('factors', [])
                })
                
        # Log the AI recommendations
        AuditLog.objects.create(
            user=request.user,
            action='ai_evaluation_recommendations',
            entity_type='offer',
            entity_id=offer.id,
            details={
                'vendor_name': offer.vendor.name,
                'recommendations_count': len(recommendations)
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
                
        return Response({
            'offer_info': {
                'id': offer.id,
                'vendor_name': offer.vendor.name,
                'tender_reference': offer.tender.reference_number
            },
            'recommendations': recommendations,
            'recommendation_count': len(recommendations)
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
    def generate_ai_evaluation_report(self, request):
        """Generate an AI evaluation report for a tender"""
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
            
        # Initialize AI analyzer
        ai_analyzer = AIAnalyzer()
        
        # Detect anomalies in evaluations
        anomaly_detection = ai_analyzer.detect_evaluation_anomalies(tender_id)
        
        if anomaly_detection.get('status') == 'error':
            return Response(
                {'error': anomaly_detection.get('message', 'Anomaly detection failed')},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Generate additional evaluation analysis
        evaluation_analysis = self._generate_evaluation_analysis(tender)
        
        # Combine the analyses
        report_data = {
            'tender_info': {
                'id': tender.id,
                'reference_number': tender.reference_number,
                'title': tender.title,
                'status': tender.status
            },
            'anomaly_detection': {
                'anomalies': anomaly_detection.get('anomalies', []),
                'anomalies_count': anomaly_detection.get('anomalies_count', 0),
                'evaluator_bias': anomaly_detection.get('evaluator_bias', [])
            },
            'evaluation_analysis': evaluation_analysis,
            'generation_timestamp': timezone.now().isoformat()
        }
        
        # Save the report
        filename = f"ai_evaluation_report_{tender.reference_number}_{uuid.uuid4().hex[:8]}.json"
        file_path = f"reports/{filename}"
        
        # Save to storage
        default_storage.save(
            file_path,
            ContentFile(json.dumps(report_data, indent=2, default=str))
        )
        
        # Create report record
        report = Report.objects.create(
            tender=tender,
            generated_by=request.user,
            report_type='ai_evaluation_report',
            filename=filename,
            file_path=file_path
        )
        
        # Log the report generation
        AuditLog.objects.create(
            user=request.user,
            action='generate_ai_evaluation_report',
            entity_type='tender',
            entity_id=tender.id,
            details={
                'report_id': report.id,
                'tender_reference': tender.reference_number
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return summary with report ID
        return Response({
            'report_id': report.id,
            'tender_reference': tender.reference_number,
            'anomalies_found': anomaly_detection.get('anomalies_count', 0),
            'biased_evaluators_found': len(anomaly_detection.get('evaluator_bias', [])),
            'report_file': filename
        })
    
    def _generate_evaluation_analysis(self, tender):
        """Generate detailed evaluation analysis for a tender"""
        # Get all offers for this tender
        offers = Offer.objects.filter(tender=tender)
        
        # Get all evaluations
        evaluations = Evaluation.objects.filter(offer__tender=tender)
        
        if not evaluations.exists():
            return {
                'status': 'No evaluations found for this tender'
            }
            
        # Get all criteria
        criteria = EvaluationCriteria.objects.filter(tender=tender)
        
        # Analysis by criteria
        criteria_analysis = {}
        for criterion in criteria:
            criterion_evaluations = evaluations.filter(criteria=criterion)
            
            scores = [float(e.score) for e in criterion_evaluations]
            if scores:
                avg_score = sum(scores) / len(scores)
                max_score = float(criterion.max_score)
                normalized_score = (avg_score / max_score) * 100 if max_score > 0 else 0
                
                if len(scores) >= 2:
                    variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
                    std_dev = math.sqrt(variance)
                else:
                    variance = 0
                    std_dev = 0
                
                criteria_analysis[criterion.id] = {
                    'criteria_id': criterion.id,
                    'criteria_name': criterion.name,
                    'criteria_category': criterion.category,
                    'weight': float(criterion.weight),
                    'max_score': max_score,
                    'avg_score': avg_score,
                    'normalized_score': normalized_score,
                    'variance': variance,
                    'std_deviation': std_dev,
                    'evaluation_count': len(scores)
                }
        
        # Analysis by evaluator
        evaluator_analysis = {}
        evaluators = User.objects.filter(evaluations__in=evaluations).distinct()
        
        for evaluator in evaluators:
            evaluator_evals = evaluations.filter(evaluator=evaluator)
            
            scores = [float(e.score) / float(e.criteria.max_score) * 100 for e in evaluator_evals]
            if scores:
                avg_score = sum(scores) / len(scores)
                
                if len(scores) >= 2:
                    variance = sum((s - avg_score) ** 2 for s in scores) / len(scores)
                    std_dev = math.sqrt(variance)
                else:
                    variance = 0
                    std_dev = 0
                
                evaluator_analysis[evaluator.id] = {
                    'evaluator_id': evaluator.id,
                    'evaluator_name': evaluator.username,
                    'avg_normalized_score': avg_score,
                    'variance': variance,
                    'std_deviation': std_dev,
                    'evaluation_count': len(scores)
                }
        
        # Analysis by offer
        offer_analysis = {}
        for offer in offers:
            offer_evals = evaluations.filter(offer=offer)
            
            if offer_evals.exists():
                offer_analysis[offer.id] = {
                    'offer_id': offer.id,
                    'vendor_name': offer.vendor.name,
                    'technical_score': float(offer.technical_score) if offer.technical_score else None,
                    'financial_score': float(offer.financial_score) if offer.financial_score else None,
                    'total_score': float(offer.total_score) if offer.total_score else None,
                    'evaluation_count': offer_evals.count()
                }
        
        # Calculate consistency metrics
        consistency_metrics = {
            'total_evaluations': evaluations.count(),
            'evaluator_count': evaluators.count(),
            'criteria_count': criteria.count(),
            'offer_count': offers.count()
        }
        
        if evaluator_analysis:
            # Calculate average of variances across evaluators
            avg_variance = sum(e['variance'] for e in evaluator_analysis.values()) / len(evaluator_analysis)
            consistency_metrics['avg_evaluator_variance'] = avg_variance
            consistency_metrics['consistency_rating'] = self._get_consistency_rating(avg_variance)
        
        return {
            'criteria_analysis': list(criteria_analysis.values()),
            'evaluator_analysis': list(evaluator_analysis.values()),
            'offer_analysis': list(offer_analysis.values()),
            'consistency_metrics': consistency_metrics
        }
    
    def _get_consistency_rating(self, variance):
        """Get a qualitative rating for evaluation consistency"""
        if variance < 50:
            return "Excellent"
        elif variance < 100:
            return "Good"
        elif variance < 200:
            return "Moderate"
        elif variance < 300:
            return "Poor"
        else:
            return "Very Poor"

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
    def analyze_team_evaluations(self, request):
        """Analyze team-related evaluations in a tender"""
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
            
        # Get team-related criteria
        team_criteria = EvaluationCriteria.objects.filter(
            tender=tender
        ).filter(
            Q(name__icontains='team') | Q(name__icontains='personnel') | 
            Q(description__icontains='team') | Q(description__icontains='personnel')
        )
        
        if not team_criteria.exists():
            return Response(
                {'message': 'No team-related criteria found for this tender'},
                status=status.HTTP_200_OK
            )
            
        # Get team-related evaluations
        team_evaluations = Evaluation.objects.filter(
            offer__tender=tender,
            criteria__in=team_criteria
        )
        
        if not team_evaluations.exists():
            return Response(
                {'message': 'No team-related evaluations found for this tender'},
                status=status.HTTP_200_OK
            )
            
        # Analyze evaluations by offer
        offer_analysis = {}
        offers = Offer.objects.filter(tender=tender)
        
        for offer in offers:
            offer_evals = team_evaluations.filter(offer=offer)
            
            if offer_evals.exists():
                # Extract scores and normalize
                scores = []
                comments = []
                
                for eval in offer_evals:
                    normalized_score = float(eval.score) / float(eval.criteria.max_score) * 100
                    scores.append(normalized_score)
                    
                    if eval.comment:
                        comments.append(eval.comment)
                
                avg_score = sum(scores) / len(scores) if scores else 0
                
                # Extract team strengths and weaknesses from comments
                strengths = []
                weaknesses = []
                
                strength_indicators = ['strong', 'excellent', 'experienced', 'qualified', 'skilled']
                weakness_indicators = ['weak', 'insufficient', 'lacking', 'inadequate', 'limited']
                
                for comment in comments:
                    # Look for strengths
                    strength_found = False
                    for indicator in strength_indicators:
                        if indicator in comment.lower():
                            # Extract the context
                            sentences = re.split(r'[.!?]', comment)
                            for sentence in sentences:
                                if indicator in sentence.lower():
                                    strength = sentence.strip().capitalize()
                                    if strength and strength not in strengths:
                                        strengths.append(strength)
                                        strength_found = True
                    
                    # Look for weaknesses
                    weakness_found = False
                    for indicator in weakness_indicators:
                        if indicator in comment.lower():
                            # Extract the context
                            sentences = re.split(r'[.!?]', comment)
                            for sentence in sentences:
                                if indicator in sentence.lower():
                                    weakness = sentence.strip().capitalize()
                                    if weakness and weakness not in weaknesses:
                                        weaknesses.append(weakness)
                                        weakness_found = True
                
                # Store the analysis
                offer_analysis[offer.id] = {
                    'offer_id': offer.id,
                    'vendor_name': offer.vendor.name,
                    'avg_team_score': avg_score,
                    'team_rating': self._get_team_rating(avg_score),
                    'evaluations_count': offer_evals.count(),
                    'strengths': strengths[:3],  # Top 3 strengths
                    'weaknesses': weaknesses[:3]  # Top 3 weaknesses
                }
        
        # Rank the offers by team score
        ranked_offers = sorted(
            list(offer_analysis.values()),
            key=lambda x: x['avg_team_score'],
            reverse=True
        )
        
        # Log the analysis
        AuditLog.objects.create(
            user=request.user,
            action='analyze_team_evaluations',
            entity_type='tender',
            entity_id=tender.id,
            details={
                'tender_reference': tender.reference_number,
                'team_criteria_count': team_criteria.count(),
                'team_evaluations_count': team_evaluations.count()
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({
            'tender_reference': tender.reference_number,
            'team_criteria': [
                {
                    'id': c.id,
                    'name': c.name,
                    'weight': float(c.weight),
                    'max_score': float(c.max_score)
                } for c in team_criteria
            ],
            'team_evaluations_count': team_evaluations.count(),
            'ranked_offers': ranked_offers
        })
    
    def _get_team_rating(self, normalized_score):
        """Get a qualitative rating for team score"""
        if normalized_score >= 90:
            return "Excellent"
        elif normalized_score >= 80:
            return "Very Good"
        elif normalized_score >= 70:
            return "Good"
        elif normalized_score >= 60:
            return "Satisfactory"
        elif normalized_score >= 50:
            return "Adequate"
        else:
            return "Needs Improvement"