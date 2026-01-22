"""
Route definitions for the web pages.

This module defines the Flask routes using a Blueprint to organize
page-related views (Home, Contact, Projects).
"""

from flask import Blueprint, render_template

# Create a Blueprint to group page routes together
bp = Blueprint("pages", __name__)


@bp.route("/")
def home():
    """
    Render the Home page.

    The 'active' variable is passed to the template to highlight
    the current navigation tab.
    """
    return render_template("pages/home.html", active="home")


@bp.route("/contact")
def contact():
    """
    Render the Contact page.

    Displays email and LinkedIn information and highlights
    the Contact tab in the navigation bar.
    """
    return render_template("pages/contact.html", active="contact")


@bp.route("/projects")
def projects():
    """
    Render the Projects page.

    Displays details about the Module 1 project and highlights
    the Projects tab in the navigation bar.
    """
    return render_template("pages/projects.html", active="projects")