
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import PermissionsMixin
from django.contrib import admin
from django.db import models

from django.core.mail import send_mail
from django.core.exceptions import ValidationError
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from django.utils.html import strip_tags

from datetime import datetime, timedelta
from dashboard import managers

import uuid
import random
import string

# Custom User Manager

# Create your models here.

class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(_("First Name"), max_length=50, blank=False, null=False)
    last_name = models.CharField(_("Last Name"), max_length=50, blank=False, null=False)
    profile_picture = models.ImageField(_("Profile Picture"), upload_to="profiles/", default="user.png")
    email = models.EmailField(_("Email"), blank=False, max_length=255, unique=True)
    phone = models.CharField(_("Phone Number"), max_length=13, blank=False, null=False, unique=True)
    created_on = models.DateTimeField(_("Joined On"), auto_now_add=True)
    updated_on = models.DateTimeField(_("Updated On"), auto_now=True)
    is_active = models.BooleanField(_("Active"), default=True)
    is_staff = models.BooleanField(_("Staff"), default=False)
    is_superuser = models.BooleanField(_("Admin"), default=False)
    
    objects = managers.CustomUserManager()
        
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "phone"]

    def deactivate(self):
        "Change user status to inactive instead of deleting."
        self.is_active = False
        self.save()
        
    def activate(self):
        "Change user status to active instead."
        self.is_active = True
        self.save()
      
    @property
    def is_new(self):
        now = datetime.now().astimezone()
        return now - timedelta(days=7) <= self.created_on <= now
    
    def get_full_name(self):
        return f"{str.capitalize(self.first_name)} {str.capitalize(self.last_name)}"
    
    def get_short_name(self):
        return f"{str.capitalize(self.first_name)}"
    
    def __str__(self):
        return self.get_full_name()
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-created_on"]
        
# Categories     
class Category(models.Model):
    
    class ADVERT_CLASSIFICATION(models.TextChoices):
        FARM_PRODUCE = "FP", _("Farm Produce/Products")
        #FARM_INPUT = "FI", _("Farm Input")
        SERVICE_LISTING = "SL", _("Service Listing")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(_("Name"), max_length=50, unique=True, blank=False, null=False)
    image = models.ImageField(_("Image"), upload_to="categories/", default="category.png")
    classification = models.CharField(_("Classification"), max_length=2, choices=ADVERT_CLASSIFICATION.choices, default=ADVERT_CLASSIFICATION.FARM_PRODUCE)
    parent = models.ForeignKey('self', verbose_name=_("Parent Category"), null=True, blank=True, on_delete=models.CASCADE, related_name='children')

    def __str__(self):
        return f"{str.capitalize(self.name)}"

    class Meta:
        verbose_name = _("Advertisement Category")
        verbose_name_plural = _("Advertisement Categories")
        ordering = ["-name"]
        
    @property
    def hierarchy_level(self):
        level = 0
        parent = self.parent
        while parent:
            level += 1
            parent = parent.parent
        return level 
       
    def clean(self):
        if self.parent:
            parent = self.parent
            while parent:
                if parent == self:
                    raise ValidationError("A category cannot be its own parent or create a circular reference.")
                parent = parent.parent
    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    

class CategoryRelation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    parent = models.ForeignKey(Category, verbose_name=_("Parent"), related_name="child_relations", on_delete=models.CASCADE)
    child = models.ForeignKey(Category, verbose_name=_("Child"), related_name="parent_relations", on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.parent.name} -> {self.child.name}"

    class Meta:
        verbose_name = _("Category Relation")
        verbose_name_plural = _("Category Relations")
        ordering = ["parent", "child"]
        constraints = [
            models.UniqueConstraint(fields=['parent', 'child'], name='unique_category_relation')
        ]
    
# Advertisements
class Advertisement(models.Model):
    id = models.UUIDField(primary_key=True, unique=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, related_name="advertisements", on_delete=models.CASCADE)

    category = models.ForeignKey(Category, related_name="advertisement_category", on_delete=models.RESTRICT)
    title = models.CharField(_("Title"), max_length=100, blank=False, null=False)
    description = models.TextField(_("Description"), blank=False, null=False)

    # location
    county = models.CharField(_("County"), max_length=50, null=False, blank=False)
    sub_county = models.CharField(_("Sub County"), max_length=50, null=False, blank=False)
    geo_location = models.URLField(_("Maps URI"), max_length=1000, blank=True)

    views = models.IntegerField(_("Views"), default=0)
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    @admin.display(
        boolean=True,
        ordering="-created_on",
        description="Is New?",
    )
    def is_new(self):
        now = datetime.now().astimezone()
        if now - timedelta(days=7) <= self.created_on <= now:
            return True

    def __str__(self):
        return F"{self.title} - {self.category.__str__}"

    class Meta:
        verbose_name_plural = "Advertisements"
        verbose_name = "Advertisement"
        ordering = ["-created_on"]

class AdvertisementPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    advert = models.ForeignKey(Advertisement, related_name="advertisement_photos", on_delete=models.CASCADE)
    photo = models.ImageField(_("Photo"), upload_to="ad-images/")

    class Meta:
        verbose_name = "Advertisement Photo"
        verbose_name_plural = "Advertisement Photos"

class ProduceAdvertisement(Advertisement):
    pass

class InputAdvertisement(Advertisement):
    pass

class ServiceAdvertisement(Advertisement):
    pass

# Reviews
class Reviews(models.Model):
    class RatingChoices(models.TextChoices):
        one = "1", _("1 Star")
        two = "2", _("2 Stars")
        three = "3", _("3 Stars")
        four = "4", _("4 Stars")
        five = "5", _("5 Stars")
        
    advertisement = models.ForeignKey(Advertisement, on_delete=models.CASCADE)
    message = models.TextField(_("Review"), blank=True)
    rating = models.CharField(_("Rating"), max_length=1, choices = RatingChoices.choices, default = RatingChoices.one)    

# Subscriptions
class SubscriptionPackage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    name = models.CharField(_("Package Name"), max_length=50, unique=True, blank=False, null=False)
    description = models.TextField(_("Package Description"), blank=False)
    duration = models.PositiveIntegerField(_("Duration (Days)"), default=30)
    pricing = models.DecimalField(_("Pricing (KSH)"), max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.name}"
    
    class Meta:
        verbose_name = "Subscription Package"
        verbose_name_plural = "Subscription Packages"
        ordering = ["-duration"]

class Offering(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False)
    package = models.ForeignKey(SubscriptionPackage, related_name="package_offerings", on_delete=models.CASCADE)
    offering = models.CharField(_("Offering"), max_length=150, blank=False, null=False)
    
    class Meta:
        verbose_name = "Package Offering"
        verbose_name_plural = "Package Offerings"


# Payment Processing
class PaymentMethods(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payment_methods')
    name = models.CharField(max_length=100)
    mpesa_phone_number = models.CharField(max_length=20)
 
class Payment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(CustomUser, on_delete=models.RESTRICT)
    transaction_type = models.CharField(_("Transaction Type"), max_length=50, default="Pay Bill")
    trans_id = models.CharField(_("Transaction ID"), max_length=50, unique=True)
    trans_time = models.DateTimeField(_("Transaction Time"), null=True, blank=True)
    trans_amount = models.DecimalField(_("Transaction Amount"), decimal_places=2, max_digits=10)
    business_short_code = models.CharField(_("Business Short Code"), max_length=50)
    bill_ref_number = models.CharField(_("Bill Reference Number"), max_length=50)
    invoice_number = models.CharField(_("Invoice Number"), max_length=50, blank=True, unique=True)
    org_account_balance = models.DecimalField(_("Organization Account Balance"), decimal_places=2, max_digits=10, null=True, blank=True)
    third_party_trans_id = models.CharField(_("Third Party Transaction ID"), max_length=50, blank=True)
    msisdn = models.CharField(_("MSISDN"), max_length=15)
    first_name = models.CharField(_("First Name"), max_length=50)
    middle_name = models.CharField(_("Middle Name"), max_length=50, blank=True)
    last_name = models.CharField(_("Last Name"), max_length=50)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    def __str__(self):
        return f"{self.trans_id} - {self.first_name} {self.last_name}"

    def generate_invoice_number(self):
        while True:
            invoice_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            if not Payment.objects.filter(invoice_number=invoice_number).exists():
                self.invoice_number = invoice_number                
                break

class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    package = models.ForeignKey(SubscriptionPackage, on_delete=models.CASCADE)
    payment = models.ForeignKey(Payment, on_delete=models.RESTRICT)
    start_date = models.DateField()
    end_date = models.DateField()
    active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-active', '-end_date']
 

# Paid Features 
class FeaturedAdvertisement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    advertisement = models.ForeignKey(Advertisement, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Featured Advertisement"
        verbose_name_plural = "Featured Advertisements"

# Mails
class Mails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sender = models.ForeignKey(CustomUser, on_delete=models.RESTRICT)
    subject = models.CharField(_("Subject"), max_length=255, blank=True)
    message = models.TextField(_("Message"))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent = models.BooleanField(_("Sent"), default=False)
    
    class Meta:
        abstract = True
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subject[:50]}..." if self.subject else "No subject"

class IndividualMail(Mails):
    recipient = models.EmailField(_("Recipient"))
    
    class Meta:
        verbose_name = _("Individual Mail")
        verbose_name_plural = _("Individual Mails")

class BulkMail(Mails):
    class BulkMailType(models.TextChoices):
        STAFF = "staff", _("Staff")
        CLIENTS = "clients", _("Clients")
        ALL = "all", _("All")
    
    recipients = models.CharField(_("Send To"), max_length=10, choices=BulkMailType.choices, default=BulkMailType.STAFF)
    
    class Meta:
        verbose_name = _("Bulk Mail")
        verbose_name_plural = _("Bulk Mails")

class MailAttachment(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.RESTRICT)
    object_id = models.UUIDField(default=uuid.uuid4)
    content_object = GenericForeignKey('content_type', 'object_id')
    file = models.FileField(_("File"), upload_to='mail_attachments/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Mail Attachment")
        verbose_name_plural = _("Mail Attachments")

    def __str__(self):
        return f"Attachment for {self.content_object}"
    
# User Site visits
class SiteVisit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(null=True, blank=True)
    path = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class PageVisit(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    token_key = models.CharField(max_length=64, null=True, blank=True)  # For Knox token
    ip_address = models.GenericIPAddressField()
    path = models.CharField(max_length=255)
    method = models.CharField(max_length=10)  # GET, POST, etc.
    is_api_call = models.BooleanField(default=False)
    referer = models.URLField(max_length=255, null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'API' if self.is_api_call else 'Page'} {self.method} {self.path} at {self.timestamp}"
    