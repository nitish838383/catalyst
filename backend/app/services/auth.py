from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.core.security import hash_password, verify_password

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email.lower()).first()

def create_user(db: Session, full_name: str, email: str, password: str, role: str):
    user = User(full_name=full_name, email=email.lower(), hashed_password=hash_password(password), role=UserRole(role))
    db.add(user); db.commit(); db.refresh(user); return user

def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user
