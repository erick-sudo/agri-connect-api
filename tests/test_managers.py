from django.test import TestCase
from django.contrib.auth import get_user_model

class CustomUserManagerTests(TestCase):

    def setUp(self):
        self.user_model = get_user_model()
        self.user_manager = self.user_model.objects

    def test_create_user_success(self):
        user = self.user_manager.create_user(
            first_name='John',
            last_name='Doe',
            email='john.doe@example.com',
            phone='1234567890',
            password='password123'
        )
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')
        self.assertEqual(user.email, 'john.doe@example.com')
        self.assertEqual(user.phone, '1234567890')
        self.assertTrue(user.check_password('password123'))
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_create_user_no_email(self):
        with self.assertRaises(ValueError) as context:
            self.user_manager.create_user(
                first_name='John',
                last_name='Doe',
                email='',
                phone='1234567890',
                password='password123'
            )
        self.assertEqual(str(context.exception), "Users must have Email")

    def test_create_user_no_phone(self):
        with self.assertRaises(ValueError) as context:
            self.user_manager.create_user(
                first_name='John',
                last_name='Doe',
                email='john.doe@example.com',
                phone='',
                password='password123'
            )
        self.assertEqual(str(context.exception), "Users must have a Phone number")

    def test_create_user_no_first_name(self):
        with self.assertRaises(ValueError) as context:
            self.user_manager.create_user(
                first_name='',
                last_name='Doe',
                email='john.doe@example.com',
                phone='1234567890',
                password='password123'
            )
        self.assertEqual(str(context.exception), "Users must have a First and Last name")

    def test_create_user_no_last_name(self):
        with self.assertRaises(ValueError) as context:
            self.user_manager.create_user(
                first_name='John',
                last_name='',
                email='john.doe@example.com',
                phone='1234567890',
                password='password123'
            )
        self.assertEqual(str(context.exception), "Users must have a First and Last name")

    def test_create_superuser_success(self):
        superuser = self.user_manager.create_superuser(
            first_name='Admin',
            last_name='User',
            email='admin@example.com',
            phone='0987654321',
            password='adminpassword'
        )
        self.assertEqual(superuser.first_name, 'Admin')
        self.assertEqual(superuser.last_name, 'User')
        self.assertEqual(superuser.email, 'admin@example.com')
        self.assertEqual(superuser.phone, '0987654321')
        self.assertTrue(superuser.check_password('adminpassword'))
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_staff)
