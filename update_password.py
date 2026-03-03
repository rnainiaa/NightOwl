import sqlite3
import bcrypt

def update_password():
    db_path = "data/nightowl.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    password = "password123"
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode('utf-8')
    
    print(f"Generated hash for '{password}': {hashed}")
    
    try:
        cursor.execute("UPDATE operators SET password_hash = ? WHERE username = ?", (hashed, "admin"))
        if cursor.rowcount == 0:
            print("User admin not found, creating...")
            cursor.execute("INSERT INTO operators (username, password_hash, role, created_at) VALUES (?, ?, ?, datetime('now'))", 
                          ("admin", hashed, "admin"))
        conn.commit()
        print("Password updated successfully")
        
        # Verify
        cursor.execute("SELECT * FROM operators WHERE username = 'admin'")
        row = cursor.fetchone()
        stored_hash = row['password_hash']
        print(f"Stored hash: {stored_hash}")
        
        # checkpw needs bytes for both
        if bcrypt.checkpw(password.encode(), stored_hash.encode()):
            print("Verification successful!")
        else:
            print("Verification FAILED!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    update_password()
