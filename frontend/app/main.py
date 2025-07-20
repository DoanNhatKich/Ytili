"""
Ytili Frontend Main Application
Flask application entry point
"""
from flask import Flask
from flask_wtf.csrf import CSRFProtect
import os

from .config import config
from .routes import main, auth, donations, transparency, payments, fundraising, fraud, api_proxy


def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')

    # Configure Flask with static folder
    app = Flask(__name__,
                static_folder='static',
                static_url_path='/static')
    app.config.from_object(config[config_name])
    
    # Initialize CSRF protection
    csrf = CSRFProtect(app)
    
    # Register blueprints
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(donations.bp)
    app.register_blueprint(transparency.bp)
    app.register_blueprint(payments.bp)
    app.register_blueprint(fundraising.bp)
    app.register_blueprint(fraud.fraud_bp)
    # Proxy: forward /api/v1/* to FastAPI backend
    app.register_blueprint(api_proxy.bp)
    
    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
