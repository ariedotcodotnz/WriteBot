Introduction
============

What is WriteBot?
-----------------

WriteBot is a Flask-based web application that uses deep learning to generate realistic handwritten text. It leverages recurrent neural networks (RNNs) with attention mechanisms to synthesize handwriting from any input text.

Features
--------

Handwriting Generation
~~~~~~~~~~~~~~~~~~~~~~~

* **Single Generation**: Generate individual handwritten text in SVG format
* **Batch Generation**: Process multiple texts from CSV files
* **Multiple Styles**: Choose from various handwriting styles
* **Character Overrides**: Replace AI-generated characters with custom hand-drawn variants

User Management
~~~~~~~~~~~~~~~

* **Authentication**: Secure login system with Flask-Login
* **User Roles**: Admin and regular user roles
* **Activity Tracking**: Log all user actions
* **Usage Statistics**: Track generation metrics

Admin Dashboard
~~~~~~~~~~~~~~~

* **User Management**: Create, edit, and delete users
* **Activity Monitoring**: View all user activities
* **Statistics**: Analyze usage patterns
* **Character Override Collections**: Manage custom character sets

Architecture
------------

Technology Stack
~~~~~~~~~~~~~~~~

* **Backend**: Flask (Python)
* **Database**: SQLAlchemy (SQLite/PostgreSQL)
* **ML Framework**: TensorFlow
* **Frontend**: Vanilla JavaScript
* **Authentication**: Flask-Login
* **Documentation**: Sphinx

Project Structure
~~~~~~~~~~~~~~~~~

::

    WriteBot/
    ├── webapp/
    │   ├── routes/          # API endpoints
    │   ├── models.py        # Database models
    │   ├── utils/           # Utility functions
    │   ├── templates/       # Jinja2 templates
    │   └── static/          # CSS, JS, assets
    ├── handwriting_synthesis/  # ML models
    ├── docs/                # Sphinx documentation
    └── app.py              # Main application

Getting Started
---------------

Installation
~~~~~~~~~~~~

1. Clone the repository
2. Install dependencies: ``pip install -r requirements.txt``
3. Initialize the database: ``python -m webapp.init_db``
4. Run the application: ``python -m webapp.app``

Configuration
~~~~~~~~~~~~~

Set the following environment variables:

* ``SECRET_KEY``: Flask secret key for sessions
* ``DATABASE_URL``: Database connection string
* ``FLASK_ENV``: Set to ``development`` or ``production``

API Authentication
~~~~~~~~~~~~~~~~~~

All API endpoints (except health check) require authentication. Use the login endpoint to obtain a session:

.. code-block:: bash

    curl -X POST http://localhost:5000/auth/login \\
         -H "Content-Type: application/x-www-form-urlencoded" \\
         -d "username=your_username&password=your_password"
