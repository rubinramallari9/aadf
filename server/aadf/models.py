from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import UserManager

class CustomUserManager(UserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')  # Set role to admin
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
            
        return self._create_user(username, email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model with additional fields"""
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('staff', 'Staff'),
        ('vendor', 'Vendor'),
        ('evaluator', 'Evaluator'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='staff')
    is_active = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='aadf_user_set',
        related_query_name='aadf_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='aadf_user_set',
        related_query_name='aadf_user',
    )

    objects = CustomUserManager()  # Use the custom manager

    class Meta:
        db_table = 'users'


class VendorCompany(models.Model):
    """Vendor company information"""
    name = models.CharField(max_length=255)
    registration_number = models.CharField(max_length=100, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    users = models.ManyToManyField(User, through='VendorUser', related_name='vendor_companies')

    class Meta:
        db_table = 'vendor_companies'
        verbose_name_plural = 'Vendor Companies'

    def __str__(self):
        return self.name


class VendorUser(models.Model):
    """Link between vendor users and companies"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    company = models.ForeignKey(VendorCompany, on_delete=models.CASCADE)

    class Meta:
        db_table = 'vendor_users'
        unique_together = ('user', 'company')


class Tender(models.Model):
    """Main tender information"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('closed', 'Closed'),
        ('awarded', 'Awarded'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_tenders')
    published_at = models.DateTimeField(null=True, blank=True)
    submission_deadline = models.DateTimeField()
    opening_date = models.DateTimeField(null=True, blank=True)
    reference_number = models.CharField(max_length=50, unique=True)
    estimated_value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tenders'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.reference_number} - {self.title}"


class TenderRequirement(models.Model):
    """Tender requirements"""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='requirements')
    description = models.TextField()
    document_type = models.CharField(max_length=100, blank=True, null=True)
    is_mandatory = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tender_requirements'

    def __str__(self):
        return f"{self.tender.reference_number} - {self.description[:50]}"


class TenderDocument(models.Model):
    """Tender documents (specifications, terms, etc.)"""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='documents')
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_path = models.TextField()
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'tender_documents'

    def __str__(self):
        return f"{self.tender.reference_number} - {self.original_filename}"


class Offer(models.Model):
    """Vendor offers/proposals"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('evaluated', 'Evaluated'),
        ('awarded', 'Awarded'),
        ('rejected', 'Rejected'),
    ]

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='offers')
    vendor = models.ForeignKey(VendorCompany, on_delete=models.CASCADE, related_name='offers')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='draft')
    submitted_at = models.DateTimeField(null=True, blank=True)
    price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    technical_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    financial_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'offers'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tender.reference_number} - {self.vendor.name}"

    def save(self, *args, **kwargs):
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        super().save(*args, **kwargs)


class OfferDocument(models.Model):
    """Offer documents"""
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='documents')
    filename = models.CharField(max_length=255)
    original_filename = models.CharField(max_length=255)
    file_path = models.TextField()
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    document_type = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'offer_documents'

    def __str__(self):
        return f"{self.offer.tender.reference_number} - {self.offer.vendor.name} - {self.original_filename}"


class EvaluationCriteria(models.Model):
    """Evaluation criteria for tenders"""
    CATEGORY_CHOICES = [
        ('technical', 'Technical'),
        ('financial', 'Financial'),
        ('other', 'Other'),
    ]

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='evaluation_criteria')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    weight = models.DecimalField(max_digits=5, decimal_places=2)
    max_score = models.DecimalField(max_digits=5, decimal_places=2)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='technical')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'evaluation_criteria'
        verbose_name_plural = 'Evaluation Criteria'

    def __str__(self):
        return f"{self.tender.reference_number} - {self.name}"


class Evaluation(models.Model):
    """Evaluations of offers"""
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='evaluations')
    evaluator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='evaluations')
    criteria = models.ForeignKey(EvaluationCriteria, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'evaluations'
        unique_together = ('offer', 'evaluator', 'criteria')

    def __str__(self):
        return f"{self.offer.tender.reference_number} - {self.evaluator.username} - {self.criteria.name}"


class Approval(models.Model):
    """Workflow approvals"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='approvals')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='approvals')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'approvals'

    def __str__(self):
        return f"{self.tender.reference_number} - {self.user.username} - {self.status}"

class DocumentVersion(models.Model):
    """Document version history"""
    # Common fields
    original_filename = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    file_path = models.TextField()
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    version_number = models.PositiveIntegerField()
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # For identifying the parent document
    document_type = models.CharField(max_length=50)  # 'tender' or 'offer'
    document_id = models.IntegerField()
    
    # Change description
    change_description = models.TextField(blank=True, null=True)
    
    class Meta:
        db_table = 'document_versions'
        ordering = ['-version_number']
        
    def __str__(self):
        return f"v{self.version_number} - {self.original_filename}"

class AuditLog(models.Model):
    """Audit logs for tracking user actions"""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=50)
    entity_id = models.IntegerField()
    details = models.JSONField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username if self.user else 'Unknown'} - {self.action} - {self.entity_type}:{self.entity_id}"

class Report(models.Model):
    """Generated reports"""
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='reports', null=True, blank=True)  # Make optional
    generated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    report_type = models.CharField(max_length=50)
    filename = models.CharField(max_length=255)
    file_path = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'reports'
        ordering = ['-created_at']

    def __str__(self):
        if self.tender:
            return f"{self.tender.reference_number} - {self.report_type}"
        else:
            return f"System Report - {self.report_type}"
        
class Notification(models.Model):
    """System notifications"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)
    related_entity_type = models.CharField(max_length=50, blank=True, null=True)
    related_entity_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.title}"