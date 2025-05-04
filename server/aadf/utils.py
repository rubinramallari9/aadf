# server/aadf/utils.py

import os
import uuid
import logging
import json
from datetime import datetime
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Avg, Sum

logger = logging.getLogger(__name__)


def generate_reference_number(prefix=None, length=None):
    """Generate a unique reference number"""
    prefix = prefix or settings.PROCUREMENT_SETTINGS.get('TENDER_REFERENCE_PREFIX', 'TND')
    length = length or settings.PROCUREMENT_SETTINGS.get('TENDER_REFERENCE_LENGTH', 8)

    # Generate a unique number based on timestamp and UUID
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = uuid.uuid4().hex[:length].upper()

    return f"{prefix}-{timestamp}-{unique_id}"


def save_uploaded_file(file, directory, filename=None):
    """Save an uploaded file with a unique filename"""
    if not filename:
        filename = f"{uuid.uuid4().hex}{os.path.splitext(file.name)[1]}"

    # Ensure the directory exists
    full_directory = os.path.join(settings.MEDIA_ROOT, directory)
    os.makedirs(full_directory, exist_ok=True)

    # Save the file
    file_path = os.path.join(directory, filename)
    full_path = os.path.join(settings.MEDIA_ROOT, file_path)

    with open(full_path, 'wb+') as destination:
        for chunk in file.chunks():
            destination.write(chunk)

    return file_path, filename


def validate_file_extension(filename):
    """Validate file extension against allowed extensions"""
    allowed_extensions = settings.PROCUREMENT_SETTINGS.get('DOCUMENT_ALLOWED_EXTENSIONS', [])
    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def validate_file_size(file):
    """Validate file size against maximum allowed size"""
    max_size = settings.PROCUREMENT_SETTINGS.get('DOCUMENT_MAX_FILE_SIZE', 10 * 1024 * 1024)
    return file.size <= max_size


def calculate_offer_score(offer):
    """Calculate total score for an offer based on evaluations"""
    from .models import Evaluation, EvaluationCriteria
    
    evaluations = Evaluation.objects.filter(offer=offer)

    if not evaluations.exists():
        return None

    # Calculate technical score
    technical_criteria = EvaluationCriteria.objects.filter(
        tender=offer.tender,
        category='technical'
    )
    technical_evaluations = evaluations.filter(criteria__category='technical')
    
    if technical_criteria.exists() and technical_evaluations.exists():
        total_weight = technical_criteria.aggregate(Sum('weight'))['weight__sum'] or 0
        weighted_scores = 0
        
        for evaluation in technical_evaluations:
            criteria_weight = evaluation.criteria.weight
            criteria_max_score = evaluation.criteria.max_score
            normalized_score = (evaluation.score / criteria_max_score) * criteria_weight
            weighted_scores += normalized_score
            
        technical_score = (weighted_scores / total_weight) * 100 if total_weight > 0 else 0
        offer.technical_score = round(technical_score, 2)
    else:
        offer.technical_score = None

    # Calculate financial score
    # Financial score is calculated by comparing with other offers
    if offer.price and offer.price > 0:
        from .models import Offer
        lowest_price = Offer.objects.filter(
            tender=offer.tender,
            status='submitted',
            price__gt=0
        ).order_by('price').first()
        
        if lowest_price:
            financial_score = (lowest_price.price / offer.price) * 100
            offer.financial_score = round(financial_score, 2)
        else:
            offer.financial_score = 100  # If only one offer
    else:
        offer.financial_score = None

    # Calculate total score
    if offer.technical_score is not None and offer.financial_score is not None:
        technical_weight = settings.PROCUREMENT_SETTINGS.get('DEFAULT_EVALUATION_WEIGHT_TECHNICAL', 70)
        financial_weight = settings.PROCUREMENT_SETTINGS.get('DEFAULT_EVALUATION_WEIGHT_FINANCIAL', 30)
        
        total_score = (
            (offer.technical_score * technical_weight / 100) +
            (offer.financial_score * financial_weight / 100)
        )
        offer.total_score = round(total_score, 2)
    else:
        offer.total_score = None

    # Save the offer with updated scores
    offer.save(update_fields=['technical_score', 'financial_score', 'total_score'])
    
    return offer.total_score


def create_notification(user, title, message, notification_type='info', related_entity=None):
    """Create a notification for a user"""
    from .models import Notification
    
    notification_data = {
        'user': user,
        'title': title,
        'message': message,
        'type': notification_type,
    }

    if related_entity:
        notification_data['related_entity_type'] = related_entity.__class__.__name__.lower()
        notification_data['related_entity_id'] = related_entity.id

    notification = Notification.objects.create(**notification_data)

    # Send email if enabled
    if settings.PROCUREMENT_SETTINGS.get('NOTIFICATION_EMAIL_ENABLED', False) and user.email:
        send_notification_email(user, title, message)

    return notification


def send_notification_email(user, title, message):
    """Send email notification to user"""
    try:
        context = {
            'user': user,
            'title': title,
            'message': message,
        }

        # Use a simple text template if HTML template is not available
        try:
            email_content = render_to_string('notifications/email.html', context)
        except:
            email_content = f"""
            Hello {user.first_name or user.username},
            
            {title}
            
            {message}
            
            Best regards,
            AADF Procurement Platform
            """

        send_mail(
            subject=title,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=email_content,
            fail_silently=False,
        )
    except Exception as e:
        logger.error(f"Failed to send email notification: {e}")


def check_tender_deadlines():
    """Check for tenders that have passed their deadline and close them"""
    from .models import Tender
    
    if not settings.PROCUREMENT_SETTINGS.get('AUTO_CLOSE_TENDERS', True):
        return

    now = timezone.now()
    tenders_to_close = Tender.objects.filter(
        status='published',
        submission_deadline__lt=now
    )

    for tender in tenders_to_close:
        tender.status = 'closed'
        tender.save(update_fields=['status'])

        # Notify relevant users
        notify_tender_closed(tender)

        logger.info(f"Tender {tender.reference_number} automatically closed")


def notify_tender_closed(tender):
    """Notify users when a tender is closed"""
    # Notify staff who created the tender
    if tender.created_by:
        create_notification(
            user=tender.created_by,
            title='Tender Closed',
            message=f'Tender {tender.reference_number} has been closed automatically.',
            notification_type='info',
            related_entity=tender
        )

    # Notify staff users
    from .models import User
    staff_users = User.objects.filter(role__in=['staff', 'admin'])
    for user in staff_users:
        if user != tender.created_by:  # Don't notify twice
            create_notification(
                user=user,
                title='Tender Closed',
                message=f'Tender {tender.reference_number} has been closed.',
                notification_type='info',
                related_entity=tender
            )

    # Notify evaluators
    evaluators = User.objects.filter(role='evaluator')
    for evaluator in evaluators:
        create_notification(
            user=evaluator,
            title='Tender Ready for Evaluation',
            message=f'Tender {tender.reference_number} has been closed and is ready for evaluation.',
            notification_type='info',
            related_entity=tender
        )

    # Notify vendors who submitted offers
    for offer in tender.offers.all():
        if offer.vendor.users.exists():
            for user in offer.vendor.users.all():
                create_notification(
                    user=user,
                    title='Tender Closed',
                    message=f'Tender {tender.reference_number} has been closed. Your offer is now under evaluation.',
                    notification_type='info',
                    related_entity=offer
                )


def generate_tender_report(tender):
    """Generate a report for a tender with all relevant information"""
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        from io import BytesIO

        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Add header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 50, f"Tender Report: {tender.reference_number}")
        
        # Add tender information
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 80, f"Title: {tender.title}")
        p.drawString(100, height - 100, f"Status: {tender.status}")
        p.drawString(100, height - 120, f"Published: {tender.published_at}")
        p.drawString(100, height - 140, f"Deadline: {tender.submission_deadline}")
        p.drawString(100, height - 160, f"Category: {tender.category or 'N/A'}")

        # Add offers information
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 190, "Offers Information")
        
        y_position = height - 220
        for offer in tender.offers.filter(status__in=['submitted', 'evaluated', 'awarded']):
            p.setFont("Helvetica-Bold", 12)
            p.drawString(100, y_position, f"Vendor: {offer.vendor.name}")
            
            p.setFont("Helvetica", 12)
            p.drawString(120, y_position - 20, f"Price: {offer.price}")
            p.drawString(120, y_position - 40, f"Technical Score: {offer.technical_score}")
            p.drawString(120, y_position - 60, f"Financial Score: {offer.financial_score}")
            p.drawString(120, y_position - 80, f"Total Score: {offer.total_score}")
            p.drawString(120, y_position - 100, f"Status: {offer.status}")
            
            y_position -= 120
            
            # Check if we need a new page
            if y_position < 100:
                p.showPage()
                y_position = height - 50
                p.setFont("Helvetica-Bold", 14)
                p.drawString(100, y_position, "Offers Information (continued)")
                y_position -= 30

        # Add evaluation information if any
        if tender.evaluation_criteria.exists():
            if y_position < 200:  # Not enough space, add a new page
                p.showPage()
                y_position = height - 50
            
            p.setFont("Helvetica-Bold", 14)
            p.drawString(100, y_position, "Evaluation Criteria")
            y_position -= 30
            
            for criteria in tender.evaluation_criteria.all():
                p.setFont("Helvetica", 12)
                p.drawString(120, y_position, f"{criteria.name} (Weight: {criteria.weight}%)")
                y_position -= 20
                
                if y_position < 100:
                    p.showPage()
                    y_position = height - 50

        p.showPage()
        p.save()

        buffer.seek(0)
        return buffer
    except Exception as e:
        logger.error(f"Error generating tender report: {e}")
        return None


def export_tender_data(tender):
    """Export tender data to CSV format"""
    try:
        import csv
        from io import StringIO

        output = StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            'Tender Reference', 'Vendor', 'Price', 'Technical Score', 
            'Financial Score', 'Total Score', 'Status', 'Submitted At'
        ])

        # Write offer data
        for offer in tender.offers.all():
            writer.writerow([
                tender.reference_number,
                offer.vendor.name,
                offer.price or 'N/A',
                offer.technical_score or 'N/A',
                offer.financial_score or 'N/A',
                offer.total_score or 'N/A',
                offer.status,
                offer.submitted_at
            ])

        output.seek(0)
        return output
    except Exception as e:
        logger.error(f"Error exporting tender data: {e}")
        return None


def clean_corrupted_evaluations():
    """Clean up any corrupted evaluation data"""
    from .models import Evaluation
    from django.db.models import F
    
    try:
        # Find evaluations with scores outside the valid range
        invalid_evaluations = Evaluation.objects.filter(score__lt=0) | Evaluation.objects.filter(score__gt=F('criteria__max_score'))
        
        count = invalid_evaluations.count()
        if count > 0:
            logger.warning(f"Found {count} invalid evaluations, cleaning up...")
            for evaluation in invalid_evaluations:
                criteria = evaluation.criteria
                if evaluation.score < 0:
                    evaluation.score = 0
                elif evaluation.score > criteria.max_score:
                    evaluation.score = criteria.max_score
                evaluation.save()
                logger.info(f"Fixed evaluation #{evaluation.id} score to {evaluation.score}")
        
        return count
    except Exception as e:
        logger.error(f"Error cleaning corrupted evaluations: {e}")
        return 0


def recalculate_all_offer_scores():
    """Recalculate scores for all submitted offers"""
    from .models import Offer
    
    try:
        offers = Offer.objects.filter(status__in=['submitted', 'evaluated', 'awarded'])
        count = 0
        
        for offer in offers:
            calculate_offer_score(offer)
            count += 1
            
        logger.info(f"Recalculated scores for {count} offers")
        return count
    except Exception as e:
        logger.error(f"Error recalculating offer scores: {e}")
        return 0


def generate_offer_audit_trail(offer):
    """Generate an audit trail for an offer"""
    from .models import AuditLog
    
    try:
        # Get all audit logs related to this offer
        logs = AuditLog.objects.filter(
            entity_type='offer',
            entity_id=offer.id
        ).order_by('created_at')
        
        audit_trail = []
        for log in logs:
            event = {
                'timestamp': log.created_at,
                'user': log.user.username if log.user else 'System',
                'action': log.action,
                'details': log.details or {}
            }
            audit_trail.append(event)
        
        # Add evaluations as events
        for evaluation in offer.evaluations.all():
            event = {
                'timestamp': evaluation.created_at,
                'user': evaluation.evaluator.username,
                'action': 'evaluate',
                'details': {
                    'criteria': evaluation.criteria.name,
                    'score': evaluation.score,
                    'comment': evaluation.comment
                }
            }
            audit_trail.append(event)
        
        # Sort by timestamp
        audit_trail.sort(key=lambda x: x['timestamp'])
        
        return audit_trail
    except Exception as e:
        logger.error(f"Error generating offer audit trail: {e}")
        return []


def get_vendor_statistics(vendor):
    """Get statistics for a vendor"""
    from .models import Offer
    
    try:
        offers = Offer.objects.filter(vendor=vendor)
        
        stats = {
            'total_offers': offers.count(),
            'submitted_offers': offers.filter(status='submitted').count(),
            'awarded_offers': offers.filter(status='awarded').count(),
            'rejected_offers': offers.filter(status='rejected').count(),
            'average_score': offers.filter(total_score__isnull=False).aggregate(Avg('total_score'))['total_score__avg']
        }
        
        return stats
    except Exception as e:
        logger.error(f"Error getting vendor statistics: {e}")
        return {
            'total_offers': 0,
            'submitted_offers': 0,
            'awarded_offers': 0,
            'rejected_offers': 0,
            'average_score': None
        }


def get_dashboard_statistics():
    """Get statistics for the dashboard"""
    from .models import Tender, Offer, User, VendorCompany
    
    try:
        stats = {
            'tenders': {
                'total': Tender.objects.count(),
                'draft': Tender.objects.filter(status='draft').count(),
                'published': Tender.objects.filter(status='published').count(),
                'closed': Tender.objects.filter(status='closed').count(),
                'awarded': Tender.objects.filter(status='awarded').count(),
            },
            'offers': {
                'total': Offer.objects.count(),
                'draft': Offer.objects.filter(status='draft').count(),
                'submitted': Offer.objects.filter(status='submitted').count(),
                'evaluated': Offer.objects.filter(status='evaluated').count(),
                'awarded': Offer.objects.filter(status='awarded').count(),
                'rejected': Offer.objects.filter(status='rejected').count(),
            },
            'users': {
                'total': User.objects.count(),
                'admin': User.objects.filter(role='admin').count(),
                'staff': User.objects.filter(role='staff').count(),
                'vendor': User.objects.filter(role='vendor').count(),
                'evaluator': User.objects.filter(role='evaluator').count(),
            },
            'vendors': {
                'total': VendorCompany.objects.count()
            },
            'recent_tenders': Tender.objects.order_by('-created_at')[:5].values(
                'id', 'reference_number', 'title', 'status', 'created_at'
            ),
            'recent_offers': Offer.objects.order_by('-created_at')[:5].values(
                'id', 'tender__reference_number', 'vendor__name', 'status', 'created_at'
            )
        }
        
        return stats
    except Exception as e:
        logger.error(f"Error getting dashboard statistics: {e}")
        return {}


def generate_secure_document_link(document, expires_in_minutes=60):
    """Generate a secure time-limited link for document download"""
    import hashlib
    import time
    
    # Create an expiration timestamp
    expiration = int(time.time()) + (expires_in_minutes * 60)
    
    # Create a signature with document ID and expiration
    document_id = str(document.id)
    document_type = 'tender' if hasattr(document, 'tender') else 'offer'
    secret_key = settings.SECRET_KEY
    
    # Generate signature
    signature_data = f"{document_type}:{document_id}:{expiration}:{secret_key}"
    signature = hashlib.sha256(signature_data.encode()).hexdigest()
    
    # Create download URL
    download_url = f"/api/download/{document_type}/{document_id}/?expires={expiration}&signature={signature}"
    
    return download_url


def verify_document_signature(document_type, document_id, expires, signature):
    """Verify the signature for secure document download"""
    import hashlib
    import time
    
    # Check if expired
    current_time = int(time.time())
    if current_time > int(expires):
        return False
    
    # Recreate the signature
    secret_key = settings.SECRET_KEY
    signature_data = f"{document_type}:{document_id}:{expires}:{secret_key}"
    expected_signature = hashlib.sha256(signature_data.encode()).hexdigest()
    
    # Compare signatures
    return signature == expected_signature


def anonymize_personal_data(user_id, keep_username=True):
    """Anonymize personal data for a user (GDPR compliance)"""
    from .models import User
    
    try:
        user = User.objects.get(id=user_id)
        
        # Generate a random identifier to replace personal data
        random_id = uuid.uuid4().hex[:8]
        
        # Anonymize user data
        if not keep_username:
            user.username = f"deleted_user_{random_id}"
        
        user.first_name = ""
        user.last_name = ""
        user.email = f"deleted_{random_id}@example.com"
        
        # Save anonymized user
        user.save(update_fields=['username', 'first_name', 'last_name', 'email'])
        
        logger.info(f"Anonymized personal data for user {user_id}")
        return True
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for anonymization")
        return False
    except Exception as e:
        logger.error(f"Error anonymizing user data: {e}")
        return False


def log_system_event(event_type, details=None):
    """Log a system event in the audit log"""
    from .models import AuditLog, User
    
    try:
        # Try to find a system user or admin
        system_user = User.objects.filter(role='admin', is_active=True).first()
        
        details = details or {}
        details['event_type'] = event_type
        
        AuditLog.objects.create(
            user=system_user,
            action='system',
            entity_type='system',
            entity_id=0,
            details=details,
            ip_address='127.0.0.1'
        )
        
        logger.info(f"System event logged: {event_type}")
        return True
    except Exception as e:
        logger.error(f"Error logging system event: {e}")
        return False

def generate_secure_document_link(document, expires_in_minutes=60):
    """Generate a unique reference number"""
    import hashlib
    import time
    
    # Create an expiration timestamp
    expiration = int(time.time()) + (expires_in_minutes * 60)
    
    # Create a signature with document ID and expiration
    document_id = str(document.id)
    document_type = 'tender' if hasattr(document, 'tender') and not hasattr(document, 'vendor') else \
                    'offer' if hasattr(document, 'tender') and hasattr(document, 'vendor') else 'report'
    secret_key = settings.SECRET_KEY
    
    # Generate signature
    signature_data = f"{document_type}:{document_id}:{expiration}:{secret_key}"
    signature = hashlib.sha256(signature_data.encode()).hexdigest()
    
    # Create download URL
    download_url = f"/api/download/{document_type}/{document_id}/?expires={expiration}&signature={signature}"
    
    return download_url

def verify_document_signature(document_type, document_id, expires, signature):
    """Verify the signature for secure document download"""
    import hashlib
    import time
    
    # Check if expired
    current_time = int(time.time())
    if current_time > int(expires):
        return False
    
    # Recreate the signature
    secret_key = settings.SECRET_KEY
    signature_data = f"{document_type}:{document_id}:{expires}:{secret_key}"
    expected_signature = hashlib.sha256(signature_data.encode()).hexdigest()
    
    # Compare signatures
    return signature == expected_signature