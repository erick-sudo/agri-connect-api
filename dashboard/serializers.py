from rest_framework import serializers
from rest_framework.validators import ValidationError, UniqueValidator

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import Group, Permission
from django.contrib.auth import get_user_model

from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from django.core.files.uploadedfile import UploadedFile
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from .utils.utils import CustomValidators, NormalizeData
from .utils.mpesa import MpesaClient

from . import models as db

CustomUser = get_user_model()

# Categories
class CategoryRelationSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.CategoryRelation
        fields = ["id", "parent", "child"]

    def validate(self, data):
        if data['parent'] == data['child']:
            raise serializers.ValidationError("A category cannot be its own parent.")
        
        # Check for circular reference
        parent = data['parent']
        while parent:
            if parent == data['child']:
                raise serializers.ValidationError("Circular reference detected.")
            parent = parent.parent
        
        return data

class SubCategorySerializer(serializers.ModelSerializer):
    sub_categories = serializers.SerializerMethodField()

    class Meta:
        model = db.Category
        fields = ["id", "classification", "image", "name", "sub_categories"]

    def get_sub_categories(self, obj):
        return SubCategorySerializer(obj.children.all(), many=True).data

class CategorySerializer(serializers.ModelSerializer):
    sub_categories = serializers.SerializerMethodField(read_only=True)
    hierarchy_level = serializers.IntegerField(read_only=True)
    parent = serializers.PrimaryKeyRelatedField(queryset=db.Category.objects.all(), required=False, allow_null=True)
    #image = serializers.ImageField(required=False, allow_null=True, use_url=True)

    class Meta:
        model = db.Category
        fields = ["id", "name", "classification", "parent", "sub_categories", "hierarchy_level"]
        extra_kwargs = {
            'name': {'required': False},
            'classification': {'required': False},
        }

    def get_sub_categories(self, obj):
        return CategorySerializer(obj.children.all(), many=True).data

    def validate(self, data):
        if 'parent' in data:
            if self.instance and data['parent'] and data['parent'].id == self.instance.id:
                raise serializers.ValidationError("A category cannot be its own parent.")
            if self.instance and data['parent'] and self.instance.children.filter(id=data['parent'].id).exists():
                raise serializers.ValidationError("Cannot set a child category as the parent (circular reference).")
        return data
       

# Advertisement Serializers
class AdvertisementPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.AdvertisementPhoto
        fields = ['id', 'photo']
        read_only_fields = ['id']

class AdvertisementSerializer(serializers.ModelSerializer):
    advertisement_photos = AdvertisementPhotoSerializer(many=True, read_only=True)

    class Meta:
        model = db.Advertisement
        fields = [
            "id",
            "category",
            "title",
            "description",
            "county",
            "sub_county",
            "geo_location",
            "views",
            "created_on",
            "updated_on",
            "advertisement_photos",
        ]
        read_only_fields = ["views", "created_on", "updated_on"]

    def create(self, validated_data):
        user = self.context.get("request").user
        photos_data = self.context.get("request").FILES
        advertisement = db.Advertisement.objects.create(user=user, **validated_data)

        for photo_data in photos_data.getlist("photos"):
            db.AdvertisementPhoto.objects.create(advert=advertisement, photo=photo_data)

        return advertisement

# Custom User serializers
class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        
        id = model.id
        fields = ["id","first_name", "last_name", "email", "phone", "created_on","last_login"]

class UserManagementSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(required=False)

    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email', 'phone', 'is_active', 'is_staff', 'is_superuser', 'profile_picture']
        read_only_fields = ['id', 'created_on', 'updated_on']
    
    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')

        if not request or not request.user.is_superuser:
            # Remove admin-only fields for non-admin users
            ret.pop('is_staff', None)
            ret.pop('is_superuser', None)

        if not request or not request.user.is_staff:
            # Remove staff-only fields for non-staff users
            ret.pop('is_active', None)
            ret.pop('is_staff', None)
            ret.pop('is_superuser', None)

        return ret
    
    def update(self, instance, validated_data):
        # Handle profile picture update separately
        profile_picture = validated_data.pop('profile_picture', None)
        if profile_picture:
            instance.profile_picture = profile_picture

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def destroy(self, instance):
        instance.deactivate()
        return instance
 
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Incorrect old password.")
        return value
       
class RegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(validators=[UniqueValidator(queryset=db.CustomUser.objects.all())])
    phone = serializers.CharField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = db.CustomUser
        fields = ["first_name", "last_name", "email", "phone", "password", "confirm_password"]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['confirm_password']:
            raise ValidationError({"confirm_password": "Passwords do not match."})
        return attrs
    
    def validate_phone(self, value):
        custom_validators = CustomValidators()
        normalizers = NormalizeData()

        # Validate phone number format and length
        custom_validators.validate_phone_number(value)

        # Normalize phone number
        normalized_phone = normalizers.normalize_phone_number(value)

        # Check if the normalized phone number already exists
        if db.CustomUser.objects.filter(phone=normalized_phone).exists():
            raise ValidationError("Phone number has already been used.")

        return normalized_phone

    def validate_password(self, value):
        # Validate password strength
        validate_password(value)
        return value

    def create(self, validated_data):
        # Remove the confirm password field
        validated_data.pop('confirm_password')
        
        first_name = validated_data['first_name']
        last_name = validated_data['last_name']
        email = BaseUserManager.normalize_email(validated_data['email'])
        phone = validated_data['phone']
        password = validated_data['password']

        user = db.CustomUser.objects.create(
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
        )
        
        user.set_password(password)
        user.save()
        
        return user

class LoginSerializer(serializers.Serializer):
    credential = serializers.CharField(required=True, help_text="Email or Phone Number")
    password = serializers.CharField(required=True, write_only=True)

class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    

# Subscriptions
class SubscriptionPackageSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.SubscriptionPackage
        fields = ['id', 'name', 'description', 'duration', 'pricing']

    def validate_duration(self, value):
        if value <= 0:
            raise serializers.ValidationError("Duration must be a positive integer.")
        return value

    def validate_pricing(self, value):
        if value < 0:
            raise serializers.ValidationError("Pricing must be a non-negative number.")
        return value

class PaymentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    
    class Meta:
        model = db.Payment
        fields = [
            "user",
            "trans_id",
            "transaction_type",
            "trans_time",
            "trans_amount",
            "business_short_code",
            "invoice_number",
            "msisdn"
            "org_account_balance",
            "third_party_trans_id",
            "first_name",
            "middle_name",
            "last_name"
        ]

    def validate_trans_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Transaction amount must be a non-negative number.")
        return value

class SubscriptionSerializer(serializers.ModelSerializer):
    payment = serializers.JSONField(write_only=True)
    package = serializers.PrimaryKeyRelatedField(queryset=db.SubscriptionPackage.objects.all())

    class Meta:
        model = db.Subscription
        fields = ['user', 'package', 'payment']

    def create(self, validated_data):
        payment_data = validated_data.pop('payment')
        package = validated_data.pop('package')

        # Create a Payment instance and generate an invoice
        payment = db.Payment.objects.create(
            user=validated_data['user'],
            trans_amount=payment_data['trans_amount'],
            msisdn=payment_data['msisdn'],
            transaction_type='Mpesa',
            business_short_code=payment_data.get('business_short_code', ''),
            bill_ref_number=payment_data.get('bill_ref_number', ''),
            first_name=payment_data['first_name'],
            middle_name=payment_data.get('middle_name', ''),
            last_name=payment_data['last_name'],
        )
        payment.generate_invoice_number()

        mpesa_client = MpesaClient()
        phone_number = payment.msisdn
        amount = payment.trans_amount
        account_reference = payment.bill_ref_number or 'Subscription'
        transaction_desc = 'Subscription Payment'

        # Initiate the payment
        mpesa_response = mpesa_client.lipa_na_mpesa_online(phone_number, amount, account_reference, transaction_desc)
        
        if mpesa_response.get('ResponseCode') == '0':
            # Payment initiated successfully, update the Payment instance with the transaction ID
            payment.trans_id = mpesa_response['CheckoutRequestID']
            payment.save()

            # Calculate start and end dates
            start_date = timezone.now().date()
            end_date = start_date + timezone.timedelta(days=package.duration)

            # Create the Subscription instance
            subscription = db.Subscription.objects.create(
                payment=payment,
                package=package,
                start_date=start_date,
                end_date=end_date,
                **validated_data
            )

            return subscription
        else:
            payment.delete()  # Remove the payment instance if payment initiation fails
            raise serializers.ValidationError("Mpesa payment initiation failed")

# Mailing
class MailSerializer(serializers.Serializer):
    mail_type = serializers.ChoiceField(choices=['individual', 'bulk'])
    recipient = serializers.EmailField(required=False)
    recipients = serializers.ChoiceField(choices=db.BulkMail.BulkMailType.choices, required=False)
    subject = serializers.CharField(max_length=255)
    message = serializers.CharField()
    attachments = serializers.ListField(
        child=serializers.FileField(max_length=100000, allow_empty_file=False, use_url=False),
        required=False
    )
    send_now = serializers.BooleanField(default=True) 

    def validate_attachments(self, value):
        if value:
            for attachment in value:
                if not isinstance(attachment, UploadedFile):
                    raise serializers.ValidationError(f"Invalid file upload for {attachment}")
                if attachment.size > 10 * 1024 * 1024:  # 10 MB limit
                    raise serializers.ValidationError(f"File {attachment.name} is too large. Max size is 10 MB.")
        return value

    def validate(self, data):
        if data['mail_type'] == 'individual':
            if not data.get('recipient'):
                raise serializers.ValidationError("Recipient is required for individual mail.")
            try:
                validate_email(data['recipient'])
            except ValidationError:
                raise serializers.ValidationError("Invalid email for recipient.")
        elif data['mail_type'] == 'bulk':
            if not data.get('recipients'):
                raise serializers.ValidationError("Recipients type is required for bulk mail.")
        return data

# Reviews
class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = db.Reviews
        fields = ['id', 'advertisement', 'message', 'rating']
        read_only_fields = ['id']

    def validate(self, data):
        user = self.context['request'].user
        advertisement = data['advertisement']
        
        if advertisement.user == user:
            raise serializers.ValidationError("You cannot review your own advertisement.")
        
        return data
    
# Groups and permissions
class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename', 'content_type']

class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']


# analytics

class AnalyticsSerializer(serializers.Serializer):
    user_analytics = serializers.DictField()
    advertisement_analytics = serializers.DictField()
    category_analytics = serializers.DictField()
    subscription_payment_analytics = serializers.DictField()
    featured_ad_analytics = serializers.DictField()
    package_analytics = serializers.DictField()