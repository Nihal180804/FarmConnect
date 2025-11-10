from flask import Flask, send_from_directory, session
from routes.auth import auth_bp
from routes.farmer import farmer_bp
from routes.customer import customer_bp
from routes.admin import admin_bp
from config import APP_CONFIG
from flask_wtf.csrf import CSRFProtect
from database import fetchone

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="routes/templates")
    app.config.from_mapping(
        SECRET_KEY="please_change_this_to_a_secure_random_value",
        SESSION_COOKIE_NAME="lfmsession",
    )
    # optionally override SECRET_KEY via environment variable in production

    # Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(farmer_bp, url_prefix="/farmer")
    app.register_blueprint(customer_bp, url_prefix="/customer")
    app.register_blueprint(admin_bp, url_prefix="/admin")

    # CSRF protection
    csrf = CSRFProtect()
    csrf.init_app(app)

    # Context processor to ensure user has name
    @app.context_processor
    def inject_user_with_name():
        if session.get('user') and not session['user'].get('Name'):
            user = session['user']
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
            
            # Update session with name
            session['user']['Name'] = name
        
        return {}

    # Favicon route
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory('static/images', 'logo.svg', mimetype='image/svg+xml')

    # error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return flask_render("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return flask_render("errors/500.html"), 500

    return app

def flask_render(tpl, **kwargs):
    from flask import render_template
    return render_template(tpl, app_config=APP_CONFIG, **kwargs)

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
