from flask import Blueprint, render_template, request, session, jsonify, redirect, url_for, flash, send_file
from functools import wraps
from database import fetchall, fetchone, execute, get_farmer_report
from config import APP_CONFIG
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

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

@farmer_bp.route("/sales_report")
@login_required
@role_required("Farmer")
def sales_report():
    """Display the sales report page with option to download PDF."""
    farmer_id = session['user']['RelatedID']
    # Get farmer report data
    farmer_report = get_farmer_report(farmer_id)
    overview = farmer_report[0][0] if farmer_report and farmer_report[0] else {}
    product_rows = farmer_report[1] if farmer_report and len(farmer_report) > 1 else []
    return flask_render("farmer/sales_report.html", overview=overview, products=product_rows)

@farmer_bp.route("/sales_report/pdf")
@login_required
@role_required("Farmer")
def sales_report_pdf():
    """Generate and download a PDF sales report for the farmer."""
    farmer_id = session['user']['RelatedID']
    farmer_name = session['user'].get('Name', 'Farmer')
    
    # Get farmer report data
    farmer_report = get_farmer_report(farmer_id)
    overview = farmer_report[0][0] if farmer_report and farmer_report[0] else {}
    product_rows = farmer_report[1] if farmer_report and len(farmer_report) > 1 else []
    
    # Create a BytesIO buffer for the PDF
    buffer = BytesIO()
    
    # Create the PDF document
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#047857'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#059669'),
        spaceAfter=10,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#374151')
    )
    
    # Title
    title = Paragraph("Sales Report", title_style)
    elements.append(title)
    
    # Farmer info and date
    date_str = datetime.now().strftime("%B %d, %Y")
    farmer_info = Paragraph(f"<b>Farmer:</b> {farmer_name}<br/><b>Report Date:</b> {date_str}", normal_style)
    elements.append(farmer_info)
    elements.append(Spacer(1, 0.3*inch))
    
    # Summary section
    elements.append(Paragraph("Summary", heading_style))
    
    summary_data = [
        ['Metric', 'Value'],
        ['Total Products', str(overview.get('TotalProducts', 0))],
        ['Total Orders', str(overview.get('TotalOrders', 0))],
        ['Total Revenue', f"₹{overview.get('TotalRevenue', '0.00')}"],
        ['Average Product Rating', f"{overview.get('AverageProductRating', '0.0')} ★"]
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f0fdf4')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1fae5')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ]))
    
    elements.append(summary_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Products breakdown section
    if product_rows:
        elements.append(Paragraph("Product Sales Breakdown", heading_style))
        
        product_data = [['Product Name', 'Price', 'Units Sold', 'Revenue']]
        
        for p in product_rows:
            product_data.append([
                str(p.get('ProductName', 'N/A')),
                f"₹{p.get('Price', '0.00')}",
                str(p.get('TotalUnitsSold', 0)),
                f"₹{p.get('ProductRevenue', '0.00')}"
            ])
        
        product_table = Table(product_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        product_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10b981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fdf4')]),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d1fae5')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]))
        
        elements.append(product_table)
    else:
        elements.append(Paragraph("No product sales data available.", normal_style))
    
    # Add footer
    elements.append(Spacer(1, 0.5*inch))
    footer_text = Paragraph(
        f"<i>Generated by FarmConnect on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    )
    elements.append(footer_text)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value from the BytesIO buffer
    buffer.seek(0)
    
    # Send the PDF file
    filename = f"Sales_Report_{farmer_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=filename
    )

@farmer_bp.route("/settings", methods=["GET", "POST"])
@login_required
@role_required("Farmer")
def settings():
    """Settings page for farmers to manage profile and password."""
    from werkzeug.security import check_password_hash, generate_password_hash
    
    farmer_id = session['user']['RelatedID']
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
                return redirect(url_for('farmer.settings'))
            
            if new_password != confirm_password:
                flash("New passwords do not match", "danger")
                return redirect(url_for('farmer.settings'))
            
            if len(new_password) < 6:
                flash("Password must be at least 6 characters", "danger")
                return redirect(url_for('farmer.settings'))
            
            # Check current password
            user = fetchone("SELECT Password FROM users WHERE UserID = %s", (user_id,))
            if not user or not check_password_hash(user['Password'], current_password):
                flash("Current password is incorrect", "danger")
                return redirect(url_for('farmer.settings'))
            
            # Update password
            hashed = generate_password_hash(new_password)
            execute("UPDATE users SET Password = %s WHERE UserID = %s", (hashed, user_id))
            flash("Password changed successfully!", "success")
            return redirect(url_for('farmer.settings'))
        
        elif action == 'update_profile':
            name = request.form.get('name')
            location = request.form.get('location')
            
            if name and location:
                execute("UPDATE farmer SET Name = %s, Location = %s WHERE FarmerID = %s", 
                       (name, location, farmer_id))
                # Update session
                session['user']['Name'] = name
                flash("Profile updated successfully!", "success")
            else:
                flash("Name and location are required", "danger")
            
            return redirect(url_for('farmer.settings'))
    
    # GET request - show settings page
    farmer = fetchone("SELECT * FROM farmer WHERE FarmerID = %s", (farmer_id,))
    user = fetchone("SELECT Email FROM users WHERE UserID = %s", (user_id,))
    
    return flask_render("farmer/settings.html", farmer=farmer, user=user)

