from rest_framework import serializers
from django.utils import timezone
from .models import (
    User, VendorCompany, VendorUser, Tender, TenderRequirement, TenderDocument,
    Offer, OfferDocument, EvaluationCriteria, Evaluation, Approval, AuditLog,
    Report, Notification
)


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'password', 'is_active', 'date_joined']
        read_only_fields = ['id', 'date_joined']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        return super().update(instance, validated_data)


class VendorUserSerializer(serializers.ModelSerializer):
    """Serializer for VendorUser model (relationship)"""
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    company_id = serializers.IntegerField(source='company.id', read_only=True)
    company_name = serializers.CharField(source='company.name', read_only=True)

    class Meta:
        model = VendorUser
        fields = ['id', 'user_id', 'username', 'company_id', 'company_name']
        read_only_fields = ['id']


class VendorCompanySerializer(serializers.ModelSerializer):
    """Serializer for VendorCompany model"""
    users = UserSerializer(many=True, read_only=True)
    user_ids = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), many=True, write_only=True,
                                                  required=False)
    vendor_users = VendorUserSerializer(source='vendoruser_set', many=True, read_only=True)
    offers_count = serializers.SerializerMethodField()
    active_tenders_count = serializers.SerializerMethodField()

    class Meta:
        model = VendorCompany
        fields = ['id', 'name', 'registration_number', 'address', 'phone', 'email',
                  'users', 'user_ids', 'vendor_users', 'offers_count', 'active_tenders_count',
                  'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at', 'offers_count', 'active_tenders_count']

    def get_offers_count(self, obj):
        return obj.offers.count()

    def get_active_tenders_count(self, obj):
        return obj.offers.filter(tender__status='published').values('tender').distinct().count()

    def create(self, validated_data):
        user_ids = validated_data.pop('user_ids', [])
        company = VendorCompany.objects.create(**validated_data)
        
        # Assign users to company through VendorUser model
        for user in user_ids:
            VendorUser.objects.create(user=user, company=company)
            
            # Update user role if needed
            if user.role != 'vendor':
                user.role = 'vendor'
                user.save()
        
        return company

    def update(self, instance, validated_data):
        user_ids = validated_data.pop('user_ids', None)
        
        # Update company fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # If user_ids is provided, update the company's users
        if user_ids is not None:
            # Remove existing relationships
            if validated_data.get('replace_users', False):
                VendorUser.objects.filter(company=instance).delete()
            
            # Add new users
            current_users = set(VendorUser.objects.filter(company=instance).values_list('user_id', flat=True))
            for user in user_ids:
                if user.id not in current_users:
                    VendorUser.objects.create(user=user, company=instance)
                    
                    # Update user role if needed
                    if user.role != 'vendor':
                        user.role = 'vendor'
                        user.save()
        
        return instance


class TenderRequirementSerializer(serializers.ModelSerializer):
    """Serializer for TenderRequirement model"""

    class Meta:
        model = TenderRequirement
        fields = ['id', 'description', 'document_type', 'is_mandatory', 'created_at']
        read_only_fields = ['id', 'created_at']


class TenderDocumentSerializer(serializers.ModelSerializer):
    """Serializer for TenderDocument model"""
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)

    class Meta:
        model = TenderDocument
        fields = ['id', 'filename', 'original_filename', 'file_path', 'file_size',
                  'mime_type', 'uploaded_by', 'uploaded_by_username', 'created_at']
        read_only_fields = ['id', 'filename', 'file_size', 'mime_type', 'uploaded_by', 'created_at']


class TenderSerializer(serializers.ModelSerializer):
    """Serializer for Tender model"""
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    requirements = TenderRequirementSerializer(many=True, read_only=True)
    documents = TenderDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = Tender
        fields = ['id', 'title', 'description', 'status', 'created_by', 'created_by_username',
                  'published_at', 'submission_deadline', 'opening_date', 'reference_number',
                  'estimated_value', 'category', 'requirements', 'documents', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_by', 'reference_number', 'published_at', 'created_at', 'updated_at']

    def validate(self, data):
        """Ensure submission deadline is in the future"""
        if 'submission_deadline' in data and data['submission_deadline'] < timezone.now():
            raise serializers.ValidationError("Submission deadline must be in the future")
        return data


class OfferDocumentSerializer(serializers.ModelSerializer):
    """Serializer for OfferDocument model"""

    class Meta:
        model = OfferDocument
        fields = ['id', 'filename', 'original_filename', 'file_path', 'file_size',
                  'mime_type', 'document_type', 'created_at']
        read_only_fields = ['id', 'filename', 'file_size', 'mime_type', 'created_at']


class OfferSerializer(serializers.ModelSerializer):
    """Serializer for Offer model"""
    vendor_name = serializers.CharField(source='vendor.name', read_only=True)
    tender_title = serializers.CharField(source='tender.title', read_only=True)
    tender_reference = serializers.CharField(source='tender.reference_number', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    documents = OfferDocumentSerializer(many=True, read_only=True)
    documents_count = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = ['id', 'tender', 'tender_title', 'tender_reference', 'vendor', 'vendor_name', 'submitted_by',
                  'submitted_by_username', 'status', 'submitted_at', 'price', 'technical_score',
                  'financial_score', 'total_score', 'notes', 'documents', 'documents_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'submitted_by', 'submitted_at', 'status', 'technical_score',
                            'financial_score', 'total_score', 'created_at', 'updated_at', 'documents_count']

    def get_documents_count(self, obj):
        return obj.documents.count()

    def validate(self, data):
        """Ensure offer is for an active tender"""
        tender = data.get('tender')
        if tender and tender.status != 'published':
            raise serializers.ValidationError("Can only submit offers for published tenders")
        if tender and tender.submission_deadline < timezone.now():
            raise serializers.ValidationError("Submission deadline has passed")
        return data


class EvaluationCriteriaSerializer(serializers.ModelSerializer):
    """Serializer for EvaluationCriteria model"""

    class Meta:
        model = EvaluationCriteria
        fields = ['id', 'name', 'description', 'weight', 'max_score', 'category', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        """Ensure weight is between 0 and 100"""
        if 'weight' in data and (data['weight'] < 0 or data['weight'] > 100):
            raise serializers.ValidationError("Weight must be between 0 and 100")
        return data


class EvaluationSerializer(serializers.ModelSerializer):
    """Serializer for Evaluation model"""
    evaluator_username = serializers.CharField(source='evaluator.username', read_only=True)
    criteria_name = serializers.CharField(source='criteria.name', read_only=True)
    criteria_category = serializers.CharField(source='criteria.category', read_only=True)

    class Meta:
        model = Evaluation
        fields = ['id', 'offer', 'evaluator', 'evaluator_username', 'criteria', 'criteria_name',
                  'criteria_category', 'score', 'comment', 'created_at', 'updated_at']
        read_only_fields = ['id', 'evaluator', 'created_at', 'updated_at']

    def validate_score(self, value):
        """Ensure score doesn't exceed criteria max_score"""
        criteria = self.initial_data.get('criteria')
        if criteria:
            try:
                criteria_obj = EvaluationCriteria.objects.get(id=criteria)
                if value > criteria_obj.max_score:
                    raise serializers.ValidationError(f"Score cannot exceed {criteria_obj.max_score}")
            except EvaluationCriteria.DoesNotExist:
                pass
        return value


class ApprovalSerializer(serializers.ModelSerializer):
    """Serializer for Approval model"""
    user_username = serializers.CharField(source='user.username', read_only=True)
    tender_reference = serializers.CharField(source='tender.reference_number', read_only=True)

    class Meta:
        model = Approval
        fields = ['id', 'tender', 'tender_reference', 'user', 'user_username',
                  'status', 'comments', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for AuditLog model"""
    user_username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = ['id', 'user', 'user_username', 'action', 'entity_type', 'entity_id',
                  'details', 'ip_address', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']


class ReportSerializer(serializers.ModelSerializer):
    """Serializer for Report model"""
    generated_by_username = serializers.CharField(source='generated_by.username', read_only=True)
    tender_reference = serializers.CharField(source='tender.reference_number', read_only=True)

    class Meta:
        model = Report
        fields = ['id', 'tender', 'tender_reference', 'generated_by', 'generated_by_username',
                  'report_type', 'filename', 'file_path', 'created_at']
        read_only_fields = ['id', 'generated_by', 'created_at']


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model"""

    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'message', 'type', 'is_read',
                  'related_entity_type', 'related_entity_id', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

    def update(self, instance, validated_data):
        """Allow updating only is_read field"""
        if 'is_read' in validated_data:
            instance.is_read = validated_data['is_read']
            instance.save()
        return instance


# Nested serializers for detailed views
class TenderDetailSerializer(TenderSerializer):
    """Detailed serializer for Tender model with all related data"""
    offers = OfferSerializer(many=True, read_only=True)
    evaluation_criteria = EvaluationCriteriaSerializer(many=True, read_only=True)
    approvals = ApprovalSerializer(many=True, read_only=True)
    reports = ReportSerializer(many=True, read_only=True)

    class Meta(TenderSerializer.Meta):
        fields = TenderSerializer.Meta.fields + ['offers', 'evaluation_criteria', 'approvals', 'reports']


class OfferDetailSerializer(OfferSerializer):
    """Detailed serializer for Offer model with all related data"""
    evaluations = EvaluationSerializer(many=True, read_only=True)

    class Meta(OfferSerializer.Meta):
        fields = OfferSerializer.Meta.fields + ['evaluations']


class VendorCompanyDetailSerializer(VendorCompanySerializer):
    """Detailed serializer for VendorCompany model with offers and users"""
    offers = OfferSerializer(many=True, read_only=True)
    
    class Meta(VendorCompanySerializer.Meta):
        fields = VendorCompanySerializer.Meta.fields + ['offers']