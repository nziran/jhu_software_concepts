"""
Application factory for the Flask web application.

This module creates and configures the Flask app instance.
Using an application factory allows for cleaner organization
and easier expansion of the project.
"""

from flask import Flask

# Import the pages blueprint, which contains route definitions
from . import pages


def create_app():
    """
    Create and configure the Flask application.

    This function initializes the Flask app and registers
    all blueprints used by the application.
    """
    # Create the Flask application instance
    app = Flask(__name__)

    # Register the pages blueprint to enable page routing
    app.register_blueprint(pages.bp)

    # Return the configured Flask app
    return app