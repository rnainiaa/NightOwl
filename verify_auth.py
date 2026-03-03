from server.database import Database
from server.security import SecurityManager

db = Database({'path': 'data/nightowl.db'})
row = db.get_operator_by_username('admin')
print(f"DB Hash: {row['password_hash']}")

sec = SecurityManager({})
is_valid = sec.verify_password("admin123", row['password_hash'])
print(f"Verify admin123: {is_valid}")
