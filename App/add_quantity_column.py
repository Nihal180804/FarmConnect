import sys
sys.path.insert(0, 'c:/Users/nihal/Documents/FarmConnect/App')

from database import get_conn

def add_quantity_column():
    cnx = get_conn()
    cursor = cnx.cursor()
    
    try:
        # Add QuantityAvailable column with default value 100
        cursor.execute('''
            ALTER TABLE Product 
            ADD COLUMN QuantityAvailable INT DEFAULT 100 NOT NULL
        ''')
        cnx.commit()
        print("✓ QuantityAvailable column added successfully")
        
        # Show updated schema
        cursor.execute("DESCRIBE Product")
        print("\nUpdated Product table schema:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
            
    except Exception as e:
        if "Duplicate column name" in str(e):
            print("✓ QuantityAvailable column already exists")
        else:
            print(f"✗ Error: {e}")
            cnx.rollback()
    finally:
        cursor.close()
        cnx.close()

if __name__ == "__main__":
    add_quantity_column()
