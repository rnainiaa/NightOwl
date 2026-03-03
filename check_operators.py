import sqlite3
import os

# Vérifier si la base de données existe
print("DB exists:", os.path.exists('data/nightowl.db'))

if os.path.exists('data/nightowl.db'):
    conn = sqlite3.connect('data/nightowl.db')
    cursor = conn.cursor()
    
    # Vérifier toutes les tables
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
    tables = cursor.fetchall()
    print("\nTables in database:")
    for table in tables:
        print(f"  {table[0]}")
    
    # Vérifier si la table operators existe
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="operators"')
    operators_table = cursor.fetchone()
    
    if operators_table:
        print(f"\nOperators table exists!")
        
        # Vérifier le schéma de operators
        print("Schema of operators table:")
        cursor.execute('PRAGMA table_info(operators)')
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # Vérifier les données
        print("\nData in operators table:")
        cursor.execute('SELECT * FROM operators')
        rows = cursor.fetchall()
        for row in rows:
            print(f"  {row}")
    else:
        print("\nOperators table does not exist")
    
    conn.close()
else:
    print("Database file does not exist")
