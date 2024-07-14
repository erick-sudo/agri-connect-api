from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from dashboard.models import (
    CustomUser, Category, CategoryRelation, Advertisement, AdvertisementPhoto,
    Reviews, SubscriptionPackage, Offering, PaymentMethods, Payment, Subscription,
    FeaturedAdvertisement, IndividualMail, BulkMail, MailAttachment
)
from django.contrib.contenttypes.models import ContentType
import uuid
from datetime import datetime, timedelta

class CustomUserTests(TestCase):

    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )

    def test_user_creation(self):
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.last_name, 'Doe')
        self.assertEqual(self.user.email, 'john.doe@example.com')
        self.assertEqual(self.user.phone, '1234567890')
        self.assertTrue(self.user.check_password('password123'))
        self.assertFalse(self.user.is_superuser)
        self.assertFalse(self.user.is_staff)

    def test_user_deactivate(self):
        self.user.deactivate()
        self.assertFalse(self.user.is_active)

    def test_user_activate(self):
        self.user.deactivate()
        self.user.activate()
        self.assertTrue(self.user.is_active)

    def test_user_is_new(self):
        self.assertTrue(self.user.is_new)

class CategoryTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name='Fruits',
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )

    def test_category_creation(self):
        self.assertEqual(self.category.name, 'Fruits')
        self.assertEqual(self.category.classification, Category.ADVERT_CLASSIFICATION.FARM_PRODUCE)

    def test_category_hierarchy_level(self):
        self.assertEqual(self.category.hierarchy_level, 0)

    def test_category_clean(self):
        with self.assertRaises(ValidationError):
            self.category.parent = self.category
            self.category.clean()

class CategoryRelationTests(TestCase):

    def setUp(self):
        self.parent_category = Category.objects.create(
            name='Fruits',
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.child_category = Category.objects.create(
            name='Apples',
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE,
            parent=self.parent_category
        )
        self.category_relation = CategoryRelation.objects.create(
            parent=self.parent_category,
            child=self.child_category
        )

    def test_category_relation_creation(self):
        self.assertEqual(self.category_relation.parent, self.parent_category)
        self.assertEqual(self.category_relation.child, self.child_category)

class AdvertisementTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.category = Category.objects.create(
            name='Fruits',
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.advertisement = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title='Fresh Apples',
            description='Fresh apples for sale',
            county='Nairobi',
            sub_county='Westlands'
        )

    def test_advertisement_creation(self):
        self.assertEqual(self.advertisement.title, 'Fresh Apples')
        self.assertEqual(self.advertisement.description, 'Fresh apples for sale')
        self.assertEqual(self.advertisement.county, 'Nairobi')
        self.assertEqual(self.advertisement.sub_county, 'Westlands')

    def test_advertisement_is_new(self):
        self.assertTrue(self.advertisement.is_new())

class AdvertisementPhotoTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.category = Category.objects.create(
            name='Fruits',
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.advertisement = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title='Fresh Apples',
            description='Fresh apples for sale',
            county='Nairobi',
            sub_county='Westlands'
        )
        self.advertisement_photo = AdvertisementPhoto.objects.create(
            advert=self.advertisement,
            photo='path/to/photo.jpg'
        )

    def test_advertisement_photo_creation(self):
        self.assertEqual(self.advertisement_photo.advert, self.advertisement)
        self.assertEqual(self.advertisement_photo.photo, 'path/to/photo.jpg')

class ReviewsTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.category = Category.objects.create(
            name='Fruits',
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.advertisement = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title='Fresh Apples',
            description='Fresh apples for sale',
            county='Nairobi',
            sub_county='Westlands'
        )
        self.review = Reviews.objects.create(
            advertisement=self.advertisement,
            message='Great product!',
            rating=Reviews.RatingChoices.five
        )

    def test_review_creation(self):
        self.assertEqual(self.review.advertisement, self.advertisement)
        self.assertEqual(self.review.message, 'Great product!')
        self.assertEqual(self.review.rating, Reviews.RatingChoices.five)

class SubscriptionPackageTests(TestCase):

    def setUp(self):
        self.package = SubscriptionPackage.objects.create(
            name='Basic Package',
            duration=30,
            pricing=100.00
        )

    def test_subscription_package_creation(self):
        self.assertEqual(self.package.name, 'Basic Package')
        self.assertEqual(self.package.duration, 30)
        self.assertEqual(self.package.pricing, 100.00)

class OfferingTests(TestCase):

    def setUp(self):
        self.package = SubscriptionPackage.objects.create(
            name='Basic Package',
            duration=30,
            pricing=100.00
        )
        self.offering = Offering.objects.create(
            package=self.package,
            offering='Basic Support'
        )

    def test_offering_creation(self):
        self.assertEqual(self.offering.package, self.package)
        self.assertEqual(self.offering.offering, 'Basic Support')

class PaymentMethodsTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.payment_method = PaymentMethods.objects.create(
            user=self.user,
            name='Mpesa',
            mpesa_phone_number='1234567890'
        )

    def test_payment_method_creation(self):
        self.assertEqual(self.payment_method.user, self.user)
        self.assertEqual(self.payment_method.name, 'Mpesa')
        self.assertEqual(self.payment_method.mpesa_phone_number, '1234567890')

class PaymentTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.payment = Payment.objects.create(
            user=self.user,
            transaction_type='Pay Bill',
            trans_id='12345',
            trans_time=datetime.now().astimezone(),
            trans_amount=100.00,
            business_short_code='123456',
            bill_ref_number='REF123',
            invoice_number='INV123',
            org_account_balance=1000.00,
            third_party_trans_id='TP123',
            msisdn='1234567890',
            first_name='John',
            middle_name='Middle',
            last_name='Doe'
        )

    def test_payment_creation(self):
        self.assertEqual(self.payment.user, self.user)
        self.assertEqual(self.payment.transaction_type, 'Pay Bill')
        self.assertEqual(self.payment.trans_id, '12345')
        self.assertEqual(self.payment.trans_amount, 100.00)
        self.assertEqual(self.payment.business_short_code, '123456')
        self.assertEqual(self.payment.bill_ref_number, 'REF123')
        self.assertEqual(self.payment.invoice_number, 'INV123')
        self.assertEqual(self.payment.org_account_balance, 1000.00)
        self.assertEqual(self.payment.third_party_trans_id, 'TP123')
        self.assertEqual(self.payment.msisdn, '1234567890')
        self.assertEqual(self.payment.first_name, 'John')
        self.assertEqual(self.payment.middle_name, 'Middle')
        self.assertEqual(self.payment.last_name, 'Doe')

class SubscriptionTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.package = SubscriptionPackage.objects.create(
            name='Basic Package',
            duration=30,
            pricing=100.00
        )
        self.payment = Payment.objects.create(
            user=self.user,
            transaction_type='Pay Bill',
            trans_id='12345',
            trans_time=datetime.now(),
            trans_amount=100.00,
            business_short_code='123456',
            bill_ref_number='REF123',
            invoice_number='INV123',
            org_account_balance=1000.00,
            third_party_trans_id='TP123',
            msisdn='1234567890',
            first_name='John',
            middle_name='Middle',
            last_name='Doe'
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            package=self.package,
            payment=self.payment,
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=30)).date(),
            active=True
        )

    def test_subscription_creation(self):
        self.assertEqual(self.subscription.user, self.user)
        self.assertEqual(self.subscription.package, self.package)
        self.assertEqual(self.subscription.payment, self.payment)
        self.assertEqual(self.subscription.start_date, datetime.now().date())
        self.assertEqual(self.subscription.end_date, (datetime.now() + timedelta(days=30)).date())
        self.assertTrue(self.subscription.active)

class FeaturedAdvertisementTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.category = Category.objects.create(
            name='Fruits',
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.advertisement = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title='Fresh Apples',
            description='Fresh apples for sale',
            county='Nairobi',
            sub_county='Westlands'
        )
        self.package = SubscriptionPackage.objects.create(
            name='Basic Package',
            duration=30,
            pricing=100.00
        )
        self.payment = Payment.objects.create(
            user=self.user,
            transaction_type='Pay Bill',
            trans_id='12345',
            trans_time=datetime.now(),
            trans_amount=100.00,
            business_short_code='123456',
            bill_ref_number='REF123',
            invoice_number='INV123',
            org_account_balance=1000.00,
            third_party_trans_id='TP123',
            msisdn='1234567890',
            first_name='John',
            middle_name='Middle',
            last_name='Doe'
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            package=self.package,
            payment=self.payment,
            start_date=datetime.now().date(),
            end_date=(datetime.now() + timedelta(days=30)).date(),
            active=True
        )
        self.featured_advertisement = FeaturedAdvertisement.objects.create(
            subscription=self.subscription,
            advertisement=self.advertisement
        )

    def test_featured_advertisement_creation(self):
        self.assertEqual(self.featured_advertisement.subscription, self.subscription)
        self.assertEqual(self.featured_advertisement.advertisement, self.advertisement)

class IndividualMailTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.individual_mail = IndividualMail.objects.create(
            sender=self.user,
            recipient='recipient@example.com',
            subject='Test Subject',
            message='Test Message'
        )

    def test_individual_mail_creation(self):
        self.assertEqual(self.individual_mail.sender, self.user)
        self.assertEqual(self.individual_mail.recipient, 'recipient@example.com')
        self.assertEqual(self.individual_mail.subject, 'Test Subject')
        self.assertEqual(self.individual_mail.message, 'Test Message')

class BulkMailTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.bulk_mail = BulkMail.objects.create(
            sender=self.user,
            subject='Test Subject',
            message='Test Message',
            recipients=BulkMail.BulkMailType.STAFF
        )

    def test_bulk_mail_creation(self):
        self.assertEqual(self.bulk_mail.sender, self.user)
        self.assertEqual(self.bulk_mail.subject, 'Test Subject')
        self.assertEqual(self.bulk_mail.message, 'Test Message')
        self.assertEqual(self.bulk_mail.recipients, BulkMail.BulkMailType.STAFF)

class MailAttachmentTests(TestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.individual_mail = IndividualMail.objects.create(
            sender=self.user,
            recipient='recipient@example.com',
            subject='Test Subject',
            message='Test Message'
        )
        self.content_type = ContentType.objects.get_for_model(IndividualMail)
        self.mail_attachment = MailAttachment.objects.create(
            content_type=self.content_type,
            object_id=self.individual_mail.id,
            content_object=self.individual_mail,
            file='path/to/file.txt'
        )

    def test_mail_attachment_creation(self):
        self.assertEqual(self.mail_attachment.content_object, self.individual_mail)
        self.assertEqual(self.mail_attachment.file, 'path/to/file.txt')