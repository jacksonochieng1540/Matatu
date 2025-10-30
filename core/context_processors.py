
from .models import Notification, SystemSetting

def system_settings(request):
    """Add system settings to all templates"""
    context = {}
    
    # Add unread notifications count for authenticated users
    if request.user.is_authenticated:
        context['unread_notifications'] = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
    
    # Add system settings
    settings_dict = {}
    for setting in SystemSetting.objects.all():
        settings_dict[setting.key] = setting.value
    context['system_settings'] = settings_dict
    
    return context

