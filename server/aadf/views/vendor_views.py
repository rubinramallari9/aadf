# server/aadf/views/vendor_views.py

from rest_framework import viewsets, permissions, status, filters, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, Count, Avg, Sum, Max, Min
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

import logging
import os
import uuid
import datetime
from dateutil.relativedelta import relativedelta

from ..models import (
    VendorCompany, VendorUser, User, Offer, Tender, Report, AuditLog
)
from ..serializers import (
    VendorCompanySerializer, UserSerializer, OfferSerializer
)
from ..permissions import IsStaffOrAdmin, IsVendor, IsAdminUser
from ..utils import (
    create_notification, get_vendor_statistics, calculate_offer_score
)

logger = logging.getLogger('aadf')


class VendorCompanyViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor companies"""
    queryset = VendorCompany.objects.all()
    serializer_class = VendorCompanySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'registration_number', 'email']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_queryset(self):
        """Filter vendor companies based on user role"""
        user = self.request.user
        queryset = VendorCompany.objects.all()
        
        # Apply user role restrictions
        if user.role == 'vendor':
            # Vendors can only see their own companies
            queryset = queryset.filter(users=user)
            
        return queryset

    def perform_create(self, serializer):
        """Handle creation of vendor company"""
        # Only staff/admin can create vendor companies
        if self.request.user.role not in ['staff', 'admin']:
            raise serializers.ValidationError("Only staff/admin can create vendor companies")
            
        serializer.save()

    @action(detail=True, methods=['post'], permission_classes=[IsAdminUser])
    def assign_user(self, request, pk=None):
        """Assign a user to a vendor company"""
        company = self.get_object()
        user_id = request.data.get('user_id')

        try:
            user = User.objects.get(id=user_id)
            if user.role == 'vendor':
                company.users.add(user)
                
                # Create notification for the user
                create_notification(
                    user=user,
                    title='Assigned to Vendor Company',
                    message=f'You have been assigned to the vendor company: {company.name}',
                    notification_type='info',
                    related_entity=company
                )
                
                # Log the assignment
                AuditLog.objects.create(
                    user=request.user,
                    action='assign_user_to_company',
                    entity_type='vendor_company',
                    entity_id=company.id,
                    details={
                        'user_id': user.id,
                        'username': user.username
                    },
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                
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
            if company.users.filter(id=user_id).exists():
                company.users.remove(user)
                
                # Create notification for the user
                create_notification(
                    user=user,
                    title='Removed from Vendor Company',
                    message=f'You have been removed from the vendor company: {company.name}',
                    notification_type='info',
                    related_entity=company
                )
                
                # Log the removal
                AuditLog.objects.create(
                    user=request.user,
                    action='remove_user_from_company',
                    entity_type='vendor_company',
                    entity_id=company.id,
                    details={
                        'user_id': user.id,
                        'username': user.username
                    },
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                
                return Response({'status': 'user removed'})
            return Response({'error': 'user is not assigned to this company'},
                            status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'error': 'user not found'},
                            status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """Get statistics for a vendor company"""
        company = self.get_object()
        
        # Check permissions
        if request.user.role == 'vendor' and not company.users.filter(id=request.user.id).exists():
            return Response(
                {'error': 'You do not have permission to view these statistics'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get statistics
        stats = get_vendor_statistics(company)
        
        # Add additional statistics
        
        # Get participation rate by tender category
        categories = Tender.objects.values_list('category', flat=True).distinct()
        category_stats = {}
        
        for category in categories:
            if not category:
                continue
                
            category_tenders = Tender.objects.filter(category=category).count()
            participated_tenders = Tender.objects.filter(
                category=category, 
                offers__vendor=company
            ).distinct().count()
            
            if category_tenders > 0:
                participation_rate = (participated_tenders / category_tenders) * 100
            else:
                participation_rate = 0
                
            category_stats[category] = {
                'total_tenders': category_tenders,
                'participated': participated_tenders,
                'participation_rate': round(participation_rate, 2)
            }
            
        stats['category_participation'] = category_stats
        
        # Get monthly offer counts for the past 12 months
        now = timezone.now()
        start_date = now - relativedelta(months=12)
        
        monthly_offers = []
        current_date = start_date
        
        while current_date <= now:
            month_end = current_date.replace(day=28) + relativedelta(days=4)
            month_end = month_end - relativedelta(days=month_end.day)
            
            count = Offer.objects.filter(
                vendor=company,
                created_at__gte=current_date,
                created_at__lte=month_end
            ).count()
            
            monthly_offers.append({
                'month': current_date.strftime('%Y-%m'),
                'count': count
            })
            
            current_date = current_date + relativedelta(months=1)
            
        stats['monthly_offers'] = monthly_offers
        
        # Get success rate by year
        years = list(range(now.year - 4, now.year + 1))
        yearly_stats = {}
        
        for year in years:
            year_offers = Offer.objects.filter(
                vendor=company,
                created_at__year=year
            )
            
            total = year_offers.count()
            awarded = year_offers.filter(status='awarded').count()
            
            if total > 0:
                success_rate = (awarded / total) * 100
            else:
                success_rate = 0
                
            yearly_stats[year] = {
                'total_offers': total,
                'awarded': awarded,
                'success_rate': round(success_rate, 2)
            }
            
        stats['yearly_performance'] = yearly_stats
        
        return Response(stats)
        
    @action(detail=True, methods=['get'], permission_classes=[IsStaffOrAdmin])
    def offers(self, request, pk=None):
        """Get all offers for this vendor company"""
        company = self.get_object()
        
        # Get offers with optional filtering
        offers = Offer.objects.filter(vendor=company)
        
        # Filter by tender status if provided
        tender_status = request.query_params.get('tender_status')
        if tender_status:
            offers = offers.filter(tender__status=tender_status)
            
        # Filter by offer status if provided
        offer_status = request.query_params.get('offer_status')
        if offer_status:
            offers = offers.filter(status=offer_status)
            
        # Filter by date range if provided
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        if start_date and end_date:
            offers = offers.filter(created_at__range=[start_date, end_date])
            
        # Serialize and return
        serializer = OfferSerializer(offers, many=True)
        return Response(serializer.data)
        
    @action(detail=True, methods=['put'], permission_classes=[IsAdminUser])
    def update_details(self, request, pk=None):
        """Update key vendor details"""
        company = self.get_object()
        
        # Update basic information
        company.name = request.data.get('name', company.name)
        company.registration_number = request.data.get('registration_number', company.registration_number)
        company.address = request.data.get('address', company.address)
        company.phone = request.data.get('phone', company.phone)
        company.email = request.data.get('email', company.email)
        
        # Save the changes
        company.save()
        
        # Log the update
        AuditLog.objects.create(
            user=request.user,
            action='update_vendor_details',
            entity_type='vendor_company',
            entity_id=company.id,
            details={field: request.data.get(field) for field in request.data},
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Return the updated company
        serializer = self.get_serializer(company)
        return Response(serializer.data)
        
    @action(detail=False, methods=['get'], permission_classes=[IsStaffOrAdmin])
    def vendor_comparison(self, request):
        """Compare performance metrics across vendors"""
        # Get the vendors to compare
        vendor_ids = request.query_params.get('vendor_ids', '').split(',')
        
        if not vendor_ids or vendor_ids[0] == '':
            # If no vendors specified, get top vendors by offer count
            vendors = VendorCompany.objects.annotate(
                offer_count=Count('offers')
            ).order_by('-offer_count')[:5]
        else:
            # Get the specified vendors
            vendors = VendorCompany.objects.filter(id__in=vendor_ids)
            
        if not vendors.exists():
            return Response({'error': 'No vendors found'}, status=status.HTTP_404_NOT_FOUND)
            
        # Prepare comparison data
        comparison = []
        
        for vendor in vendors:
            # Get vendor statistics
            stats = get_vendor_statistics(vendor)
            
            vendor_data = {
                'id': vendor.id,
                'name': vendor.name,
                'total_offers': stats['total_offers'],
                'success_rate': stats.get('success_rate', 0),
                'avg_score': stats.get('avg_score', 0),
                'awarded_offers': stats.get('awarded_offers', 0),
                'avg_price': Offer.objects.filter(vendor=vendor, price__isnull=False).aggregate(avg=Avg('price'))['avg']
            }
            
            comparison.append(vendor_data)
            
        return Response(comparison)
        
    @action(detail=False, methods=['get'])
    def my_company(self, request):
        """Get the vendor company for the current user"""
        # This is a convenience endpoint for vendor users
        if request.user.role != 'vendor':
            return Response(
                {'error': 'Only vendor users can access this endpoint'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Get the vendor company for this user
        company = VendorCompany.objects.filter(users=request.user).first()
        
        if not company:
            return Response(
                {'error': 'You are not associated with any vendor company'},
                status=status.HTTP_404_NOT_FOUND
            )
            
        # Get the company data with statistics
        serializer = self.get_serializer(company)
        data = serializer.data
        
        # Add company statistics
        stats = get_vendor_statistics(company)
        data['statistics'] = stats
        
        # Add user role information
        company_users = User.objects.filter(vendor_companies=company)
        data['users'] = UserSerializer(company_users, many=True).data
        
        return Response(data)


class VendorUserViewSet(viewsets.ModelViewSet):
    """ViewSet for managing vendor users (through relationship)"""
    queryset = VendorUser.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsStaffOrAdmin]
    
    def get_queryset(self):
        """Filter vendor users based on parameters"""
        queryset = VendorUser.objects.all()
        
        # Filter by company if provided
        company_id = self.request.query_params.get('company_id')
        if company_id:
            queryset = queryset.filter(company_id=company_id)
            
        # Filter by user if provided
        user_id = self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Create a new vendor user relationship"""
        user_id = request.data.get('user_id')
        company_id = request.data.get('company_id')
        
        if not user_id or not company_id:
            return Response(
                {'error': 'Both user_id and company_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            user = User.objects.get(id=user_id)
            company = VendorCompany.objects.get(id=company_id)
            
            # Check if relationship already exists
            if VendorUser.objects.filter(user=user, company=company).exists():
                return Response(
                    {'error': 'User is already associated with this company'},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Create the relationship
            vendor_user = VendorUser.objects.create(
                user=user,
                company=company
            )
            
            # Update user role if needed
            if user.role != 'vendor':
                user.role = 'vendor'
                user.save()
                
            # Log the creation
            AuditLog.objects.create(
                user=request.user,
                action='create_vendor_user',
                entity_type='vendor_user',
                entity_id=vendor_user.id,
                details={
                    'user_id': user.id,
                    'username': user.username,
                    'company_id': company.id,
                    'company_name': company.name
                },
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Send notification
            create_notification(
                user=user,
                title='Vendor Company Assignment',
                message=f'You have been assigned to vendor company: {company.name}',
                notification_type='info',
                related_entity=company
            )
            
            return Response({
                'id': vendor_user.id,
                'user_id': user.id,
                'username': user.username,
                'company_id': company.id,
                'company_name': company.name
            }, status=status.HTTP_201_CREATED)
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except VendorCompany.DoesNotExist:
            return Response(
                {'error': 'Vendor company not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def destroy(self, request, *args, **kwargs):
        """Remove a vendor user relationship"""
        vendor_user = self.get_object()
        
        # Store data for logging before deletion
        user_id = vendor_user.user.id
        username = vendor_user.user.username
        company_id = vendor_user.company.id
        company_name = vendor_user.company.name
        
        # Send notification before deletion
        create_notification(
            user=vendor_user.user,
            title='Vendor Company Removal',
            message=f'You have been removed from vendor company: {vendor_user.company.name}',
            notification_type='info',
            related_entity=vendor_user.company
        )
        
        # Delete the relationship
        vendor_user.delete()
        
        # Log the deletion
        AuditLog.objects.create(
            user=request.user,
            action='delete_vendor_user',
            entity_type='vendor_user',
            entity_id=0,  # ID no longer exists
            details={
                'user_id': user_id,
                'username': username,
                'company_id': company_id,
                'company_name': company_name
            },
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)