import mysql.connector
from config import DB_CONFIG

cnx = mysql.connector.connect(**DB_CONFIG)
cursor = cnx.cursor(dictionary=True)

print("=" * 80)
print("CHECKING PRODUCT SEASONAL DATA")
print("=" * 80)

# Check if products have season data
cursor.execute("""
    SELECT 
        p.ProductID,
        p.Name as ProductName,
        GROUP_CONCAT(s.SeasonName SEPARATOR ', ') as Seasons
    FROM product p
    LEFT JOIN product_season ps ON p.ProductID = ps.ProductID
    LEFT JOIN season s ON ps.SeasonID = s.SeasonID
    GROUP BY p.ProductID, p.Name
    ORDER BY p.ProductID
""")
products = cursor.fetchall()

print(f"\nTotal Products: {len(products)}")
print("-" * 80)

products_with_seasons = 0
products_without_seasons = 0

for product in products:
    if product['Seasons']:
        products_with_seasons += 1
        print(f"✓ {product['ProductName']:<30} → {product['Seasons']}")
    else:
        products_without_seasons += 1
        print(f"✗ {product['ProductName']:<30} → NO SEASON DATA")

print("-" * 80)
print(f"\nProducts WITH season data: {products_with_seasons}")
print(f"Products WITHOUT season data: {products_without_seasons}")

# Check available seasons
print("\n" + "=" * 80)
print("AVAILABLE SEASONS IN DATABASE")
print("=" * 80)
cursor.execute("SELECT * FROM season")
seasons = cursor.fetchall()

for season in seasons:
    print(f"Season ID: {season['SeasonID']} - {season['SeasonName']}")

cursor.close()
cnx.close()

print("\n" + "=" * 80)
