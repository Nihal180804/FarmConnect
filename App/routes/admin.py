from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from functools import wraps
from database import fetchall, fetchone, execute, update_order_status
from config import APP_CONFIG

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")

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

def admin_required(f):
    @wraps(f)
    def inner(*args, **kwargs):
        if session.get('user')['UserType'] != 'Admin':
            flash("Admins only", "danger")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return inner

@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    totals = {}
    totals['farmers'] = fetchone("SELECT COUNT(*) AS cnt FROM farmer")['cnt']
    totals['customers'] = fetchone("SELECT COUNT(*) AS cnt FROM customer")['cnt']
    totals['products'] = fetchone("SELECT COUNT(*) AS cnt FROM product")['cnt']
    totals['orders'] = fetchone("SELECT COUNT(*) AS cnt FROM orders")['cnt']
    totals['revenue'] = fetchone("SELECT COALESCE(SUM(TotalAmount),0) as r FROM orders")['r']
    
    # Add inventory statistics
    inventory_stats = fetchone("""
        SELECT 
            COALESCE(SUM(QuantityAvailable), 0) as total_stock,
            COALESCE(SUM(CASE WHEN QuantityAvailable <= 10 THEN 1 ELSE 0 END), 0) as low_stock_count,
            COALESCE(SUM(CASE WHEN QuantityAvailable = 0 THEN 1 ELSE 0 END), 0) as out_of_stock_count
        FROM product
    """)
    
    if inventory_stats:
        totals['total_stock'] = inventory_stats['total_stock']
        totals['low_stock_count'] = inventory_stats['low_stock_count']
        totals['out_of_stock_count'] = inventory_stats['out_of_stock_count']
    
    return flask_render("admin/dashboard.html", totals=totals)

@admin_bp.route("/farmers")
@login_required
@admin_required
def farmers():
    rows = fetchall("SELECT f.*, GetFarmerProductCount(f.FarmerID) as product_count FROM farmer f")
    return flask_render("admin/farmers.html", farmers=rows)

@admin_bp.route("/orders")
@login_required
@admin_required
def orders():
    rows = fetchall("""
        SELECT o.*, c.Name as customer_name, (SELECT CalculateOrderTotal(o.OrderID)) as computed_total
        FROM orders o
        LEFT JOIN customer c ON o.CustomerID = c.CustomerID
        ORDER BY o.OrderDate DESC
    """)
    return flask_render("admin/orders.html", orders=rows)

@admin_bp.route("/inventory")
@login_required
@admin_required
def inventory():
    """View all products with quantity information grouped by farmer"""
    products = fetchall("""
        SELECT 
            p.ProductID,
            p.Name as ProductName,
            p.Price,
            p.QuantityAvailable,
            p.FarmerID,
            f.Name as FarmerName,
            f.Location as FarmerLocation,
            c.CategoryName,
            (SELECT COALESCE(SUM(op.Quantity), 0) FROM order_product op WHERE op.ProductID = p.ProductID) as TotalSold
        FROM Product p
        JOIN Farmer f ON p.FarmerID = f.FarmerID
        LEFT JOIN Category c ON p.CategoryID = c.CategoryID
        ORDER BY f.Name, p.Name
    """)
    
    # Group products by farmer
    farmers_inventory = {}
    for product in products:
        farmer_id = product['FarmerID']
        if farmer_id not in farmers_inventory:
            farmers_inventory[farmer_id] = {
                'FarmerName': product['FarmerName'],
                'FarmerLocation': product['FarmerLocation'],
                'products': [],
                'total_stock_value': 0,
                'low_stock_count': 0
            }
        
        farmers_inventory[farmer_id]['products'].append(product)
        farmers_inventory[farmer_id]['total_stock_value'] += float(product['Price']) * int(product['QuantityAvailable'])
        if product['QuantityAvailable'] <= 10:
            farmers_inventory[farmer_id]['low_stock_count'] += 1
    
    return flask_render("admin/inventory.html", farmers_inventory=farmers_inventory, products=products)

@admin_bp.route("/price_audit")
@login_required
@admin_required
def price_audit():
    rows = fetchall("SELECT ppa.*, pr.Name as product_name FROM product_price_audit ppa JOIN product pr ON pr.ProductID = ppa.ProductID ORDER BY ChangedAt DESC")
    return flask_render("admin/audit.html", audits=rows)

@admin_bp.route("/order/update_status", methods=["POST"])
@login_required
@admin_required
def update_order_status_route():
    """Update order status using UpdateOrderStatus stored procedure"""
    order_id = request.form.get('order_id')
    new_status = request.form.get('status')
    
    if not order_id or not new_status:
        return jsonify({'success': False, 'message': 'Missing order ID or status'}), 400
    
    result = update_order_status(int(order_id), new_status)
    return jsonify(result)

@admin_bp.route("/settings", methods=["GET", "POST"])
@login_required
@admin_required
def settings():
    """Settings page for admins to manage password."""
    from werkzeug.security import check_password_hash, generate_password_hash
    
    user_id = session['user']['UserID']
    
    if request.method == "POST":
        action = request.form.get('action')
        
        if action == 'change_password':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Validate
            if not all([current_password, new_password, confirm_password]):
                flash("All fields are required", "danger")
                return redirect(url_for('admin.settings'))
            
            if new_password != confirm_password:
                flash("New passwords do not match", "danger")
                return redirect(url_for('admin.settings'))
            
            if len(new_password) < 6:
                flash("Password must be at least 6 characters", "danger")
                return redirect(url_for('admin.settings'))
            
            # Check current password
            user = fetchone("SELECT Password FROM users WHERE UserID = %s", (user_id,))
            if not user or not check_password_hash(user['Password'], current_password):
                flash("Current password is incorrect", "danger")
                return redirect(url_for('admin.settings'))
            
            # Update password
            hashed = generate_password_hash(new_password)
            execute("UPDATE users SET Password = %s WHERE UserID = %s", (hashed, user_id))
            flash("Password changed successfully!", "success")
            return redirect(url_for('admin.settings'))
    
    # GET request - show settings page
    user = fetchone("SELECT Email FROM users WHERE UserID = %s", (user_id,))
    
    return flask_render("admin/settings.html", user=user)
