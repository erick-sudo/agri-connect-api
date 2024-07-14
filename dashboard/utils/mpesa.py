import requests
import logging
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException, HTTPError, ConnectionError, Timeout
from django.conf import settings
from base64 import b64encode
from datetime import datetime
from typing import Dict, Any
import os

class MpesaClient:
    TRANSACTION_TYPE_CUSTOMER_PAY_BILL_ONLINE = "CustomerPayBillOnline"

    def __init__(self):
        self.consumer_key = settings.MPESA_CONSUMER_KEY
        self.consumer_secret = settings.MPESA_CONSUMER_SECRET 
        self.api_url = settings.MPESA_API_URL
        self.shortcode = settings.MPESA_SHORTCODE
        self.passkey = settings.MPESA_PASSKEY
        self.callback_url = settings.MPESA_CALLBACK_URL
        self.lipa_na_mpesa_online_url = f"{self.api_url}/mpesa/stkpush/v1/processrequest"
        self.logger = logging.getLogger(__name__)
        self.access_token = self.get_access_token()

    def get_access_token(self) -> str:
        """
        Fetch the access token from M-Pesa API.

        Returns:
            str: The access token.

        Raises:
            RequestException: If there's an error in the request.
        """
        try:
            response = requests.get(
                f"{self.api_url}/oauth/v1/generate?grant_type=client_credentials",
                auth=HTTPBasicAuth(self.consumer_key, self.consumer_secret),
                timeout=10
            )
            response.raise_for_status()
            return response.json()['access_token']
        except (RequestException, HTTPError, ConnectionError, Timeout) as e:
            self.logger.error(f"Failed to obtain access token: {e}")
            raise

    def lipa_na_mpesa_online(self, phone_number: str, amount: int, account_reference: str, transaction_desc: str) -> Dict[str, Any]:
        """
        Initiate Lipa Na M-Pesa Online payment.

        Args:
            phone_number (str): The phone number to charge.
            amount (int): The amount to charge.
            account_reference (str): The account reference.
            transaction_desc (str): The transaction description.

        Returns:
            Dict[str, Any]: The response from M-Pesa API.

        Raises:
            RequestException: If there's an error in the request.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self.generate_password(),
            "Timestamp": self.generate_timestamp(),
            "TransactionType": self.TRANSACTION_TYPE_CUSTOMER_PAY_BILL_ONLINE,
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": self.callback_url,
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }
        try:
            response = requests.post(self.lipa_na_mpesa_online_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except (RequestException, HTTPError, ConnectionError, Timeout) as e:
            self.logger.error(f"Mpesa payment request failed: {e}")
            raise

    def check_payment_status(self, checkout_request_id):
        """
        Check if the payment request is completed
        """
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.access_token}'
        }
        payload = {
            "BusinessShortCode": self.shortcode,
            "Password": self.generate_password(),  
            "Timestamp": self.generate_timestamp(),    
            "CheckoutRequestID": checkout_request_id,
        }

        try:
            response = requests.request("POST", 'https:/sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query', headers = headers, data = payload)
            response.raise_for_status()
            return response.json()

        except(RequestException, HTTPError, ConnectionError, Timeout) as e:
            self.logger.error(f"Mpesa payment query request failed: {e}")
            raise

    def generate_password(self) -> str:
        """
        Generate the password for the M-Pesa API request.

        Returns:
            str: The generated password.
        """
        data_to_encode = self.shortcode + self.passkey + self.generate_timestamp()
        return b64encode(data_to_encode.encode('utf-8')).decode('utf-8')

    def generate_timestamp(self) -> str:
        """
        Generate the timestamp for the M-Pesa API request.

        Returns:
            str: The generated timestamp.
        """
        return datetime.now().strftime('%Y%m%d%H%M%S')

    def refresh_token(self) -> None:
        """
        Refresh the access token.
        """
        self.access_token = self.get_access_token()