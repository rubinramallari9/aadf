# server/aadf/views/auth_views.py

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.db.models import Q

import logging

from ..models import User, VendorCompany, AuditLog, Notification
from ..serializers import UserSerializer, VendorCompanySerializer
from ..utils import create_notification

logger = logging.getLogger('aadf')


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

            # Delete any existing tokens for this user
            Token.objects.filter(user=user).delete()
            
            # Create a new token
            token = Token.objects.create(user=user)
            
            # Log the login action
            ip_address = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
            if ip_address:
                ip_address = ip_address.split(',')[0].strip()
                
            AuditLog.objects.create(
                user=user,
                action='login',
                entity_type='auth',
                entity_id=0,
                details={'method': 'token'},
                ip_address=ip_address
            )
            
            return Response({
                'token': token.key,
                'user_id': user.id,
                'username': user.username,
                'role': user.role,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
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
            # Log the logout action
            AuditLog.objects.create(
                user=request.user,
                action='logout',
                entity_type='auth',
                entity_id=0,
                details={'method': 'token'},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Delete the user's token
            request.user.auth_token.delete()
            return Response(
                {'message': 'Successfully logged out'},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
            return Response(
                {'error': 'Something went wrong'},
                status=status.HTTP_400_BAD_REQUEST
            )


class RegisterView(APIView):
    """Handle new user registration"""
    permission_classes = []

    def post(self, request):
        # Check if registrations are allowed for this role
        role = request.data.get('role', 'vendor')
        
        # Only vendor registration is allowed without admin approval
        if role != 'vendor' and not request.user.is_authenticated:
            return Response(
                {'error': 'Only vendor registration is allowed without admin approval'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        # If staff/admin registration, check if request is from an admin
        if role in ['staff', 'admin'] and (not request.user.is_authenticated or request.user.role != 'admin'):
            return Response(
                {'error': 'Only administrators can create staff or admin accounts'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            # Create the user
            user = serializer.save()
            
            # Generate token for the new user
            token = Token.objects.create(user=user)
            
            # If role is vendor, create a vendor company if requested
            company_name = request.data.get('company_name')
            if role == 'vendor' and company_name:
                company_data = {
                    'name': company_name,
                    'registration_number': request.data.get('registration_number', ''),
                    'email': user.email,
                    'phone': request.data.get('phone', ''),
                    'address': request.data.get('address', '')
                }
                
                vendor_company = VendorCompany.objects.create(**company_data)
                vendor_company.users.add(user)
                
            # Log the registration
            AuditLog.objects.create(
                user=user,
                action='register',
                entity_type='user',
                entity_id=user.id,
                details={'role': role},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Create welcome notification
            create_notification(
                user=user,
                title='Welcome to AADF Procurement Platform',
                message='Thank you for registering. Your account has been created successfully.',
                notification_type='info'
            )
            
            # Notify admins about new vendor registration
            if role == 'vendor':
                admin_users = User.objects.filter(role='admin', is_active=True)
                for admin_user in admin_users:
                    create_notification(
                        user=admin_user,
                        title='New Vendor Registration',
                        message=f'A new vendor user {user.username} has registered.',
                        notification_type='info',
                        related_entity=user
                    )

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
        
        if not old_password or not new_password:
            return Response(
                {'error': 'Both old and new passwords are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not user.check_password(old_password):
            return Response(
                {'error': 'Current password is incorrect'},
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

        # Update token after password change
        user.auth_token.delete()
        token = Token.objects.create(user=user)
        
        # Log the password change
        AuditLog.objects.create(
            user=user,
            action='change_password',
            entity_type='user',
            entity_id=user.id,
            details={},
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        # Create notification
        create_notification(
            user=user,
            title='Password Changed',
            message='Your password has been changed successfully.',
            notification_type='info'
        )

        return Response({
            'message': 'Password changed successfully',
            'token': token.key
        }, status=status.HTTP_200_OK)


class UserProfileView(APIView):
    """Handle user profile operations"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get authenticated user's profile"""
        user = request.user
        serializer = UserSerializer(user)
        
        # Add extra information based on user role
        data = serializer.data
        
        if user.role == 'vendor':
            # Get vendor companies for this user
            companies = VendorCompany.objects.filter(users=user)
            data['companies'] = VendorCompanySerializer(companies, many=True).data
            
        # Get notification counts
        data['unread_notifications'] = Notification.objects.filter(user=user, is_read=False).count()
        
        return Response(data)

    def put(self, request):
        """Update authenticated user's profile"""
        user = request.user
        
        # Prevent role change through profile update unless by admin
        if 'role' in request.data and user.role != 'admin':
            return Response(
                {'error': 'Role cannot be changed through profile update'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            
            # Log the profile update
            AuditLog.objects.create(
                user=user,
                action='update_profile',
                entity_type='user',
                entity_id=user.id,
                details={},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class AdminCreateUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # Check if the requester is an admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can create users'},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            # Create the user
            user = serializer.save()
            
            # Log the creation
            AuditLog.objects.create(
                user=request.user,
                action='create_user',
                entity_type='user',
                entity_id=user.id,
                details={'role': user.role},
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Create welcome notification
            create_notification(
                user=user,
                title='Welcome to AADF Procurement Platform',
                message='Your account has been created.',
                notification_type='info'
            )

            return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)