from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Category, CategoryRelations, CategoryHierarchy

@receiver(post_save, sender=CategoryRelations)
def update_hierarchy_level(sender, instance, created, **kwargs):
    if created:
        parent_level = instance.parent.hierarchy_level
        instance.child.hierarchy_level = parent_level + 1
        instance.child.save()

        # Also update the CategoryHierarchy table
        CategoryHierarchy.objects.update_or_create(
            category=instance.child,
            defaults={'hierarchy_level': instance.child.hierarchy_level}
        )

@receiver(post_delete, sender=CategoryRelations)
def reset_hierarchy_level(sender, instance, **kwargs):
    instance.child.hierarchy_level = 0
    instance.child.save()

    # Also update the CategoryHierarchy table
    CategoryHierarchy.objects.update_or_create(
        category=instance.child,
        defaults={'hierarchy_level': instance.child.hierarchy_level}
    )
