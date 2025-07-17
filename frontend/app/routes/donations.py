"""
Donation routes for the frontend
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateField, SubmitField
from wtforms.validators import DataRequired, Optional, NumberRange
import httpx

from ..utils.api import APIClient

bp = Blueprint('donations', __name__, url_prefix='/donations')


class DonationForm(FlaskForm):
    """Donation creation form"""
    donation_type = SelectField('Donation Type', choices=[
        ('medication', 'Medication'),
        ('medical_supply', 'Medical Supply'),
        ('food', 'Food/Nutrition'),
        ('cash', 'Cash Donation')
    ], validators=[DataRequired()])
    
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description')
    
    # For physical items
    item_name = StringField('Item Name')
    quantity = IntegerField('Quantity', validators=[Optional(), NumberRange(min=1)])
    unit = StringField('Unit (e.g., boxes, bottles, pieces)')
    expiry_date = DateField('Expiry Date', validators=[Optional()])
    batch_number = StringField('Batch Number')
    manufacturer = StringField('Manufacturer')
    
    # For cash donations
    amount = IntegerField('Amount (VND)', validators=[Optional(), NumberRange(min=1000, max=999999999999)])
    
    # Logistics
    pickup_address = TextAreaField('Pickup Address')
    
    submit = SubmitField('Create Donation')


@bp.route('/')
async def index():
    """Donations listing page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    
    api_client = APIClient()
    
    try:
        # Get user's donations
        donations = await api_client.get('/donations/')
        
        # Get available donations for hospitals
        available_donations = []
        if user.get('user_type') == 'hospital':
            available_donations = await api_client.get('/matching/available')
        
        return render_template('donations/index.html', 
                             donations=donations, 
                             available_donations=available_donations,
                             user=user)
    
    except httpx.HTTPStatusError as e:
        flash(f'Error loading donations: {e}', 'error')
        return render_template('donations/index.html', 
                             donations=[], 
                             available_donations=[],
                             user=user)


@bp.route('/create', methods=['GET', 'POST'])
async def create():
    """Create donation page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    
    form = DonationForm()
    
    if form.validate_on_submit():
        api_client = APIClient()
        
        # Prepare donation data
        donation_data = {
            'donation_type': form.donation_type.data,
            'title': form.title.data,
            'description': form.description.data,
            'pickup_address': form.pickup_address.data
        }
        
        # Add type-specific fields
        if form.donation_type.data in ['medication', 'medical_supply', 'food']:
            donation_data.update({
                'item_name': form.item_name.data,
                'quantity': form.quantity.data,
                'unit': form.unit.data,
                'batch_number': form.batch_number.data,
                'manufacturer': form.manufacturer.data
            })
            
            if form.expiry_date.data:
                donation_data['expiry_date'] = form.expiry_date.data.isoformat()
        
        elif form.donation_type.data == 'cash':
            donation_data.update({
                'amount': form.amount.data,
                'currency': 'VND'
            })
        
        try:
            response = await api_client.post('/donations/', donation_data)
            flash('Donation created successfully!', 'success')
            return redirect(url_for('donations.detail', donation_id=response['id']))

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                flash('Your session has expired. Please log in again.', 'warning')
                return redirect(url_for('auth.login'))
            elif e.response.status_code == 403:
                flash('You need to verify your account before creating donations.', 'warning')
                return redirect(url_for('main.dashboard'))
            else:
                try:
                    error_detail = e.response.json().get('detail', str(e))
                    flash(f'Failed to create donation: {error_detail}', 'error')
                except:
                    flash(f'Failed to create donation: {e}', 'error')
    
    return render_template('donations/create.html', form=form)


@bp.route('/<string:donation_id>')
async def detail(donation_id):
    """Donation detail page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    
    api_client = APIClient()
    
    try:
        donation = await api_client.get(f'/donations/{donation_id}')
        
        # Get matches if user is the donor
        matches = []
        if donation['donor_id'] == user['id'] and donation['status'] == 'verified':
            try:
                match_response = await api_client.post('/matching/find', {
                    'donation_id': donation_id
                })
                matches = match_response
            except:
                pass  # Matches are optional
        
        return render_template('donations/detail.html', 
                             donation=donation, 
                             matches=matches,
                             user=user)
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            flash('Donation not found', 'error')
        else:
            flash(f'Error loading donation: {e}', 'error')
        return redirect(url_for('donations.index'))


@bp.route('/<int:donation_id>/accept', methods=['POST'])
async def accept(donation_id):
    """Accept a donation (hospital only)"""
    user = session.get('user')
    if not user or user.get('user_type') != 'hospital':
        flash('Only hospitals can accept donations', 'error')
        return redirect(url_for('donations.index'))
    
    api_client = APIClient()
    
    try:
        await api_client.post(f'/matching/{donation_id}/accept')
        flash('Donation accepted successfully!', 'success')
        
    except httpx.HTTPStatusError as e:
        flash(f'Failed to accept donation: {e}', 'error')
    
    return redirect(url_for('donations.detail', donation_id=donation_id))


@bp.route('/live-tracking')
async def live_tracking():
    """Live donation tracking page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))

    api_client = APIClient()

    try:
        # Get user's donations with live tracking data
        donations = await api_client.get('/donations/live-tracking')

        # Get donation statistics
        stats = await api_client.get('/donations/stats')

        return render_template('donations/live_tracking.html',
                             donations=donations.get('donations', []),
                             stats=stats.get('stats', {}),
                             user=user)

    except httpx.HTTPStatusError as e:
        flash(f'Error loading live tracking: {e}', 'error')
        return render_template('donations/live_tracking.html',
                             donations=[],
                             stats={},
                             user=user)


@bp.route('/api/live-tracking')
async def api_live_tracking():
    """API endpoint for live tracking data"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    api_client = APIClient()

    try:
        # Get live tracking data
        donations = await api_client.get('/donations/live-tracking')
        stats = await api_client.get('/donations/stats')

        return jsonify({
            'success': True,
            'donations': donations.get('donations', []),
            'stats': stats.get('stats', {})
        })

    except httpx.HTTPStatusError as e:
        return jsonify({
            'success': False,
            'error': f'Failed to load tracking data: {e}'
        }), 500


@bp.route('/catalog')
async def catalog():
    """Medication catalog page"""
    api_client = APIClient()
    
    try:
        # Get search parameters
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        
        # Build query parameters
        params = {}
        if search:
            params['search'] = search
        if category:
            params['category'] = category
        
        medications = await api_client.get('/catalog/', params)
        categories = await api_client.get('/catalog/categories')
        
        return render_template('donations/catalog.html', 
                             medications=medications,
                             categories=categories.get('categories', []),
                             search=search,
                             selected_category=category)
    
    except httpx.HTTPStatusError as e:
        flash(f'Error loading catalog: {e}', 'error')
        return render_template('donations/catalog.html', 
                             medications=[],
                             categories=[],
                             search='',
                             selected_category='')


@bp.route('/marketplace')
def marketplace():
    """Donation marketplace page"""
    return render_template('donations/marketplace.html')
