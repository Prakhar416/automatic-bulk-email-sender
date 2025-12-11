from setuptools import setup, find_packages

setup(
    name="automatic-bulk-email-sender",
    version="0.1.0",
    description="Automatic bulk email sender with Jinja2 templates, Gmail/SendGrid support",
    author="",
    author_email="",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "Jinja2>=3.0.0",
        "email-validator>=1.3.0",
        "google-auth-oauthlib>=0.7.0",
        "google-auth-httplib2>=0.1.0",
        "google-api-python-client>=2.50.0",
        "sendgrid>=6.9.0",
        "python-dotenv>=0.19.0",
        "click>=8.0.0",
        "pydantic>=1.9.0",
        "requests>=2.28.0",
        "PyYAML>=5.4.0",
    ],
    entry_points={
        "console_scripts": [
            "email-sender=email_sender.cli:main",
        ],
    },
)
