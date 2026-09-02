from app.models.notification import Notification

def create_notification(db, user_id:int, title:str, message:str, notification_type:str="general", related_id:int|None=None):
    n=Notification(user_id=user_id,title=title,message=message,notification_type=notification_type,related_id=related_id)
    db.add(n); return n
