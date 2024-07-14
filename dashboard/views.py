from rest_framework.renderers import JSONRenderer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework import viewsets, permissions, status, serializers
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import generics, status
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework import permissions

from knox.auth import TokenAuthentication
from knox.views import LoginView, APIView
from knox.models import AuthToken


from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.files.storage import default_storage
from django.contrib.auth.models import AnonymousUser
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError, ObjectDoesNotExist

from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str

from django.middleware.csrf import get_token as get_csrf_token
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone

from . import models as  db
from . import serializers

from .analytics import Analytics
from .serializers import AnalyticsSerializer

from .utils.utils import NormalizeData
from .utils import mailing

from datetime import timezone

import logging
import re


logger = logging.getLogger(__name__)   

    
class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        # Allow any authenticated user to access the view
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Restrict destructive or update actions to staff users
        if request.method in ['DELETE', 'PUT', 'PATCH']:
            return request.user.is_staff
        # Allow other actions to be performed by any authenticated user
        return True
    
class IsAdminOrSelf(permissions.BasePermission):
    """ Check if request user is an admin or the owner"""
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj == request.user

class IsStaff(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user

# Classifications
class AdvertClassificationView(APIView):
    permissions = [permissions.IsAuthenticated]

    def get(self, request):
        classifications = [
            {
                'value': choice[0],
                'label': choice[1]
            }
            for choice in db.Category.ADVERT_CLASSIFICATION.choices
        ]
        return Response(classifications, status=status.HTTP_200_OK)

# ADCategories
class CategoryList(generics.ListAPIView):
    """List all root categories"""
    queryset = db.Category.objects.filter(parent__isnull=True)
    serializer_class = serializers.CategorySerializer

class NewCategory(generics.CreateAPIView):
    """Create a new category"""
    queryset = db.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request, format=None):
        serializer = self.serializer_class()
        return Response(serializer.data)

    def perform_create(self, serializer):
        parent_id = self.request.data.get('parent')
        if parent_id:
            if parent_id == self.request.data.get('id'):
                raise serializers.ValidationError({"detail": "A category cannot be its own parent"})

            if db.Category.objects.filter(id=parent_id, parent_id=self.request.data.get('id')).exists():
                raise serializers.ValidationError({"detail": "Circular reference detected"})

        serializer.save()

class CategoryDetail(generics.RetrieveUpdateDestroyAPIView):
    """Manage a category"""
    queryset = db.Category.objects.all()
    serializer_class = serializers.CategorySerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def patch(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Create a mutable copy of request.data
        data = request.data.copy()

        # Handle image file
        if 'image' in request.FILES:
            data['image'] = request.FILES['image']
        elif 'image' in data and data['image'] in ['', 'null', 'undefined']:
            # Clear the image if explicitly set to empty
            data['image'] = None
        elif 'image' not in data and partial:
            # If no image is provided in a PATCH request, don't change the existing image
            data.pop('image', None)

        serializer = self.get_serializer(instance, data=data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)
    
    def perform_update(self, serializer):
        parent_id = self.request.data.get('parent')
        if parent_id:
            if parent_id == self.kwargs.get('pk'):
                raise serializers.ValidationError({"detail": "A category cannot be its own parent"})

            if db.Category.objects.filter(id=parent_id, parent_id=self.kwargs.get('pk')).exists():
                raise serializers.ValidationError({"detail": "Circular reference detected"})

        serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.children.exists():
            return Response({"detail": "Cannot delete a category with subcategories."}, status=status.HTTP_400_BAD_REQUEST)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

class CategoryRelationsList(generics.ListCreateAPIView):
    """List category relations or create new relation"""
    queryset = db.CategoryRelation.objects.all()
    serializer_class = serializers.CategoryRelationSerializer
    permission_classes = [permissions.IsAdminUser]

    def create(self, request, *args, **kwargs):
        parent_id = request.data.get('parent')
        child_id = request.data.get('child')

        if parent_id == child_id:
            return Response({"detail": "Parent and child categories cannot be the same"}, status=status.HTTP_400_BAD_REQUEST)

        if db.CategoryRelation.objects.filter(parent_id=parent_id, child_id=child_id).exists():
            return Response({"detail": "Relationship already exists"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class CategoryRelationDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = db.CategoryRelation.objects.all()
    serializer_class = serializers.CategoryRelationSerializer
    permission_classes = [permissions.IsAdminUser]

# Ads
class AdsList(generics.ListAPIView):
    """
    List all Advertisements
    """
    queryset = db.Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer
    permission_classes = [permissions.IsAdminUser, IsAdminOrSelf]
    authentication_classes = [TokenAuthentication]

class UserAdsList(generics.ListAPIView):
    """
    List all Advertisements created by the authenticated user
    """
    serializer_class = serializers.AdvertisementSerializer

    def get_queryset(self):
        user = self.request.user
        return db.Advertisement.objects.filter(user=user)

class NewAd(generics.CreateAPIView):
    """
    Create new Advertisements
    """
    queryset = db.Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer
    permission_classes = [permissions.IsAuthenticated]

    #def perform_create(self, serializer):
    #    serializer.save(user=self.request.user)

class AdDetail(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, Update, or Delete an Advertisement
    """
    queryset = db.Advertisement.objects.all()
    serializer_class = serializers.AdvertisementSerializer

    def get_object(self):
        obj = super().get_object()
        if self.request.method == 'GET':
            obj.views += 1
            obj.save(update_fields=['views'])
        return obj

    def get_permissions(self):
        """
        Returns the list of permissions that this view requires.
        """
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            self.permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]
        else:
            self.permission_classes = [permissions.IsAuthenticated]  # Default permission for other methods

        return super().get_permissions()

class ProduceAdsList(generics.ListAPIView):
    """ 
    List all Farm Produce/Products Advertisements
    """
    serializer_class = serializers.AdvertisementSerializer
    def get_queryset(self):
        return db.Advertisement.objects.filter(
            category__classification=db.Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        )

class InputAdsList(generics.ListAPIView):
    """ List all Farm Input Advertisements """
    serializer_class = serializers.AdvertisementSerializer
    def get_queryset(self):
        return db.Advertisement.objects.filter(
            category__classification=db.Category.ADVERT_CLASSIFICATION.FARM_INPUT
        )
    
class ServiceAdsList(generics.ListAPIView):
    """ List all Service Advertisements """
    serializer_class = serializers.AdvertisementSerializer
    def get_queryset(self):
        return db.Advertisement.objects.filter(
            category__classification=db.Category.ADVERT_CLASSIFICATION.SERVICE_LISTING
        )

# Top ADs
class TopProduceAds(generics.ListAPIView):
    """
    List the 10 most popular Farm Produce/Product Advertisements
    """
    serializer_class = serializers.AdvertisementSerializer

    def get_queryset(self):
        return db.Advertisement.objects.filter(
            category__classification=db.Category.ADVERT_CLASSIFICATION.FARM_PRODUCE
        ).order_by('-views')[:10]

class TopInputAds(generics.ListAPIView):
    """
    List the 10 most popular Farm Input Advertisements
    """
    serializer_class = serializers.AdvertisementSerializer
    def get_queryset(self):
        return db.Advertisement.objects.filter(
            category__classification=db.Category.ADVERT_CLASSIFICATION.FARM_INPUT
        ).order_by('-views')[:10]

class TopServiceAds(generics.ListAPIView):
    """
    List the 10 most popular Service Advertisements
    """
    serializer_class = serializers.AdvertisementSerializer
    def get_queryset(self):
        return db.Advertisement.objects.filter(
            category__classification=db.Category.ADVERT_CLASSIFICATION.SERVICE_LISTING
        ).order_by('-views')[:10]
    
# User management views.
class UserList(generics.ListAPIView):
    """Users List"""
    queryset = db.CustomUser.objects.all()
    serializer_class = serializers.UserListSerializer
    
    #authentication_classes = [TokenAuthentication]
    permission_classes = [IsAdminUser]

class User(generics.RetrieveUpdateDestroyAPIView):
    """User management"""
    queryset = db.CustomUser.objects.all()
    serializer_class = serializers.UserManagementSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]
    parser_classes = (MultiPartParser, FormParser, JSONParser)
    
    #authentication_classes = [TokenAuthentication]

    def get_object(self):
        # Knox sets request.user automatically when token is valid
        user = self.request.user
        if not user or user.is_anonymous:
            raise NotAuthenticated("Please Login or Register")

        self.check_object_permissions(self.request, user)
        return user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        # Clear prefetched objects cache if it exists
        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"detail": "User deactivated successfully."}, status=status.HTTP_200_OK)

    def perform_destroy(self, instance):
        instance.deactivate()

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = serializers.ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # The old password is correct, and the new password is valid
            self.object = self.get_object()
            self.object.set_password(serializer.validated_data['new_password'])
            self.object.save()
            mailing.send_password_change_success_email(self.object.id)
            return Response({"detail": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Accounts
class Signup(generics.CreateAPIView):
    """ 
    Create User     
    """
    queryset = db.CustomUser.objects.all()
    serializer_class = serializers.RegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer()
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        headers = self.get_success_headers(serializer.data)
        
        # Log the user in
        login(request, user)
        
        # Create Knox token
        token = AuthToken.objects.create(user)
        
        # Send welcome email
        mailing.send_welcome_email(user.first_name, user.email)
        
        return Response({
            "user": {
                "first_name": user.first_name
            },
            'token': token[1],
            "message": "User created and Signed in successfully",
            "result": "success",
        }, status=status.HTTP_201_CREATED, headers=headers)
    

class Login(LoginView):
    """
    Login User
    """
    User = get_user_model()
    permission_classes = (permissions.AllowAny,)
    serializer_class = serializers.LoginSerializer

    def get(self, request, format=None):
        serializer = self.serializer_class()
        return Response(serializer.data)

    def login_response(self, request, user):
        token = AuthToken.objects.create(user)
        return Response({
            'user': {
                "staff": user.is_staff,
            },
            'token': token[1],  # token[1] contains the token string
            'result': "success",
        }, status=status.HTTP_200_OK)

    def invalid_credentials_response(self):
        return Response({"error": "Invalid credentials"}, status=status.HTTP_400_BAD_REQUEST)
    
    def post(self, request, format=None):
        # Check if the user is already authenticated
        if request.user.is_authenticated:
            return self.login_response(request, request.user)

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            credential = serializer.validated_data.get('credential')
            password = serializer.validated_data.get('password')

            try:
                user = None
                if '@' in credential:
                    user = self.User.objects.filter(email=credential).first()
                else:
                    normalized_phone = NormalizeData().normalize_phone_number(credential)
                    user = self.User.objects.filter(phone=normalized_phone).first()

                if user is None:
                    return self.invalid_credentials_response()

                if user.check_password(password):
                    login(request, user)
                    return self.login_response(request, user)
                else:
                    return self.invalid_credentials_response()

            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_403_NOT_FOUND)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

   
class Logout(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        logger.debug(f"Request method: {request.method}")
        logger.debug(f"Request headers: {request.headers}")
        logger.debug(f"Request user: {request.user}")
        logger.debug(f"Request auth: {request.auth}")

        if not request.user.is_authenticated:
            logger.error("User is not authenticated")
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # Perform Knox token logout
            request.auth.delete()
            # Perform Django session logout
            logout(request)
            return Response({"result": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Error during logout process")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, *args, **kwargs):
        return Response({"detail": "This endpoint only accepts POST requests for logout."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class LogoutAll(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        logger.debug(f"Request method: {request.method}")
        logger.debug(f"Request headers: {request.headers}")
        logger.debug(f"Request user: {request.user}")
        logger.debug(f"Request auth: {request.auth}")

        if not request.user.is_authenticated:
            logger.error("User is not authenticated")
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # Perform Knox tokens logout
            AuthToken.objects.filter(user=request.user).delete()
            # Perform Django session logout
            logout(request)
            return Response({"result": "success"}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("Error during logout process")
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, *args, **kwargs):
        return Response({"detail": "This endpoint only accepts POST requests for logout."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

class ResetPassword(generics.GenericAPIView):
    """ 
    Reset User password
    """
    User = get_user_model()
    serializer_class = serializers.PasswordResetSerializer
    
    def get(self, request, format=None):
        serializer = self.serializer_class()
        return Response(serializer.data)
    
    def post(self, request, uid=None, token=None, format=None):
        if uid and token:
            # Handle password reset confirmation
            return self.confirm_reset(request, uid, token)
        else:
            # Handle password reset request
            return self.request_reset(request)

    def request_reset(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = self.User.objects.filter(email=email).first()
            token = default_token_generator.make_token(user)
            if user:
                mailing.send_password_reset_email(user.id, token)
            
            # Don't reveal whether the user exists or not
            return Response({
                "message": "If a user with this email exists, a password reset email has been sent.",
                "result": "success"
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def confirm_reset(self, request, uid, token):
        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = self.User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, self.User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            new_password = request.data.get('new_password')
            if new_password:
                user.set_password(new_password)
                user.save()
                mailing.send_password_change_success_email(user.id)
                return Response({"message": "Password has been reset successfully.", "result": "success"}, status=status.HTTP_200_OK)
            else:
                return Response({"error": "New password is required."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "Invalid reset link or expired."}, status=status.HTTP_400_BAD_REQUEST)

   
# Subscriptions
class SubscriptionCreateView(generics.CreateAPIView):
    queryset = db.Subscription.objects.all()
    serializer_class = serializers.SubscriptionSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class SubscriptionList(generics.ListAPIView):
    queryset = db.Subscription.objects.all()
    serializer_class = serializers.SubscriptionSerializer
    permissions = [permissions.IsAdminUser]

class SubscriptionHistory(generics.ListAPIView):
    """ Get Subscription History """
    pass

class SubscriptionPackageList(generics.ListAPIView):
    queryset = db.SubscriptionPackage.objects.all()
    serializer_class = serializers.SubscriptionPackageSerializer
    
class NewSubscriptionPackage(generics.CreateAPIView):
    queryset = db.SubscriptionPackage.objects.all()
    serializer_class = serializers.SubscriptionPackageSerializer
    permissions = [permissions.IsAdminUser, IsAdminUser]

class SubscriptionPackageDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = db.SubscriptionPackage.objects.all()
    serializer_class = serializers.SubscriptionPackageSerializer
    permission_classes = [IsAdminUser]
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "Package deleted successfully"}, status=status.HTTP_204_NO_CONTENT)
    
    def perform_destroy(self, instance):
        # Custom logic before deletion if needed
        instance.delete()

@method_decorator(csrf_exempt, name='dispatch')
class MpesaCallbackView(APIView):
    def post(self, request, *args, **kwargs):
        data = request.data
        
        if data['Body']['stkCallback']['ResultCode'] == 0:
            callback_data = data['Body']['stkCallback']['CallbackMetadata']['Item']
            trans_id = callback_data[1]['Value']
            payment = db.Payment.objects.get(trans_id=data['Body']['stkCallback']['CheckoutRequestID'])
            payment.trans_id = trans_id
            payment.trans_time = callback_data[3]['Value']
            payment.trans_amount = callback_data[0]['Value']
            payment.bill_ref_number = callback_data[5]['Value']
            payment.save()
            
            # Mark the subscription as active
            subscription = payment.subscription_set.first()
            subscription.active = True
            subscription.save()

            # Send email confirmation with invoice number
            payment.send_invoice_email()
            
            return Response(status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)

# Payment 
class Payments(generics.ListAPIView):
    """ Payment processing """
    def post(self, request):
        """ Make a Payment """
        serializer = serializers.PaymentSerializer(data=request.data)
        if serializer.is_valid():
            # Simulate Mpesa payment processing
            # In a real-world scenario, you would integrate with the Mpesa API here
            
            # Generate a dummy receipt number
            receipt = f"MPESA{timezone.now().strftime('%Y%m%d%H%M%S')}"
            
            payment = serializer.save(
                receipt=receipt,
                date=timezone.now()
            )
            
            return Response({
                "status": "success",
                "message": "Payment processed successfully",
                "data": serializers.PaymentSerializer(payment).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request):
        """ Get all payments """
        payments = serializers.Payment.objects.all()
        serializer = serializers.PaymentSerializer(payments, many=True)
        return Response(serializer.data)

# Mail
class MailViewSet(viewsets.ViewSet):
    User = get_user_model()
    permission_classes = [IsAdminUser]

    def create(self, request):
        serializer = serializers.MailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        mail_type = serializer.validated_data['mail_type']
        sender = serializer.validated_data['sender']
        subject = serializer.validated_data['subject']
        message = serializer.validated_data['message']
        attachments = serializer.validated_data.get('attachments', [])
        send_now = serializer.validated_data['send_now']

        try:
            # Database operations in a transaction
            with transaction.atomic():
                if mail_type == 'individual':
                    mail = db.IndividualMail.objects.create(
                        sender=request.user,
                        recipient=serializer.validated_data['recipient'],
                        subject=subject,
                        message=message,
                        sent=False
                    )
                    recipients = [serializer.validated_data['recipient']]
                else:  # bulk mail
                    mail = db.BulkMail.objects.create(
                        sender=request.user,
                        recipients=serializer.validated_data['recipients'],
                        subject=subject,
                        message=message,
                        sent=False
                    )
                    recipients = self.get_bulk_mail_recipients(mail.recipients)

                attachment_objects = self.create_attachments(mail, attachments)

            if send_now:
                failed_recipients = self.send_emails(request.user.email, recipients, subject, message, attachment_objects)
                
                if failed_recipients:
                    mail.sent = True
                    mail.save()
                    return Response({
                        "message": "Mail sent with some failures",
                        "failed_recipients": failed_recipients
                    }, status=status.HTTP_207_MULTI_STATUS)
                else:
                    mail.sent = True
                    mail.save()
                    return Response({"message": "Mail sent successfully"}, status=status.HTTP_201_CREATED)
            else:
                return Response({"message": "Mail created successfully but not sent"}, status=status.HTTP_201_CREATED)

        except Exception as e:
            for attachment in attachment_objects:
                default_storage.delete(attachment.file.name)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        individual_mails = db.IndividualMail.objects.filter(sender=request.user)
        bulk_mails = db.BulkMail.objects.filter(sender=request.user)
        
        individual_data = [{"id": mail.id, "type": "individual", "recipient": mail.recipient, "subject": mail.subject, "created_at": mail.created_at} for mail in individual_mails]
        bulk_data = [{"id": mail.id, "type": "bulk", "recipients": mail.recipients, "subject": mail.subject, "created_at": mail.created_at} for mail in bulk_mails]
        
        return Response(individual_data + bulk_data)

    def retrieve(self, request, pk=None):
        try:
            mail = db.IndividualMail.objects.get(id=pk, sender=request.user)
            mail_type = "individual"
        except db.IndividualMail.DoesNotExist:
            try:
                mail = db.BulkMail.objects.get(id=pk, sender=request.user)
                mail_type = "bulk"
            except db.BulkMail.DoesNotExist:
                return Response({"error": "Mail not found"}, status=status.HTTP_404_NOT_FOUND)

        attachments = db.MailAttachment.objects.filter(content_type=ContentType.objects.get_for_model(mail), object_id=mail.id)
        attachment_data = [{"id": att.id, "filename": att.file.name} for att in attachments]

        data = {
            "id": mail.id,
            "type": mail_type,
            "subject": mail.subject,
            "message": mail.message,
            "created_at": mail.created_at,
            "updated_at": mail.updated_at,
            "attachments": attachment_data
        }

        if mail_type == "individual":
            data["recipient"] = mail.recipient
        else:
            data["recipients"] = mail.recipients

        return Response(data)

    @action(detail=False, methods=['get'])
    def requirements(self, request):
        requirements = {
            "individual": {
                "mail_type": "individual",
                "recipient": "Email address of the recipient",
                "subject": "Subject of the email",
                "message": "Body of the email",
                "attachments": "List of files to attach (optional)",
                "send_now": "Boolean to send immediately or not (default: True)"
            },
            "bulk": {
                "mail_type": "bulk",
                "recipients": f"One of: {', '.join(db.BulkMail.BulkMailType.values)}",
                "subject": "Subject of the email",
                "message": "Body of the email",
                "attachments": "List of files to attach (optional)",
                "send_now": "Boolean to send immediately or not (default: True)"
            }
        }

        return Response(requirements)

    @action(detail=False, methods=['get'])
    def example(self, request):
        examples = {
            "individual": {
                "mail_type": "individual",
                "recipient": "user@example.com",
                "subject": "Hello from our app",
                "message": "This is an example of an individual email.",
                "attachments": ["file1.pdf", "image.jpg"],
                "send_now": True
            },
            "bulk": {
                "mail_type": "bulk",
                "recipients": "staff",
                "subject": "Team Announcement",
                "message": "This is an example of a bulk email to all staff.",
                "attachments": ["document.pdf"],
                "send_now": False
            }
        }

        return Response(examples)

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        try:
            mail = db.IndividualMail.objects.get(id=pk, sender=request.user)
            recipients = [mail.recipient]
        except db.IndividualMail.DoesNotExist:
            try:
                mail = db.BulkMail.objects.get(id=pk, sender=request.user)
                recipients = self.get_bulk_mail_recipients(mail.recipients)
            except db.BulkMail.DoesNotExist:
                return Response({"error": "Mail not found"}, status=status.HTTP_404_NOT_FOUND)
        
        if mail.sent:
            return Response({"error": "Mail has already been sent"}, status=status.HTTP_400_BAD_REQUEST)

        attachments = db.MailAttachment.objects.filter(content_type=ContentType.objects.get_for_model(mail), object_id=mail.id)
        
        failed_recipients = self.send_emails(request.user.email, recipients, mail.subject, mail.message, attachments)

        if failed_recipients:
            return Response({
                "message": "Mail sent with some failures",
                "failed_recipients": failed_recipients
            }, status=status.HTTP_207_MULTI_STATUS)
        
        mail.sent = True
        mail.save()
        return Response({"message": "Mail sent successfully"}, status=status.HTTP_200_OK)

    def get_bulk_mail_recipients(self, recipient_type):
        User = get_user_model()
        if recipient_type == db.BulkMail.BulkMailType.STAFF:
            return User.objects.filter(is_staff=True).values_list('email', flat=True)
        elif recipient_type == db.BulkMail.BulkMailType.CLIENTS:
            return User.objects.filter(is_staff=False).values_list('email', flat=True)
        else:  # ALL
            return User.objects.all().values_list('email', flat=True)

    def create_attachments(self, mail, attachments):
        attachment_objects = []
        for attachment in attachments:
            file_name = default_storage.get_available_name(attachment.name)
            file_path = default_storage.save(f'mail_attachments/{file_name}', ContentFile(attachment.read()))
            attachment_obj = db.MailAttachment.objects.create(
                content_object=mail,
                file=file_path
            )
            attachment_objects.append(attachment_obj)
        return attachment_objects

    def send_emails(self, from_email, recipients, subject, message, attachments):
        attachment_paths = [attachment.file.path for attachment in attachments]
        failed_recipients = []
        for recipient in recipients:
            try:
                mailing.send_email(from_email, recipient, subject, message, attachment_paths)
            except Exception as e:
                failed_recipients.append(recipient)
                logger.error(f"Failed to send email to {recipient}: {str(e)}")
        return failed_recipients

# Reviews
class ReviewCreateView(generics.CreateAPIView):
    queryset = db.Reviews.objects.all()
    serializer_class = serializers.ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        advertisement = serializer.validated_data['advertisement']
        if advertisement.user == self.request.user:
            raise PermissionDenied("You cannot review your own advertisement.")
        serializer.save()

class ReviewListView(generics.ListAPIView):
    serializer_class = serializers.ReviewSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        advertisement_id = self.kwargs.get('advertisement_id')
        return db.Reviews.objects.filter(advertisement_id=advertisement_id)
    
# Groups and permissions
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = serializers.GroupSerializer
    permission_classes = [permissions.IsAdminUser]  # Only admin users can manage groups

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk=None):
        group = get_object_or_404(Group, pk=pk)
        serializer = self.get_serializer(group, data=request.data)
        if serializer.is_valid():
            self.perform_update(serializer)
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        group = get_object_or_404(Group, pk=pk)
        self.perform_destroy(group)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def permissions(self, request, pk=None):
        group = get_object_or_404(Group, pk=pk)
        permissions = group.permissions.all()
        serializer = serializers.PermissionSerializer(permissions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_permission(self, request, pk=None):
        group = get_object_or_404(Group, pk=pk)
        permission_id = request.data.get('permission_id')
        if not permission_id:
            return Response({"error": "permission_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            permission = Permission.objects.get(pk=permission_id)
        except Permission.DoesNotExist:
            return Response({"error": f"Permission with id {permission_id} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if group.permissions.filter(id=permission_id).exists():
            return Response({"error": f"Group '{group.name}' already has permission '{permission.name}'"}, status=status.HTTP_400_BAD_REQUEST)

        group.permissions.add(permission)
        return Response({"message": f"Permission '{permission.name}' added to group '{group.name}'"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_permission(self, request, pk=None):
        group = get_object_or_404(Group, pk=pk)
        permission_id = request.data.get('permission_id')
        if not permission_id:
            return Response({"error": "permission_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            permission = Permission.objects.get(pk=permission_id)
        except Permission.DoesNotExist:
            return Response({"error": f"Permission with id {permission_id} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if not group.permissions.filter(id=permission_id).exists():
            return Response({"error": f"Group '{group.name}' does not have permission '{permission.name}'"}, status=status.HTTP_400_BAD_REQUEST)

        group.permissions.remove(permission)
        return Response({"message": f"Permission '{permission.name}' removed from group '{group.name}'"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'])
    def available_permissions(self, request):
        permissions = Permission.objects.all()
        serializer = serializers.PermissionSerializer(permissions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def create_permission(self, request):
        name = request.data.get('name')
        codename = request.data.get('codename')
        app_label = request.data.get('app_label')
        model = request.data.get('model')

        # Check if all required fields are provided
        if not all([name, codename, app_label, model]):
            return Response({
                "error": "All fields (name, codename, app_label, and model) are required"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate name
        if len(name) > 255:
            return Response({
                "error": "Permission name must be 255 characters or fewer"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate codename
        if not re.match(r'^[a-z_][a-z0-9_]*$', codename):
            return Response({
                "error": "Codename must contain only lowercase letters, numbers, and underscores, and start with a letter or underscore"
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(codename) > 100:
            return Response({
                "error": "Codename must be 100 characters or fewer"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate app_label and model
        try:
            content_type = ContentType.objects.get(app_label=app_label, model=model)
        except ContentType.DoesNotExist:
            return Response({
                "error": f"ContentType with app_label '{app_label}' and model '{model}' does not exist"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if permission already exists
        if Permission.objects.filter(content_type=content_type, codename=codename).exists():
            return Response({
                "error": f"Permission with codename '{codename}' already exists for this content type"
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            permission = Permission.objects.create(
                name=name,
                codename=codename,
                content_type=content_type
            )
            serializer = serializers.PermissionSerializer(permission)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except IntegrityError as e:
            return Response({
                "error": f"Database integrity error: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            return Response({
                "error": f"Validation error: {str(e)}"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                "error": f"An unexpected error occurred: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def add_user(self, request, pk=None):
        group = get_object_or_404(Group, pk=pk)
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with id {user_id} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if user.groups.filter(id=group.id).exists():
            return Response({"error": f"User '{user.username}' is already in group '{group.name}'"}, status=status.HTTP_400_BAD_REQUEST)

        user.groups.add(group)
        return Response({"message": f"User '{user.username}' added to group '{group.name}'"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def remove_user(self, request, pk=None):
        group = get_object_or_404(Group, pk=pk)
        user_id = request.data.get('user_id')
        if not user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return Response({"error": f"User with id {user_id} does not exist"}, status=status.HTTP_404_NOT_FOUND)

        if not user.groups.filter(id=group.id).exists():
            return Response({"error": f"User '{user.username}' is not in group '{group.name}'"}, status=status.HTTP_400_BAD_REQUEST)

        user.groups.remove(group)
        return Response({"message": f"User '{user.username}' removed from group '{group.name}'"}, status=status.HTTP_200_OK)

# Analytics
# views.py
class AnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]  # Restrict to admin users

    def get(self, request):
        analytics_data = Analytics.get_all_analytics()
        serializer = AnalyticsSerializer(analytics_data)
        return Response(serializer.data)

class UserAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(Analytics.user_analytics())

class AdvertisementAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(Analytics.advertisement_analytics())

class CategoryAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(Analytics.category_analytics())

class SubscriptionPaymentAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(Analytics.subscription_payment_analytics())

class FeaturedAdAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(Analytics.featured_ad_analytics())

class PackageAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(Analytics.package_analytics())

class APITrafficAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(Analytics.analyze_api_traffic())

class SiteVisitAnalyticsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response(Analytics.site_visit_analytics())
    
# Get Authorization Token
@api_view(['GET'])
def get_token(request):
    """ Get a Knox Authorization token"""
    if isinstance(request.user, AnonymousUser):
        return Response({
            'error': 'User is not authenticated'
        }, status=status.HTTP_401_UNAUTHORIZED)

    user = request.user
    token_instance, token = AuthToken.objects.get(user=user)
    print("\n", token, "\n")
    return Response({
        'auth_token': token
    }, status=status.HTTP_200_OK)

# Get CSRF Token
@api_view(['GET'])
def get_csrf(request):
    """ Get a CSRF TOKEN"""
    # Return a CSRF token 
    csrf_token = get_csrf_token(request._request)
    
    json = JSONRenderer().render(data=csrf_token)
    return Response({'csrf_token': csrf_token}, status=status.HTTP_200_OK)

# API Root
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'api-root': reverse('api-root', request=request, format=format),
        
        'all-analytics': reverse('all-analytics', request=request, format=format),
        'user-analytics': reverse('user-analytics', request=request, format=format),
        'ad-analytics': reverse('ad-analytics', request=request, format=format),
        'category-analytics': reverse('category-analytics', request=request, format=format),
        'subscription-payment-analytics': reverse('sub-payment-analytics', request=request, format=format),
        'featured-ad-analytics': reverse('featured-ad-analytics', request=request, format=format),
        'package-analytics': reverse('package-analytics', request=request, format=format),
        'api-traffic-analytics': reverse('api-traffic-analytics', request=request, format=format),
        'site-visit-analytics': reverse('site-visit-analytics', request=request, format=format),
        
        'users': reverse('user-list', request=request, format=format),
        'user': reverse('user', request=request, format=format),
        "change-password": reverse('change-password', request=request, format=format),
        
        'signup': reverse('signup', request=request, format=format),
        'login': reverse('login', request=request, format=format),
        'logout': reverse('logout', request=request, format=format),
        'logoutall': reverse('logout-all', request=request, format=format),
        'password-reset': reverse('password-reset', request=request, format=format),
        
        # Categries
        'classifications': reverse("classifications", request=request, format=format),
        'categories': reverse("categories", request=request, format=format ),
        'category-detail': reverse("category-detail", args=['pk'],request=request, format=format ),
        'new-category': reverse("new-category", request=request, format=format ),
        
        # ADs
        'ads': reverse("ads", request=request, format=format),
        'user-ads': reverse("user-ads", request=request, format=format),
        'new-ad': reverse("new-ad", request=request, format=format ),
        'ad-detail': reverse("ad-detail", args=['pk'],request=request, format=format),
        
        'produce-ads':reverse("produce-ads", request=request, format=format),
        'input-ads': reverse("input-ads", request=request, format=format),
        'service-ads':reverse("service-ads", request=request, format=format),
        
        #'produce-ads-detail':reverse("produce-ads-detail", request=request, format=format), 
        #'input-ads-detail': reverse("input-ads-detail", request=request, format=format),
        #'service-ads-detail': reverse("service-ads-detail", request=request, format=format),
        
        'top-produce': reverse('top-produce-ads', request=request, format=format),
        'top-inputs': reverse('top-input-ads', request=request, format=format),
        'top-services': reverse('top-service-ads', request=request, format=format),        
        
        # Reviews
        'reviews': reverse('review-list', args=['advertisement_id'], request=request, format=format),
        'new-review': reverse('new-review',request=request, format=format),
        
        # Subscription Packages
        'subscription-packages': reverse("subscription-packages", request=request, format=format),
        'new-subscription-package': reverse("new-subscription-package", request=request, format=format),
        'subscription-packages-detail': reverse("subscription-package-detail", args=['pk'],request=request, format=format),
        
        # Subscriptions
        'subscriptions': reverse("subscriptions", request=request, format=format),
        'new-subscriptions': reverse("new-subscription", request=request, format=format),
        'subscription-detail': reverse("subscription-detail", args=['pk'],request=request, format=format),
        
        #'payment-methods': reverse("payment-methods", request=request, format=format),
        #'payment-method': reverse("payment-method", request=request, format=format),
        
        # Mailing
        'mail-list-create': reverse("mail-list-create", request=request, format=format),
        'mail-detail': reverse("mail-detail", args=['pk'],request=request, format=format),
        'mail-send': reverse("mail-send", args=['pk'],request=request, format=format),
        'mail-requirements': reverse("mail-requirements", request=request, format=format),
        'mail-example': reverse("mail-example", request=request, format=format),
        
        # Tokens            
        #'authorization-token': reverse('token', request=request, format=format),
        'csrf-token': reverse('csrf-token', request=request, format=format),
        
        # Api docs and playground
        'api-playground': reverse('schema-swagger-ui', request=request, format=format),
        'api-docs': reverse('schema-redoc', request=request, format=format),
    })


    