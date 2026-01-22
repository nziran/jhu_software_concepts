"""
Entry point for the Flask web application.

This file creates the Flask app using the application factory pattern
and starts the development server when run with:
    python run.py

The server is explicitly configured to run on port 8080 and bind to
0.0.0.0 (or localhost), as required by the assignment.
"""

# Import the application factory function
from ziran_bio_flask.board import create_app

# Create the Flask application instance
app = create_app()

# Only run the server if this file is executed directly
if __name__ == "__main__":
    # Start the Flask development server
    # host="0.0.0.0" allows access via localhost or local network
    # port=8080 satisfies the assignment requirement
    app.run(host="0.0.0.0", port=8080, debug=True)