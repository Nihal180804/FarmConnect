"""
Script to update product images in the database based on product names
"""
import mysql.connector
from config import DB_CONFIG
import os

# Image mapping based on product names
IMAGE_MAPPINGS = {
    # Fruits
    'apple': 'Apple.jpg',
    'organic apple': 'Organic Apple.jpg',
    'banana': 'Banana.jpg',
    'grapes': 'Grapes.jpg',
    'guava': 'Guava.jpg',
    'mango': 'Mango.jpg',
    'orange': 'Orange.jpg',
    'papaya': 'Papaya.jpg',
    'pineapple': 'Pineapple.jpg',
    'pomegranate': 'Pomegranate.jpg',
    'watermelon': 'Watermelon.jpg',
    
    # Vegetables
    'beans': 'Beans.jpg',
    'bell pepper': 'Bell Pepper.jpg',
    'pepper': 'Bell Pepper.jpg',
    'brinjal': 'Brinjal.jpg',
    'eggplant': 'Brinjal.jpg',
    'carrot': 'Carrot.jpg',
    'organic carrot': 'Organic Carrots.jpg',
    'cauliflower': 'Cauliflower.jpg',
    'cucumber': 'Cucumber.jpg',
    'onion': 'Onion.jpg',
    'potato': 'Potato.jpg',
    'spinach': 'Spinach.jpg',
    'organic spinach': 'Organic Spinach.jpg',
    'tomato': 'Tomato.jpg',
    'organic tomato': 'Organic Tomato.jpg',
    'turmeric': 'Turmeric.jpg',
    
    # Grains & Pulses
    'corn': 'Corn.webp',
    'maize': 'Maize.webp',
    'moong dal': 'Moong Dal.webp',
    'rice': 'Rice.jpg',
    'organic rice': 'Organic Rice.jpg',
    'sprouts': 'Sprouts.webp',
    'toor dal': 'Toor Dal.webp',
    'wheat': 'Wheat.jpg',
    
    # Dairy & Others
    'buttermilk': 'Buttermilk.jpg',
    'curd': 'Curd.jpg',
    'eggs': 'Eggs.jpg',
    'egg': 'Eggs.jpg',
    'ghee': 'Ghee.jpg',
    'honey': 'Honey.jpg',
    'milk': 'Milk.jpg',
    'paneer': 'Paneer.jpg',
}

def get_image_for_product(product_name):
    """Find the best matching image for a product name"""
    product_name_lower = product_name.lower().strip()
    
    # Try exact match first
    if product_name_lower in IMAGE_MAPPINGS:
        return IMAGE_MAPPINGS[product_name_lower]
    
    # Try partial match
    for key, image in IMAGE_MAPPINGS.items():
        if key in product_name_lower or product_name_lower in key:
            return image
    
    # Default to product name with .jpg extension
    return f"{product_name}.jpg"

def update_database():
    """Update the database with product images"""
    try:
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # First, check if ImagePath column exists, if not add it
        cursor.execute("SHOW COLUMNS FROM product LIKE 'ImagePath'")
        if not cursor.fetchone():
            print("Adding ImagePath column to product table...")
            cursor.execute("ALTER TABLE product ADD COLUMN ImagePath VARCHAR(255) DEFAULT NULL")
            conn.commit()
            print("ImagePath column added successfully!")
        
        # Get all products
        cursor.execute("SELECT ProductID, Name FROM product")
        products = cursor.fetchall()
        
        print(f"\nFound {len(products)} products to update")
        print("-" * 60)
        
        updated_count = 0
        for product in products:
            product_id = product['ProductID']
            product_name = product['Name']
            
            # Get the image filename
            image_file = get_image_for_product(product_name)
            
            # Check if image file exists
            image_path = os.path.join('static', 'images', 'products', image_file)
            full_path = os.path.join(os.path.dirname(__file__), image_path)
            
            if os.path.exists(full_path):
                # Update the database
                cursor.execute(
                    "UPDATE product SET ImagePath = %s WHERE ProductID = %s",
                    (image_file, product_id)
                )
                print(f"✓ Product: {product_name:<30} → {image_file}")
                updated_count += 1
            else:
                print(f"✗ Product: {product_name:<30} → {image_file} (NOT FOUND)")
        
        conn.commit()
        print("-" * 60)
        print(f"\nSuccessfully updated {updated_count} products with images!")
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("FarmConnect - Product Image Updater")
    print("=" * 60)
    update_database()
