from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, flash
from database import fetchall, fetchone, place_order_proc, call_proc, add_product_review, get_customer_loyalty_points, get_seasonal_products
from functools import wraps
from config import APP_CONFIG

customer_bp = Blueprint("customer", __name__, template_folder="../templates/customer")

# helper
def flask_render(tpl, **kwargs):
    return render_template(tpl, app_config=APP_CONFIG, **kwargs)

def login_required(f):
    from functools import wraps
    @wraps(f)
    def inner(*args, **kwargs):
        if not session.get('user'):
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return inner

def role_required(role):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def inner(*args, **kwargs):
            if session.get('user')['UserType'] != role:
                flash("Access denied", "danger")
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return inner
    return decorator

@customer_bp.route("/orders")
@login_required
@role_required("Customer")
def orders():
    customer_id = session['user']['RelatedID']
    # Fetch orders for this customer with product details from order_product junction table
    orders_list = fetchall("""
        SELECT 
            o.OrderID, 
            o.OrderDate, 
            o.Status, 
            o.TotalAmount,
            p.Name as ProductName,
            op.Quantity,
            p.Price as UnitPrice
        FROM orders o
        JOIN order_product op ON o.OrderID = op.OrderID
        JOIN product p ON op.ProductID = p.ProductID
        WHERE o.CustomerID = %s
        ORDER BY o.OrderDate DESC
    """, (customer_id,))
    return flask_render("customer/orders.html", orders=orders_list)

@customer_bp.route("/order/<int:order_id>")
@login_required
@role_required("Customer")
def order_detail(order_id):
    customer_id = session['user']['RelatedID']
    # Fetch order details with all products in the order
    order_items = fetchall("""
        SELECT 
            o.OrderID, 
            o.OrderDate, 
            o.Status, 
            o.TotalAmount,
            op.Quantity,
            p.Name as ProductName,
            p.Price as UnitPrice,
            p.ProductID,
            c.Name as CustomerName,
            c.Location as CustomerLocation
        FROM orders o
        JOIN order_product op ON o.OrderID = op.OrderID
        JOIN product p ON op.ProductID = p.ProductID
        JOIN customer c ON o.CustomerID = c.CustomerID
        WHERE o.OrderID = %s AND o.CustomerID = %s
    """, (order_id, customer_id))
    
    if not order_items:
        flash("Order not found", "error")
        return redirect(url_for('customer.orders'))
    
    # First item contains order info
    order = order_items[0]
    return flask_render("customer/order_detail.html", order=order, order_items=order_items)

@customer_bp.route("/order/<int:order_id>/invoice")
@login_required
@role_required("Customer")
def download_invoice(order_id):
    from flask import make_response
    from io import BytesIO
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    
    customer_id = session['user']['RelatedID']
    
    # Fetch order details with all products
    order_items = fetchall("""
        SELECT 
            o.OrderID, 
            o.OrderDate, 
            o.Status, 
            o.TotalAmount,
            op.Quantity,
            p.Name as ProductName,
            p.Price as UnitPrice,
            c.Name as CustomerName,
            c.Location as CustomerLocation,
            c.Email as CustomerEmail,
            f.Name as FarmerName,
            f.Location as FarmerLocation
        FROM orders o
        JOIN order_product op ON o.OrderID = op.OrderID
        JOIN product p ON op.ProductID = p.ProductID
        JOIN customer c ON o.CustomerID = c.CustomerID
        JOIN farmer f ON p.FarmerID = f.FarmerID
        WHERE o.OrderID = %s AND o.CustomerID = %s
    """, (order_id, customer_id))
    
    if not order_items:
        flash("Order not found", "error")
        return redirect(url_for('customer.orders'))
    
    # First item contains order and customer info
    order = order_items[0]
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    # Container for PDF elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#10b981'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#059669'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    # Title
    elements.append(Paragraph("FARMCONNECT INVOICE", title_style))
    elements.append(Spacer(1, 12))
    
    # Invoice details
    invoice_data = [
        ['Invoice Number:', f'INV-{order["OrderID"]:06d}', 'Order ID:', f'#{order["OrderID"]}'],
        ['Date:', str(order['OrderDate']), 'Status:', order['Status']]
    ]
    
    invoice_table = Table(invoice_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    invoice_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
        ('BACKGROUND', (2, 0), (2, -1), colors.HexColor('#f3f4f6')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    elements.append(invoice_table)
    elements.append(Spacer(1, 20))
    
    # Customer Details
    elements.append(Paragraph("Customer Details", heading_style))
    customer_data = [
        ['Name:', order['CustomerName']],
        ['Email:', order['CustomerEmail']],
        ['Location:', order['CustomerLocation']]
    ]
    
    customer_table = Table(customer_data, colWidths=[1.5*inch, 5*inch])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#fef3c7')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey)
    ]))
    
    elements.append(customer_table)
    elements.append(Spacer(1, 20))
    
    # Order Items
    elements.append(Paragraph("Order Details", heading_style))
    
    # Table header
    items_data = [['Product', 'Farmer', 'Quantity', 'Unit Price', 'Subtotal']]
    
    # Add each product
    for item in order_items:
        subtotal = float(item['UnitPrice']) * int(item['Quantity'])
        items_data.append([
            item['ProductName'],
            f"{item['FarmerName']}\n{item['FarmerLocation']}",
            str(item['Quantity']),
            f"₹{item['UnitPrice']:.2f}",
            f"₹{subtotal:.2f}"
        ])
    
    items_table = Table(items_data, colWidths=[2*inch, 1.8*inch, 0.8*inch, 1*inch, 1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    
    # Totals
    totals_data = [
        ['Subtotal:', f"₹{order['TotalAmount']:.2f}"],
        ['Shipping:', '₹0.00'],
        ['Tax (0%):', '₹0.00'],
        ['', ''],
        ['Total Amount:', f"₹{order['TotalAmount']:.2f}"]
    ]
    
    totals_table = Table(totals_data, colWidths=[5*inch, 1.5*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (0, 2), 'Helvetica'),
        ('FONTNAME', (0, 4), (-1, 4), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 3), 10),
        ('FONTSIZE', (0, 4), (-1, 4), 14),
        ('TEXTCOLOR', (0, 4), (-1, 4), colors.HexColor('#10b981')),
        ('LINEABOVE', (0, 4), (-1, 4), 2, colors.HexColor('#10b981')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(totals_table)
    elements.append(Spacer(1, 30))
    
    # Footer
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        alignment=TA_CENTER
    )
    
    elements.append(Paragraph("Thank you for shopping with FarmConnect!", footer_style))
    elements.append(Paragraph("Support local farmers, eat fresh & healthy.", footer_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("FarmConnect - Fresh from Farm to Table", footer_style))
    elements.append(Paragraph("Email: support@farmconnect.com", footer_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get PDF data
    pdf_data = buffer.getvalue()
    buffer.close()
    
    # Send PDF as response
    response = make_response(pdf_data)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{order_id}.pdf'
    return response

@customer_bp.route("/shop")
@login_required
@role_required("Customer")
def shop():
    # basic shop with filters
    category = request.args.get('category')
    season = request.args.get('season')
    
    # Use GetSeasonalProducts stored procedure if season filter is applied
    if season and season.lower() != 'all':
        products = get_seasonal_products(season)
        # Filter by category if also specified
        if category and category.lower() != 'all':
            products = [p for p in products if p.get('CategoryName', '').lower() == category.lower()]
    else:
        # Regular query with category filter - include season data and quantity
        q = """SELECT v.*, p.ImagePath, p.QuantityAvailable,
               GROUP_CONCAT(s.SeasonName SEPARATOR ', ') as SeasonName
               FROM v_productdetails v 
               JOIN Product p ON v.ProductID = p.ProductID
               LEFT JOIN product_season ps ON p.ProductID = ps.ProductID
               LEFT JOIN season s ON ps.SeasonID = s.SeasonID"""
        params = []
        where = []
        if category and category.lower() != 'all':
            where.append("v.CategoryName=%s"); params.append(category)
        if where:
            q += " WHERE " + " AND ".join(where)
        q += " GROUP BY v.ProductID, v.ProductName, v.Price, v.CategoryName, v.FarmerName, p.ImagePath, p.QuantityAvailable"
        products = fetchall(q, tuple(params))
    
    return flask_render("customer/shop.html", products=products)

# CART stored in session
@customer_bp.route("/cart")
@login_required
@role_required("Customer")
def cart():
    cart = session.get('cart', {})
    # load product details
    items = []
    for pid, qty in cart.items():
        row = fetchone("SELECT ProductID, Name, Price, QuantityAvailable FROM Product WHERE ProductID=%s", (pid,))
        if row:
            row['quantity'] = qty
            row['subtotal'] = float(row['Price']) * int(qty)
            items.append(row)
    total = sum(i['subtotal'] for i in items)
    return flask_render("customer/cart.html", items=items, total=total)

@customer_bp.route("/checkout")
@login_required
@role_required("Customer")
def checkout():
    customer_id = session['user']['RelatedID']
    cart = session.get('cart', {})
    
    if not cart:
        flash("Your cart is empty", "error")
        return redirect(url_for('customer.shop'))
    
    # Get loyalty points
    loyalty_points = get_customer_loyalty_points(customer_id)
    
    # load product details and check stock availability
    items = []
    out_of_stock = []
    insufficient_stock = []
    
    for pid, qty in cart.items():
        row = fetchone("SELECT ProductID, Name, Price, QuantityAvailable FROM Product WHERE ProductID=%s", (pid,))
        if row:
            row['quantity'] = qty
            row['subtotal'] = float(row['Price']) * int(qty)
            
            # Check stock availability
            if row['QuantityAvailable'] == 0:
                out_of_stock.append(row['Name'])
            elif row['QuantityAvailable'] < qty:
                insufficient_stock.append({
                    'name': row['Name'],
                    'requested': qty,
                    'available': row['QuantityAvailable']
                })
            
            items.append(row)
    
    # If any items are out of stock or insufficient, redirect back to cart with error
    if out_of_stock or insufficient_stock:
        error_messages = []
        
        if out_of_stock:
            error_messages.append(f"Out of stock: {', '.join(out_of_stock)}")
        
        if insufficient_stock:
            for item in insufficient_stock:
                error_messages.append(f"{item['name']}: Only {item['available']} available (you have {item['requested']} in cart)")
        
        for msg in error_messages:
            flash(msg, "error")
        
        return redirect(url_for('customer.cart'))
    
    total = sum(i['subtotal'] for i in items)
    
    # Calculate maximum discount from loyalty points (1 point = ₹1 discount)
    max_discount = min(loyalty_points, total)  # Can't discount more than total
    
    return flask_render("customer/checkout.html", 
                       items=items, 
                       total=total, 
                       loyalty_points=loyalty_points,
                       max_discount=max_discount)

@customer_bp.route("/cart/add", methods=["POST"])
@login_required
@role_required("Customer")
def cart_add():
    pid = request.form.get('product_id')
    qty = int(request.form.get('quantity', 1))
    
    # Check product availability
    product = fetchone("SELECT QuantityAvailable, Name FROM Product WHERE ProductID=%s", (pid,))
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    
    # Check current cart quantity
    cart = session.get('cart', {})
    current_qty = cart.get(str(pid), 0)
    new_total_qty = current_qty + qty
    
    if new_total_qty > product['QuantityAvailable']:
        return jsonify({
            'success': False, 
            'message': f'Only {product["QuantityAvailable"]} units of {product["Name"]} available. You already have {current_qty} in cart.'
        }), 400
    
    cart[str(pid)] = new_total_qty
    session['cart'] = cart
    return jsonify({'success': True, 'cartCount': sum(cart.values())})

@customer_bp.route("/cart/update", methods=["POST"])
@login_required
@role_required("Customer")
def cart_update():
    pid = request.form.get('product_id')
    qty = int(request.form.get('quantity', 1))
    
    # Check product availability
    product = fetchone("SELECT QuantityAvailable, Name FROM Product WHERE ProductID=%s", (pid,))
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    
    if qty > product['QuantityAvailable']:
        return jsonify({
            'success': False, 
            'message': f'Only {product["QuantityAvailable"]} units of {product["Name"]} available'
        }), 400
    
    cart = session.get('cart', {})
    if qty <= 0:
        cart.pop(str(pid), None)
    else:
        cart[str(pid)] = qty
    session['cart'] = cart
    return jsonify({'success': True})

@customer_bp.route("/order/place", methods=["POST"])
@login_required
@role_required("Customer")
def order_place():
    from database import execute, get_conn
    cart = session.get('cart', {})
    if not cart:
        return jsonify({'success': False, 'message': 'Cart empty'}), 400
    
    customer_id = session['user']['RelatedID']
    
    # Get loyalty points to use from the request
    loyalty_points_used = int(request.form.get('loyalty_points_used', 0))
    
    # First, check all products have sufficient stock
    for pid, qty in cart.items():
        product = fetchone("SELECT QuantityAvailable, Name FROM Product WHERE ProductID=%s", (pid,))
        if not product:
            return jsonify({'success': False, 'message': f'Product ID {pid} not found'}), 404
        if product['QuantityAvailable'] < qty:
            return jsonify({
                'success': False, 
                'message': f'Insufficient stock for {product["Name"]}. Only {product["QuantityAvailable"]} available.'
            }), 400
    
    # Calculate cart total
    cart_total = 0
    for pid, qty in cart.items():
        row = fetchone("SELECT Price FROM Product WHERE ProductID=%s", (pid,))
        if row:
            cart_total += float(row['Price']) * int(qty)
    
    # Apply loyalty discount (1 point = ₹1 discount)
    discount = min(loyalty_points_used, cart_total)
    final_total = cart_total - discount
    
    # Use a transaction to ensure atomicity
    cnx = get_conn()
    cursor = cnx.cursor()
    
    try:
        # Place orders for each product and deduct stock
        order_ids = []
        for pid, qty in cart.items():
            # Place order using stored procedure
            cursor.callproc('PlaceOrder', (customer_id, int(pid), int(qty), 0))
            cnx.commit()
            
            # Get the order ID
            cursor.execute("SELECT LAST_INSERT_ID()")
            order_id = cursor.fetchone()[0]
            order_ids.append(order_id)
            
            # Deduct quantity from product stock
            cursor.execute("""
                UPDATE Product 
                SET QuantityAvailable = QuantityAvailable - %s 
                WHERE ProductID = %s
            """, (qty, int(pid)))
            cnx.commit()
        
        # Update the last order total to reflect the discount
        if order_ids and discount > 0:
            cursor.execute("""
                UPDATE orders 
                SET TotalAmount = TotalAmount - %s 
                WHERE OrderID = %s
            """, (discount, order_ids[0]))
            cnx.commit()
        
        cursor.close()
        cnx.close()
        
        session.pop('cart', None)
        
        return jsonify({
            'success': True, 
            'order_ids': order_ids,
            'discount_applied': discount,
            'final_total': final_total
        })
        
    except Exception as e:
        cnx.rollback()
        cursor.close()
        cnx.close()
        return jsonify({'success': False, 'message': f'Error placing order: {str(e)}'}), 500

@customer_bp.route("/review/add", methods=["POST"])
@login_required
@role_required("Customer")
def add_review():
    customer_id = session['user']['RelatedID']
    product_id = request.form.get('product_id')
    rating = request.form.get('rating')
    comment = request.form.get('comment', '')
    result = add_product_review(customer_id, int(product_id), float(rating), comment)
    return jsonify(result)

@customer_bp.route("/loyalty")
@login_required
@role_required("Customer")
def loyalty():
    customer_id = session['user']['RelatedID']
    loyalty_points = get_customer_loyalty_points(customer_id)
    
    # Get order history to show points earned
    orders = fetchall("""
        SELECT OrderID, OrderDate, TotalAmount, Status
        FROM orders
        WHERE CustomerID = %s AND Status = 'Completed'
        ORDER BY OrderDate DESC
    """, (customer_id,))
    
    total_spent = sum(float(order['TotalAmount']) for order in orders)
    
    return flask_render("customer/loyalty.html", 
                       loyalty_points=loyalty_points, 
                       orders=orders,
                       total_spent=total_spent)

@customer_bp.route("/api/loyalty-points")
@login_required
@role_required("Customer")
def api_loyalty_points():
    """API endpoint to get loyalty points for AJAX requests"""
    customer_id = session['user']['RelatedID']
    loyalty_points = get_customer_loyalty_points(customer_id)
    return jsonify({'points': loyalty_points})

@customer_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required("Customer")
def settings():
    from werkzeug.security import check_password_hash, generate_password_hash
    from database import execute
    
    customer_id = session['user']['RelatedID']
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
                return redirect(url_for('customer.settings'))
            
            if new_password != confirm_password:
                flash("New passwords do not match", "danger")
                return redirect(url_for('customer.settings'))
            
            if len(new_password) < 6:
                flash("Password must be at least 6 characters", "danger")
                return redirect(url_for('customer.settings'))
            
            # Check current password
            user = fetchone("SELECT Password FROM users WHERE UserID = %s", (user_id,))
            if not user or not check_password_hash(user['Password'], current_password):
                flash("Current password is incorrect", "danger")
                return redirect(url_for('customer.settings'))
            
            # Update password
            hashed = generate_password_hash(new_password)
            execute("UPDATE users SET Password = %s WHERE UserID = %s", (hashed, user_id))
            flash("Password changed successfully!", "success")
            return redirect(url_for('customer.settings'))
        
        elif action == 'update_profile':
            name = request.form.get('name')
            location = request.form.get('location')
            
            if name and location:
                execute("UPDATE customer SET Name = %s, Location = %s WHERE CustomerID = %s", 
                       (name, location, customer_id))
                # Update session
                session['user']['Name'] = name
                flash("Profile updated successfully!", "success")
            else:
                flash("Name and location are required", "danger")
            
            return redirect(url_for('customer.settings'))
    
    # GET request - show settings page
    customer = fetchone("SELECT * FROM customer WHERE CustomerID = %s", (customer_id,))
    user = fetchone("SELECT Email FROM users WHERE UserID = %s", (user_id,))
    
    return flask_render("customer/settings.html", customer=customer, user=user)
