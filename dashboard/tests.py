# tests.py
from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from .models import CustomUser
from .models import Category, CategoryRelation
from .models import Advertisement, AdvertisementPhoto, InputAdvertisement, ServiceAdvertisement, ProduceAdvertisement
from .models import SubscriptionPackage, Offering, Subscription, Payment, PaymentMethods
from .models import IndividualMail, BulkMail, MailAttachment, Reviews, FeaturedAdvertisement

from datetime import date, timedelta
import uuid

class CustomUserModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
    def test_user_creation(self):
        self.assertEqual(self.user.first_name, "John")
        self.assertEqual(self.user.last_name, "Doe")
        self.assertEqual(self.user.email, "john.doe@example.com")
        self.assertEqual(self.user.phone, "1234567890")
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_user_full_name(self):
        self.assertEqual(self.user.get_full_name(), "John Doe")

    def test_user_short_name(self):
        self.assertEqual(self.user.get_short_name(), "John")

    def test_user_str(self):
        self.assertEqual(str(self.user), "John Doe")

    def test_user_deactivate(self):
        self.user.deactivate()
        self.assertFalse(self.user.is_active)

    def test_user_activate(self):
        self.user.deactivate()
        self.user.activate()
        self.assertTrue(self.user.is_active)

class CategoryModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Fruits",
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )

    def test_category_creation(self):
        self.assertEqual(self.category.name, "Fruits")
        self.assertEqual(self.category.classification, Category.ADVERT_CLASSIFICATION.FARM_PRODUCE)

    def test_category_str(self):
        self.assertEqual(str(self.category), "Fruits")

    def test_category_hierarchy_level(self):
        self.assertEqual(self.category.hierarchy_level, 0)

    def test_category_clean(self):
        parent_category = Category.objects.create(
            name="Food",
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.category.parent = parent_category
        self.category.save()
        self.assertEqual(self.category.parent, parent_category)

class CategoryRelationModelTest(TestCase):
    def setUp(self):
        self.parent_category = Category.objects.create(
            name="Food",
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.child_category = Category.objects.create(
            name="Fruits",
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

    def test_category_relation_str(self):
        self.assertEqual(str(self.category_relation), "Food -> Fruits")

class AdvertisementModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.category = Category.objects.create(
            name="Fruits",
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.advertisement = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title="Fresh Apples",
            description="Delicious and fresh apples.",
            county="Nairobi",
            sub_county="Westlands",
            geo_location="http://maps.google.com/?q=1.2921,36.8219"
        )

    def test_advertisement_creation(self):
        self.assertEqual(self.advertisement.title, "Fresh Apples")
        self.assertEqual(self.advertisement.description, "Delicious and fresh apples.")
        self.assertEqual(self.advertisement.county, "Nairobi")
        self.assertEqual(self.advertisement.sub_county, "Westlands")
        self.assertEqual(self.advertisement.geo_location, "http://maps.google.com/?q=1.2921,36.8219")
        self.assertEqual(self.advertisement.views, 0)

    def test_advertisement_str(self):
        self.assertEqual(str(self.advertisement), "Fresh Apples - Fruits")

    def test_advertisement_is_new(self):
        self.assertTrue(self.advertisement.is_new())

class AdvertisementPhotoModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.category = Category.objects.create(
            name="Fruits",
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.advertisement = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title="Fresh Apples",
            description="Delicious and fresh apples.",
            county="Nairobi",
            sub_county="Westlands",
            geo_location="http://maps.google.com/?q=1.2921,36.8219"
        )
        self.advertisement_photo = AdvertisementPhoto.objects.create(
            advert=self.advertisement,
            photo="ad-images/test_photo.jpg"
        )

    def test_advertisement_photo_creation(self):
        self.assertEqual(self.advertisement_photo.advert, self.advertisement)
        self.assertEqual(self.advertisement_photo.photo, "ad-images/test_photo.jpg")

class ReviewsModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.category = Category.objects.create(
            name="Fruits",
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.advertisement = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title="Fresh Apples",
            description="Delicious and fresh apples.",
            county="Nairobi",
            sub_county="Westlands",
            geo_location="http://maps.google.com/?q=1.2921,36.8219"
        )
        self.review = Reviews.objects.create(
            advertisement=self.advertisement,
            message="Great product!",
            rating=Reviews.RatingChoices.five
        )

    def test_review_creation(self):
        self.assertEqual(self.review.advertisement, self.advertisement)
        self.assertEqual(self.review.message, "Great product!")
        self.assertEqual(self.review.rating, Reviews.RatingChoices.five)

class SubscriptionPackageModelTest(TestCase):
    def setUp(self):
        self.package = SubscriptionPackage.objects.create(
            name="Basic Package",
            duration=30,
            pricing=100.00
        )

    def test_subscription_package_creation(self):
        self.assertEqual(self.package.name, "Basic Package")
        self.assertEqual(self.package.duration, 30)
        self.assertEqual(self.package.pricing, 100.00)

    def test_subscription_package_str(self):
        self.assertEqual(str(self.package), "Basic Package")

class OfferingModelTest(TestCase):
    def setUp(self):
        self.package = SubscriptionPackage.objects.create(
            name="Basic Package",
            duration=30,
            pricing=100.00
        )
        self.offering = Offering.objects.create(
            package=self.package,
            offering="Unlimited Listings"
        )

    def test_offering_creation(self):
        self.assertEqual(self.offering.package, self.package)
        self.assertEqual(self.offering.offering, "Unlimited Listings")

class PaymentMethodsModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.payment_method = PaymentMethods.objects.create(
            user=self.user,
            name="M-Pesa",
            mpesa_phone_number="1234567890"
        )

    def test_payment_method_creation(self):
        self.assertEqual(self.payment_method.user, self.user)
        self.assertEqual(self.payment_method.name, "M-Pesa")
        self.assertEqual(self.payment_method.mpesa_phone_number, "1234567890")
        
class PaymentModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.payment = Payment.objects.create(
            user=self.user,
            transaction_type="Pay Bill",
            trans_id="ABC123",
            trans_amount=100.00,
            business_short_code="12345",
            bill_ref_number="REF123",
            msisdn="1234567890",
            first_name="John",
            last_name="Doe"
        )

    def test_payment_creation(self):
        self.assertEqual(self.payment.user, self.user)
        self.assertEqual(self.payment.transaction_type, "Pay Bill")
        self.assertEqual(self.payment.trans_id, "ABC123")
        self.assertEqual(self.payment.trans_amount, 100.00)
        self.assertEqual(self.payment.business_short_code, "12345")
        self.assertEqual(self.payment.bill_ref_number, "REF123")
        self.assertEqual(self.payment.msisdn, "1234567890")
        self.assertEqual(self.payment.first_name, "John")
        self.assertEqual(self.payment.last_name, "Doe")

    def test_payment_str(self):
        self.assertEqual(str(self.payment), "ABC123 - John Doe")
        
class SubscriptionModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.package = SubscriptionPackage.objects.create(
            name="Basic Package",
            duration=30,
            pricing=100.00
        )
        self.payment = Payment.objects.create(
            user=self.user,
            transaction_type="Pay Bill",
            trans_id="ABC123",
            trans_amount=100.00,
            business_short_code="12345",
            bill_ref_number="REF123",
            msisdn="1234567890",
            first_name="John",
            last_name="Doe"
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            package=self.package,
            payment=self.payment,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            active=True
        )

    def test_subscription_creation(self):
        self.assertEqual(self.subscription.user, self.user)
        self.assertEqual(self.subscription.package, self.package)
        self.assertEqual(self.subscription.payment, self.payment)
        self.assertEqual(self.subscription.start_date, date.today())
        self.assertEqual(self.subscription.end_date, date.today() + timedelta(days=30))
        self.assertTrue(self.subscription.active)
        
class FeaturedAdvertisementModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.category = Category.objects.create(
            name="Fruits",
            classification=Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )
        self.advertisement = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title="Fresh Apples",
            description="Delicious and fresh apples.",
            county="Nairobi",
            sub_county="Westlands",
            geo_location="http://maps.google.com/?q=1.2921,36.8219"
        )
        self.package = SubscriptionPackage.objects.create(
            name="Basic Package",
            duration=30,
            pricing=100.00
        )
        self.payment = Payment.objects.create(
            user=self.user,
            transaction_type="Pay Bill",
            trans_id="ABC123",
            trans_amount=100.00,
            business_short_code="12345",
            bill_ref_number="REF123",
            msisdn="1234567890",
            first_name="John",
            last_name="Doe"
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            package=self.package,
            payment=self.payment,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=30),
            active=True
        )
        self.featured_advertisement = FeaturedAdvertisement.objects.create(
            subscription=self.subscription,
            advertisement=self.advertisement
        )

    def test_featured_advertisement_creation(self):
        self.assertEqual(self.featured_advertisement.subscription, self.subscription)
        self.assertEqual(self.featured_advertisement.advertisement, self.advertisement)

class IndividualMailModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.mail = IndividualMail.objects.create(
            sender=self.user,
            recipient="recipient@example.com",
            subject="Test Subject",
            message="Test Message"
        )

    def test_individual_mail_creation(self):
        self.assertEqual(self.mail.sender, self.user)
        self.assertEqual(self.mail.recipient, "recipient@example.com")
        self.assertEqual(self.mail.subject, "Test Subject")
        self.assertEqual(self.mail.message, "Test Message")

    def test_individual_mail_str(self):
        self.assertEqual(str(self.mail), "Test Subject...")

class BulkMailModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.mail = BulkMail.objects.create(
            sender=self.user,
            recipients=BulkMail.BulkMailType.STAFF,
            subject="Test Subject",
            message="Test Message"
        )

    def test_bulk_mail_creation(self):
        self.assertEqual(self.mail.sender, self.user)
        self.assertEqual(self.mail.recipients, BulkMail.BulkMailType.STAFF)
        self.assertEqual(self.mail.subject, "Test Subject")
        self.assertEqual(self.mail.message, "Test Message")

    def test_bulk_mail_str(self):
        self.assertEqual(str(self.mail), "Test Subject...")
        
class MailAttachmentModelTest(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            phone="1234567890"
        )
        self.mail = IndividualMail.objects.create(
            sender=self.user,
            recipient="recipient@example.com",
            subject="Test Subject",
            message="Test Message"
        )
        self.content_type = ContentType.objects.get_for_model(IndividualMail)
        self.attachment = MailAttachment.objects.create(
            content_type=self.content_type,
            object_id=self.mail.id,
            file="mail_attachments/test_file.txt"
        )

    def test_mail_attachment_creation(self):
        self.assertEqual(self.attachment.content_type, self.content_type)
        self.assertEqual(self.attachment.object_id, self.mail.id)
        self.assertEqual(self.attachment.file, "mail_attachments/test_file.txt")

    def test_mail_attachment_str(self):
        self.assertEqual(str(self.attachment), f"Attachment for {self.mail}") 