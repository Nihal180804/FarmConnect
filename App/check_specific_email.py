import mysql.connector
from config import DB_CONFIG

cnx = mysql.connector.connect(**DB_CONFIG)
cursor = cnx.cursor(dictionary=True)

print("=" * 80)
print("SEARCHING FOR: nihaljayaprakash2004@gmail.com")
print("=" * 80)

# Check users table
cursor.execute("SELECT * FROM users WHERE Email = %s", ("nihaljayaprakash2004@gmail.com",))
user = cursor.fetchone()

if user:
    print(f"\n✓ USER FOUND:")
    print(f"  - User ID: {user['UserID']}")
    print(f"  - Email: {user['Email']}")
    print(f"  - Type: {user['UserType']}")
    print(f"  - Related ID: {user['RelatedID']}")
    print(f"  - Created: {user['CreatedAt']}")
    print(f"  - Last Login: {user['LastLogin'] or 'Never'}")
    
    if user['UserType'] == 'Farmer' and user['RelatedID']:
        cursor.execute("SELECT * FROM farmer WHERE FarmerID = %s", (user['RelatedID'],))
        farmer = cursor.fetchone()
        
        if farmer:
            print(f"\n✓ FARMER DETAILS:")
            print(f"  - Farmer ID: {farmer['FarmerID']}")
            print(f"  - Name: {farmer['Name']}")
            print(f"  - Contact: {farmer.get('Contact', 'N/A')}")
            print(f"  - Location: {farmer.get('Location', 'N/A')}")
            print(f"  - Email: {farmer.get('Email', 'N/A')}")
            
            # Check products
            cursor.execute("SELECT COUNT(*) as count FROM product WHERE FarmerID = %s", (farmer['FarmerID'],))
            product_count = cursor.fetchone()['count']
            print(f"  - Total Products: {product_count}")
        else:
            print(f"\n✗ Farmer record not found for RelatedID: {user['RelatedID']}")
            
    elif user['UserType'] == 'Customer' and user['RelatedID']:
        cursor.execute("SELECT * FROM customer WHERE CustomerID = %s", (user['RelatedID'],))
        customer = cursor.fetchone()
        
        if customer:
            print(f"\n✓ CUSTOMER DETAILS:")
            print(f"  - Customer ID: {customer['CustomerID']}")
            print(f"  - Name: {customer['Name']}")
            print(f"  - Email: {customer.get('Email', 'N/A')}")
            print(f"  - Location: {customer.get('Location', 'N/A')}")
else:
    print(f"\n✗ NO USER FOUND with email: nihaljayaprakash2004@gmail.com")
    print("\nThe account was NOT created in the database.")
    print("\nPossible reasons:")
    print("  1. Registration form had an error")
    print("  2. Email validation failed")
    print("  3. Database transaction was rolled back")
    print("  4. Form wasn't submitted properly")

cursor.close()
cnx.close()

print("\n" + "=" * 80)
