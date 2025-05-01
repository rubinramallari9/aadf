# server/aadf/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, VendorCompany, VendorUser, Tender, TenderRequirement, TenderDocument,
    Offer, OfferDocument, EvaluationCriteria, Evaluation, Approval, AuditLog,
    Report, Notification
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom user admin"""
    list_display = ('username', 'email', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'date_joined')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Extra Fields', {'fields': ('role',)}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Extra Fields', {'fields': ('role',)}),
    )


@admin.register(VendorCompany)
class VendorCompanyAdmin(admin.ModelAdmin):
    """Vendor company admin"""
    list_display = ('name', 'registration_number', 'email', 'phone', 'created_at')
    search_fields = ('name', 'registration_number', 'email')
    list_filter = ('created_at',)
    filter_horizontal = ('users',)


@admin.register(VendorUser)
class VendorUserAdmin(admin.ModelAdmin):
    """Vendor user admin"""
    list_display = ('user', 'company')
    list_filter = ('company',)


@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    """Tender admin"""
    list_display = ('reference_number', 'title', 'status', 'created_by', 'submission_deadline', 'created_at')
    list_filter = ('status', 'category', 'created_at', 'submission_deadline')
    search_fields = ('title', 'reference_number', 'description')
    readonly_fields = ('reference_number', 'created_at', 'updated_at')


@admin.register(TenderRequirement)
class TenderRequirementAdmin(admin.ModelAdmin):
    """Tender requirement admin"""
    list_display = ('tender', 'description', 'document_type', 'is_mandatory')
    list_filter = ('is_mandatory', 'document_type')
    search_fields = ('description',)


@admin.register(TenderDocument)
class TenderDocumentAdmin(admin.ModelAdmin):
    """Tender document admin"""
    list_display = ('tender', 'original_filename', 'file_size', 'uploaded_by', 'created_at')
    list_filter = ('created_at', 'mime_type')
    search_fields = ('original_filename', 'tender__reference_number')


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Offer admin"""
    list_display = ('tender', 'vendor', 'status', 'submitted_by', 'price', 'total_score', 'submitted_at')
    list_filter = ('status', 'submitted_at', 'created_at')
    search_fields = ('vendor__name', 'tender__reference_number')
    readonly_fields = ('submitted_at', 'total_score', 'technical_score', 'financial_score')


@admin.register(OfferDocument)
class OfferDocumentAdmin(admin.ModelAdmin):
    """Offer document admin"""
    list_display = ('offer', 'original_filename', 'document_type', 'file_size', 'created_at')
    list_filter = ('document_type', 'created_at')
    search_fields = ('original_filename', 'offer__vendor__name')


@admin.register(EvaluationCriteria)
class EvaluationCriteriaAdmin(admin.ModelAdmin):
    """Evaluation criteria admin"""
    list_display = ('tender', 'name', 'category', 'weight', 'max_score')
    list_filter = ('category', 'tender')
    search_fields = ('name', 'description')


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    """Evaluation admin"""
    list_display = ('offer', 'evaluator', 'criteria', 'score', 'created_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('offer__vendor__name', 'evaluator__username', 'criteria__name')


@admin.register(Approval)
class ApprovalAdmin(admin.ModelAdmin):
    """Approval admin"""
    list_display = ('tender', 'user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('tender__reference_number', 'user__username')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit log admin"""
    list_display = ('user', 'action', 'entity_type', 'entity_id', 'ip_address', 'created_at')
    list_filter = ('action', 'entity_type', 'created_at')
    search_fields = ('user__username', 'action', 'entity_type')
    readonly_fields = ('created_at',)


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    """Report admin"""
    list_display = ('tender', 'report_type', 'filename', 'generated_by', 'created_at')
    list_filter = ('report_type', 'created_at')
    search_fields = ('tender__reference_number', 'filename')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Notification admin"""
    list_display = ('user', 'title', 'type', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')