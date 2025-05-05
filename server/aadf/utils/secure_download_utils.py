# server/aadf/utils/secure_download_utils.py

import hashlib
import time
import logging
from django.conf import settings
from urllib.parse import urljoin

logger = logging.getLogger('aadf')

def generate_secure_document_link(document, expires_in_minutes=60, base_url=None):
    """
    Generate a secure time-limited link for document download
    
    Args:
        document: The document object (TenderDocument, OfferDocument, or Report)
        expires_in_minutes: How long the link should be valid, in minutes
        base_url: Optional base URL, defaults to settings.BASE_URL if not provided
    
    Returns:
        A string containing the secure download URL
    """
    try:
        # Create an expiration timestamp
        expiration = int(time.time()) + (expires_in_minutes * 60)
        
        # Determine document type
        if hasattr(document, 'tender') and hasattr(document, 'offer'):
            document_type = 'offer'
        elif hasattr(document, 'tender') and not hasattr(document, 'offer'):
            document_type = 'tender'
        else:
            document_type = 'report'
        
        document_id = str(document.id)
        secret_key = settings.SECRET_KEY
        
        # Generate signature
        signature_data = f"{document_type}:{document_id}:{expiration}:{secret_key}"
        signature = hashlib.sha256(signature_data.encode()).hexdigest()
        
        # Create the relative download URL path
        relative_url = f"/api/download/{document_type}/{document_id}/?expires={expiration}&signature={signature}"
        
        # If base_url is provided, create an absolute URL
        if base_url:
            return urljoin(base_url, relative_url)
        
        # Otherwise return the relative URL
        return relative_url
        
    except Exception as e:
        logger.error(f"Error generating secure download link: {str(e)}")
        return None

def verify_document_signature(document_type, document_id, expires, signature):
    """
    Verify the signature for secure document download
    
    Args:
        document_type: Type of document ('tender', 'offer', 'report')
        document_id: ID of the document
        expires: Expiration timestamp
        signature: The signature to verify
    
    Returns:
        Boolean indicating whether the signature is valid and not expired
    """
    try:
        # Check if expired
        current_time = int(time.time())
        if current_time > int(expires):
            logger.warning(f"Secure download link expired for {document_type}:{document_id}")
            return False
        
        # Recreate the signature
        secret_key = settings.SECRET_KEY
        signature_data = f"{document_type}:{document_id}:{expires}:{secret_key}"
        expected_signature = hashlib.sha256(signature_data.encode()).hexdigest()
        
        # Compare signatures
        is_valid = signature == expected_signature
        
        if not is_valid:
            logger.warning(f"Invalid signature for {document_type}:{document_id}")
            
        return is_valid
        
    except Exception as e:
        logger.error(f"Error verifying document signature: {str(e)}")
        return False