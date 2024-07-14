from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from . import models as db
from .forms import CustomUserCreationForm, CustomUserChangeForm
# Custom User forms

# Register your models here.

# Custom User Admin
class CustomUserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    prepolulated_field = {"slug": ["email"]}
    list_display = ["__str__","phone", "created_on", "is_active"]
    list_filter = ["is_active", "is_staff", "is_superuser"]
    fieldsets= (
        ("Profile Picture:", {"fields":["profile_picture"]}),
        ("Personal Info:", {"fields":["first_name", "last_name"]}),
        ("Contact Info:", {"fields":["phone", "email"]}),
        ("Permissions", {"fields": ["is_active", "is_staff","is_superuser"]}),
    )
    add_fieldsets = [
        (
            None,
            {
                "classes": ["wide"],
                "fields": ["first_name", "last_name","email", "phone", "password1", "password2"],
            },
        ),
    ]
    search_fields = ["email"]
    ordering = ["email"]
    filter_horizontal = []
    
class OfferingsInline(admin.StackedInline):
    model = db.Offering
    extra = 2
    
class SubscriptionPackageAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Package Info:", {"fields": ["name", "duration"]}),
    )
    inlines = [OfferingsInline]
    list_disply = ["__str__"]
    
class SubscriptionAdmin(admin.ModelAdmin):
    fieldsets =(
        ("Subscription Info:", {"fields": ["user", "package", "active"]}),
    )
    list_display = ["user", "package", "start_date", "end_date",'active']

# Categories Admin
class CategoryInline(admin.StackedInline):
    model = db.Category
    fk_name = "parent"
    extra = 0
    verbose_name = "Sub-category"
    verbose_name_plural = "Sub-categories"

class CategoryRelationInline(admin.StackedInline):
    model = db.CategoryRelation
    fk_name = "parent"
    extra = 0
    verbose_name = "Additional Child Category"
    verbose_name_plural = "Additional Child Categories"

class CategoryAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Banner Image", {"fields": ["image"]}),
        ("Category Info", {"fields": ["name", "classification", "parent"]}),
    )
    inlines = [CategoryInline, CategoryRelationInline]
    
    list_display = ["name", "classification", "parent", "hierarchy_level"]
    list_filter = ["classification", "parent"]
    search_fields = ["name", "classification"]

class CategoryRelationAdmin(admin.ModelAdmin):
    list_display = ["parent", "child"]
    list_filter = ["parent", "child"]
    search_fields = ["parent__name", "child__name"]
# Advertisement Admins
class AdvertPhotosInline(admin.StackedInline):
    model = db.AdvertisementPhoto
    extra = 3

class ProduceAdvertisementAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Advertisement Info", {"fields": ["title", "category", "description"]}),
    )
    inlines = [AdvertPhotosInline]

class InputAdvertisementAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Advertisement Info", {"fields": ["title", "category", "description"]}),
    )
    inlines = [AdvertPhotosInline]

class ServiceAdvertisementAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Advertisement Info", {"fields": ["title", "category", "description"]}),
    )
    inlines = [AdvertPhotosInline]
 

# Page visits
@admin.register(db.PageVisit)
class PageVisitAdmin(admin.ModelAdmin):
    list_display = ('path', 'method', 'is_api_call', 'user', 'token_key', 'ip_address', 'timestamp')
    list_filter = ('timestamp', 'path', 'method', 'is_api_call')
    search_fields = ('path', 'ip_address', 'user__username', 'token_key')
    date_hierarchy = 'timestamp'

# Register admins
admin.site.register(db.CustomUser, CustomUserAdmin)
admin.site.register(db.ProduceAdvertisement, ProduceAdvertisementAdmin)
admin.site.register(db.InputAdvertisement, InputAdvertisementAdmin)
admin.site.register(db.ServiceAdvertisement, ServiceAdvertisementAdmin)
admin.site.register(db.Category, CategoryAdmin)
admin.site.register(db.SubscriptionPackage, SubscriptionPackageAdmin)
admin.site.register(db.Subscription, SubscriptionAdmin)

#admin.site.unregister(Group)