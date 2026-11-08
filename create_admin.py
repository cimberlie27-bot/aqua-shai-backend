from app.database import SessionLocal
from app.models import User
from app.security import hash_password

db = SessionLocal()

# 1. Hanapin at burahin ang lumang admin (kung meron)
old_admin = db.query(User).filter(User.role == 'admin').first()
if old_admin:
    print("Nahanap ang lumang admin. Binubura...")
    db.delete(old_admin)
    db.commit()

# 2. Gumawa ng bagong admin
print("Gumagawa ng bagong admin...")
new_admin = User(
    full_name='Station Admin',
    email='admin@aquashai.ph',
    contact_number='09000000000',
    password_hash=hash_password('Admin12345!'),
    default_address='Peñaranda',
    role='admin',
    is_verified=True,
    is_active=True
)
db.add(new_admin)
db.commit()

print("✅ TAGUMPAY!")
print("Email: admin@aquashai.ph")
print("Password: Admin12345!")
db.close()