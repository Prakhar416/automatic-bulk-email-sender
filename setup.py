from setuptools import setup, find_packages

setup(
    name="email-tracking-service",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "Flask==3.0.0",
        "Werkzeug==3.0.1",
        "click==8.1.7",
        "requests==2.31.0",
        "python-dotenv==1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "email-tracking-cli=tracking.cli:cli",
        ],
    },
)
