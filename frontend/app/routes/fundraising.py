"""
Fundraising routes for the frontend
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, FloatField, DateField, SubmitField, BooleanField
from wtforms.validators import DataRequired, NumberRange, Optional
import httpx
from datetime import datetime, timedelta

from ..utils.api import APIClient

bp = Blueprint('fundraising', __name__, url_prefix='/fundraising')


class CampaignForm(FlaskForm):
    """Campaign creation form"""
    title = StringField('Campaign Title', validators=[DataRequired()])
    description = TextAreaField('Campaign Description', validators=[DataRequired()])
    category = SelectField('Category', choices=[
        ('emergency_medical', 'Emergency Medical'),
        ('children_health', 'Children\'s Health'),
        ('surgery_treatment', 'Surgery & Treatment'),
        ('hospital_equipment', 'Hospital Equipment')
    ], validators=[DataRequired()])
    
    target_amount = FloatField('Target Amount (VND)', validators=[
        DataRequired(), 
        NumberRange(min=100000, max=1000000000, message='Amount must be between 100,000 and 1,000,000,000 VND')
    ])
    
    end_date = DateField('Campaign End Date', validators=[DataRequired()])
    
    beneficiary_name = StringField('Beneficiary Name', validators=[DataRequired()])
    beneficiary_story = TextAreaField('Beneficiary Story', validators=[DataRequired()])
    
    urgency_level = SelectField('Urgency Level', choices=[
        ('urgent', 'Urgent'),
        ('high', 'High'),
        ('normal', 'Normal'),
        ('low', 'Low')
    ], default='normal')
    
    submit = SubmitField('Create Campaign')


class DonationForm(FlaskForm):
    """Donation to campaign form"""
    amount = FloatField('Donation Amount (VND)', validators=[
        DataRequired(),
        NumberRange(min=10000, max=100000000, message='Amount must be between 10,000 and 100,000,000 VND')
    ])
    message = TextAreaField('Message (Optional)')
    is_anonymous = BooleanField('Donate Anonymously')
    submit = SubmitField('Donate Now')


@bp.route('/')
def index():
    """Fundraising campaigns page"""
    import requests

    try:
        # Get campaigns from API
        campaigns_response = requests.get('http://localhost:8000/api/v1/fundraising/campaigns')
        campaigns = campaigns_response.json() if campaigns_response.status_code == 200 else []

        # Get categories
        categories_response = requests.get('http://localhost:8000/api/v1/fundraising/campaigns/categories')
        categories_data = categories_response.json() if categories_response.status_code == 200 else {}
        categories = categories_data.get('categories', [])

        return render_template('fundraising.html',
                             campaigns=campaigns,
                             categories=categories)

    except Exception as e:
        flash(f'Error loading campaigns: {e}', 'error')
        return render_template('fundraising.html', campaigns=[], categories=[])


@bp.route('/create', methods=['GET', 'POST'])
def create():
    """Create a new fundraising campaign"""
    import requests

    user = session.get('user')
    access_token = session.get('access_token')

    if not user:
        flash('Please log in to create a campaign', 'warning')
        return redirect(url_for('auth.login'))

    if not access_token:
        flash('Authentication session expired. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

    if user.get('status') != 'verified':
        flash('You need to verify your account before creating campaigns', 'warning')
        return redirect(url_for('main.dashboard'))

    form = CampaignForm()

    if form.validate_on_submit():
        # Validate end date
        if form.end_date.data <= datetime.now().date():
            flash('End date must be in the future', 'error')
            return render_template('fundraising/create.html', form=form)

        # Prepare campaign data
        campaign_data = {
            'title': form.title.data,
            'description': form.description.data,
            'category': form.category.data,
            'target_amount': form.target_amount.data,
            'end_date': form.end_date.data.isoformat(),
            'beneficiary_name': form.beneficiary_name.data,
            'beneficiary_story': form.beneficiary_story.data,
            'urgency_level': form.urgency_level.data,
            'currency': 'VND'
        }

        try:
            # Get auth token from session
            auth_headers = {'Content-Type': 'application/json'}
            access_token = session.get('access_token')
            if access_token:
                auth_headers['Authorization'] = f"Bearer {access_token}"
            else:
                flash('Authentication token not found. Please log in again.', 'warning')
                return redirect(url_for('auth.login'))

            response = requests.post(
                'http://localhost:8000/api/v1/fundraising/campaigns',
                json=campaign_data,
                headers=auth_headers
            )

            if response.status_code == 200 or response.status_code == 201:
                response_data = response.json()
                flash('Campaign created successfully! It will be reviewed before going live.', 'success')
                return redirect(url_for('fundraising.detail', campaign_id=response_data['id']))
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_detail = error_data.get('detail', f'HTTP {response.status_code}')
                flash(f'Failed to create campaign: {error_detail}', 'error')

        except Exception as e:
            flash(f'Failed to create campaign: {str(e)}', 'error')

    return render_template('fundraising/create.html', form=form)


@bp.route('/<campaign_id>')
def detail(campaign_id):
    """Campaign detail page"""
    import requests

    try:
        # Get campaign details
        response = requests.get(f'http://localhost:8000/api/v1/fundraising/campaigns/{campaign_id}')

        if response.status_code == 200:
            campaign = response.json()
        elif response.status_code == 404:
            flash('Campaign not found', 'error')
            return redirect(url_for('fundraising.index'))
        else:
            flash('Error loading campaign', 'error')
            return redirect(url_for('fundraising.index'))

        # Get current user for donation form
        user = session.get('user')

        return render_template('fundraising/detail.html',
                             campaign=campaign,
                             user=user)

    except Exception as e:
        flash(f'Error loading campaign: {e}', 'error')
        return redirect(url_for('fundraising.index'))


@bp.route('/<campaign_id>/donate', methods=['GET', 'POST'])
def donate(campaign_id):
    """Donate to a campaign"""
    import requests

    user = session.get('user')
    if not user:
        flash('Please log in to donate', 'warning')
        return redirect(url_for('auth.login'))

    if user.get('status') != 'verified':
        flash('You need to verify your account before donating', 'warning')
        return redirect(url_for('main.dashboard'))

    # Get campaign details
    try:
        response = requests.get(f'http://localhost:8000/api/v1/fundraising/campaigns/{campaign_id}')
        if response.status_code == 200:
            campaign = response.json()
        else:
            flash('Campaign not found', 'error')
            return redirect(url_for('fundraising.index'))
    except Exception as e:
        flash('Campaign not found', 'error')
        return redirect(url_for('fundraising.index'))

    form = DonationForm()

    if form.validate_on_submit():
        # Prepare donation data
        donation_data = {
            'amount': form.amount.data,
            'currency': 'VND',
            'message': form.message.data,
            'is_anonymous': form.is_anonymous.data
        }

        try:
            # Get auth token
            access_token = session.get('access_token')
            auth_headers = {'Content-Type': 'application/json'}
            if access_token:
                auth_headers['Authorization'] = f"Bearer {access_token}"

            response = requests.post(
                f'http://localhost:8000/api/v1/fundraising/campaigns/{campaign_id}/donate',
                json=donation_data,
                headers=auth_headers
            )

            if response.status_code in [200, 201]:
                flash(f'Thank you for your donation of {form.amount.data:,.0f} VND!', 'success')
                return redirect(url_for('fundraising.detail', campaign_id=campaign_id))
            else:
                error_data = response.json() if response.headers.get('content-type', '').startswith('application/json') else {}
                error_detail = error_data.get('detail', f'HTTP {response.status_code}')
                flash(f'Failed to process donation: {error_detail}', 'error')

        except Exception as e:
            flash(f'Failed to process donation: {str(e)}', 'error')

    return render_template('fundraising/donate.html',
                         form=form,
                         campaign=campaign,
                         user=user)


@bp.route('/category/<category>')
def category(category):
    """View campaigns by category"""
    import requests

    try:
        # Get campaigns by category
        campaigns_response = requests.get(f'http://localhost:8000/api/v1/fundraising/campaigns?category={category}')
        campaigns = campaigns_response.json() if campaigns_response.status_code == 200 else []

        # Get categories for navigation
        categories_response = requests.get('http://localhost:8000/api/v1/fundraising/campaigns/categories')
        categories_data = categories_response.json() if categories_response.status_code == 200 else {}
        categories = categories_data.get('categories', [])

        # Find current category name
        current_category = next((cat for cat in categories if cat['id'] == category), None)
        category_name = current_category['name'] if current_category else category.replace('_', ' ').title()

        return render_template('fundraising/category.html',
                             campaigns=campaigns,
                             categories=categories,
                             current_category=category,
                             category_name=category_name)

    except Exception as e:
        flash(f'Error loading campaigns: {e}', 'error')
        return redirect(url_for('fundraising.index'))


@bp.route('/my-campaigns')
def my_campaigns():
    """View user's own campaigns"""
    import requests

    user = session.get('user')
    if not user:
        flash('Please log in to view your campaigns', 'warning')
        return redirect(url_for('auth.login'))

    try:
        # Get all campaigns and filter by user
        campaigns_response = requests.get('http://localhost:8000/api/v1/fundraising/campaigns?status=all')
        all_campaigns = campaigns_response.json() if campaigns_response.status_code == 200 else []
        my_campaigns_list = [c for c in all_campaigns if c.get('creator_id') == user.get('id')]

        return render_template('fundraising/my_campaigns.html',
                             campaigns=my_campaigns_list,
                             user=user)

    except Exception as e:
        flash(f'Error loading your campaigns: {e}', 'error')
        return render_template('fundraising/my_campaigns.html', campaigns=[], user=user)


@bp.route('/api/quick-donate', methods=['POST'])
def quick_donate():
    """Quick donation API endpoint for AJAX calls"""
    import requests

    user = session.get('user')
    if not user:
        return jsonify({'error': 'Not logged in'}), 401

    if user.get('status') != 'verified':
        return jsonify({'error': 'Account not verified'}), 403

    data = request.get_json()
    campaign_id = data.get('campaign_id')
    amount = data.get('amount')

    if not campaign_id or not amount:
        return jsonify({'error': 'Missing campaign_id or amount'}), 400

    try:
        donation_data = {
            'amount': float(amount),
            'currency': 'VND',
            'message': data.get('message', ''),
            'is_anonymous': data.get('is_anonymous', False)
        }

        # Get auth token
        access_token = session.get('access_token')
        auth_headers = {'Content-Type': 'application/json'}
        if access_token:
            auth_headers['Authorization'] = f"Bearer {access_token}"

        response = requests.post(
            f'http://localhost:8000/api/v1/fundraising/campaigns/{campaign_id}/donate',
            json=donation_data,
            headers=auth_headers
        )

        if response.status_code in [200, 201]:
            response_data = response.json()
            return jsonify({
                'success': True,
                'message': f'Thank you for your donation of {amount:,.0f} VND!',
                'new_total': response_data.get('campaign_new_total', 0)
            })
        else:
            return jsonify({'error': 'Donation failed'}), 500

    except Exception as e:
        return jsonify({'error': 'Donation failed'}), 500
