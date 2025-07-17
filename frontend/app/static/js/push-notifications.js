/**
 * Push Notifications Manager for Ytili Platform
 * Handles browser push notifications for mobile and desktop
 */

class PushNotificationManager {
    constructor() {
        this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
        this.registration = null;
        this.subscription = null;
        this.vapidPublicKey = null; // Will be fetched from server
        
        this.init();
    }
    
    async init() {
        if (!this.isSupported) {
            console.warn('Push notifications are not supported in this browser');
            return;
        }
        
        try {
            // Register service worker
            await this.registerServiceWorker();
            
            // Get VAPID public key from server
            await this.getVapidKey();
            
            // Check existing subscription
            await this.checkExistingSubscription();
            
        } catch (error) {
            console.error('Failed to initialize push notifications:', error);
        }
    }
    
    async registerServiceWorker() {
        try {
            this.registration = await navigator.serviceWorker.register('/static/js/sw.js', {
                scope: '/'
            });
            
            console.log('Service Worker registered successfully');
            
            // Listen for service worker updates
            this.registration.addEventListener('updatefound', () => {
                console.log('Service Worker update found');
            });
            
        } catch (error) {
            console.error('Service Worker registration failed:', error);
            throw error;
        }
    }
    
    async getVapidKey() {
        try {
            const response = await fetch('/api/push-notifications/vapid-key');
            if (response.ok) {
                const data = await response.json();
                this.vapidPublicKey = data.vapid_public_key;
            } else {
                // Use a default key for development
                this.vapidPublicKey = 'BEl62iUYgUivxIkv69yViEuiBIa40HI80NM9f8HtLlVLVWjOVpJvQFhHBFhHUfYKzHcy_j-oUMwUIoBmeKHWHfU';
            }
        } catch (error) {
            console.error('Failed to get VAPID key:', error);
            // Use default key as fallback
            this.vapidPublicKey = 'BEl62iUYgUivxIkv69yViEuiBIa40HI80NM9f8HtLlVLVWjOVpJvQFhHBFhHUfYKzHcy_j-oUMwUIoBmeKHWHfU';
        }
    }
    
    async checkExistingSubscription() {
        try {
            this.subscription = await this.registration.pushManager.getSubscription();
            
            if (this.subscription) {
                console.log('Existing push subscription found');
                // Verify subscription with server
                await this.verifySubscription();
            }
            
        } catch (error) {
            console.error('Failed to check existing subscription:', error);
        }
    }
    
    async requestPermission() {
        if (!this.isSupported) {
            throw new Error('Push notifications are not supported');
        }
        
        const permission = await Notification.requestPermission();
        
        if (permission === 'granted') {
            console.log('Push notification permission granted');
            return true;
        } else if (permission === 'denied') {
            console.log('Push notification permission denied');
            return false;
        } else {
            console.log('Push notification permission dismissed');
            return false;
        }
    }
    
    async subscribe() {
        try {
            if (!this.registration) {
                throw new Error('Service Worker not registered');
            }
            
            if (!this.vapidPublicKey) {
                throw new Error('VAPID public key not available');
            }
            
            // Request permission first
            const hasPermission = await this.requestPermission();
            if (!hasPermission) {
                throw new Error('Push notification permission not granted');
            }
            
            // Create subscription
            this.subscription = await this.registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: this.urlBase64ToUint8Array(this.vapidPublicKey)
            });
            
            console.log('Push subscription created successfully');
            
            // Send subscription to server
            await this.sendSubscriptionToServer();
            
            return this.subscription;
            
        } catch (error) {
            console.error('Failed to subscribe to push notifications:', error);
            throw error;
        }
    }
    
    async unsubscribe() {
        try {
            if (!this.subscription) {
                console.log('No active subscription to unsubscribe');
                return true;
            }
            
            // Unsubscribe from browser
            const success = await this.subscription.unsubscribe();
            
            if (success) {
                console.log('Successfully unsubscribed from push notifications');
                
                // Remove subscription from server
                await this.removeSubscriptionFromServer();
                
                this.subscription = null;
                return true;
            }
            
            return false;
            
        } catch (error) {
            console.error('Failed to unsubscribe from push notifications:', error);
            return false;
        }
    }
    
    async sendSubscriptionToServer() {
        try {
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            if (!token) {
                console.warn('No auth token available for push subscription');
                return;
            }
            
            const response = await fetch('/api/push-notifications/subscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    subscription: this.subscription.toJSON(),
                    user_agent: navigator.userAgent,
                    device_type: this.getDeviceType()
                })
            });
            
            if (response.ok) {
                console.log('Push subscription sent to server successfully');
            } else {
                console.error('Failed to send push subscription to server');
            }
            
        } catch (error) {
            console.error('Error sending subscription to server:', error);
        }
    }
    
    async removeSubscriptionFromServer() {
        try {
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            if (!token) {
                return;
            }
            
            const response = await fetch('/api/push-notifications/unsubscribe', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    endpoint: this.subscription.endpoint
                })
            });
            
            if (response.ok) {
                console.log('Push subscription removed from server successfully');
            }
            
        } catch (error) {
            console.error('Error removing subscription from server:', error);
        }
    }
    
    async verifySubscription() {
        try {
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            if (!token) {
                return;
            }
            
            const response = await fetch('/api/push-notifications/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    endpoint: this.subscription.endpoint
                })
            });
            
            if (!response.ok) {
                console.log('Subscription not valid on server, re-subscribing...');
                await this.sendSubscriptionToServer();
            }
            
        } catch (error) {
            console.error('Error verifying subscription:', error);
        }
    }
    
    async testNotification() {
        try {
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
            
            if (!token) {
                throw new Error('Authentication required');
            }
            
            const response = await fetch('/api/push-notifications/test', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (response.ok) {
                console.log('Test notification sent');
                return true;
            } else {
                console.error('Failed to send test notification');
                return false;
            }
            
        } catch (error) {
            console.error('Error sending test notification:', error);
            return false;
        }
    }
    
    // Utility methods
    urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/-/g, '+')
            .replace(/_/g, '/');
        
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        
        return outputArray;
    }
    
    getDeviceType() {
        const userAgent = navigator.userAgent.toLowerCase();
        
        if (/mobile|android|iphone|ipad|phone/i.test(userAgent)) {
            return 'mobile';
        } else if (/tablet|ipad/i.test(userAgent)) {
            return 'tablet';
        } else {
            return 'desktop';
        }
    }
    
    isSubscribed() {
        return this.subscription !== null;
    }
    
    getPermissionStatus() {
        if (!this.isSupported) {
            return 'not-supported';
        }
        
        return Notification.permission;
    }
    
    // Public API methods
    async enableNotifications() {
        try {
            await this.subscribe();
            return true;
        } catch (error) {
            console.error('Failed to enable notifications:', error);
            return false;
        }
    }
    
    async disableNotifications() {
        try {
            await this.unsubscribe();
            return true;
        } catch (error) {
            console.error('Failed to disable notifications:', error);
            return false;
        }
    }
    
    showLocalNotification(title, options = {}) {
        if (!this.isSupported || Notification.permission !== 'granted') {
            console.warn('Cannot show notification: permission not granted');
            return;
        }
        
        const defaultOptions = {
            icon: '/static/images/icon-192x192.png',
            badge: '/static/images/badge-72x72.png',
            tag: 'ytili-notification',
            renotify: true,
            requireInteraction: false,
            ...options
        };
        
        return new Notification(title, defaultOptions);
    }
}

// Global push notification manager
let pushManager = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Only initialize if user is logged in
    const hasToken = localStorage.getItem('access_token') || sessionStorage.getItem('access_token');
    
    if (hasToken) {
        pushManager = new PushNotificationManager();
        
        // Make it globally available
        window.pushManager = pushManager;
        
        // Auto-subscribe if user previously agreed
        const autoSubscribe = localStorage.getItem('ytili_push_enabled');
        if (autoSubscribe === 'true') {
            setTimeout(() => {
                pushManager.enableNotifications().catch(console.error);
            }, 2000);
        }
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PushNotificationManager;
}
