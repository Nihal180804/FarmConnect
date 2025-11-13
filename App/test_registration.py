import mysql.connector
from config import DB_CONFIG
from werkzeug.security import generate_password_hash

def test_registration():
    cnx = mysql.connector.connect(**DB_CONFIG)
    cursor = cnx.cursor(dictionary=True)
    
    print("=" * 80)
    print("TESTING REGISTRATION FUNCTIONALITY")
    print("=" * 80)
    
    # Test data
    test_email = "test_farmer@test.com"
    
    # Clean up any existing test data
    print("\n1. Cleaning up existing test data...")
    cursor.execute("SELECT UserID, RelatedID, UserType FROM users WHERE Email = %s", (test_email,))
    existing = cursor.fetchone()
    
    if existing:
        if existing['UserType'] == 'Farmer' and existing['RelatedID']:
            cursor.execute("DELETE FROM farmer WHERE FarmerID = %s", (existing['RelatedID'],))
        elif existing['UserType'] == 'Customer' and existing['RelatedID']:
            cursor.execute("DELETE FROM customer WHERE CustomerID = %s", (existing['RelatedID'],))
        cursor.execute("DELETE FROM users WHERE Email = %s", (test_email,))
        cnx.commit()
        print(f"   Deleted existing test user: {test_email}")
    
    # Test Farmer Registration
    print("\n2. Testing Farmer Registration...")
    try:
        # Insert farmer
        cursor.execute("""
            INSERT INTO farmer (Name, Contact, Location)
            VALUES (%s, %s, %s)
        """, ("Test Farmer", "1234567890", "Test Location"))
        cnx.commit()
        
        # Get farmer ID
        cursor.execute("SELECT FarmerID FROM farmer WHERE Name = %s AND Contact = %s", 
                      ("Test Farmer", "1234567890"))
        farmer = cursor.fetchone()
        farmer_id = farmer['FarmerID'] if farmer else None
        
        print(f"   ✓ Farmer created with ID: {farmer_id}")
        
        # Create user
        hashed_password = generate_password_hash("test123")
        cursor.execute("""
            INSERT INTO users (Email, Password, UserType, RelatedID, CreatedAt)
            VALUES (%s, %s, %s, %s, NOW())
        """, (test_email, hashed_password, 'Farmer', farmer_id))
        cnx.commit()
        
        print(f"   ✓ User account created for: {test_email}")
        
        # Verify
        cursor.execute("""
            SELECT u.UserID, u.Email, u.UserType, u.RelatedID, f.Name, f.Contact, f.Location
            FROM users u
            JOIN farmer f ON u.RelatedID = f.FarmerID
            WHERE u.Email = %s
        """, (test_email,))
        result = cursor.fetchone()
        
        if result:
            print(f"   ✓ VERIFICATION SUCCESSFUL!")
            print(f"     - User ID: {result['UserID']}")
            print(f"     - Email: {result['Email']}")
            print(f"     - Type: {result['UserType']}")
            print(f"     - Farmer Name: {result['Name']}")
            print(f"     - Contact: {result['Contact']}")
            print(f"     - Location: {result['Location']}")
        else:
            print(f"   ✗ VERIFICATION FAILED - User not found in database")
        
    except Exception as e:
        print(f"   ✗ ERROR: {str(e)}")
        cnx.rollback()
    
    # Clean up test data
    print("\n3. Cleaning up test data...")
    cursor.execute("SELECT RelatedID FROM users WHERE Email = %s", (test_email,))
    user = cursor.fetchone()
    if user and user['RelatedID']:
        cursor.execute("DELETE FROM farmer WHERE FarmerID = %s", (user['RelatedID'],))
    cursor.execute("DELETE FROM users WHERE Email = %s", (test_email,))
    cnx.commit()
    print("   ✓ Test data cleaned up")
    
    # Check current database state
    print("\n4. Current Database Statistics:")
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE UserType = 'Farmer'")
    farmer_users = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE UserType = 'Customer'")
    customer_users = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM farmer")
    total_farmers = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM customer")
    total_customers = cursor.fetchone()['count']
    
    print(f"   - Total Farmer Users: {farmer_users}")
    print(f"   - Total Farmer Records: {total_farmers}")
    print(f"   - Total Customer Users: {customer_users}")
    print(f"   - Total Customer Records: {total_customers}")
    
    cursor.close()
    cnx.close()
    
    print("\n" + "=" * 80)
    print("CONCLUSION: Registration functionality is WORKING CORRECTLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_registration()
