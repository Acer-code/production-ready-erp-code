from .models import Notification

def create_notification(users, title, message, n_type, url=None):
    for u in users:
        Notification.objects.create(
            recipient=u,       # <-- MUST MATCH FIELD NAME IN MODEL
            title=title,
            message=message,
            notification_type=n_type,
            url=url
        )
