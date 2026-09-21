from getpass import getpass

from app.db.session import SessionLocal
from app.models.user import UserRole
from app.services.auth import create_user, get_user_by_email


def main():
    print("\n=== SkillBridge AI - Create Admin ===\n")

    full_name = input("Admin full name: ").strip()
    email = input("Admin email: ").strip().lower()

    if not full_name:
        raise SystemExit("Admin full name is required.")

    if not email or "@" not in email:
        raise SystemExit("A valid admin email is required.")

    password = getpass("Admin password: ")
    confirm_password = getpass("Confirm password: ")

    if password != confirm_password:
        raise SystemExit("Passwords do not match.")

    if len(password) < 10:
        raise SystemExit(
            "Use a password with at least 10 characters."
        )

    db = SessionLocal()

    try:
        existing = get_user_by_email(db, email)

        if existing:
            print(
                "\nAn account with this email already exists."
            )
            print(
                f"Current role: {getattr(existing.role, 'value', existing.role)}"
            )
            print(
                "For safety this script will not automatically promote "
                "an existing account to admin."
            )
            raise SystemExit(1)

        admin = create_user(
            db=db,
            full_name=full_name,
            email=email,
            password=password,
            role=UserRole.admin.value,
        )

        # Admin accounts created by this private bootstrap script are
        # active and trusted. Public registration must never create admins.
        admin.is_active = True
        admin.is_verified = True

        db.commit()
        db.refresh(admin)

        print("\nAdmin created successfully.")
        print(f"ID: {admin.id}")
        print(f"Name: {admin.full_name}")
        print(f"Email: {admin.email}")
        print(f"Role: {getattr(admin.role, 'value', admin.role)}")
        print("\nYou can now sign in through the private Admin Login page.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
