from django.db.models import Count, Avg, Sum
from django.utils import timezone
from datetime import timedelta
from .models import CustomUser, Advertisement, Category, Subscription, Payment, FeaturedAdvertisement, SubscriptionPackage, PageVisit, SiteVisit

class Analytics:

    @staticmethod
    def user_analytics():
        total_users = CustomUser.objects.count()
        active_users = CustomUser.objects.filter(is_active=True).count()
        new_users_last_week = CustomUser.objects.filter(created_on__gte=timezone.now() - timedelta(days=7)).count()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_users_last_week': new_users_last_week,
            'inactive_users': total_users - active_users,
        }

    @staticmethod
    def advertisement_analytics():
        total_ads = Advertisement.objects.count()
        ads_by_category = Advertisement.objects.values('category__name').annotate(count=Count('id'))
        most_viewed_ads = Advertisement.objects.order_by('-views')[:10]
        
        ads_last_month = Advertisement.objects.filter(created_on__gte=timezone.now() - timedelta(days=30))
        avg_views_last_month = ads_last_month.aggregate(Avg('views'))['views__avg']
        
        return {
            'total_ads': total_ads,
            'ads_by_category': list(ads_by_category),
            'most_viewed_ads': list(most_viewed_ads.values('title', 'views')),
            'avg_views_last_month': avg_views_last_month,
        }

    @staticmethod
    def category_analytics():
        total_categories = Category.objects.count()
        categories_by_classification = Category.objects.values('classification').annotate(count=Count('id'))
        top_level_categories = Category.objects.filter(parent__isnull=True).count()
        
        return {
            'total_categories': total_categories,
            'categories_by_classification': list(categories_by_classification),
            'top_level_categories': top_level_categories,
        }

    @staticmethod
    def subscription_payment_analytics():
        total_subscriptions = Subscription.objects.count()
        active_subscriptions = Subscription.objects.filter(active=True).count()
        subscriptions_by_package = Subscription.objects.values('package__name').annotate(count=Count('id'))
        
        total_revenue = Payment.objects.aggregate(Sum('trans_amount'))['trans_amount__sum']
        payments_last_month = Payment.objects.filter(trans_time__gte=timezone.now() - timedelta(days=30))
        revenue_last_month = payments_last_month.aggregate(Sum('trans_amount'))['trans_amount__sum']
        
        return {
            'total_subscriptions': total_subscriptions,
            'active_subscriptions': active_subscriptions,
            'subscriptions_by_package': list(subscriptions_by_package),
            'total_revenue': total_revenue,
            'revenue_last_month': revenue_last_month,
        }

    @staticmethod
    def featured_ad_analytics():
        total_featured_ads = FeaturedAdvertisement.objects.count()
        featured_ads_by_package = FeaturedAdvertisement.objects.values(
            'subscription__package__name'
        ).annotate(count=Count('id'))
        
        return {
            'total_featured_ads': total_featured_ads,
            'featured_ads_by_package': list(featured_ads_by_package),
        }

    @staticmethod
    def package_analytics():
        total_packages = SubscriptionPackage.objects.count()
        packages_by_duration = SubscriptionPackage.objects.values('duration').annotate(count=Count('id'))
        most_popular_package = Subscription.objects.values('package__name').annotate(
            count=Count('id')
        ).order_by('-count').first()
        
        return {
            'total_packages': total_packages,
            'packages_by_duration': list(packages_by_duration),
            'most_popular_package': most_popular_package,
        }

    @staticmethod
    def analyze_api_traffic():
        # Count API calls
        api_calls = PageVisit.objects.filter(is_api_call=True).count()
        print(f"Total API calls: {api_calls}")

        # Most used API endpoints
        top_endpoints = PageVisit.objects.filter(is_api_call=True).values('path', 'method').annotate(
            call_count=Count('id')
        ).order_by('-call_count')[:10]
        print("Top API endpoints:")
        for endpoint in top_endpoints:
            print(f"{endpoint['method']} {endpoint['path']}: {endpoint['call_count']} calls")

        # API usage by authenticated users
        auth_api_calls = PageVisit.objects.filter(is_api_call=True, user__isnull=False).count()
        print(f"API calls by authenticated users: {auth_api_calls}")

        # API usage by unauthenticated users
        unauth_api_calls = PageVisit.objects.filter(is_api_call=True, user__isnull=True).count()
        print(f"API calls by unauthenticated users: {unauth_api_calls}")

        # Most active API users
        top_users = PageVisit.objects.filter(is_api_call=True, user__isnull=False).values('user__email').annotate(
            call_count=Count('id')
        ).order_by('-call_count')[:10]
        print("Top API users:")
        for user in top_users:
            print(f"{user['user__email']}: {user['call_count']} calls")

    @staticmethod
    def site_visit_analytics():
        total_visits = SiteVisit.objects.count()
        visits_today = SiteVisit.objects.filter(timestamp__date=timezone.now().date()).count()
        visits_last_week = SiteVisit.objects.filter(timestamp__gte=timezone.now() - timedelta(days=7)).count()
        
        top_pages = SiteVisit.objects.values('path').annotate(
            visit_count=Count('id')
        ).order_by('-visit_count')[:10]
        
        unique_visitors = SiteVisit.objects.values('ip_address').distinct().count()
        
        return {
            'total_visits': total_visits,
            'visits_today': visits_today,
            'visits_last_week': visits_last_week,
            'top_pages': list(top_pages),
            'unique_visitors': unique_visitors,
        }
    
    @staticmethod
    def get_all_analytics():
        return {
            'user_analytics': Analytics.user_analytics(),
            'advertisement_analytics': Analytics.advertisement_analytics(),
            'category_analytics': Analytics.category_analytics(),
            'subscription_payment_analytics': Analytics.subscription_payment_analytics(),
            'featured_ad_analytics': Analytics.featured_ad_analytics(),
            'package_analytics': Analytics.package_analytics(),
            "api-traffic-analytics": Analytics.analyze_api_traffic(),
            "site-visit-analytics": Analytics.site_visit_analytics(),
        }
        
        