from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

@login_required
def mark_notifications_read(request):
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return JsonResponse({'status': 'ok'})
