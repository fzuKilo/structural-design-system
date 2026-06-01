"""
Database migration script for RBAC
Run this to initialize roles and permissions
"""
import uuid
from sqlalchemy.orm import Session
from backend.database.session import engine, SessionLocal
from backend.database.models import Base, Role, Permission, RolePermission, User, UserRole
import bcrypt


def run_migration():
    """Run RBAC migration"""
    # Create all tables
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    try:
        # Check if roles already exist
        existing_roles = db.query(Role).count()
        if existing_roles > 0:
            print("Roles already exist, skipping migration")
            _ensure_admin_user(db)
            return

        # Create roles
        roles = [
            Role(id='role-admin', name='admin', display_name='管理员',
                 description='系统管理员，拥有所有权限'),
            Role(id='role-user', name='user', display_name='普通用户',
                 description='普通用户，可以创建和查看自己的设计'),
        ]
        db.add_all(roles)
        db.flush()

        # Create permissions
        permissions = [
            Permission(id='perm-design-create', name='design:create',
                      resource='design', action='create', description='创建设计任务'),
            Permission(id='perm-design-read', name='design:read',
                      resource='design', action='read', description='查看设计任务'),
            Permission(id='perm-design-update', name='design:update',
                      resource='design', action='update', description='更新设计任务'),
            Permission(id='perm-design-delete', name='design:delete',
                      resource='design', action='delete', description='删除设计任务'),
            Permission(id='perm-user-manage', name='user:manage',
                      resource='user', action='manage', description='管理用户'),
            Permission(id='perm-role-manage', name='role:manage',
                      resource='role', action='manage', description='管理角色'),
            Permission(id='perm-system-config', name='system:config',
                      resource='system', action='config', description='系统配置')
        ]
        db.add_all(permissions)
        db.flush()

        # Assign all permissions to admin
        admin_role = db.query(Role).filter(Role.name == 'admin').first()
        all_perms = db.query(Permission).all()
        for perm in all_perms:
            db.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))

        # Assign design permissions to user
        user_role = db.query(Role).filter(Role.name == 'user').first()
        design_perms = db.query(Permission).filter(Permission.resource == 'design').all()
        for perm in design_perms:
            db.add(RolePermission(role_id=user_role.id, permission_id=perm.id))

        db.commit()
        print("✓ RBAC migration completed successfully")

        _ensure_admin_user(db)

    except Exception as e:
        db.rollback()
        print(f"✗ Migration failed: {e}")
        raise
    finally:
        db.close()


def _ensure_admin_user(db: Session):
    """创建默认管理员账号（admin / 123456），已存在则跳过。"""
    existing = db.query(User).filter(User.username == 'admin').first()
    if existing:
        print("Admin user already exists, skipping")
        return

    password_hash = bcrypt.hashpw('123456'.encode(), bcrypt.gensalt()).decode()
    admin_user = User(
        id=str(uuid.uuid4()),
        username='admin',
        email='admin@structural-design.local',
        password_hash=password_hash,
        quota_daily=9999,
        quota_monthly=99999,
    )
    db.add(admin_user)
    db.flush()

    admin_role = db.query(Role).filter(Role.name == 'admin').first()
    db.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
    db.commit()
    print("✓ Default admin user created (username: admin, password: 123456)")


if __name__ == "__main__":
    run_migration()

