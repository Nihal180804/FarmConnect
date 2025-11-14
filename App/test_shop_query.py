import mysql.connector
from config import DB_CONFIG

cnx = mysql.connector.connect(**DB_CONFIG)
cursor = cnx.cursor(dictionary=True)

print("=" * 80)
print("TESTING SHOP QUERY - EXACTLY AS IT RUNS")
print("=" * 80)

# This is the exact query from customer.py shop route
q = """SELECT v.*, p.ImagePath,
       GROUP_CONCAT(s.SeasonName SEPARATOR ', ') as SeasonName
       FROM v_productdetails v 
       JOIN Product p ON v.ProductID = p.ProductID
       LEFT JOIN product_season ps ON p.ProductID = ps.ProductID
       LEFT JOIN season s ON ps.SeasonID = s.SeasonID
       GROUP BY v.ProductID, v.ProductName, v.Price, v.CategoryName, v.FarmerName, p.ImagePath
       LIMIT 10"""

cursor.execute(q)
products = cursor.fetchall()

print(f"\nShowing first 10 products:\n")

for p in products:
    print(f"Product: {p['ProductName']:<30}")
    print(f"  Category: {p.get('CategoryName', 'N/A')}")
    print(f"  SeasonName: {p.get('SeasonName', 'N/A')}")
    print(f"  ImagePath: {p.get('ImagePath', 'N/A')}")
    print(f"  All keys: {list(p.keys())}")
    print("-" * 80)

cursor.close()
cnx.close()
