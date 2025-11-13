import mysql.connector
from config import DB_CONFIG

# Connect to database
cnx = mysql.connector.connect(**DB_CONFIG)
cursor = cnx.cursor(dictionary=True)

print("=" * 80)
print("TRIGGERS IN DATABASE")
print("=" * 80)

# Get all triggers
cursor.execute("SHOW TRIGGERS FROM localfarmermanagement")
triggers = cursor.fetchall()

if triggers:
    for trigger in triggers:
        print(f"\nTrigger: {trigger['Trigger']}")
        print(f"  Table: {trigger['Table']}")
        print(f"  Event: {trigger['Event']}")
        print(f"  Timing: {trigger['Timing']}")
        print(f"  Statement: {trigger['Statement'][:100]}...")
        print("-" * 80)
else:
    print("\nNo triggers found in the database.")

print("\n" + "=" * 80)
print("STORED PROCEDURES")
print("=" * 80)

# Get all stored procedures
cursor.execute("SHOW PROCEDURE STATUS WHERE Db = 'localfarmermanagement'")
procedures = cursor.fetchall()

if procedures:
    for proc in procedures:
        print(f"\nProcedure: {proc['Name']}")
        print(f"  Type: {proc['Type']}")
        print(f"  Created: {proc['Created']}")
else:
    print("\nNo stored procedures found.")

print("\n" + "=" * 80)
print("STORED FUNCTIONS")
print("=" * 80)

# Get all stored functions
cursor.execute("SHOW FUNCTION STATUS WHERE Db = 'localfarmermanagement'")
functions = cursor.fetchall()

if functions:
    for func in functions:
        print(f"\nFunction: {func['Name']}")
        print(f"  Type: {func['Type']}")
        print(f"  Created: {func['Created']}")
else:
    print("\nNo stored functions found.")

cursor.close()
cnx.close()

print("\n" + "=" * 80)
