# server/aadf/utils.py

import os
import uuid
import logging
from datetime import datetime
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from .models import Tender, Notification

logger = logging.getLogger(__name__)


def generate_reference_number(prefix=None, length=None):
    """Generate a unique reference number"""
    prefix = prefix or settings.PROCUREMENT_SETTINGS.get('TENDER_REFERENCE_PREFIX', 'TND')
    length = length or settings.PROCUREMENT_SETTINGS.get('TENDER_REFERENCE_LENGTH', 8)

    # Generate a unique number based on timestamp and UUID
    timestamp = datetime.now().strftime('%Y%m%d')
    unique_id = uuid.uuid4().hex[:4].upper()

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
    evaluations = offer.evaluations.all()

    if not evaluations:
        return None

    total_score = 0
    total_weight = 0

    for evaluation in evaluations:
        criteria = evaluation.criteria
        weighted_score = (evaluation.score / criteria.max_score) * criteria.weight
        total_score += weighted_score
        total_weight += criteria.weight

    if total_weight > 0:
        return total_score  # Already weighted
    return None


def create_notification(user, title, message, notification_type='info', related_entity=None):
    """Create a notification for a user"""
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
    if settings.PROCUREMENT_SETTINGS.get('NOTIFICATION_EMAIL_ENABLED', False):
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

        email_content = render_to_string('notifications/email.html', context)

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
    if not settings.PROCUREMENT_SETTINGS.get('AUTO_CLOSE_TENDERS', True):
        return

    now = timezone.now()
    tenders_to_close = Tender.objects.filter(
        status='published',
        submission_deadline__lt=now
    )

    for tender in tenders_to_close:
        tender.status = 'closed'
        tender.save()

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
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from io import BytesIO

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)

    # Add content to PDF
    p.drawString(100, 750, f"Tender Report: {tender.reference_number}")
    p.drawString(100, 730, f"Title: {tender.title}")
    p.drawString(100, 710, f"Status: {tender.status}")
    p.drawString(100, 690, f"Published: {tender.published_at}")
    p.drawString(100, 670, f"Deadline: {tender.submission_deadline}")

    # Add offers information
    y_position = 650
    for offer in tender.offers.all():
        p.drawString(100, y_position, f"Offer from: {offer.vendor.name}")
        p.drawString(120, y_position - 20, f"Price: {offer.price}")
        p.drawString(120, y_position - 40, f"Score: {offer.total_score}")
        y_position -= 80

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer


def export_tender_data(tender):
    """Export tender data to CSV format"""
    import csv
    from io import StringIO

    output = StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(['Vendor', 'Price', 'Technical Score', 'Financial Score', 'Total Score', 'Status'])

    # Write offer data
    for offer in tender.offers.all():
        writer.writerow([
            offer.vendor.name,
            offer.price,
            offer.technical_score,
            offer.financial_score,
            offer.total_score,
            offer.status
        ])

    output.seek(0)
    return output