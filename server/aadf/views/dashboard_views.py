# server/aadf/views/dashboard_views.py

from rest_framework import permissions, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q, Count, Sum, Avg, Max, Min, F, Value
from django.db.models.functions import TruncMonth, TruncYear
from django.utils import timezone
from datetime import datetime, timedelta

import logging

from ..models import (
    User, Tender, Offer, VendorCompany, Notification, AuditLog,
    Evaluation, EvaluationCriteria, Report
)
from ..serializers import UserSerializer, TenderSerializer
from ..permissions import IsStaffOrAdmin, IsAdminUser
from ..utils import get_dashboard_statistics, get_vendor_statistics

logger = logging.getLogger('aadf')


class DashboardView(APIView):
    """Dashboard data endpoint with enhanced analytics"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get dashboard statistics based on user role"""
        user = request.user
        data = {}
        
        # Get time period for filtering (default: last 30 days)
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)

        if user.role in ['admin', 'staff']:
            # Get comprehensive dashboard data for staff/admin
            basic_stats = get_dashboard_statistics()
            
            # Add user-specific information
            data.update(basic_stats)
            data['user'] = {
                'created_tenders': Tender.objects.filter(created_by=user).count(),
                'unread_notifications': Notification.objects.filter(user=user, is_read=False).count(),
                'recent_activity': AuditLog.objects.filter(user=user).order_by('-created_at')[:5].values(
                    'action', 'entity_type', 'entity_id', 'created_at'
                )
            }
            
            # Add enhanced analytics for staff/admin
            # Trend analysis - tenders created over time (by month)
            tender_trends = Tender.objects.filter(
                created_at__gte=start_date
            ).annotate(
                month=TruncMonth('created_at')
            ).values('month').annotate(
                count=Count('id')
            ).order_by('month')
            
            # Tender category distribution
            category_distribution = Tender.objects.exclude(
                category__isnull=True
            ).exclude(
                category=''
            ).values('category').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Offer statistics by vendor
            vendor_offer_stats = Offer.objects.values(
                'vendor__name', 'vendor__id'
            ).annotate(
                total=Count('id'),
                submitted=Count('id', filter=Q(status='submitted')),
                awarded=Count('id', filter=Q(status='awarded')),
                rejected=Count('id', filter=Q(status='rejected')),
                avg_score=Avg('total_score', filter=Q(total_score__isnull=False))
            ).order_by('-total')[:10]
            
            # Average evaluation scores by criteria category
            avg_evaluation_scores = Evaluation.objects.values(
                'criteria__category'
            ).annotate(
                avg_score=Avg('score')
            ).order_by('criteria__category')
            
            # Recent system activity
            recent_activity = AuditLog.objects.select_related('user').order_by('-created_at')[:20].values(
                'id', 'user__username', 'action', 'entity_type', 'entity_id', 'created_at'
            )
            
            # Add enhanced analytics to response
            data['analytics'] = {
                'tender_trends': list(tender_trends),
                'category_distribution': list(category_distribution),
                'vendor_offer_stats': list(vendor_offer_stats),
                'avg_evaluation_scores': list(avg_evaluation_scores),
                'recent_activity': list(recent_activity)
            }
            
            # Add KPI metrics
            data['kpis'] = {
                'avg_offers_per_tender': Offer.objects.count() / max(Tender.objects.count(), 1),
                'avg_days_to_award': self._calculate_avg_days_to_award(),
                'total_awarded_value': Offer.objects.filter(status='awarded').aggregate(
                    sum=Sum('price'))['sum'] or 0,
                'tender_success_rate': self._calculate_tender_success_rate(),
                'vendor_participation_rate': self._calculate_vendor_participation_rate(),
                'evaluation_completion_rate': self._calculate_evaluation_completion_rate()
            }
            
        elif user.role == 'vendor':
            # Get vendor companies for this user
            vendor_companies = VendorCompany.objects.filter(users=user)
            
            if vendor_companies.exists():
                # Get offers for all companies
                offers = Offer.objects.filter(vendor__in=vendor_companies)
                
                # Basic vendor dashboard
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
                    'companies': [get_vendor_statistics(company) for company in vendor_companies],
                    'recent_offers': offers.order_by('-created_at')[:5].values(
                        'id', 'tender__reference_number', 'tender__title', 'status', 'submitted_at', 'total_score'
                    ),
                    'recent_tenders': Tender.objects.filter(status='published').order_by('-published_at')[:5].values(
                        'id', 'reference_number', 'title', 'submission_deadline'
                    ),
                    'unread_notifications': Notification.objects.filter(user=user, is_read=False).count()
                })
                
                # Enhanced vendor analytics
                # Offer success rate trend
                offer_trend = offers.filter(
                    created_at__gte=start_date
                ).annotate(
                    month=TruncMonth('created_at')
                ).values('month', 'status').annotate(
                    count=Count('id')
                ).order_by('month', 'status')
                
                # Score comparison
                score_comparison = offers.filter(
                    total_score__isnull=False
                ).values('tender__reference_number').annotate(
                    my_score=Avg('total_score'),
                    avg_score=Avg('tender__offers__total_score', filter=~Q(tender__offers__vendor__in=vendor_companies)),
                    max_score=Max('tender__offers__total_score')
                ).order_by('-my_score')[:10]
                
                # Participation by category
                participation_by_category = Tender.objects.filter(
                    offers__vendor__in=vendor_companies
                ).exclude(
                    category__isnull=True
                ).exclude(
                    category=''
                ).values('category').annotate(
                    total=Count('id'),
                    won=Count('id', filter=Q(offers__vendor__in=vendor_companies, offers__status='awarded'))
                ).order_by('-total')
                
                # Add enhanced analytics to response
                data['analytics'] = {
                    'offer_trend': list(offer_trend),
                    'score_comparison': list(score_comparison),
                    'participation_by_category': list(participation_by_category)
                }
                
                # Add KPIs
                data['kpis'] = {
                    'success_rate': offers.filter(status='awarded').count() / max(offers.filter(status__in=['submitted', 'evaluated', 'awarded', 'rejected']).count(), 1) * 100,
                    'avg_tender_value': offers.filter(status='awarded').aggregate(avg=Avg('price'))['avg'] or 0,
                    'avg_score': offers.aggregate(avg=Avg('total_score'))['avg'] or 0,
                    'avg_technical_score': offers.aggregate(avg=Avg('technical_score'))['avg'] or 0,
                    'avg_financial_score': offers.aggregate(avg=Avg('financial_score'))['avg'] or 0
                }
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
            # Get assigned tenders (tenders with offers that have evaluations by this user)
            assigned_tenders = Tender.objects.filter(
                status__in=['closed', 'awarded'],
                offers__evaluations__evaluator=user
            ).distinct()
            
            # Get evaluations by this user
            user_evaluations = Evaluation.objects.filter(evaluator=user)
            
            # Basic evaluator dashboard
            data.update({
                'tenders': {
                    'total_to_evaluate': Tender.objects.filter(status__in=['closed', 'awarded']).count(),
                    'evaluated': assigned_tenders.count(),
                    'in_progress': Tender.objects.filter(
                        status__in=['closed', 'awarded'],
                        offers__evaluations__evaluator=user
                    ).exclude(
                        id__in=assigned_tenders.filter(status='awarded').values_list('id', flat=True)
                    ).distinct().count()
                },
                'evaluations': {
                    'completed': user_evaluations.count(),
                    'recent': user_evaluations.order_by('-created_at')[:5].values(
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
            
            # Enhanced evaluator analytics
            # Evaluation trend over time
            evaluation_trend = user_evaluations.filter(
                created_at__gte=start_date
            ).annotate(
                day=TruncMonth('created_at')
            ).values('day').annotate(
                count=Count('id')
            ).order_by('day')
            
            # Average scores given by category
            avg_scores_by_category = user_evaluations.values(
                'criteria__category'
            ).annotate(
                avg_score=Avg('score')
            ).order_by('criteria__category')
            
            # Score comparison with other evaluators (average score difference)
            score_comparison = []
            for tender in assigned_tenders:
                # Get all evaluations for this tender
                tender_evaluations = Evaluation.objects.filter(
                    offer__tender=tender
                )
                
                # Get average score given by this evaluator
                user_avg = tender_evaluations.filter(
                    evaluator=user
                ).aggregate(avg=Avg('score'))['avg']
                
                # Get average score given by all other evaluators
                others_avg = tender_evaluations.exclude(
                    evaluator=user
                ).aggregate(avg=Avg('score'))['avg']
                
                if user_avg is not None and others_avg is not None:
                    score_comparison.append({
                        'tender_id': tender.id,
                        'tender_reference': tender.reference_number,
                        'user_avg': user_avg,
                        'others_avg': others_avg,
                        'difference': user_avg - others_avg
                    })
            
            # Add enhanced analytics to response
            data['analytics'] = {
                'evaluation_trend': list(evaluation_trend),
                'avg_scores_by_category': list(avg_scores_by_category),
                'score_comparison': score_comparison
            }
            
            # Add KPIs
            total_possible_evaluations = 0
            for tender in assigned_tenders:
                # Count number of offers and criteria
                offers_count = Offer.objects.filter(
                    tender=tender,
                    status__in=['submitted', 'evaluated', 'awarded']
                ).count()
                
                criteria_count = EvaluationCriteria.objects.filter(
                    tender=tender
                ).count()
                
                total_possible_evaluations += offers_count * criteria_count
            
            data['kpis'] = {
                'completion_rate': user_evaluations.count() / max(total_possible_evaluations, 1) * 100,
                'avg_score_given': user_evaluations.aggregate(avg=Avg('score'))['avg'] or 0,
                'evaluations_per_day': user_evaluations.filter(
                    created_at__gte=start_date
                ).count() / max(days, 1)
            }

        return Response(data)
    
    def _calculate_avg_days_to_award(self):
        """Calculate average days from closing to award"""
        awarded_tenders = Tender.objects.filter(status='awarded')
        
        total_days = 0
        count = 0
        
        for tender in awarded_tenders:
            # Find when the tender was closed
            if tender.status == 'awarded' and tender.updated_at and tender.published_at:
                days_to_award = (tender.updated_at - tender.published_at).days
                if days_to_award >= 0:  # Sanity check
                    total_days += days_to_award
                    count += 1
        
        return total_days / max(count, 1)
    
    def _calculate_tender_success_rate(self):
        """Calculate percentage of tenders that received at least one valid offer"""
        closed_tenders = Tender.objects.filter(status__in=['closed', 'awarded']).count()
        tenders_with_offers = Tender.objects.filter(
            status__in=['closed', 'awarded'],
            offers__status__in=['submitted', 'evaluated', 'awarded']
        ).distinct().count()
        
        return tenders_with_offers / max(closed_tenders, 1) * 100
    
    def _calculate_vendor_participation_rate(self):
        """Calculate percentage of vendors who have submitted at least one offer"""
        total_vendors = VendorCompany.objects.count()
        active_vendors = VendorCompany.objects.filter(
            offers__status__in=['submitted', 'evaluated', 'awarded', 'rejected']
        ).distinct().count()
        
        return active_vendors / max(total_vendors, 1) * 100
    
    def _calculate_evaluation_completion_rate(self):
        """Calculate percentage of required evaluations that have been completed"""
        # Get all closed or awarded tenders
        closed_tenders = Tender.objects.filter(status__in=['closed', 'awarded'])
        
        total_required = 0
        total_completed = 0
        
        for tender in closed_tenders:
            # Count offers and criteria
            offers_count = Offer.objects.filter(
                tender=tender,
                status__in=['submitted', 'evaluated', 'awarded']
            ).count()
            
            criteria_count = EvaluationCriteria.objects.filter(
                tender=tender
            ).count()
            
            # Count evaluators assigned to this tender
            evaluator_count = User.objects.filter(role='evaluator').count()
            
            # Calculate required evaluations (could vary based on your evaluation workflow)
            required = offers_count * criteria_count * evaluator_count
            
            # Calculate completed evaluations
            completed = Evaluation.objects.filter(
                offer__tender=tender
            ).count()
            
            total_required += required
            total_completed += completed
        
        return total_completed / max(total_required, 1) * 100


class TenderSearchView(APIView):
    """Advanced search for tenders with detailed filtering"""
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

        # Filter by date range - created_at
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
            
        # Filter by creator
        created_by = request.query_params.get('created_by')
        if created_by:
            queryset = queryset.filter(created_by__username=created_by)
            
        # Filter by value range
        min_value = request.query_params.get('min_value')
        if min_value:
            queryset = queryset.filter(estimated_value__gte=min_value)
            
        max_value = request.query_params.get('max_value')
        if max_value:
            queryset = queryset.filter(estimated_value__lte=max_value)
            
        # Sort results
        sort_by = request.query_params.get('sort_by', '-created_at')
        valid_sort_fields = ['created_at', 'submission_deadline', 'title', 'reference_number', 'status', 'estimated_value']
        
        # Validate sort field (prevent injection)
        sort_field = sort_by.lstrip('-')
        if sort_field in valid_sort_fields:
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-created_at')  # Default sort
            
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        
        # Count total results for pagination info
        total_count = queryset.count()
        
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
            for tender in queryset[start:end]:
                tender_data = TenderSerializer(tender).data
                tender_data['has_participated'] = tender.id in participated_tenders
                results.append(tender_data)
        else:
            # For other roles, just return the serialized tenders
            results = TenderSerializer(queryset[start:end], many=True).data

        return Response({
            'results': results,
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': (total_count + page_size - 1) // page_size
        })


class UserManagementView(APIView):
    """User management endpoints for admins"""
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request, user_id=None):
        """Get users or a specific user"""
        if user_id:
            # Get a specific user
            try:
                user = User.objects.get(id=user_id)
                serializer = UserSerializer(user)
                
                # Add extended info for admin view
                data = serializer.data
                
                # Add activity stats
                data['activity'] = {
                    'audit_logs': AuditLog.objects.filter(user=user).count(),
                    'last_login': AuditLog.objects.filter(
                        user=user, action='login'
                    ).order_by('-created_at').first().created_at if AuditLog.objects.filter(
                        user=user, action='login'
                    ).exists() else None,
                    'tenders_created': Tender.objects.filter(created_by=user).count(),
                    'evaluations': Evaluation.objects.filter(evaluator=user).count()
                }
                
                # Add vendor company info if applicable
                # Continuing UserManagementView class from server/aadf/views/dashboard_views.py

                # Add vendor company info if applicable
                if user.role == 'vendor':
                    companies = VendorCompany.objects.filter(users=user)
                    data['vendor_companies'] = [
                        {
                            'id': company.id,
                            'name': company.name,
                            'registration_number': company.registration_number,
                            'offers_count': Offer.objects.filter(vendor=company).count()
                        } for company in companies
                    ]
                
                return Response(data)
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Get all users
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
            
            # Pagination
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
            start = (page - 1) * page_size
            end = start + page_size
            
            # Count total results for pagination info
            total_count = users.count()
            
            # Add last login info to each user
            user_data = []
            for user in users[start:end]:
                data = UserSerializer(user).data
                
                # Add last login date
                last_login = AuditLog.objects.filter(
                    user=user, action='login'
                ).order_by('-created_at').first()
                
                data['last_login'] = last_login.created_at if last_login else None
                
                user_data.append(data)
            
            return Response({
                'results': user_data,
                'total': total_count,
                'page': page,
                'page_size': page_size,
                'total_pages': (total_count + page_size - 1) // page_size
            })

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
            
            # If role is vendor, assign to a company if requested
            if user.role == 'vendor' and request.data.get('company_id'):
                try:
                    company = VendorCompany.objects.get(id=request.data.get('company_id'))
                    company.users.add(user)
                except VendorCompany.DoesNotExist:
                    # Don't fail the request if company doesn't exist
                    pass
                    
            # Create welcome notification
            from ..utils import create_notification
            
            create_notification(
                user=user,
                title='Welcome to AADF Procurement Platform',
                message='Your account has been created by an administrator.',
                notification_type='info'
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
            
            # Handle company assignments for vendor users
            if user.role == 'vendor':
                # Get company IDs to assign
                company_ids = request.data.get('company_ids', [])
                if company_ids:
                    # Remove from all companies first if replace_companies is True
                    if request.data.get('replace_companies', False):
                        user.vendor_companies.clear()
                    
                    # Add to specified companies
                    for company_id in company_ids:
                        try:
                            company = VendorCompany.objects.get(id=company_id)
                            company.users.add(user)
                        except VendorCompany.DoesNotExist:
                            # Skip invalid company IDs
                            pass
            
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
        from ..utils import create_notification
        
        create_notification(
            user=user,
            title='Password Reset',
            message='Your password has been reset by an administrator. Please login with your new password.',
            notification_type='warning'
        )
        
        return Response({'message': 'Password reset successful'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get user statistics"""
        # Count users by role
        role_counts = User.objects.values('role').annotate(count=Count('id')).order_by('role')
        
        # Count active vs inactive users
        active_count = User.objects.filter(is_active=True).count()
        inactive_count = User.objects.filter(is_active=False).count()
        
        # Get recently created users
        recent_users = User.objects.order_by('-date_joined')[:10].values(
            'id', 'username', 'email', 'role', 'date_joined', 'is_active'
        )
        
        # Get most active users (based on audit logs)
        most_active = AuditLog.objects.values('user__username', 'user_id').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Calculate login statistics
        logins = AuditLog.objects.filter(action='login')
        total_logins = logins.count()
        
        # Get logins by month
        logins_by_month = logins.annotate(
            month=TruncMonth('created_at')
        ).values('month').annotate(
            count=Count('id')
        ).order_by('month')
        
        return Response({
            'total_users': User.objects.count(),
            'role_distribution': list(role_counts),
            'active_users': active_count,
            'inactive_users': inactive_count,
            'recent_users': list(recent_users),
            'most_active_users': list(most_active),
            'login_statistics': {
                'total_logins': total_logins,
                'logins_by_month': list(logins_by_month)
            }
        })
    
    @action(detail=True, methods=['post'])
    def change_role(self, request, user_id):
        """Change a user's role"""
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        new_role = request.data.get('role')
        if not new_role:
            return Response(
                {'error': 'Role is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Validate role
        valid_roles = [choice[0] for choice in User.ROLE_CHOICES]
        if new_role not in valid_roles:
            return Response(
                {'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Save old role for logging
        old_role = user.role
        
        # Update role
        user.role = new_role
        user.save()
        
        # Log the role change
        AuditLog.objects.create(
            user=request.user,
            action='change_role',
            entity_type='user',
            entity_id=user.id,
            details={
                'old_role': old_role,
                'new_role': new_role
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Create notification for the user
        from ..utils import create_notification
        
        create_notification(
            user=user,
            title='Role Changed',
            message=f'Your role has been changed from {old_role} to {new_role}.',
            notification_type='info'
        )
        
        return Response({
            'message': f'Role changed from {old_role} to {new_role}',
            'user': UserSerializer(user).data
        })