"""
Transparency routes for the frontend
"""
from flask import Blueprint, render_template, request, flash
import httpx

from ..utils.api import APIClient

bp = Blueprint('transparency', __name__, url_prefix='/transparency')


@bp.route('/')
async def dashboard():
    """Public transparency dashboard"""
    api_client = APIClient()
    
    try:
        # Get public transparency data
        transparency_data = await api_client.get('/transparency/public')
        
        # Get transparency statistics
        stats = await api_client.get('/transparency/stats')
        
        return render_template('transparency/dashboard.html',
                             transparency_data=transparency_data,
                             stats=stats)
    
    except httpx.HTTPStatusError as e:
        flash(f'Error loading transparency data: {e}', 'error')
        return render_template('transparency/dashboard.html',
                             transparency_data={'donations': [], 'statistics': {}, 'platform_integrity': 0},
                             stats={})


@bp.route('/donation/<string:donation_id>')
async def donation_detail(donation_id):
    """Donation transparency detail page"""
    api_client = APIClient()
    
    try:
        # Get donation transaction chain
        chain = await api_client.get(f'/transparency/donation/{donation_id}/chain')
        
        # Get chain integrity verification
        integrity = await api_client.get(f'/transparency/donation/{donation_id}/verify')
        
        return render_template('transparency/donation_detail.html',
                             donation_id=donation_id,
                             chain=chain,
                             integrity=integrity)
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            flash('Donation not found', 'error')
        elif e.response.status_code == 403:
            flash('Access denied - you can only view your own donations', 'error')
        else:
            flash(f'Error loading donation details: {e}', 'error')
        
        return render_template('transparency/donation_detail.html',
                             donation_id=donation_id,
                             chain=[],
                             integrity={'valid': False, 'message': 'Error loading data'})


@bp.route('/search')
async def search():
    """Transaction search page (admin only)"""
    from flask import session
    
    user = session.get('user')
    if not user or user.get('user_type') != 'government':
        flash('Admin access required', 'error')
        return render_template('transparency/search.html', transactions=[], user=user)
    
    api_client = APIClient()
    
    # Get search parameters
    donation_id = request.args.get('donation_id')
    transaction_type = request.args.get('transaction_type')
    actor_type = request.args.get('actor_type')
    
    transactions = []
    
    if any([donation_id, transaction_type, actor_type]):
        try:
            # Build search parameters
            params = {}
            if donation_id:
                params['donation_id'] = donation_id
            if transaction_type:
                params['transaction_type'] = transaction_type
            if actor_type:
                params['actor_type'] = actor_type
            
            # Search transactions
            search_result = await api_client.get('/transparency/search', params)
            transactions = search_result.get('transactions', [])
            
        except httpx.HTTPStatusError as e:
            flash(f'Search failed: {e}', 'error')
    
    return render_template('transparency/search.html',
                         transactions=transactions,
                         search_params={
                             'donation_id': donation_id,
                             'transaction_type': transaction_type,
                             'actor_type': actor_type
                         },
                         user=user)
