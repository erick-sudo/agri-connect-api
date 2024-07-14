import uuid
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import serializers

from dashboard.models import (
    CustomUser, 
    Category, CategoryRelation, 
    Advertisement, AdvertisementPhoto,
    SubscriptionPackage, Payment, Subscription
    )
from dashboard.serializers import (
    CategoryRelationSerializer, SubCategorySerializer, CategorySerializer, 
    AdvertisementSerializer, AdvertisementPhotoSerializer,
    UserListSerializer, UserManagementSerializer, ChangePasswordSerializer,
    RegistrationSerializer, LoginSerializer, PasswordResetSerializer,
    SubscriptionPackageSerializer, PaymentSerializer, SubscriptionSerializer
    )

from dashboard.utils.mpesa import MpesaClient

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            # if the obj is uuid, we simply return the value of uuid
            return str(obj)
        return json.JSONEncoder.default(self, obj)

class CategoryRelationSerializerTest(TestCase):
    def setUp(self):
        self.parent = Category.objects.create(name="Parent", classification="FP")
        self.child = Category.objects.create(name="Child", classification="FP")
        self.relation = CategoryRelation.objects.create(parent=self.parent, child=self.child)

    def test_serializer_contains_expected_fields(self):
        serializer = CategoryRelationSerializer(instance=self.relation)
        self.assertEqual(set(serializer.data.keys()), {'id', 'parent', 'child'})

    def test_serializer_data(self):
        serializer = CategoryRelationSerializer(instance=self.relation)
        self.assertEqual(serializer.data['parent'], self.parent.id)  # Changed this line
        self.assertEqual(serializer.data['child'], self.child.id)  # Changed this line

    def test_create_invalid_relation(self):
        # Attempt to create a circular reference
        data = {'parent': self.parent.id, 'child': self.child.id}
        serializer = CategoryRelationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_create_self_reference(self):
        # Attempt to set a category as its own parent
        data = {'parent': self.parent.id, 'child': self.parent.id}
        serializer = CategoryRelationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

class SubCategorySerializerTest(TestCase):
    def setUp(self):
        self.parent = Category.objects.create(name="Parent", classification="FP")
        self.child1 = Category.objects.create(name="Child1", classification="FP", parent=self.parent)
        self.child2 = Category.objects.create(name="Child2", classification="FP", parent=self.parent)
        self.grandchild = Category.objects.create(name="Grandchild", classification="FP", parent=self.child1)

    def test_serializer_contains_expected_fields(self):
        serializer = SubCategorySerializer(instance=self.parent)
        self.assertEqual(set(serializer.data.keys()), {'id', 'classification', 'image', 'name', 'sub_categories'})

    def test_serializer_data(self):
        serializer = SubCategorySerializer(instance=self.parent)
        self.assertEqual(serializer.data['name'], "Parent")
        self.assertEqual(len(serializer.data['sub_categories']), 2)

    def test_nested_sub_categories(self):
        serializer = SubCategorySerializer(instance=self.parent)
        child1_data = next(cat for cat in serializer.data['sub_categories'] if cat['name'] == 'Child1')
        self.assertEqual(len(child1_data['sub_categories']), 1)
        self.assertEqual(child1_data['sub_categories'][0]['name'], 'Grandchild')

class CategorySerializerTest(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(email="test@example.com", phone="1234567890", first_name="Test", last_name="User")
        self.parent = Category.objects.create(name="Parent", classification="FP")
        self.child = Category.objects.create(name="Child", classification="FP", parent=self.parent)

    def test_serializer_contains_expected_fields(self):
        serializer = CategorySerializer(instance=self.parent)
        self.assertEqual(set(serializer.data.keys()), {'id', 'name', 'classification', 'parent', 'sub_categories', 'hierarchy_level'})

    def test_serializer_data(self):
        serializer = CategorySerializer(instance=self.parent)
        self.assertEqual(serializer.data['name'], "Parent")
        self.assertEqual(serializer.data['classification'], "FP")
        self.assertIsNone(serializer.data['parent'])
        self.assertEqual(len(serializer.data['sub_categories']), 1)

    def test_serializer_validation_circular_reference(self):
        serializer = CategorySerializer(instance=self.parent, data={'parent': self.child.id})
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_serializer_validation_self_parent(self):
        serializer = CategorySerializer(instance=self.parent, data={'parent': self.parent.id})
        with self.assertRaises(serializers.ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_create_category(self):
        data = {
            'name': 'New Category',
            'classification': 'SL',
        }
        serializer = CategorySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        category = serializer.save()
        self.assertEqual(category.name, 'New Category')
        self.assertEqual(category.classification, 'SL')

    def test_update_category(self):
        data = {
            'name': 'Updated Parent',
            'classification': 'SL',
        }
        serializer = CategorySerializer(instance=self.parent, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_category = serializer.save()
        self.assertEqual(updated_category.name, 'Updated Parent')
        self.assertEqual(updated_category.classification, 'SL')

    def test_category_with_image(self):
        image = SimpleUploadedFile("test_image.jpg", b"file_content", content_type="image/jpeg")
        data = {
            'name': 'Category with Image',
            'classification': 'FP',
            'image': image
        }
        serializer = CategorySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        category = serializer.save()
        self.assertIsNotNone(category.image)

    def test_category_hierarchy_level(self):
        grandchild = Category.objects.create(name="Grandchild", classification="FP", parent=self.child)
        serializer = CategorySerializer(instance=grandchild)
        self.assertEqual(serializer.data['hierarchy_level'], 2)

    def test_invalid_classification(self):
        data = {
            'name': 'Invalid Category',
            'classification': 'INVALID',
        }
        serializer = CategorySerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('classification', serializer.errors)

    def test_category_with_advertisements(self):
        Advertisement.objects.create(
            user=self.user,
            category=self.parent,
            title="Test Ad",
            description="Test Description",
            county="Test County",
            sub_county="Test Sub County"
        )
        serializer = CategorySerializer(instance=self.parent)
        self.assertEqual(serializer.data['name'], "Parent")


class AdvertisementSerializerTests(TestCase):
    def setUp(self):
        # Create a user and category for testing
        self.user = CustomUser.objects.create(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            phone='1234567890'
        )
        self.category = Category.objects.create(
            name='Test Category'
        )

    def test_advertisement_photo_serializer(self):
        # Create an Advertisement instance first
        advertisement_instance = Advertisement.objects.create(
            user=self.user,
            category=self.category,
            title='Test Advertisement',
            description='This is a test advertisement',
            county='Test County',
            sub_county='Test Sub County',
            geo_location='https://example.com'
        )

        # Create AdvertisementPhoto instances
        photo1 = AdvertisementPhoto.objects.create(
            advert=advertisement_instance,
            photo=SimpleUploadedFile('test_photo1.jpg', b'')
        )
        photo2 = AdvertisementPhoto.objects.create(
            advert=advertisement_instance,
            photo=SimpleUploadedFile('test_photo2.jpg', b'')
        )

        # Serialize AdvertisementPhoto instances
        serializer1 = AdvertisementPhotoSerializer(photo1)
        serializer2 = AdvertisementPhotoSerializer(photo2)

        # Check serialized data
        self.assertIn('id', serializer1.data)
        self.assertIn('photo', serializer1.data)

        self.assertIn('id', serializer2.data)
        self.assertIn('photo', serializer2.data)

    def test_advertisement_serializer(self):
        # Test AdvertisementSerializer
        factory = RequestFactory()
        request = factory.post('/api/ads/new')
        request.user = self.user

        # Create Advertisement instance with associated photos
        photo1_file = SimpleUploadedFile('test_photo1.jpg', b'content of photo1')
        photo2_file = SimpleUploadedFile('test_photo2.jpg', b'content of photo2')

        data = {
            'category': str(self.category.id),
            'title': 'Test Advertisement',
            'description': 'This is a test advertisement',
            'county': 'Test County',
            'sub_county': 'Test Sub County',
            'geo_location': 'https://example.com',
            'photos': [
                {'photo': photo1_file},
                {'photo': photo2_file}
            ]
        }

        serializer = AdvertisementSerializer(data=data, context={'request': request})
        self.assertTrue(serializer.is_valid())
        advertisement_instance = serializer.save()
        
        # Check if advertisement instance is created properly
        self.assertIsNotNone(advertisement_instance.id)
        self.assertEqual(advertisement_instance.user, self.user)

        for photo in data["photos"]:
            AdvertisementPhoto.objects.create(advert=advertisement_instance, photo=photo["photo"])

        advertisement_photos = AdvertisementPhoto.objects.filter(advert=advertisement_instance)

        # Check if advertisement photo instances are created properly
        self.assertEqual(advertisement_photos.count(), 2)
        self.assertTrue(advertisement_photos.filter(photo__startswith='ad-images/').exists())

        # Test deserialization and creation of new Advertisement instance
        new_data = {
            'category': str(self.category.id),
            'title': 'New Test Advertisement',
            'description': 'This is a new test advertisement',
            'county': 'New Test County',
            'sub_county': 'New Test Sub County',
            'geo_location': 'https://newexample.com',
            'photos': [
                {'photo': photo1_file}
            ]
        }
        serializer_new = AdvertisementSerializer(data=new_data, context={'request': request})
        self.assertTrue(serializer_new.is_valid())
        new_advertisement_instance = serializer_new.save()

        # Check if new advertisement instance is created properly
        self.assertIsNotNone(new_advertisement_instance.id)
        self.assertEqual(new_advertisement_instance.title, 'New Test Advertisement')

        for photo in new_data["photos"]:
            AdvertisementPhoto.objects.create(advert=new_advertisement_instance, photo=photo["photo"])

        new_advertisement_instance_photos = AdvertisementPhoto.objects.filter(advert=new_advertisement_instance)

        # Check if new advertisement photo instance is created properly
        self.assertEqual(new_advertisement_instance_photos.count(), 1)
        self.assertTrue(new_advertisement_instance_photos.first().photo.name.startswith('ad-images/'))


class TestUserListSerializer(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            phone='1234567890'
        )

    def test_user_list_serializer(self):
        serializer = UserListSerializer(instance=self.user)
        data = serializer.data

        self.assertEqual(data['id'], str(self.user.id))
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['phone'], '1234567890')
        self.assertIn('created_on', data)
        self.assertIn('last_login', data)

class TestUserManagementSerializer(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            phone='1234567890'
        )

    def tearDown(self):
        CustomUser.objects.get(id=self.user.id).delete()

    def test_user_management_serializer_admin(self):
        # Test for admin user
        mock_request = Mock()
        mock_request.user = Mock(is_staff=True, is_superuser=True)
        serializer_context = {'request': mock_request}
        serializer = UserManagementSerializer(instance=self.user, context=serializer_context)
        data = serializer.data

        self.assertEqual(data['id'], str(self.user.id))
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['phone'], '1234567890')
        self.assertIn('is_active', data)
        self.assertIn('is_staff', data)
        self.assertIn('is_superuser', data)
        self.assertIn('profile_picture', data)

    def test_user_management_serializer_non_admin_staff(self):
        # Test for non-admin staff user
        mock_request = Mock()
        mock_request.user = Mock(is_staff=True, is_superuser=False)
        serializer_context = {'request': mock_request}
        serializer = UserManagementSerializer(instance=self.user, context=serializer_context)
        data = serializer.data

        self.assertEqual(data['id'], str(self.user.id))
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['phone'], '1234567890')
        self.assertIn('is_active', data)
        self.assertNotIn('is_staff', data)
        self.assertNotIn('is_superuser', data)
        self.assertIn('profile_picture', data)

    def test_user_management_serializer_non_staff(self):
        # Test for non-staff user
        mock_request = Mock()
        mock_request.user = Mock(is_staff=False, is_superuser=False)
        serializer_context = {'request': mock_request}
        serializer = UserManagementSerializer(instance=self.user, context=serializer_context)
        data = serializer.data

        self.assertEqual(data['id'], str(self.user.id))
        self.assertEqual(data['first_name'], 'John')
        self.assertEqual(data['last_name'], 'Doe')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['phone'], '1234567890')
        self.assertNotIn('is_active', data)
        self.assertNotIn('is_staff', data)
        self.assertNotIn('is_superuser', data)
        self.assertIn('profile_picture', data)

    def test_user_management_serializer_update(self):
        serializer = UserManagementSerializer(instance=self.user, data={'first_name': 'Jane'}, partial=True)
        self.assertTrue(serializer.is_valid())
        updated_user = serializer.save()

        self.assertEqual(updated_user.first_name, 'Jane')

class TestChangePasswordSerializer(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            phone='1234567890'
        )
        self.user.set_password('old_Pass0')

    def test_change_password_serializer_valid(self):
        serializer_context = {'request': Mock(user=self.user)}
        data = {'old_password': 'old_Pass0', 'new_password': 'new_Pass1'}
        serializer = ChangePasswordSerializer(data=data, context=serializer_context)

        self.assertTrue(serializer.is_valid())

    def test_change_password_serializer_invalid(self):
        serializer_context = {'request': Mock(user=self.user)}
        data = {'old_password': 'wrong_pass', 'new_password': 'new_pass'}
        serializer = ChangePasswordSerializer(data=data, context=serializer_context)

        self.assertFalse(serializer.is_valid())
        self.assertIn('old_password', serializer.errors)


class TestRegistrationSerializer(TestCase):
    def setUp(self):
        self.user_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
            "phone": "1234567890",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123"
        }

    def test_registration_serializer_valid(self):
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.first_name, self.user_data["first_name"])
        self.assertEqual(user.last_name, self.user_data["last_name"])
        self.assertEqual(user.email, self.user_data["email"])
        self.assertEqual(user.phone, '+'+self.user_data["phone"])
        self.assertTrue(user.check_password(self.user_data["password"]))

    def test_registration_serializer_password_mismatch(self):
        self.user_data["confirm_password"] = "DifferentPass123"
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("confirm_password", serializer.errors)

    def test_registration_serializer_duplicate_email(self):
        CustomUser.objects.create_user(
            first_name="Jane",
            last_name="Doe",
            email="john@example.com",
            phone="0987654321",
            password="StrongPass123"
        )
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_registration_serializer_duplicate_phone(self):
        CustomUser.objects.create_user(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            phone="+1234567890",
            password="StrongPass123"
        )
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("phone", serializer.errors)

    def test_registration_serializer_invalid_email(self):
        self.user_data["email"] = "not-an-email"
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("email", serializer.errors)

    def test_registration_serializer_short_password(self):
        self.user_data["password"] = self.user_data["confirm_password"] = "short"
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("password", serializer.errors)

    def test_registration_serializer_missing_first_name(self):
        self.user_data.pop("first_name")
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("first_name", serializer.errors)

    def test_registration_serializer_missing_last_name(self):
        self.user_data.pop("last_name")
        serializer = RegistrationSerializer(data=self.user_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("last_name", serializer.errors)

class TestLoginSerializer(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            first_name="Jane",
            last_name="Doe",
            email="john@example.com",
            phone="1234567890",
            password="StrongPass123"
        )
        self.login_data_email = {
            "credential": "john@example.com",
            "password": "StrongPass123"
        }
        self.login_data_phone = {
            "credential": "1234567890",
            "password": "StrongPass123"
        }
        self.invalid_login_data = {
            "credential": "john@example.com",
            "password": "WrongPass123"
        }

    def test_login_serializer_valid_email(self):
        serializer = LoginSerializer(data=self.login_data_email)
        self.assertTrue(serializer.is_valid())

    def test_login_serializer_valid_phone(self):
        serializer = LoginSerializer(data=self.login_data_phone)
        self.assertTrue(serializer.is_valid())

    def test_login_serializer_invalid(self):
        serializer = LoginSerializer(data=self.invalid_login_data)
        self.assertTrue(serializer.is_valid())

class TestPasswordResetSerializer(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="1234567890",
            password="StrongPass123"
        )
        self.reset_data = {
            "email": "john@example.com"
        }
        self.invalid_reset_data = {
            "email": "unknown@example.com"
        }

    def test_password_reset_serializer_valid(self):
        serializer = PasswordResetSerializer(data=self.reset_data)
        self.assertTrue(serializer.is_valid())

    def test_password_reset_serializer_invalid(self):
        serializer = PasswordResetSerializer(data=self.invalid_reset_data)
        self.assertTrue(serializer.is_valid())


class TestSubscriptionPackageSerializer(TestCase):
    def setUp(self):
        self.package_data = {
            "name": "Test Package",
            "description": "This is a test package",
            "duration": 30,
            "pricing": 100.0
        }

    def test_subscription_package_serializer_valid(self):
        serializer = SubscriptionPackageSerializer(data=self.package_data)
        self.assertTrue(serializer.is_valid())
        package = serializer.save()
        self.assertEqual(package.name, self.package_data["name"])
        self.assertEqual(package.description, self.package_data["description"])
        self.assertEqual(package.duration, self.package_data["duration"])
        self.assertEqual(package.pricing, self.package_data["pricing"])

    def test_subscription_package_serializer_invalid_duration(self):
        self.package_data["duration"] = -1  # Invalid duration
        serializer = SubscriptionPackageSerializer(data=self.package_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("duration", serializer.errors)

    def test_subscription_package_serializer_invalid_pricing(self):
        self.package_data["pricing"] = -50.0  # Invalid pricing
        serializer = SubscriptionPackageSerializer(data=self.package_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("pricing", serializer.errors)

    def test_subscription_package_serializer_zero_duration(self):
        self.package_data["duration"] = 0  # Invalid duration
        serializer = SubscriptionPackageSerializer(data=self.package_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("duration", serializer.errors)

    def test_subscription_package_serializer_zero_pricing(self):
        self.package_data["pricing"] = 0  # Invalid pricing
        serializer = SubscriptionPackageSerializer(data=self.package_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("pricing", serializer.errors)


class TestPaymentSerializer(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            phone='1234567890'
        )
        self.payment_data = {
            "user": self.user.id, 
            "trans_id": "1",
            "trans_amount": 100.0,
            "msisdn": "1234567890",
            "transaction_type": "Mpesa",
            "business_short_code": "12345",
            "bill_ref_number": "TEST123",
            "first_name": "John",
            "middle_name": "M",
            "last_name": "Doe"
        }

    def test_payment_serializer_valid(self):
        serializer = PaymentSerializer(data=self.payment_data)
        self.assertTrue(serializer.is_valid())
        payment = serializer.save()
        self.assertEqual(payment.user.id, self.payment_data["user"])  # Compare with the user ID
        self.assertEqual(payment.trans_amount, self.payment_data["trans_amount"])
        self.assertEqual(payment.msisdn, self.payment_data["msisdn"])
        self.assertEqual(payment.transaction_type, self.payment_data["transaction_type"])

    def test_payment_serializer_invalid(self):
        self.payment_data["trans_amount"] = -100.0  # Invalid amount
        serializer = PaymentSerializer(data=self.payment_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("trans_amount", serializer.errors)

class TestSubscriptionSerializer(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create(
            email='test@example.com',
            first_name='John',
            last_name='Doe',
            phone='1234567890'
        )
        self.package = SubscriptionPackage.objects.create(
            name="Test Package",
            description="This is a test package",
            duration=30,
            pricing=100.0
        )
        self.payment_data = {
            "user": str(self.user.id),
            "trans_amount": 100.0,
            "msisdn": "1234567890",
            "first_name": "John",
            "middle_name": "M",
            "last_name": "Doe"
        }

        self.subscription_data = {
            "user": self.user.id,
            "package": self.package.id,
            "payment": self.payment_data
        }

    @patch('dashboard.utils.mpesa.MpesaClient.lipa_na_mpesa_online')
    def test_subscription_serializer_valid(self, mock_lipa_na_mpesa_online):
        mock_lipa_na_mpesa_online.return_value = {
            'ResponseCode': '0',
            'CheckoutRequestID': 'test_checkout_request_id'
        }
        serializer = SubscriptionSerializer(data=self.subscription_data)
        if not serializer.is_valid():
            print(f"\n{serializer.errors}\n")
        self.assertTrue(serializer.is_valid())
        subscription = serializer.save()
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.package, self.package)
        self.assertEqual(subscription.payment.trans_id, 'test_checkout_request_id')

    @patch('dashboard.utils.mpesa.MpesaClient.lipa_na_mpesa_online')
    def test_subscription_serializer_invalid_payment(self, mock_lipa_na_mpesa_online):
        mock_lipa_na_mpesa_online.return_value = {
            'ResponseCode': '1'
        }
        serializer = SubscriptionSerializer(data=self.subscription_data)
        if not serializer.is_valid():
            print(f"\n{serializer.errors}\n")

        self.assertTrue(serializer.is_valid())
        
        with self.assertRaises(serializers.ValidationError) as context:
            serializer.save()
        
        self.assertIn("Mpesa payment initiation failed", str(context.exception))

