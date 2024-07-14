from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework import permissions 
from django.contrib.auth import views as auth_views
from django.urls import path

from drf_yasg.views import get_schema_view 
from drf_yasg import openapi 

from .import views

schema_view = get_schema_view( 
openapi.Info( 
	title="Dummy API", 
	default_version='v1', 
	description="Dummy description", 
	terms_of_service="https://www.google.com/policies/terms/", 
	contact=openapi.Contact(email="contact@dummy.local"), 
	license=openapi.License(name="BSD License"), 
), 
public=True, 
permission_classes=(permissions.AllowAny,), 
) 


urlpatterns = [
    path('', views.api_root, name="api-root"),
    
    # Classification
    path('classifications/', views.AdvertClassificationView.as_view(), name='classifications'),

    # Categories
    path('categories/', views.CategoryList.as_view(), name="categories"),
    path('categories/new', views.NewCategory.as_view(), name="new-category"),
    path('category/<pk>', views.CategoryDetail.as_view(), name="category-detail"),
    
    # ADs
    path("ads/", views.AdsList.as_view(), name="ads"),
    path('ads/user/list', views.UserAdsList.as_view(), name="user-ads"),
    path("ads/new", views.NewAd.as_view(), name="new-ad"),
    path("ads/detail/<pk>", views.AdDetail.as_view(), name="ad-detail"),
    
    path("ads/produce", views.ProduceAdsList.as_view(), name="produce-ads"),    
    path("ads/inputs", views.InputAdsList.as_view(), name="input-ads"),    
    path("ads/services", views.ServiceAdsList.as_view(), name="service-ads"),
    
    #path("ads/produce/<pk>", views.ProduceAdDetail.as_view(), name="produce-ads-detail"),
    #path("ads/inputs/<pk>", views.InputAdDetail.as_view(), name="input-ads-detail"),
    #path("ads/services/<pk>", views.ServiceAdDetail.as_view(), name="service-ads-detail"),
    
    # Top ADs
    path('ads/produce/top', views.TopProduceAds.as_view(), name='top-produce-ads'),
    path('ads/inputs/top', views.TopInputAds.as_view(), name='top-input-ads'),
    path('ads/services/top', views.TopServiceAds.as_view(), name='top-service-ads'),
    
    # Reviews
    path('reviews/new', views.ReviewCreateView.as_view(), name='new-review'),
    path('reviews/<advertisement_id>', views.ReviewListView.as_view(), name='review-list'),
    
    # Accounts Requests
    path('accounts/signup', views.Signup.as_view(), name="signup"),
    path('accounts/login', views.Login.as_view(), name="login"),
    path('accounts/logout', views.Logout.as_view(), name="logout"),
    path('accounts/logout-all', views.LogoutAll.as_view(), name="logout-all"),
    path('accounts/password-reset', views.ResetPassword.as_view(), name="password-reset"),
    path('accounts/password-reset/<str:uid>/<str:token>/', views.ResetPassword.as_view(), name="password-reset"),
    
    # Subscriptions and Packages
    path('subscription/packages', views.SubscriptionPackageList.as_view(), name="subscription-packages"),
    path('subscription/packages/new', views.NewSubscriptionPackage.as_view(), name="new-subscription-package"),
    path('subscription/packages/<pk>', views.SubscriptionPackageDetail.as_view(), name="subscription-package-detail"),
    
    path('subscriptions/', views.SubscriptionList.as_view(), name="subscriptions"),
    path('subscriptions/new', views.SubscriptionCreateView.as_view(), name="new-subscription"),
    path('subscription/<pk>', views.SubscriptionPackageDetail.as_view(), name="subscription-detail"),
    
    # payments
    path('mpesa/callback/', views.MpesaCallbackView.as_view(), name='mpesa-callback'),
    path('payments/', views.Payments.as_view(), name="payments"),
    
    # Mail
    path('mail/', views.MailViewSet.as_view({'get': 'list', 'post': 'create'}), name="mail-list-create"),
    path('mail/requirements/', views.MailViewSet.as_view({'get': 'requirements'}), name="mail-requirements"),
    path('mail/example/', views.MailViewSet.as_view({'get': 'example'}), name="mail-example"),
    path('mail/<pk>/', views.MailViewSet.as_view({'get': 'retrieve'}), name="mail-detail"),
    path('mail/<pk>/send/', views.MailViewSet.as_view({'post': 'send'}), name="mail-send"),

    
    # User Requests    
    path('users/list', views.UserList.as_view(), name="user-list"),
    path('user/', views.User.as_view(), name="user"),
    path('user/change-password', views.ChangePasswordView.as_view(), name='change-password'),
    
    # Analytics
    # urls.py
    path('analytics/', views.AnalyticsView.as_view(), name='all-analytics'),
    path('analytics/users/', views.UserAnalyticsView.as_view(), name='user-analytics'),
    path('analytics/advertisements/', views.AdvertisementAnalyticsView.as_view(), name='ad-analytics'),
    path('analytics/categories/', views.CategoryAnalyticsView.as_view(), name='category-analytics'),
    path('analytics/subscriptions/', views.SubscriptionPaymentAnalyticsView.as_view(), name='sub-payment-analytics'),
    path('analytics/featured-ads/', views.FeaturedAdAnalyticsView.as_view(), name='featured-ad-analytics'),
    path('analytics/packages/',views.PackageAnalyticsView.as_view(), name='package-analytics'),
    path('analytics/api-traffic/',views.APITrafficAnalyticsView.as_view(), name='api-traffic-analytics'),
    path('analytics/site-visits/',views.SiteVisitAnalyticsView.as_view(), name='site-visit-analytics'),
    

    

    # Tokens
    path('get/token', views.get_token, name="token"),
    path('get/csrf-token', views.get_csrf, name="csrf-token"),
        
    # API Playground and Docs
    path('playground/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'), 
    path('docs/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

urlpatterns = format_suffix_patterns(urlpatterns)