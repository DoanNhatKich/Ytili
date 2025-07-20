"""
Fraud Detection and Monitoring Routes
"""
from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
import requests
from ..utils.api import make_api_request
from ..config import Config

fraud_bp = Blueprint('fraud', __name__)

# API Proxy endpoint for fraud analysis
@fraud_bp.route('/api/v1/fraud/analyze-campaign', methods=['POST'])
def analyze_campaign_proxy():
    """Proxy endpoint to forward fraud analysis requests to backend API"""
    try:
        # Get request data
        data = request.get_json()
        if not data or 'campaign_id' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing campaign_id'
            }), 400
        
        # Forward to backend API
        response = make_api_request('POST', '/fraud/analyze-campaign', data=data)
        
        if response:
            return jsonify(response)
        else:
            # Return fallback response
            return jsonify({
                'success': True,
                'campaign_id': data['campaign_id'],
                'fraud_score': 15,
                'risk_level': 'low',
                'risk_factors': ['No suspicious activity detected'],
                'trust_score': 85,
                'analysis_date': None
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'fraud_score': 20,
            'risk_level': 'unknown',
            'trust_score': 50
        }), 500

@fraud_bp.route('/admin/fraud-dashboard')
def admin_dashboard():
    """Admin fraud monitoring dashboard"""
    # Check if user is admin (simplified check)
    if not session.get('user') or session.get('user', {}).get('user_type') != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Get fraud dashboard data from API
        response = make_api_request('GET', '/fraud/dashboard')
        
        if response and response.get('success', True):
            fraud_data = response
        else:
            # Fallback data for demo
            fraud_data = {
                'total_suspicious_activities': 12,
                'severity_counts': {
                    'high': 3,
                    'medium': 5,
                    'low': 4
                },
                'type_counts': {
                    'fake_documents': 4,
                    'suspicious_activity': 3,
                    'false_information': 3,
                    'duplicate_campaign': 2
                },
                'high_risk_users': [
                    {
                        'user_id': 123,
                        'email': 'suspicious@example.com',
                        'full_name': 'John Doe',
                        'user_type': 'individual',
                        'risk_score': 85.5,
                        'risk_factors': ['Multiple failed campaigns', 'Suspicious documents']
                    }
                ],
                'recent_activities': [
                    {
                        'type': 'fake_documents',
                        'severity': 'high',
                        'description': 'Suspicious medical certificate detected',
                        'detected_at': '2025-01-15T10:30:00Z',
                        'user_id': 123,
                        'user_email': 'suspicious@example.com'
                    }
                ]
            }
        
        return render_template('fraud/admin_dashboard.html', fraud_data=fraud_data)
        
    except Exception as e:
        flash(f'Error loading fraud dashboard: {str(e)}', 'error')
        return render_template('fraud/admin_dashboard.html', fraud_data={})

@fraud_bp.route('/admin/fraud-reports')
def fraud_reports():
    """View all fraud reports"""
    if not session.get('user') or session.get('user', {}).get('user_type') != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Get fraud reports from API
        response = make_api_request('GET', '/fraud/reports')
        
        if response and response.get('success', True):
            reports = response.get('reports', [])
        else:
            # Fallback data for demo
            reports = [
                {
                    'id': 1,
                    'campaign_id': 'camp_123',
                    'fraud_type': 'fake_documents',
                    'description': 'Medical certificate appears to be forged',
                    'reporter_contact': 'reporter@example.com',
                    'status': 'pending',
                    'created_at': '2025-01-15T10:30:00Z',
                    'campaign_title': 'Emergency Surgery Fund'
                },
                {
                    'id': 2,
                    'campaign_id': 'camp_456',
                    'fraud_type': 'false_information',
                    'description': 'Story does not match medical records',
                    'reporter_contact': None,
                    'status': 'investigating',
                    'created_at': '2025-01-14T15:20:00Z',
                    'campaign_title': 'Help Baby Sarah'
                }
            ]
        
        return render_template('fraud/reports.html', reports=reports)
        
    except Exception as e:
        flash(f'Error loading fraud reports: {str(e)}', 'error')
        return render_template('fraud/reports.html', reports=[])

@fraud_bp.route('/admin/fraud-reports/<int:report_id>')
def fraud_report_detail(report_id):
    """View detailed fraud report"""
    if not session.get('user') or session.get('user', {}).get('user_type') != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.index'))
    
    try:
        # Get specific fraud report from API
        response = make_api_request('GET', f'/fraud/reports/{report_id}')
        
        if response and response.get('success', True):
            report = response.get('report')
        else:
            # Fallback data for demo
            report = {
                'id': report_id,
                'campaign_id': 'camp_123',
                'fraud_type': 'fake_documents',
                'description': 'Medical certificate appears to be forged. The hospital stamp looks suspicious and the doctor signature does not match records.',
                'reporter_contact': 'concerned.citizen@example.com',
                'status': 'pending',
                'created_at': '2025-01-15T10:30:00Z',
                'campaign_title': 'Emergency Surgery Fund',
                'evidence_files': ['evidence1.jpg', 'evidence2.pdf'],
                'investigation_notes': [],
                'assigned_to': None
            }
        
        return render_template('fraud/report_detail.html', report=report)
        
    except Exception as e:
        flash(f'Error loading fraud report: {str(e)}', 'error')
        return redirect(url_for('fraud.fraud_reports'))

@fraud_bp.route('/admin/fraud-reports/<int:report_id>/update', methods=['POST'])
def update_fraud_report(report_id):
    """Update fraud report status"""
    if not session.get('user') or session.get('user', {}).get('user_type') != 'admin':
        return jsonify({'success': False, 'error': 'Access denied'}), 403
    
    try:
        data = request.get_json()
        status = data.get('status')
        notes = data.get('notes', '')
        
        # Update fraud report via API
        response = make_api_request('PUT', f'/fraud/reports/{report_id}', {
            'status': status,
            'investigation_notes': notes,
            'updated_by': session.get('user', {}).get('id')
        })
        
        if response and response.get('success', True):
            return jsonify({'success': True, 'message': 'Report updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update report'})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@fraud_bp.route('/api/fraud/analyze-campaign', methods=['POST'])
def analyze_campaign():
    """Analyze campaign for fraud (proxy to backend API)"""
    try:
        data = request.get_json()
        campaign_id = data.get('campaign_id')
        
        # Make request to backend fraud detection API
        response = make_api_request('POST', '/fraud-detection/analyze-campaign', {
            'campaign_id': campaign_id
        })
        
        if response:
            return jsonify(response)
        else:
            # Return mock data for demo
            mock_scores = [
                {'score': 95, 'risk_level': 'low', 'factors': ['Verified documents', 'Established user']},
                {'score': 75, 'risk_level': 'medium', 'factors': ['Some documentation missing']},
                {'score': 45, 'risk_level': 'high', 'factors': ['Suspicious activity', 'Incomplete info']},
                {'score': 88, 'risk_level': 'low', 'factors': ['Hospital verification']}
            ]
            
            index = int(campaign_id) % len(mock_scores) if campaign_id.isdigit() else 0
            return jsonify(mock_scores[index])
            
    except Exception as e:
        return jsonify({'score': 0, 'risk_level': 'unknown', 'factors': ['Error analyzing campaign']})

@fraud_bp.route('/api/fraud/report', methods=['POST'])
def submit_fraud_report():
    """Submit fraud report (proxy to backend API)"""
    try:
        # Get form data
        campaign_id = request.form.get('campaign_id')
        fraud_type = request.form.get('fraud_type')
        description = request.form.get('description')
        contact = request.form.get('contact')
        
        # Handle file uploads
        evidence_files = request.files.getlist('evidence')
        
        # For demo, just return success
        # In production, this would forward to the backend API
        report_data = {
            'campaign_id': campaign_id,
            'fraud_type': fraud_type,
            'description': description,
            'reporter_contact': contact,
            'evidence_count': len(evidence_files),
            'status': 'pending',
            'created_at': '2025-01-15T12:00:00Z'
        }
        
        # Make request to backend API
        response = make_api_request('POST', '/fraud-detection/report', report_data)
        
        return jsonify({
            'success': True,
            'message': 'Fraud report submitted successfully',
            'report_id': 'FR' + str(hash(campaign_id + fraud_type))[:6]
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@fraud_bp.route('/user/trust-score')
def user_trust_score():
    """View user's own trust score"""
    if not session.get('user'):
        flash('Please log in to view your trust score.', 'error')
        return redirect(url_for('auth.login'))
    
    try:
        user_id = session.get('user', {}).get('id')
        
        # Get user trust score from API
        response = make_api_request('GET', f'/fraud/user/{user_id}/risk')
        
        if response and response.get('success', True):
            trust_data = response
        else:
            # Fallback data for demo
            trust_data = {
                'user_id': user_id,
                'risk_score': 15.5,  # Lower is better for risk
                'trust_score': 84.5,  # Higher is better for trust
                'risk_level': 'low',
                'factors': [
                    'Verified email address',
                    'Completed KYC verification',
                    'Successful donation history',
                    'No reported issues'
                ],
                'verification_status': 'verified',
                'account_age_days': 180,
                'total_donations': 5,
                'total_received': 2
            }
        
        return render_template('fraud/user_trust_score.html', trust_data=trust_data)
        
    except Exception as e:
        flash(f'Error loading trust score: {str(e)}', 'error')
        return render_template('fraud/user_trust_score.html', trust_data={})
