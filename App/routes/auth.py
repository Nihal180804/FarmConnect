from flask import Blueprint, request, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import fetchone, fetchall, execute
from database import get_conn
from config import APP_CONFIG

auth_bp = Blueprint("auth", __name__)

# helper
def flask_render(tpl, **kwargs):
    return render_template(tpl, app_config=APP_CONFIG, **kwargs)

def get_user_by_email(email):
    row = fetchone("SELECT * FROM users WHERE Email = %s", (email,))
    return row

def login_user(user):
    # Fetch the name from related table based on user type
    name = user['Email'].split('@')[0]  # Default fallback
    
    if user['UserType'] == 'Customer' and user.get('RelatedID'):
        customer = fetchone("SELECT Name FROM customer WHERE CustomerID = %s", (user['RelatedID'],))
        if customer:
            name = customer['Name']
    elif user['UserType'] == 'Farmer' and user.get('RelatedID'):
        farmer = fetchone("SELECT Name FROM farmer WHERE FarmerID = %s", (user['RelatedID'],))
        if farmer:
            name = farmer['Name']
    elif user['UserType'] == 'Admin':
        name = "Administrator"
    
    session['user'] = {
        'UserID': user['UserID'],
        'Email': user['Email'],
        'UserType': user['UserType'],
        'RelatedID': user.get('RelatedID'),
        'Name': name
    }

@auth_bp.route("/", methods=["GET"])
def index():
    # Show landing page
    return flask_render("index.html")

@auth_bp.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form['email'].strip()
        password = request.form['password'].strip()
        user = get_user_by_email(email)
        if not user:
            flash("Invalid credentials", "danger")
            return flask_render("login.html")
        stored = user['Password']
        # Support both plaintext (existing demo rows) and hashed passwords.
        # If password matches stored plaintext, accept and update to hashed version for security.
        if stored == password:
            # update to hashed password
            hashed = generate_password_hash(password)
            conn = get_conn()
            cur = conn.cursor()
            cur.execute("UPDATE users SET Password=%s WHERE UserID=%s", (hashed, user['UserID']))
            conn.commit()
            cur.close()
            conn.close()
            user['Password'] = hashed
        # Now check hashed
        if check_password_hash(user['Password'], password):
            login_user(user)
            flash("Logged in successfully.", "success")
            # update last login
            execute("UPDATE users SET LastLogin = NOW() WHERE UserID = %s", (user['UserID'],))
            # redirect role-wise
            if user['UserType'] == 'Admin':
                return redirect(url_for('admin.dashboard'))
            elif user['UserType'] == 'Farmer':
                return redirect(url_for('farmer.dashboard'))
            else:
                return redirect(url_for('customer.shop'))
        else:
            flash("Invalid credentials", "danger")
    return flask_render("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        user_type = request.form.get('user_type', 'Customer').strip()
        location = request.form.get('location', '').strip()
        phone = request.form.get('phone', '').strip()

        # Validation
        if not all([full_name, email, password, confirm_password]):
            flash("All fields are required", "danger")
            return flask_render("register.html")
        
        if password != confirm_password:
            flash("Passwords do not match", "danger")
            return flask_render("register.html")
        
        if len(password) < 6:
            flash("Password must be at least 6 characters", "danger")
            return flask_render("register.html")
        
        # Check if email exists
        existing = get_user_by_email(email)
        if existing:
            flash("Email already registered", "danger")
            return flask_render("register.html")
        
        try:
            # Hash password
            hashed_password = generate_password_hash(password)
            
            if user_type == 'Farmer':
                # Create Farmer first
                farmer_query = """
                    INSERT INTO farmer (Name, Contact, Location)
                    VALUES (%s, %s, %s)
                """
                execute(farmer_query, (full_name, phone, location))
                
                # Get the inserted farmer ID
                farmer = fetchone("SELECT FarmerID FROM farmer WHERE Name = %s AND Contact = %s", (full_name, phone))
                farmer_id = farmer['FarmerID'] if farmer else None
                
                # Create user entry
                user_query = """
                    INSERT INTO users (Email, Password, UserType, RelatedID, CreatedAt)
                    VALUES (%s, %s, %s, %s, NOW())
                """
                execute(user_query, (email, hashed_password, 'Farmer', farmer_id))
                
                # Auto-login the user
                user = get_user_by_email(email)
                if user:
                    login_user(user)
                    flash("Farmer account created successfully! Welcome to FarmConnect!", "success")
                    return redirect(url_for('farmer.dashboard'))
            else:
                # Create Customer
                customer_query = """
                    INSERT INTO customer (Name, Email, Location)
                    VALUES (%s, %s, %s)
                """
                execute(customer_query, (full_name, email, location))
                
                # Get the inserted customer ID
                customer = fetchone("SELECT CustomerID FROM customer WHERE Name = %s AND Email = %s", (full_name, email))
                customer_id = customer['CustomerID'] if customer else None
                
                # Create user entry
                user_query = """
                    INSERT INTO users (Email, Password, UserType, RelatedID, CreatedAt)
                    VALUES (%s, %s, %s, %s, NOW())
                """
                execute(user_query, (email, hashed_password, 'Customer', customer_id))
                
                # Auto-login the user
                user = get_user_by_email(email)
                if user:
                    login_user(user)
                    flash("Customer account created successfully! Welcome to FarmConnect!", "success")
                    return redirect(url_for('customer.shop'))
            
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            flash(f"Registration failed: {str(e)}", "danger")
            return flask_render("register.html")
    
    return flask_render("register.html")

@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("Logged out", "info")
    return redirect(url_for('auth.login'))
