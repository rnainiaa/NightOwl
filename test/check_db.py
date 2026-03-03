import sqlite3
import os

# Vérifier si la base de données existe
print("DB exists:", os.path.exists('nightowl.db'))

if os.path.exists('nightowl.db'):
    conn = sqlite3.connect('nightowl.db')
    cursor = conn.cursor()
    
    # Vérifier toutes les tables
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cursor.fetchall()
    print("\nTables in database:")
    for table in tables:
        print(f"  {table[0]}")
    
    # Vérifier le schéma de operators si elle existe
    if any('operators' in table for table in tables):
        print("\nSchema of operators table:")
        cursor.execute('PRAGMA table_info(operators)')
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
    else:
        print("\nOperators table does not exist")
    
    conn.close()
else:
    print("Database file does not exist")