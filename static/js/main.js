// ============================================
// MatatuBook Custom JavaScript
// ============================================

// Global Configuration
const CONFIG = {
    apiBaseUrl: '/api',
    csrfToken: document.querySelector('[name=csrfmiddlewaretoken]')?.value,
    toastDuration: 3000,
};

// ============================================
// Utility Functions
// ============================================

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `alert alert-${type} alert-dismissible fade show`;
    toast.role = 'alert';
    toast.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, CONFIG.toastDuration);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 9999; min-width: 300px;';
    document.body.appendChild(container);
    return container;
}

/**
 * Format currency
 */
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-KE', {
        style: 'currency',
        currency: 'KES',
        minimumFractionDigits: 0,
    }).format(amount);
}

/**
 * Format date
 */
function formatDate(dateString, format = 'long') {
    const date = new Date(dateString);
    const options = format === 'long' 
        ? { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }
        : { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

/**
 * Format time
 */
function formatTime(timeString) {
    const [hours, minutes] = timeString.split(':');
    const hour = parseInt(hours);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour % 12 || 12;
    return `${displayHour}:${minutes} ${ampm}`;
}

/**
 * AJAX Request Helper
 */
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': CONFIG.csrfToken,
        },
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, options);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Request Error:', error);
        throw error;
    }
}

/**
 * Show loading overlay
 */
function showLoading() {
    const overlay = document.createElement('div');
    overlay.id = 'loadingOverlay';
    overlay.className = 'loading-overlay';
    overlay.innerHTML = '<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>';
    document.body.appendChild(overlay);
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) {
        overlay.remove();
    }
}

/**
 * Debounce function
 */
function debounce(func, wait) {
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

/**
 * Copy to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showToast('Copied to clipboard!', 'success');
    } catch (err) {
        console.error('Failed to copy:', err);
        showToast('Failed to copy to clipboard', 'danger');
    }
}

// ============================================
// Form Validation
// ============================================

/**
 * Validate phone number (Kenya format)
 */
function validatePhoneNumber(phone) {
    const phoneRegex = /^(?:254|\+254|0)?([17]\d{8})$/;
    return phoneRegex.test(phone);
}

/**
 * Validate email
 */
function validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

/**
 * Form validation handler
 */
function setupFormValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    form.addEventListener('submit', function(e) {
        if (!form.checkValidity()) {
            e.preventDefault();
            e.stopPropagation();
        }
        form.classList.add('was-validated');
    });
}

// ============================================
// Search & Filter
// ============================================

/**
 * Real-time search
 */
function setupSearch(inputId, targetClass) {
    const searchInput = document.getElementById(inputId);
    if (!searchInput) return;
    
    const handleSearch = debounce(function(e) {
        const searchTerm = e.target.value.toLowerCase();
        const items = document.querySelectorAll(`.${targetClass}`);
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            item.style.display = text.includes(searchTerm) ? '' : 'none';
        });
    }, 300);
    
    searchInput.addEventListener('input', handleSearch);
}

// ============================================
// Booking Functions
// ============================================

/**
 * Update booking summary
 */
function updateBookingSummary(seats, farePerSeat) {
    const numSeats = seats.length;
    const totalFare = numSeats * farePerSeat;
    
    document.getElementById('selectedSeatsCount').textContent = numSeats;
    document.getElementById('totalFare').textContent = formatCurrency(totalFare);
    
    // Show/hide proceed button
    const proceedBtn = document.getElementById('proceedBtn');
    if (proceedBtn) {
        proceedBtn.disabled = numSeats === 0;
    }
}

/**
 * Check seat availability
 */
async function checkSeatAvailability(tripId) {
    try {
        const data = await apiRequest(`/ajax/check-seats/?trip_id=${tripId}`);
        return data;
    } catch (error) {
        showToast('Failed to check seat availability', 'danger');
        return null;
    }
}

/**
 * Verify promotion code
 */
async function verifyPromotionCode(code, amount) {
    try {
        const data = await apiRequest(`/ajax/verify-promo/?code=${code}&amount=${amount}`);
        return data;
    } catch (error) {
        showToast('Failed to verify promotion code', 'danger');
        return null;
    }
}

// ============================================
// Payment Functions
// ============================================

/**
 * Initialize payment
 */
async function initiatePayment(bookingId, paymentMethod, phoneNumber = null) {
    showLoading();
    
    try {
        const data = await apiRequest('/api/payments/initiate/', 'POST', {
            booking_id: bookingId,
            payment_method: paymentMethod,
            phone_number: phoneNumber,
        });
        
        hideLoading();
        
        if (data.success) {
            showToast('Payment initiated successfully', 'success');
            return true;
        } else {
            showToast(data.message || 'Payment initiation failed', 'danger');
            return false;
        }
    } catch (error) {
        hideLoading();
        showToast('Payment initiation failed', 'danger');
        return false;
    }
}

/**
 * Check payment status
 */
async function checkPaymentStatus(bookingId) {
    try {
        const data = await apiRequest(`/api/payments/status/${bookingId}/`);
        return data;
    } catch (error) {
        console.error('Failed to check payment status:', error);
        return null;
    }
}

// ============================================
// Notification Functions
// ============================================

/**
 * Mark notification as read
 */
async function markNotificationRead(notificationId) {
    try {
        await apiRequest(`/api/notifications/${notificationId}/read/`, 'POST');
        
        const badge = document.getElementById('notificationBadge');
        if (badge) {
            const count = parseInt(badge.textContent) - 1;
            badge.textContent = count > 0 ? count : '';
            badge.style.display = count > 0 ? '' : 'none';
        }
    } catch (error) {
        console.error('Failed to mark notification as read:', error);
    }
}

/**
 * Load notifications
 */
async function loadNotifications() {
    try {
        const data = await apiRequest('/api/notifications/');
        
        const container = document.getElementById('notificationList');
        if (!container) return;
        
        if (data.notifications.length === 0) {
            container.innerHTML = '<p class="text-muted text-center p-3">No notifications</p>';
            return;
        }
        
        container.innerHTML = data.notifications.map(notif => `
            <div class="notification-item ${notif.is_read ? '' : 'unread'}" onclick="markNotificationRead('${notif.id}')">
                <h6>${notif.title}</h6>
                <p>${notif.message}</p>
                <small>${formatDate(notif.created_at)}</small>
            </div>
        `).join('');
    } catch (error) {
        console.error('Failed to load notifications:', error);
    }
}

// ============================================
// Auto-refresh for pending status
// ============================================

/**
 * Auto-refresh page for pending payments/bookings
 */
function setupAutoRefresh(interval = 30000) {
    const hasPendingStatus = document.querySelector('[data-status="pending"]');
    
    if (hasPendingStatus) {
        setInterval(() => {
            location.reload();
        }, interval);
    }
}

// ============================================
// Image Preview
// ============================================

/**
 * Preview image before upload
 */
function setupImagePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    
    if (!input || !preview) return;
    
    input.addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                preview.src = e.target.result;
                preview.style.display = 'block';
            };
            reader.readAsDataURL(file);
        }
    });
}

// ============================================
// Date & Time Helpers
// ============================================

/**
 * Set minimum date for date inputs (today)
 */
function setMinimumDate() {
    const dateInputs = document.querySelectorAll('input[type="date"]');
    const today = new Date().toISOString().split('T')[0];
    
    dateInputs.forEach(input => {
        if (!input.hasAttribute('min')) {
            input.setAttribute('min', today);
        }
    });
}

/**
 * Calculate time difference
 */
function getTimeDifference(targetDate, targetTime) {
    const now = new Date();
    const target = new Date(`${targetDate}T${targetTime}`);
    const diff = target - now;
    
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    
    return { hours, minutes, total: diff };
}

// ============================================
// Initialize on DOM Load
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    // Set minimum dates
    setMinimumDate();
    
    // Setup auto-refresh for pending status
    setupAutoRefresh();
    
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts after 5 seconds
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        alerts.forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);
    
    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                e.preventDefault();
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Confirm before leaving page with unsaved changes
    let formChanged = false;
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('change', () => {
            formChanged = true;
        });
        
        form.addEventListener('submit', () => {
            formChanged = false;
        });
    });
    
    window.addEventListener('beforeunload', (e) => {
        if (formChanged) {
            e.preventDefault();
            e.returnValue = '';
        }
    });
});

// ============================================
// Export functions for global use
// ============================================

window.MatatuBook = {
    showToast,
    formatCurrency,
    formatDate,
    formatTime,
    apiRequest,
    showLoading,
    hideLoading,
    copyToClipboard,
    validatePhoneNumber,
    validateEmail,
    updateBookingSummary,
    checkSeatAvailability,
    verifyPromotionCode,
    initiatePayment,
    checkPaymentStatus,
    markNotificationRead,
    loadNotifications,
    debounce,
};

// ============================================
// Service Worker Registration (for PWA)
// ============================================

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/sw.js')
            .then(registration => {
                console.log('ServiceWorker registered:', registration);
            })
            .catch(err => {
                console.log('ServiceWorker registration failed:', err);
            });
    });
}