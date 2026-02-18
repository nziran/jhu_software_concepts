from setuptools import find_packages, setup

setup(
    name="module_5_gradcafe_app",
    version="0.1.0",
    description="Module 5 GradCafe Flask app + secure SQL pipeline",
    packages=find_packages(),  # finds the 'src' package (src/__init__.py)
    install_requires=[
        "Flask",
        "psycopg[binary]",
        "beautifulsoup4",
        "requests",
    ],
    python_requires=">=3.10",
)