import mysql.connector
from config import DB_CONFIG

cnx = mysql.connector.connect(**DB_CONFIG)
cursor = cnx.cursor(dictionary=True)

print("=" * 80)
print("SEARCHING FOR 'Nihal J' ACCOUNT")
print("=" * 80)

# Search in farmer table
print("\n1. Checking Farmer Table:")
cursor.execute("SELECT * FROM farmer WHERE Name LIKE %s", ("%Nihal%",))
farmers = cursor.fetchall()

if farmers:
    for farmer in farmers:
        print(f"\n   ✓ Found Farmer:")
        print(f"     - Farmer ID: {farmer['FarmerID']}")
        print(f"     - Name: {farmer['Name']}")
        print(f"     - Contact: {farmer.get('Contact', 'N/A')}")
        print(f"     - Location: {farmer.get('Location', 'N/A')}")
        print(f"     - Email: {farmer.get('Email', 'N/A')}")
        
        # Check if linked to user account
        cursor.execute("""
            SELECT UserID, Email, UserType, CreatedAt, LastLogin 
            FROM users 
            WHERE RelatedID = %s AND UserType = 'Farmer'
        """, (farmer['FarmerID'],))
        user = cursor.fetchone()
        
        if user:
            print(f"\n   ✓ Linked User Account:")
            print(f"     - User ID: {user['UserID']}")
            print(f"     - Email: {user['Email']}")
            print(f"     - Created: {user['CreatedAt']}")
            print(f"     - Last Login: {user['LastLogin'] or 'Never'}")
        else:
            print(f"\n   ✗ No user account linked to this farmer")
else:
    print("   ✗ No farmer found with name 'Nihal'")

# Also check users table directly
print("\n2. Checking Users Table:")
cursor.execute("SELECT * FROM users WHERE Email LIKE %s", ("%nihal%",))
users = cursor.fetchall()

if users:
    for user in users:
        print(f"\n   ✓ Found User:")
        print(f"     - User ID: {user['UserID']}")
        print(f"     - Email: {user['Email']}")
        print(f"     - Type: {user['UserType']}")
        print(f"     - Related ID: {user['RelatedID']}")
else:
    print("   ✗ No user found with email containing 'nihal'")

cursor.close()
cnx.close()

print("\n" + "=" * 80)
