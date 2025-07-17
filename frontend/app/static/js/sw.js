/**
 * Service Worker for Ytili Platform
 * Handles push notifications, caching, and offline functionality
 */

const CACHE_NAME = 'ytili-v1';
const STATIC_CACHE_URLS = [
    '/',
    '/static/css/mobile.css',
    '/static/css/main.css',
    '/static/js/mobile.js',
    '/static/js/websocket.js',
    '/static/js/push-notifications.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css'
];

// Install event - cache static resources
self.addEventListener('install', (event) => {
    console.log('Service Worker installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('Caching static resources');
                return cache.addAll(STATIC_CACHE_URLS);
            })
            .catch((error) => {
                console.error('Failed to cache static resources:', error);
            })
    );
    
    // Skip waiting to activate immediately
    self.skipWaiting();
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('Service Worker activating...');
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
    );
    
    // Claim all clients immediately
    self.clients.claim();
});

// Fetch event - serve from cache with network fallback
self.addEventListener('fetch', (event) => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') {
        return;
    }
    
    // Skip WebSocket and API requests
    if (event.request.url.includes('/ws/') || event.request.url.includes('/api/')) {
        return;
    }
    
    event.respondWith(
        caches.match(event.request)
            .then((response) => {
                // Return cached version if available
                if (response) {
                    return response;
                }
                
                // Otherwise fetch from network
                return fetch(event.request)
                    .then((response) => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }
                        
                        // Clone the response for caching
                        const responseToCache = response.clone();
                        
                        caches.open(CACHE_NAME)
                            .then((cache) => {
                                cache.put(event.request, responseToCache);
                            });
                        
                        return response;
                    })
                    .catch(() => {
                        // Return offline page for navigation requests
                        if (event.request.mode === 'navigate') {
                            return caches.match('/offline.html');
                        }
                    });
            })
    );
});

// Push event - handle push notifications
self.addEventListener('push', (event) => {
    console.log('Push notification received');
    
    let notificationData = {
        title: 'Ytili Notification',
        body: 'You have a new update',
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        tag: 'ytili-notification',
        data: {}
    };
    
    // Parse push data if available
    if (event.data) {
        try {
            const pushData = event.data.json();
            notificationData = {
                ...notificationData,
                ...pushData
            };
        } catch (error) {
            console.error('Failed to parse push data:', error);
            notificationData.body = event.data.text() || notificationData.body;
        }
    }
    
    // Customize notification based on type
    if (notificationData.type) {
        switch (notificationData.type) {
            case 'donation_update':
                notificationData.title = 'Donation Update';
                notificationData.body = `Your donation status: ${notificationData.status}`;
                notificationData.icon = '/static/images/donation-icon.png';
                notificationData.actions = [
                    {
                        action: 'view',
                        title: 'View Details',
                        icon: '/static/images/view-icon.png'
                    }
                ];
                break;
                
            case 'payment_update':
                if (notificationData.status === 'paid') {
                    notificationData.title = 'Payment Successful!';
                    notificationData.body = 'Your donation payment has been confirmed';
                    notificationData.icon = '/static/images/success-icon.png';
                } else if (notificationData.status === 'expired') {
                    notificationData.title = 'Payment Expired';
                    notificationData.body = 'Your payment session has expired';
                    notificationData.icon = '/static/images/warning-icon.png';
                }
                break;
                
            case 'donation_matched':
                notificationData.title = 'Donation Matched!';
                notificationData.body = `Your donation has been matched with ${notificationData.hospital_name}`;
                notificationData.icon = '/static/images/match-icon.png';
                notificationData.actions = [
                    {
                        action: 'track',
                        title: 'Track Progress',
                        icon: '/static/images/track-icon.png'
                    }
                ];
                break;
                
            case 'emergency_alert':
                notificationData.title = 'Emergency Alert';
                notificationData.requireInteraction = true;
                notificationData.icon = '/static/images/emergency-icon.png';
                notificationData.vibrate = [200, 100, 200, 100, 200];
                break;
                
            case 'points_update':
                notificationData.title = 'Points Earned!';
                notificationData.body = `You earned ${notificationData.points_earned} points!`;
                notificationData.icon = '/static/images/points-icon.png';
                break;
        }
    }
    
    // Show notification
    event.waitUntil(
        self.registration.showNotification(notificationData.title, {
            body: notificationData.body,
            icon: notificationData.icon,
            badge: notificationData.badge,
            tag: notificationData.tag,
            data: notificationData.data,
            actions: notificationData.actions,
            requireInteraction: notificationData.requireInteraction || false,
            vibrate: notificationData.vibrate,
            renotify: true,
            timestamp: Date.now()
        })
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('Notification clicked:', event.notification.tag);
    
    event.notification.close();
    
    const notificationData = event.notification.data || {};
    let targetUrl = '/';
    
    // Determine target URL based on notification type and action
    if (event.action) {
        switch (event.action) {
            case 'view':
                if (notificationData.donation_id) {
                    targetUrl = `/donations/${notificationData.donation_id}`;
                }
                break;
                
            case 'track':
                targetUrl = '/donations/live-tracking';
                break;
                
            default:
                targetUrl = '/';
        }
    } else {
        // Default click behavior based on notification type
        switch (notificationData.type) {
            case 'donation_update':
            case 'donation_matched':
                if (notificationData.donation_id) {
                    targetUrl = `/donations/${notificationData.donation_id}`;
                } else {
                    targetUrl = '/donations/live-tracking';
                }
                break;
                
            case 'payment_update':
                if (notificationData.status === 'paid') {
                    targetUrl = '/payments/success';
                } else {
                    targetUrl = '/payments/';
                }
                break;
                
            case 'points_update':
                targetUrl = '/profile/points';
                break;
                
            case 'emergency_alert':
                targetUrl = '/emergency';
                break;
                
            default:
                targetUrl = '/';
        }
    }
    
    // Open or focus the target page
    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Check if target URL is already open
                for (const client of clientList) {
                    if (client.url.includes(targetUrl) && 'focus' in client) {
                        return client.focus();
                    }
                }
                
                // Open new window/tab
                if (clients.openWindow) {
                    return clients.openWindow(targetUrl);
                }
            })
    );
});

// Background sync event (for offline actions)
self.addEventListener('sync', (event) => {
    console.log('Background sync triggered:', event.tag);
    
    if (event.tag === 'background-sync') {
        event.waitUntil(
            // Perform background sync operations
            syncOfflineActions()
        );
    }
});

// Message event - handle messages from main thread
self.addEventListener('message', (event) => {
    console.log('Service Worker received message:', event.data);
    
    if (event.data && event.data.type) {
        switch (event.data.type) {
            case 'SKIP_WAITING':
                self.skipWaiting();
                break;
                
            case 'GET_VERSION':
                event.ports[0].postMessage({ version: CACHE_NAME });
                break;
                
            case 'CACHE_URLS':
                event.waitUntil(
                    caches.open(CACHE_NAME)
                        .then((cache) => {
                            return cache.addAll(event.data.urls);
                        })
                );
                break;
        }
    }
});

// Helper functions
async function syncOfflineActions() {
    try {
        // Get offline actions from IndexedDB or localStorage
        // This would sync any actions that were queued while offline
        console.log('Syncing offline actions...');
        
        // Example: sync offline donations, payments, etc.
        // Implementation would depend on specific offline functionality needed
        
    } catch (error) {
        console.error('Failed to sync offline actions:', error);
    }
}

// Periodic background sync (if supported)
if ('periodicSync' in self.registration) {
    self.addEventListener('periodicsync', (event) => {
        if (event.tag === 'content-sync') {
            event.waitUntil(
                // Perform periodic sync operations
                syncOfflineActions()
            );
        }
    });
}

console.log('Service Worker loaded successfully');
