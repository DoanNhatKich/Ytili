/**
 * Mobile-First JavaScript for Ytili Platform
 * Handles touch interactions, responsive behaviors, and mobile-specific features
 */

class YtiliMobile {
    constructor() {
        this.init();
        this.bindEvents();
        this.setupTouchHandlers();
        this.optimizeForMobile();
    }

    init() {
        // Detect mobile device
        this.isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
        this.isTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0;
        
        // Set viewport for mobile
        this.setViewport();
        
        // Initialize mobile-specific features
        this.initMobileFeatures();
    }

    setViewport() {
        // Ensure proper viewport for mobile
        let viewport = document.querySelector('meta[name="viewport"]');
        if (!viewport) {
            viewport = document.createElement('meta');
            viewport.name = 'viewport';
            document.head.appendChild(viewport);
        }
        viewport.content = 'width=device-width, initial-scale=1.0, maximum-scale=5.0, user-scalable=yes';
    }

    initMobileFeatures() {
        // Add mobile class to body
        if (this.isMobile) {
            document.body.classList.add('mobile-device');
        }
        
        if (this.isTouch) {
            document.body.classList.add('touch-device');
        }

        // Initialize smooth scrolling for mobile
        this.initSmoothScroll();
        
        // Initialize mobile navigation
        this.initMobileNav();
        
        // Initialize touch feedback
        this.initTouchFeedback();
    }

    bindEvents() {
        // Handle orientation change
        window.addEventListener('orientationchange', () => {
            setTimeout(() => {
                this.handleOrientationChange();
            }, 100);
        });

        // Handle resize for responsive adjustments
        window.addEventListener('resize', this.debounce(() => {
            this.handleResize();
        }, 250));

        // Handle scroll for mobile optimizations
        window.addEventListener('scroll', this.throttle(() => {
            this.handleScroll();
        }, 16));

        // Handle form focus for mobile keyboards
        this.handleMobileFormFocus();
    }

    setupTouchHandlers() {
        // Add touch handlers for better mobile interaction
        document.addEventListener('touchstart', (e) => {
            this.handleTouchStart(e);
        }, { passive: true });

        document.addEventListener('touchend', (e) => {
            this.handleTouchEnd(e);
        }, { passive: true });

        // Prevent double-tap zoom on buttons
        document.addEventListener('touchend', (e) => {
            if (e.target.matches('.btn, .nav-link, .card')) {
                e.preventDefault();
                e.target.click();
            }
        });
    }

    initSmoothScroll() {
        // Smooth scroll for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', (e) => {
                e.preventDefault();
                const href = anchor.getAttribute('href');
                
                // Validate selector before using it
                if (href && href.length > 1 && href !== '#') {
                    try {
                        const target = document.querySelector(href);
                        if (target) {
                            target.scrollIntoView({
                                behavior: 'smooth',
                                block: 'start'
                            });
                        }
                    } catch (error) {
                        console.warn('Invalid selector:', href, error);
                    }
                } else {
                    // Handle empty hash - scroll to top
                    window.scrollTo({
                        top: 0,
                        behavior: 'smooth'
                    });
                }
            });
        });
    }

    initMobileNav() {
        const navToggler = document.querySelector('.navbar-toggler');
        const navCollapse = document.querySelector('.navbar-collapse');
        
        if (navToggler && navCollapse) {
            // Close mobile nav when clicking outside
            document.addEventListener('click', (e) => {
                if (!navToggler.contains(e.target) && !navCollapse.contains(e.target)) {
                    if (navCollapse.classList.contains('show')) {
                        navToggler.click();
                    }
                }
            });

            // Close mobile nav when clicking on nav links
            navCollapse.querySelectorAll('.nav-link').forEach(link => {
                link.addEventListener('click', () => {
                    if (navCollapse.classList.contains('show')) {
                        navToggler.click();
                    }
                });
            });
        }
    }

    initTouchFeedback() {
        // Add visual feedback for touch interactions
        document.querySelectorAll('.btn, .card, .nav-link').forEach(element => {
            element.addEventListener('touchstart', () => {
                element.classList.add('touch-active');
            }, { passive: true });

            element.addEventListener('touchend', () => {
                setTimeout(() => {
                    element.classList.remove('touch-active');
                }, 150);
            }, { passive: true });
        });
    }

    handleTouchStart(e) {
        // Store touch start position for swipe detection
        this.touchStartX = e.touches[0].clientX;
        this.touchStartY = e.touches[0].clientY;
    }

    handleTouchEnd(e) {
        if (!this.touchStartX || !this.touchStartY) return;

        const touchEndX = e.changedTouches[0].clientX;
        const touchEndY = e.changedTouches[0].clientY;
        
        const deltaX = this.touchStartX - touchEndX;
        const deltaY = this.touchStartY - touchEndY;

        // Detect swipe gestures
        if (Math.abs(deltaX) > Math.abs(deltaY)) {
            if (Math.abs(deltaX) > 50) {
                if (deltaX > 0) {
                    this.handleSwipeLeft();
                } else {
                    this.handleSwipeRight();
                }
            }
        }

        this.touchStartX = null;
        this.touchStartY = null;
    }

    handleSwipeLeft() {
        // Handle left swipe (could be used for navigation)
        console.log('Swipe left detected');
    }

    handleSwipeRight() {
        // Handle right swipe (could be used for navigation)
        console.log('Swipe right detected');
    }

    handleOrientationChange() {
        // Adjust layout for orientation change
        const isLandscape = window.orientation === 90 || window.orientation === -90;
        
        if (isLandscape) {
            document.body.classList.add('landscape');
            document.body.classList.remove('portrait');
        } else {
            document.body.classList.add('portrait');
            document.body.classList.remove('landscape');
        }

        // Force repaint to fix iOS orientation bugs
        document.body.style.height = '100.1%';
        setTimeout(() => {
            document.body.style.height = '100%';
        }, 500);
    }

    handleResize() {
        // Handle responsive adjustments
        const width = window.innerWidth;
        
        // Update mobile classes based on screen size
        if (width < 768) {
            document.body.classList.add('mobile-screen');
            document.body.classList.remove('tablet-screen', 'desktop-screen');
        } else if (width < 992) {
            document.body.classList.add('tablet-screen');
            document.body.classList.remove('mobile-screen', 'desktop-screen');
        } else {
            document.body.classList.add('desktop-screen');
            document.body.classList.remove('mobile-screen', 'tablet-screen');
        }
    }

    handleScroll() {
        // Handle scroll-based optimizations
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        
        // Add scrolled class for styling
        if (scrollTop > 50) {
            document.body.classList.add('scrolled');
        } else {
            document.body.classList.remove('scrolled');
        }
    }

    handleMobileFormFocus() {
        // Handle mobile keyboard appearance
        const inputs = document.querySelectorAll('input, textarea, select');
        
        inputs.forEach(input => {
            input.addEventListener('focus', () => {
                // Scroll input into view on mobile
                if (this.isMobile) {
                    setTimeout(() => {
                        input.scrollIntoView({
                            behavior: 'smooth',
                            block: 'center'
                        });
                    }, 300);
                }
            });

            input.addEventListener('blur', () => {
                // Reset viewport on mobile keyboard close
                if (this.isMobile) {
                    window.scrollTo(0, 0);
                }
            });
        });
    }

    optimizeForMobile() {
        // Optimize images for mobile
        this.optimizeImages();
        
        // Optimize animations for mobile
        this.optimizeAnimations();
        
        // Add loading states
        this.addLoadingStates();
    }

    optimizeImages() {
        // Lazy load images on mobile
        const images = document.querySelectorAll('img[data-src]');
        
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        }
    }

    optimizeAnimations() {
        // Reduce animations on mobile for better performance
        if (this.isMobile) {
            const style = document.createElement('style');
            style.textContent = `
                @media (max-width: 767px) {
                    *, *::before, *::after {
                        animation-duration: 0.3s !important;
                        animation-delay: 0s !important;
                        transition-duration: 0.3s !important;
                        transition-delay: 0s !important;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }

    addLoadingStates() {
        // Add loading states for buttons and forms
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    submitBtn.classList.add('loading');
                    submitBtn.disabled = true;
                }
            });
        });
    }

    // Utility functions
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    }
}

// Initialize mobile functionality when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new YtiliMobile();
});

// Add CSS for touch feedback
const touchStyles = document.createElement('style');
touchStyles.textContent = `
    .touch-active {
        opacity: 0.7;
        transform: scale(0.98);
        transition: all 0.1s ease;
    }
    
    .loading {
        position: relative;
        pointer-events: none;
    }
    
    .loading::after {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 16px;
        height: 16px;
        margin: -8px 0 0 -8px;
        border: 2px solid transparent;
        border-top: 2px solid currentColor;
        border-radius: 50%;
        animation: spin 1s linear infinite;
    }
`;
document.head.appendChild(touchStyles);
