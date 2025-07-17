/**
 * WebSocket Client for Real-time Notifications
 * Handles real-time communication with Ytili backend
 */

class YtiliWebSocket {
    constructor(options = {}) {
        this.options = {
            autoReconnect: true,
            reconnectInterval: 5000,
            maxReconnectAttempts: 10,
            heartbeatInterval: 30000,
            ...options
        };
        
        this.ws = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.heartbeatTimer = null;
        this.reconnectTimer = null;
        
        // Event handlers
        this.eventHandlers = {
            'connection_established': [],
            'donation_update': [],
            'payment_update': [],
            'donation_matched': [],
            'emergency_alert': [],
            'system_notification': [],
            'points_update': [],
            'error': [],
            'disconnect': [],
            'reconnect': []
        };
        
        this.init();
    }
    
    init() {
        this.connect();
        this.setupEventListeners();
    }
    
    connect() {
        try {
            // Get WebSocket URL
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.hostname;
            const port = window.location.hostname === 'localhost' ? ':8000' : '';
            
            // Get auth token if available
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            const tokenParam = token ? `?token=${encodeURIComponent(token)}` : '';
            
            const wsUrl = `${protocol}//${host}${port}/api/v1/ws/connect${tokenParam}`;
            
            console.log('Connecting to WebSocket:', wsUrl);
            
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = (event) => {
                console.log('WebSocket connected');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.startHeartbeat();
                this.trigger('connect', { event });
            };
            
            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.ws.onclose = (event) => {
                console.log('WebSocket disconnected:', event.code, event.reason);
                this.isConnected = false;
                this.stopHeartbeat();
                this.trigger('disconnect', { event });
                
                if (this.options.autoReconnect && this.reconnectAttempts < this.options.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }
            };
            
            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.trigger('error', { error });
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.trigger('error', { error });
        }
    }
    
    disconnect() {
        this.options.autoReconnect = false;
        this.stopHeartbeat();
        
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        
        this.isConnected = false;
    }
    
    scheduleReconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
        }
        
        this.reconnectAttempts++;
        const delay = this.options.reconnectInterval * Math.pow(1.5, this.reconnectAttempts - 1);
        
        console.log(`Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`);
        
        this.reconnectTimer = setTimeout(() => {
            console.log(`Reconnect attempt ${this.reconnectAttempts}`);
            this.connect();
            this.trigger('reconnect', { attempt: this.reconnectAttempts });
        }, delay);
    }
    
    startHeartbeat() {
        this.stopHeartbeat();
        
        this.heartbeatTimer = setInterval(() => {
            if (this.isConnected) {
                this.send({
                    type: 'ping',
                    timestamp: new Date().toISOString()
                });
            }
        }, this.options.heartbeatInterval);
    }
    
    stopHeartbeat() {
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
    }
    
    send(message) {
        if (this.isConnected && this.ws) {
            try {
                this.ws.send(JSON.stringify(message));
                return true;
            } catch (error) {
                console.error('Failed to send WebSocket message:', error);
                return false;
            }
        }
        return false;
    }
    
    handleMessage(message) {
        console.log('WebSocket message received:', message);
        
        const messageType = message.type;
        
        // Handle specific message types
        switch (messageType) {
            case 'connection_established':
                this.showNotification('Connected to real-time notifications', 'success');
                break;
                
            case 'donation_update':
                this.handleDonationUpdate(message);
                break;
                
            case 'payment_update':
                this.handlePaymentUpdate(message);
                break;
                
            case 'donation_matched':
                this.handleDonationMatched(message);
                break;
                
            case 'emergency_alert':
                this.handleEmergencyAlert(message);
                break;
                
            case 'system_notification':
                this.handleSystemNotification(message);
                break;
                
            case 'points_update':
                this.handlePointsUpdate(message);
                break;
                
            case 'pong':
                // Heartbeat response
                break;
                
            case 'error':
                console.error('WebSocket error message:', message.message);
                this.showNotification(message.message, 'error');
                break;
                
            default:
                console.log('Unknown message type:', messageType);
        }
        
        // Trigger event handlers
        this.trigger(messageType, message);
    }
    
    handleDonationUpdate(message) {
        const { donation_id, status, details } = message;
        
        this.showNotification(
            `Donation ${donation_id} status updated to: ${status}`,
            'info'
        );
        
        // Update UI elements
        this.updateDonationStatus(donation_id, status, details);
    }
    
    handlePaymentUpdate(message) {
        const { payment_reference, status, details } = message;
        
        if (status === 'paid') {
            this.showNotification('Payment successful!', 'success');
            
            // Redirect to success page if on payment page
            if (window.location.pathname.includes('/payments/')) {
                setTimeout(() => {
                    window.location.href = '/payments/success';
                }, 2000);
            }
        } else if (status === 'expired') {
            this.showNotification('Payment expired', 'warning');
        }
        
        // Update payment UI
        this.updatePaymentStatus(payment_reference, status, details);
    }
    
    handleDonationMatched(message) {
        const { donation_id, hospital_name } = message;
        
        this.showNotification(
            `Your donation has been matched with ${hospital_name}!`,
            'success'
        );
    }
    
    handleEmergencyAlert(message) {
        const { alert_type, message: alertMessage } = message;
        
        this.showNotification(alertMessage, 'error', true); // persistent
        
        // Show emergency modal if available
        this.showEmergencyModal(alert_type, alertMessage);
    }
    
    handleSystemNotification(message) {
        const { notification_type, message: notificationMessage } = message;
        
        this.showNotification(notificationMessage, notification_type);
    }
    
    handlePointsUpdate(message) {
        const { points_earned, total_points, reason } = message;
        
        this.showNotification(
            `You earned ${points_earned} points! Total: ${total_points}`,
            'success'
        );
        
        // Update points display
        this.updatePointsDisplay(total_points);
    }
    
    // Utility methods
    updateDonationStatus(donationId, status, details) {
        const statusElements = document.querySelectorAll(`[data-donation-id="${donationId}"] .donation-status`);
        statusElements.forEach(element => {
            element.textContent = status;
            element.className = `donation-status status-${status.toLowerCase()}`;
        });
    }
    
    updatePaymentStatus(paymentReference, status, details) {
        const statusElements = document.querySelectorAll(`[data-payment-reference="${paymentReference}"] .payment-status`);
        statusElements.forEach(element => {
            element.textContent = status;
            element.className = `payment-status status-${status.toLowerCase()}`;
        });
        
        // Update payment page specific elements
        const paymentStatusEl = document.getElementById('paymentStatus');
        if (paymentStatusEl) {
            if (status === 'paid') {
                paymentStatusEl.className = 'status-indicator status-success';
                paymentStatusEl.innerHTML = '<i class="fas fa-check-circle"></i><span>Payment successful!</span>';
            } else if (status === 'expired') {
                paymentStatusEl.className = 'status-indicator status-expired';
                paymentStatusEl.innerHTML = '<i class="fas fa-times-circle"></i><span>Payment expired</span>';
            }
        }
    }
    
    updatePointsDisplay(totalPoints) {
        const pointsElements = document.querySelectorAll('.user-points, .points-display');
        pointsElements.forEach(element => {
            element.textContent = totalPoints.toLocaleString();
        });
    }
    
    showNotification(message, type = 'info', persistent = false) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type} fade-in-mobile`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
                <button class="notification-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Add to notification container
        let container = document.getElementById('notification-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'notification-container';
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
        
        container.appendChild(notification);
        
        // Auto-remove after delay (unless persistent)
        if (!persistent) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.classList.add('fade-out');
                    setTimeout(() => {
                        notification.remove();
                    }, 300);
                }
            }, 5000);
        }
    }
    
    getNotificationIcon(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    }
    
    showEmergencyModal(alertType, message) {
        // Create emergency modal if it doesn't exist
        let modal = document.getElementById('emergency-modal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'emergency-modal';
            modal.className = 'modal emergency-modal';
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">
                        <h4><i class="fas fa-exclamation-triangle text-danger"></i> Emergency Alert</h4>
                    </div>
                    <div class="modal-body">
                        <p id="emergency-message"></p>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-primary" onclick="document.getElementById('emergency-modal').style.display='none'">
                            Understood
                        </button>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        document.getElementById('emergency-message').textContent = message;
        modal.style.display = 'block';
    }
    
    // Event system
    on(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].push(handler);
        }
    }
    
    off(event, handler) {
        if (this.eventHandlers[event]) {
            const index = this.eventHandlers[event].indexOf(handler);
            if (index > -1) {
                this.eventHandlers[event].splice(index, 1);
            }
        }
    }
    
    trigger(event, data) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    console.error('Event handler error:', error);
                }
            });
        }
    }
    
    // Public API methods
    subscribeToRoom(room) {
        return this.send({
            type: 'subscribe',
            room: room
        });
    }
    
    unsubscribeFromRoom(room) {
        return this.send({
            type: 'unsubscribe',
            room: room
        });
    }
    
    requestDonationStatus(donationId) {
        return this.send({
            type: 'donation_status_request',
            donation_id: donationId
        });
    }
    
    requestPaymentStatus(paymentReference) {
        return this.send({
            type: 'payment_status_request',
            payment_reference: paymentReference
        });
    }
    
    getStatus() {
        return this.send({
            type: 'get_status'
        });
    }
    
    setupEventListeners() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                // Page is hidden, reduce activity
                this.stopHeartbeat();
            } else {
                // Page is visible, resume activity
                if (this.isConnected) {
                    this.startHeartbeat();
                }
            }
        });
        
        // Handle page unload
        window.addEventListener('beforeunload', () => {
            this.disconnect();
        });
    }
}

// Global WebSocket instance
let ytiliWS = null;

// Initialize WebSocket when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if user is logged in
    const hasToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    
    if (hasToken) {
        ytiliWS = new YtiliWebSocket();
        
        // Make it globally available
        window.ytiliWS = ytiliWS;
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = YtiliWebSocket;
}
