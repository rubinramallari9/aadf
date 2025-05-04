# server/aadf/models/document_models.py

from django.db import models
from django.utils import timezone
from django.conf import settings

class DocumentVersion(models.Model):
    """Document version history"""
    # Common fields
    original_filename = models.CharField(max_length=255)
    filename = models.CharField(max_length=255)
    file_path = models.TextField()
    file_size = models.IntegerField(null=True, blank=True)
    mime_type = models.CharField(max_length=100, blank=True, null=True)
    version_number = models.PositiveIntegerField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
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