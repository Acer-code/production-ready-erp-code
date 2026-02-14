def notification_data(request):
    if request.user.is_authenticated:
        try:
            notifications = request.user.notifications.order_by('-created_at')[:20]
            unread_count = request.user.notifications.filter(is_read=False).count()
        except Exception:
            notifications = []
            unread_count = 0

        return {
            'top_notifications': notifications,
            'unread_notifications': unread_count
        }
    return {}
