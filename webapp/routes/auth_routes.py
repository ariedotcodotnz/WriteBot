"""
Authentication routes for login and logout.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from webapp.models import db, User
from webapp.utils.auth_utils import log_activity

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Handle user login.

    GET: Renders the login page.
    POST: Processes the login form submission, validates credentials,
          logs the user in, and redirects to the requested page or home.
    """
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'

        if not username or not password:
            flash('Please provide both username and password.', 'error')
            return render_template('auth/login.html')

        # Find user by username
        user = User.query.filter_by(username=username).first()

        if user is None:
            flash('Invalid username or password.', 'error')
            return render_template('auth/login.html')

        if not user.is_active:
            flash('Your account has been disabled. Please contact an administrator.', 'error')
            return render_template('auth/login.html')

        if not user.check_password(password):
            flash('Invalid username or password.', 'error')
            return render_template('auth/login.html')

        # Login successful
        login_user(user, remember=remember)
        user.update_last_login()
        log_activity('login', f'User {username} logged in successfully')

        # Redirect to next page or index
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        return redirect(url_for('index'))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Handle user logout.

    Logs the current user out, records the activity, and redirects to login.
    """
    username = current_user.username
    log_activity('logout', f'User {username} logged out')
    logout_user()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login'))
