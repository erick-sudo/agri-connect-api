import requests_mock
import requests
import logging
from unittest import TestCase
from io import StringIO
from freezegun import freeze_time
from dashboard.utils.mpesa import MpesaClient
from django.conf import settings
import os

class LogCaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(self.format(record))


class MpesaClientTestCase(TestCase):
    def setUp(self):
        # Set up logging
        self.logger = logging.getLogger('__main__')  # Use the same logger name as in MpesaClient
        self.logger.setLevel(logging.DEBUG)  # Capture all log levels
        self.log_capture_handler = LogCaptureHandler()
        self.log_capture_handler.setLevel(logging.DEBUG)  # Capture all log levels
        self.logger.addHandler(self.log_capture_handler)

        # Clear any existing handlers to avoid duplicate logging
        self.logger.handlers = []
        self.logger.addHandler(self.log_capture_handler)

        # Set environment variables for testing
        settings.MPESA_CONSUMER_KEY = 'test_consumer_key'
        settings.MPESA_CONSUMER_SECRET = 'test_consumer_secret'
        settings.MPESA_API_URL = 'https://api.safaricom.co.ke'
        settings.MPESA_SHORTCODE = '174379'
        settings.MPESA_PASSKEY = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
        settings.MPESA_CALLBACK_URL = 'http://127.0.0.1:8000/api/mpesa/callback/'

        # Mock the requests.get method to prevent actual API calls
        self.requests_mock = requests_mock.Mocker()
        self.requests_mock.start()
        self.addCleanup(self.requests_mock.stop)

        # Mock the initial access token request
        self.requests_mock.get(
            "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            json={"access_token": "initial_mock_token"},
            status_code=200
        )

        # Create MpesaClient instance after mocking
        self.mpesa_client = MpesaClient()
        
        # Replace the logger in MpesaClient with our test logger
        self.mpesa_client.logger = self.logger
    def tearDown(self):
        self.logger.removeHandler(self.log_capture_handler)

    def test_get_access_token(self):
        # The access token should already be set from the setUp method
        self.assertEqual(self.mpesa_client.access_token, "initial_mock_token")

        # Test getting a new access token
        self.requests_mock.get(
            "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            json={"access_token": "new_mock_token"},
            status_code=200
        )
        new_token = self.mpesa_client.get_access_token()
        self.assertEqual(new_token, "new_mock_token")

    def test_lipa_na_mpesa_online(self):
        # Mock Mpesa payment request
        mock_response = {
            "MerchantRequestID": "12345",
            "CheckoutRequestID": "67890",
            "ResponseCode": "0",
            "ResponseDescription": "Success",
            "CustomerMessage": "Success"
        }
        self.requests_mock.post(self.mpesa_client.lipa_na_mpesa_online_url, json=mock_response, status_code=200)

        response = self.mpesa_client.lipa_na_mpesa_online(
            phone_number="254712345678",
            amount=100,
            account_reference="test123",
            transaction_desc="Test payment"
        )
        self.assertEqual(response["ResponseCode"], "0")
        self.assertEqual(response["ResponseDescription"], "Success")

    def test_failed_requests(self):
        test_cases = [
            ("get_access_token", "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"),
            ("lipa_na_mpesa_online", "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"),
        ]

        for method_name, url in test_cases:
            with self.subTest(method_name=method_name):
                # Clear previous log messages
                self.log_capture_handler.messages.clear()

                # Mock the request to fail
                self.requests_mock.get(url, status_code=400, text="Bad Request")
                self.requests_mock.post(url, status_code=400, text="Bad Request")

                method = getattr(self.mpesa_client, method_name)
                
                with self.assertRaises(requests.RequestException):
                    if method_name == "lipa_na_mpesa_online":
                        method(
                            phone_number="254712345678",
                            amount=100,
                            account_reference="test123",
                            transaction_desc="Test payment"
                        )
                    else:
                        method()

                log_messages = self.log_capture_handler.messages
                error_message = f"{'Failed to obtain access token' if method_name == 'get_access_token' else 'Mpesa payment request failed'}"
                self.assertTrue(any(error_message in msg for msg in log_messages),
                                f"Expected '{error_message}' in log messages, but got: {log_messages}")
    @freeze_time("2023-01-01 12:00:00")
    def test_generate_timestamp(self):
        timestamp = self.mpesa_client.generate_timestamp()
        self.assertEqual(timestamp, "20230101120000")

    def test_generate_password(self):
        with freeze_time("2023-01-01 12:00:00"):
            password = self.mpesa_client.generate_password()
        expected_password = "MTc0Mzc5YmZiMjc5ZjlhYTliZGJjZjE1OGU5N2RkNzFhNDY3Y2QyZTBjODkzMDU5YjEwZjc4ZTZiNzJhZGExZWQyYzkxOTIwMjMwMTAxMTIwMDAw"
        self.assertEqual(password, expected_password)

    def test_refresh_token(self):
        self.requests_mock.get(
            "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            json={"access_token": "refreshed_token"},
            status_code=200
        )
        self.mpesa_client.refresh_token()
        self.assertEqual(self.mpesa_client.access_token, "refreshed_token")

