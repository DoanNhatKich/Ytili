"""
Authentication routes for the frontend
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, EqualTo, ValidationError
import re
import httpx

from ..utils.api import APIClient

bp = Blueprint('auth', __name__, url_prefix='/auth')


def validate_password_strength(form, field):
    """Custom validator for password strength according to Supabase requirements"""
    password = field.data

    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')

    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')

    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')

    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one number.')

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>).')


class LoginForm(FlaskForm):
    """Login form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class RegisterForm(FlaskForm):
    """Registration form"""
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[
        DataRequired(),
        validate_password_strength
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    full_name = StringField('Full Name', validators=[DataRequired()])
    phone = StringField('Phone Number')
    user_type = SelectField('User Type', choices=[
        ('individual', 'Individual'),
        ('hospital', 'Hospital/Clinic'),
        ('organization', 'Organization')
    ], validators=[DataRequired()])
    organization_name = StringField('Organization Name')
    license_number = StringField('License Number')
    address = StringField('Address')
    city = StringField('City')
    province = StringField('Province')
    submit = SubmitField('Register')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    import requests

    form = LoginForm()

    if form.validate_on_submit():
        try:
            login_data = {
                'email': form.email.data,
                'password': form.password.data
            }

            response = requests.post(
                'http://localhost:8000/api/v1/auth/login',
                json=login_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )

            if response.status_code == 200:
                response_data = response.json()

                # Store token in session
                session['access_token'] = response_data['access_token']
                session['user'] = response_data['user']

                flash('Login successful!', 'success')
                return redirect(url_for('main.index'))

            elif response.status_code == 401:
                flash('Invalid email or password', 'error')
            elif response.status_code == 403:
                # Email verification required
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_detail = error_data.get('detail', 'Email verification required')
                flash(error_detail, 'warning')
            elif response.status_code == 422:
                flash('Invalid login data format', 'error')
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_detail = error_data.get('detail', f'HTTP {response.status_code}')
                flash(f'Login failed: {error_detail}', 'error')

        except Exception as e:
            flash(f'Login failed: {str(e)}', 'error')

    return render_template('auth/login.html', form=form)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """Registration page"""
    import requests

    form = RegisterForm()

    if form.validate_on_submit():
        # Prepare user data
        user_data = {
            'email': form.email.data,
            'password': form.password.data,
            'full_name': form.full_name.data,
            'user_type': form.user_type.data,
            'phone': form.phone.data,
            'organization_name': form.organization_name.data,
            'license_number': form.license_number.data,
            'address': form.address.data,
            'city': form.city.data,
            'province': form.province.data
        }

        try:
            response = requests.post(
                'http://localhost:8000/api/v1/auth/register',
                json=user_data,
                headers={'Content-Type': 'application/json'},
                timeout=30  # 30 second timeout
            )

            if response.status_code in [200, 201]:
                response_data = response.json()
                # Check if user was auto-verified
                if response_data.get('user_profile', {}).get('status') == 'verified':
                    flash('Registration successful! Your account is ready to use.', 'success')
                else:
                    flash('Registration successful! Your account is pending verification.', 'info')
                return redirect(url_for('auth.login'))
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_detail = error_data.get('detail', f'HTTP {response.status_code}')
                flash(f'Registration failed: {error_detail}', 'error')

        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')

    return render_template('auth/register.html', form=form)


@bp.route('/verify-email/<token>')
def verify_email(token):
    """Email verification"""
    import requests

    try:
        response = requests.post(
            f'http://localhost:8000/api/v1/auth/verify-email/{token}',
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if response.status_code == 200:
            flash('Email verified successfully!', 'success')
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_detail = error_data.get('detail', 'Email verification failed')
            flash(f'Email verification failed: {error_detail}', 'error')

        return redirect(url_for('auth.login'))

    except Exception as e:
        flash(f'Email verification failed: {str(e)}', 'error')
        return redirect(url_for('auth.login'))


@bp.route('/verify-account', methods=['POST'])
def verify_account():
    """Manually verify user account"""
    import requests

    user = session.get('user')
    if not user:
        flash('Please log in first', 'error')
        return redirect(url_for('auth.login'))

    try:
        # Get auth token
        access_token = session.get('access_token')
        auth_headers = {'Content-Type': 'application/json'}
        if access_token:
            auth_headers['Authorization'] = f"Bearer {access_token}"

        response = requests.post(
            'http://localhost:8000/api/v1/auth/verify-account',
            json={},
            headers=auth_headers,
            timeout=30
        )

        if response.status_code == 200:
            # Update user session with verified status
            user['status'] = 'verified'
            user['is_email_verified'] = True
            user['is_kyc_verified'] = True
            session['user'] = user

            flash('Account verified successfully!', 'success')
        else:
            error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
            error_detail = error_data.get('detail', 'Verification failed')
            flash(f'Verification failed: {error_detail}', 'error')

        return redirect(url_for('main.dashboard'))

    except Exception as e:
        flash(f'Verification failed: {str(e)}', 'error')
        return redirect(url_for('main.dashboard'))


@bp.route('/logout')
def logout():
    """Logout user"""
    session.pop('access_token', None)
    session.pop('user', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('main.index'))
