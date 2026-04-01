"""
Assign default user role to existing users
"""
from sqlalchemy.orm import Session
from backend.database.session import SessionLocal
from backend.database.models import User, Role, UserRole


def assign_default_roles():
    """Assign user role to all existing users without roles"""
    db: Session = SessionLocal()

    try:
        user_role = db.query(Role).filter(Role.name == 'user').first()
        if not user_role:
            print("✗ User role not found. Run migration first.")
            return

        users = db.query(User).all()
        assigned = 0

        for user in users:
            existing = db.query(UserRole).filter(
                UserRole.user_id == user.id
            ).first()

            if not existing:
                db.add(UserRole(user_id=user.id, role_id=user_role.id))
                assigned += 1

        db.commit()
        print(f"✓ Assigned default role to {assigned} users")

    except Exception as e:
        db.rollback()
        print(f"✗ Failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    assign_default_roles()
