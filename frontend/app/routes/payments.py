"""
Payment routes for Ytili frontend
Handles mobile-optimized payment flows
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from ..utils.api import APIClient
import httpx

bp = Blueprint('payments', __name__, url_prefix='/payments')


@bp.route('/vietqr/<donation_id>')
async def vietqr_mobile(donation_id):
    """Mobile-optimized VietQR payment page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    
    api_client = APIClient()
    
    try:
        # Get donation details
        donation = await api_client.get(f'/donations/{donation_id}')
        
        if not donation:
            flash('Donation not found', 'error')
            return redirect(url_for('donations.index'))
        
        # Calculate amount (could be from form or donation data)
        amount = request.args.get('amount', donation.get('amount', 0))
        description = f"Donation for {donation.get('medication_name', 'Medical Supplies')}"
        
        return render_template('payments/mobile_vietqr.html',
                             donation_id=donation_id,
                             donation=donation,
                             amount=amount,
                             description=description,
                             payment_reference=f"YTILI_{donation_id}",
                             user=user)
    
    except httpx.HTTPStatusError as e:
        flash(f'Error loading donation: {e}', 'error')
        return redirect(url_for('donations.index'))


@bp.route('/success')
async def payment_success():
    """Payment success page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    
    return render_template('payments/success.html', user=user)


@bp.route('/cancel')
async def payment_cancel():
    """Payment cancellation page"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    
    return render_template('payments/cancel.html', user=user)


@bp.route('/api/create-qr', methods=['POST'])
async def create_qr_api():
    """API endpoint to create VietQR payment (mobile-optimized)"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Invalid request data'}), 400
        
        # Validate required fields
        required_fields = ['donation_id', 'amount', 'description']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        api_client = APIClient()
        
        # Create VietQR payment via backend API
        payment_data = {
            'donation_id': data['donation_id'],
            'amount': float(data['amount']),
            'description': data['description'],
            'expires_in_minutes': data.get('expires_in_minutes', 30)
        }
        
        result = await api_client.post('/vietqr-payments/create-qr', payment_data)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except httpx.HTTPStatusError as e:
        return jsonify({
            'success': False,
            'error': f'Payment creation failed: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500


@bp.route('/api/status/<payment_reference>')
async def check_payment_status(payment_reference):
    """Check payment status (mobile-optimized)"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        api_client = APIClient()
        
        # Check payment status via backend API
        result = await api_client.get(f'/vietqr-payments/status/{payment_reference}')
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except httpx.HTTPStatusError as e:
        return jsonify({
            'success': False,
            'error': f'Status check failed: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500


@bp.route('/api/verify', methods=['POST'])
async def verify_payment_api():
    """Verify payment completion (mobile-optimized)"""
    user = session.get('user')
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        
        if not data or 'payment_reference' not in data:
            return jsonify({'error': 'Payment reference required'}), 400
        
        api_client = APIClient()
        
        # Verify payment via backend API
        verification_data = {
            'payment_reference': data['payment_reference'],
            'bank_transaction_id': data.get('bank_transaction_id')
        }
        
        result = await api_client.post('/vietqr-payments/verify', verification_data)
        
        return jsonify({
            'success': True,
            'data': result
        })
    
    except httpx.HTTPStatusError as e:
        return jsonify({
            'success': False,
            'error': f'Payment verification failed: {e}'
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }), 500


@bp.route('/donate/<donation_id>')
async def donate_form(donation_id):
    """Mobile-optimized donation form with payment options"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    
    api_client = APIClient()
    
    try:
        # Get donation details
        donation = await api_client.get(f'/donations/{donation_id}')
        
        if not donation:
            flash('Donation not found', 'error')
            return redirect(url_for('donations.index'))
        
        return render_template('payments/donate_form.html',
                             donation_id=donation_id,
                             donation=donation,
                             user=user)
    
    except httpx.HTTPStatusError as e:
        flash(f'Error loading donation: {e}', 'error')
        return redirect(url_for('donations.index'))


@bp.route('/donate/<donation_id>', methods=['POST'])
async def process_donation(donation_id):
    """Process donation form submission"""
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    
    try:
        amount = request.form.get('amount')
        payment_method = request.form.get('payment_method', 'vietqr')
        
        if not amount:
            flash('Amount is required', 'error')
            return redirect(url_for('payments.donate_form', donation_id=donation_id))
        
        # Validate amount
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError("Amount must be positive")
        except ValueError:
            flash('Invalid amount', 'error')
            return redirect(url_for('payments.donate_form', donation_id=donation_id))
        
        # Redirect to appropriate payment method
        if payment_method == 'vietqr':
            return redirect(url_for('payments.vietqr_mobile', 
                                  donation_id=donation_id, 
                                  amount=amount))
        else:
            flash('Payment method not supported yet', 'error')
            return redirect(url_for('payments.donate_form', donation_id=donation_id))
    
    except Exception as e:
        flash(f'Error processing donation: {str(e)}', 'error')
        return redirect(url_for('payments.donate_form', donation_id=donation_id))


# Mobile-specific utility functions
def is_mobile_request():
    """Check if request is from mobile device"""
    user_agent = request.headers.get('User-Agent', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)


def get_optimized_qr_size():
    """Get optimal QR code size based on device"""
    if is_mobile_request():
        return 250  # Smaller for mobile
    else:
        return 300  # Larger for desktop


@bp.context_processor
def inject_mobile_context():
    """Inject mobile-specific context into templates"""
    return {
        'is_mobile': is_mobile_request(),
        'qr_size': get_optimized_qr_size()
    }
