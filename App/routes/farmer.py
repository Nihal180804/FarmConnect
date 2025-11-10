from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, flash
from functools import wraps
from database import fetchall, fetchone, execute, get_farmer_report
from config import APP_CONFIG

farmer_bp = Blueprint("farmer", __name__, template_folder="../templates/farmer")

# helper
def flask_render(tpl, **kwargs):
    return render_template(tpl, app_config=APP_CONFIG, **kwargs)

def login_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return inner

def role_required(role):
    def decorator(f):
        @wraps(f)
        def inner(*args, **kwargs):
            if not session.get('user') or session['user']['UserType'] != role:
                flash("Access denied.", "danger")
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return inner
    return decorator

@farmer_bp.route("/dashboard")
@login_required
@role_required("Farmer")
def dashboard():
    farmer_id = session['user']['RelatedID']
    # gather metrics
    total_products_row = fetchone("SELECT GetFarmerProductCount(%s) AS total", (farmer_id,))
    total_products = total_products_row['total'] if total_products_row else 0
    # total orders and revenue via GetFarmerReport
    farmer_report = get_farmer_report(farmer_id)
    overview = farmer_report[0][0] if farmer_report and farmer_report[0] else {}
    product_rows = farmer_report[1] if farmer_report and len(farmer_report) > 1 else []
    return flask_render("farmer/dashboard.html", overview=overview, products=product_rows, total_products=total_products)

@farmer_bp.route("/products")
@login_required
@role_required("Farmer")
def products():
    farmer_id = session['user']['RelatedID']
    rows = fetchall("""
        SELECT 
            p.ProductID,
            p.FarmerID,
            p.Name as ProductName,
            c.CategoryName as Category,
            p.Price,
            GROUP_CONCAT(s.SeasonName SEPARATOR ', ') as Season,
            p.Freshness,
            (SELECT COALESCE(SUM(op.Quantity), 0) FROM order_product op WHERE op.ProductID=p.ProductID) as Quantity,
            COALESCE((SELECT AVG(r.Rating) FROM review r WHERE r.ProductID=p.ProductID), 0) as avg_rating, 
            COALESCE((SELECT COUNT(DISTINCT op.OrderID) FROM order_product op WHERE op.ProductID=p.ProductID), 0) as total_orders 
        FROM product p 
        LEFT JOIN category c ON p.CategoryID = c.CategoryID
        LEFT JOIN product_season ps ON p.ProductID = ps.ProductID
        LEFT JOIN season s ON ps.SeasonID = s.SeasonID
        WHERE p.FarmerID=%s
        GROUP BY p.ProductID, p.FarmerID, p.Name, c.CategoryName, p.Price, p.Freshness
        ORDER BY p.ProductID DESC
    """, (farmer_id,))
    return flask_render("farmer/products.html", products=rows)

@farmer_bp.route("/product/edit_price", methods=["POST"])
@login_required
@role_required("Farmer")
def edit_price():
    product_id = request.form.get('product_id')
    new_price = request.form.get('price')
    if not product_id or not new_price:
        return jsonify({'success': False, 'message': 'Missing fields'}), 400
    try:
        execute("UPDATE product SET Price=%s WHERE ProductID=%s", (new_price, product_id))
        return jsonify({'success': True, 'message': 'Price updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@farmer_bp.route("/product/delete/<int:product_id>", methods=["POST"])
@login_required
@role_required("Farmer")
def delete_product(product_id):
    farmer_id = session['user']['RelatedID']
    # ensure ownership
    prod = fetchone("SELECT FarmerID FROM product WHERE ProductID=%s", (product_id,))
    if not prod or prod['FarmerID'] != farmer_id:
        flash("Unauthorized", "danger")
        return redirect(url_for('farmer.products'))
    execute("DELETE FROM product WHERE ProductID=%s", (product_id,))
    flash("Product deleted", "success")
    return redirect(url_for('farmer.products'))

@farmer_bp.route("/product/add", methods=["GET", "POST"])
@login_required
@role_required("Farmer")
def add_product():
    # Load categories and seasons for form
    categories = fetchall("SELECT CategoryID, CategoryName FROM category ORDER BY CategoryName")
    seasons = fetchall("SELECT SeasonID, SeasonName FROM season ORDER BY SeasonName")
    if request.method == "POST":
        farmer_id = session['user']['RelatedID']
        
        # Get form data
        product_name = request.form.get('product_name', '').strip()
        category_id = request.form.get('category_id', '').strip()
        price = request.form.get('price', '').strip()
        season_id = request.form.get('season_id', '').strip()
        freshness = request.form.get('freshness', 'Fresh').strip()
        
        # Validation
        if not all([product_name, category_id, price, season_id]):
            flash("All required fields must be filled", "danger")
            return flask_render("farmer/add_product.html", categories=categories, seasons=seasons)
        
        try:
            price = float(price)
            category_id = int(category_id)
            season_id = int(season_id)
            
            if price < 0:
                flash("Price must be positive", "danger")
                return flask_render("farmer/add_product.html", categories=categories, seasons=seasons)
            
            # Validate category exists
            category_row = fetchone("SELECT CategoryID FROM category WHERE CategoryID=%s", (category_id,))
            if not category_row:
                flash("Invalid category selected", "danger")
                return flask_render("farmer/add_product.html", categories=categories, seasons=seasons)
            
            # Validate season exists
            season_row = fetchone("SELECT SeasonID FROM season WHERE SeasonID=%s", (season_id,))
            if not season_row:
                flash("Invalid season selected", "danger")
                return flask_render("farmer/add_product.html", categories=categories, seasons=seasons)
            
            # Insert product
            product_id = execute(
                "INSERT INTO product (FarmerID, Name, Price, Freshness, CategoryID) VALUES (%s, %s, %s, %s, %s)",
                (farmer_id, product_name, price, freshness, category_id)
            )
            
            # Link product with season
            execute(
                "INSERT INTO product_season (ProductID, SeasonID) VALUES (%s, %s)",
                (product_id, season_id)
            )
            
            flash("Product added successfully!", "success")
            return redirect(url_for('farmer.products'))
        
        except ValueError:
            flash("Price must be a valid number", "danger")
            return flask_render("farmer/add_product.html", categories=categories, seasons=seasons)
        except Exception as e:
            flash(f"Error adding product: {str(e)}", "danger")
            return flask_render("farmer/add_product.html", categories=categories, seasons=seasons)
    
    # GET request - show the form
    return flask_render("farmer/add_product.html", categories=categories, seasons=seasons)

@farmer_bp.route("/product/restock/<int:product_id>", methods=["POST"])
@login_required
@role_required("Farmer")
def restock_product(product_id):
    # Note: This schema doesn't use direct quantity tracking on products
    # Quantities are managed through orders. This endpoint is deprecated.
    return jsonify({'success': False, 'message': 'Restock not supported in this version'}), 400
