# aadf/permissions.py

from rest_framework import permissions


class IsStaffOrAdmin(permissions.BasePermission):
    """
    Permission class for staff and admin users
    """

    def has_permission(self, request, view):
        return request.user.role in ['staff', 'admin']

    def has_object_permission(self, request, view, obj):
        return request.user.role in ['staff', 'admin']


class IsVendor(permissions.BasePermission):
    """
    Permission class for vendor users
    """

    def has_permission(self, request, view):
        return request.user.role == 'vendor'

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'vendor'


class IsEvaluator(permissions.BasePermission):
    """
    Permission class for evaluator users
    """

    def has_permission(self, request, view):
        return request.user.role == 'evaluator'

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'evaluator'


class IsAdminUser(permissions.BasePermission):
    """
    Permission class for admin users only
    """

    def has_permission(self, request, view):
        return request.user.role == 'admin'

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'admin'


class CanManageOwnOffers(permissions.BasePermission):
    """
    Permission for vendors to manage their own offers
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role == 'vendor':
            # Check if the user belongs to the vendor company that owns the offer
            return obj.vendor.users.filter(id=request.user.id).exists()
        return True


class CanViewOwnDocuments(permissions.BasePermission):
    """
    Permission for users to view documents they have access to
    """

    def has_object_permission(self, request, view, obj):
        # Allow staff and admin to view all documents
        if request.user.role in ['staff', 'admin']:
            return True

        # Allow vendors to view their own offer documents
        if request.user.role == 'vendor':
            return obj.offer.vendor.users.filter(id=request.user.id).exists()

        # Allow evaluators to view documents for tenders they're evaluating
        if request.user.role == 'evaluator':
            # Implement logic based on your evaluation system
            pass

        return False