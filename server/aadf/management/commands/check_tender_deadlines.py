# server/aadf/management/commands/check_tender_deadlines.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from aadf.models import Tender
from aadf.utils import notify_tender_closed


class Command(BaseCommand):
    help = 'Check for tenders that have passed their deadline and close them'

    def handle(self, *args, **options):
        now = timezone.now()
        tenders_to_close = Tender.objects.filter(
            status='published',
            submission_deadline__lt=now
        )

        closed_count = 0
        for tender in tenders_to_close:
            tender.status = 'closed'
            tender.save()

            # Notify relevant users
            notify_tender_closed(tender)

            closed_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Successfully closed tender "{tender.reference_number}"')
            )

        if closed_count == 0:
            self.stdout.write(self.style.WARNING('No tenders to close'))
        else:
            self.stdout.write(
                self.style.SUCCESS(f'Successfully closed {closed_count} tenders')
            )