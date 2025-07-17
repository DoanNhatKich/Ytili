"""
Main routes for the frontend
"""
from flask import Blueprint, render_template, session, redirect, url_for

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Homepage"""
    user = session.get('user')
    return render_template('index.html', user=user)


@bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@bp.route('/dashboard')
def dashboard():
    """User dashboard"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))

    return render_template('dashboard.html', user=user)


# Fundraising route moved to fundraising.py


@bp.route('/profile')
def profile():
    """User profile page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))

    return render_template('profile.html', user=user)


@bp.route('/rewards')
def rewards():
    """Points & Rewards page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))

    return render_template('rewards.html', user=user)


@bp.route('/debug-session')
def debug_session():
    """Debug session information"""
    user = session.get('user')
    access_token = session.get('access_token')

    debug_info = {
        'user_logged_in': user is not None,
        'user_data': user if user else 'No user data',
        'has_access_token': access_token is not None,
        'access_token_preview': access_token[:20] + '...' if access_token else 'No token',
        'session_keys': list(session.keys())
    }

    return f"<pre>{debug_info}</pre>"
