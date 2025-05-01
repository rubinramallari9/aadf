# server/aadf/tests.py

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    VendorCompany, Tender, TenderRequirement, TenderDocument,
    Offer, OfferDocument, EvaluationCriteria, Evaluation
)


class UserModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.user = self.User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com',
            role='staff'
        )

    def test_user_creation(self):
        """Test user creation with custom role"""
        self.assertEqual(self.user.role, 'staff')
        self.assertTrue(self.user.is_active)
        self.assertEqual(str(self.user), 'testuser')

    def test_user_role_choices(self):
        """Test that user roles are properly handled"""
        vendor_user = self.User.objects.create_user(
            username='vendor1',
            password='testpass123',
            role='vendor'
        )
        self.assertEqual(vendor_user.role, 'vendor')


class VendorCompanyModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.vendor_user = self.User.objects.create_user(
            username='vendor1',
            password='testpass123',
            role='vendor'
        )
        self.vendor_company = VendorCompany.objects.create(
            name='Test Vendor Co.',
            registration_number='VND123',
            email='vendor@example.com'
        )
        self.vendor_company.users.add(self.vendor_user)

    def test_vendor_company_creation(self):
        """Test vendor company creation"""
        self.assertEqual(self.vendor_company.name, 'Test Vendor Co.')
        self.assertEqual(str(self.vendor_company), 'Test Vendor Co.')

    def test_vendor_user_association(self):
        """Test association between vendor company and users"""
        self.assertIn(self.vendor_user, self.vendor_company.users.all())
        self.assertIn(self.vendor_company, self.vendor_user.vendor_companies.all())


class TenderModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.staff_user = self.User.objects.create_user(
            username='staff1',
            password='testpass123',
            role='staff'
        )
        self.tender = Tender.objects.create(
            title='Test Tender',
            description='Test Description',
            reference_number='TND-20240501-ABCD',
            submission_deadline=timezone.now() + timezone.timedelta(days=7),
            created_by=self.staff_user
        )

    def test_tender_creation(self):
        """Test tender creation"""
        self.assertEqual(self.tender.title, 'Test Tender')
        self.assertEqual(self.tender.status, 'draft')
        self.assertEqual(str(self.tender), 'TND-20240501-ABCD - Test Tender')

    def test_tender_status_transitions(self):
        """Test tender status changes"""
        self.assertEqual(self.tender.status, 'draft')

        # Publish tender
        self.tender.status = 'published'
        self.tender.published_at = timezone.now()
        self.tender.save()
        self.assertEqual(self.tender.status, 'published')
        self.assertIsNotNone(self.tender.published_at)


class OfferModelTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.vendor_user = self.User.objects.create_user(
            username='vendor1',
            password='testpass123',
            role='vendor'
        )
        self.vendor_company = VendorCompany.objects.create(
            name='Test Vendor Co.'
        )
        self.vendor_company.users.add(self.vendor_user)

        self.tender = Tender.objects.create(
            title='Test Tender',
            description='Test Description',
            reference_number='TND-20240501-ABCD',
            submission_deadline=timezone.now() + timezone.timedelta(days=7),
            status='published'
        )

        self.offer = Offer.objects.create(
            tender=self.tender,
            vendor=self.vendor_company,
            submitted_by=self.vendor_user,
            price=1000.00
        )

    def test_offer_creation(self):
        """Test offer creation"""
        self.assertEqual(self.offer.status, 'draft')
        self.assertEqual(self.offer.price, 1000.00)
        self.assertEqual(str(self.offer), f"{self.tender.reference_number} - {self.vendor_company.name}")

    def test_offer_submission(self):
        """Test offer submission"""
        self.offer.status = 'submitted'
        self.offer.save()
        self.assertEqual(self.offer.status, 'submitted')
        self.assertIsNotNone(self.offer.submitted_at)


class EvaluationTest(TestCase):
    def setUp(self):
        self.User = get_user_model()
        self.evaluator = self.User.objects.create_user(
            username='evaluator1',
            password='testpass123',
            role='evaluator'
        )

        self.tender = Tender.objects.create(
            title='Test Tender',
            description='Test Description',
            reference_number='TND-20240501-ABCD',
            submission_deadline=timezone.now() + timezone.timedelta(days=7),
            status='published'
        )

        self.vendor_company = VendorCompany.objects.create(
            name='Test Vendor Co.'
        )

        self.offer = Offer.objects.create(
            tender=self.tender,
            vendor=self.vendor_company,
            price=1000.00
        )

        self.criteria = EvaluationCriteria.objects.create(
            tender=self.tender,
            name='Technical Quality',
            weight=70,
            max_score=100,
            category='technical'
        )

    def test_evaluation_creation(self):
        """Test evaluation creation"""
        evaluation = Evaluation.objects.create(
            offer=self.offer,
            evaluator=self.evaluator,
            criteria=self.criteria,
            score=85.5,
            comment='Good technical quality'
        )

        self.assertEqual(evaluation.score, 85.5)
        self.assertEqual(evaluation.comment, 'Good technical quality')