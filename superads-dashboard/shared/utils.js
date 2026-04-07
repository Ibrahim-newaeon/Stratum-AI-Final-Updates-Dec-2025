// =============================================================================
// Stratum AI - Utility Functions
// =============================================================================

// -------------------------------------------------------------------------
// Formatting Utilities
// -------------------------------------------------------------------------
function formatCurrency(value, compact = false) {
    if (compact && value >= 1000000) {
        return (value / 1000000).toFixed(1) + 'M';
    }
    if (compact && value >= 1000) {
        return (value / 1000).toFixed(0) + 'K';
    }
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(value);
}

function formatNumber(value, decimals = 0) {
    if (value >= 1000000) {
        return (value / 1000000).toFixed(1) + 'M';
    }
    if (value >= 1000) {
        return (value / 1000).toFixed(1) + 'K';
    }
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value);
}

function formatPercent(value, decimals = 1) {
    return value.toFixed(decimals) + '%';
}

function formatDate(dateString, format = 'short') {
    const date = new Date(dateString);
    const options = format === 'long'
        ? { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' }
        : { year: 'numeric', month: 'short', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

function formatRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) return 'Just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    if (diffHour < 24) return `${diffHour}h ago`;
    if (diffDay < 7) return `${diffDay}d ago`;
    return formatDate(dateString);
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

// -------------------------------------------------------------------------
// Animation Utilities
// -------------------------------------------------------------------------
function animateValue(elementId, endValue, prefix = '', decimals = 0, isNumber = false) {
    const el = document.getElementById(elementId);
    if (!el) return;

    // Handle string values (like "2.4M")
    if (typeof endValue === 'string' && !isNumber) {
        el.textContent = prefix + endValue;
        return;
    }

    const startValue = 0;
    const duration = 1500;
    const startTime = performance.now();

    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easeProgress = 1 - Math.pow(1 - progress, 3); // easeOutCubic

        const currentValue = startValue + (endValue - startValue) * easeProgress;
        el.textContent = prefix + currentValue.toFixed(decimals);

        if (progress < 1) {
            requestAnimationFrame(update);
        } else {
            el.textContent = prefix + endValue.toFixed(decimals);
        }
    }

    requestAnimationFrame(update);
}

function animateProgressBar(elementId, targetWidth) {
    const el = document.getElementById(elementId);
    if (!el) return;

    el.style.width = '0%';
    setTimeout(() => {
        el.style.width = targetWidth + '%';
    }, 100);
}

// -------------------------------------------------------------------------
// DOM Utilities
// -------------------------------------------------------------------------
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

function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

function createElement(tag, attributes = {}, children = []) {
    const el = document.createElement(tag);
    Object.entries(attributes).forEach(([key, value]) => {
        if (key === 'className') {
            el.className = value;
        } else if (key === 'innerHTML') {
            el.innerHTML = value;
        } else if (key.startsWith('data')) {
            el.setAttribute(key.replace(/([A-Z])/g, '-$1').toLowerCase(), value);
        } else if (key.startsWith('on')) {
            el.addEventListener(key.slice(2).toLowerCase(), value);
        } else {
            el.setAttribute(key, value);
        }
    });
    children.forEach(child => {
        if (typeof child === 'string') {
            el.appendChild(document.createTextNode(child));
        } else if (child) {
            el.appendChild(child);
        }
    });
    return el;
}

function clearElement(element) {
    while (element.firstChild) {
        element.removeChild(element.firstChild);
    }
}

// -------------------------------------------------------------------------
// Date Utilities
// -------------------------------------------------------------------------
function getDateRange(period) {
    const end = new Date();
    end.setHours(23, 59, 59, 999);

    const start = new Date();
    start.setHours(0, 0, 0, 0);

    switch (period) {
        case '7d':
            start.setDate(start.getDate() - 7);
            break;
        case '30d':
            start.setDate(start.getDate() - 30);
            break;
        case '90d':
            start.setDate(start.getDate() - 90);
            break;
        case 'mtd':
            start.setDate(1);
            break;
        case 'ytd':
            start.setMonth(0, 1);
            break;
        default:
            start.setDate(start.getDate() - 30);
    }

    return {
        start: start.toISOString().split('T')[0],
        end: end.toISOString().split('T')[0]
    };
}

function formatDateForAPI(date) {
    return date.toISOString().split('T')[0];
}

// -------------------------------------------------------------------------
// Chart/Visualization Utilities
// -------------------------------------------------------------------------
function createSparkline(containerId, data, color = '#8b5cf6') {
    const container = document.getElementById(containerId);
    if (!container || !data || data.length === 0) return;

    const width = container.offsetWidth || 100;
    const height = container.offsetHeight || 30;
    const padding = 2;

    const max = Math.max(...data);
    const min = Math.min(...data);
    const range = max - min || 1;

    const points = data.map((value, index) => {
        const x = padding + (index / (data.length - 1)) * (width - 2 * padding);
        const y = height - padding - ((value - min) / range) * (height - 2 * padding);
        return `${x},${y}`;
    }).join(' ');

    container.innerHTML = `
        <svg width="${width}" height="${height}" style="overflow: visible;">
            <defs>
                <linearGradient id="sparklineGradient-${containerId}" x1="0%" y1="0%" x2="0%" y2="100%">
                    <stop offset="0%" style="stop-color:${color};stop-opacity:0.3" />
                    <stop offset="100%" style="stop-color:${color};stop-opacity:0" />
                </linearGradient>
            </defs>
            <polyline
                fill="url(#sparklineGradient-${containerId})"
                stroke="none"
                points="${points} ${width - padding},${height - padding} ${padding},${height - padding}"
            />
            <polyline
                fill="none"
                stroke="${color}"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                points="${points}"
            />
        </svg>
    `;
}

function createDonutChart(containerId, value, total, color = '#10b981') {
    const container = document.getElementById(containerId);
    if (!container) return;

    const size = 60;
    const strokeWidth = 6;
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (value / total) * circumference;

    container.innerHTML = `
        <svg width="${size}" height="${size}" style="transform: rotate(-90deg);">
            <circle
                cx="${size/2}"
                cy="${size/2}"
                r="${radius}"
                fill="none"
                stroke="var(--bg-tertiary)"
                stroke-width="${strokeWidth}"
            />
            <circle
                cx="${size/2}"
                cy="${size/2}"
                r="${radius}"
                fill="none"
                stroke="${color}"
                stroke-width="${strokeWidth}"
                stroke-linecap="round"
                stroke-dasharray="${circumference}"
                stroke-dashoffset="${offset}"
                style="transition: stroke-dashoffset 1s ease;"
            />
        </svg>
    `;
}

// -------------------------------------------------------------------------
// Color Utilities
// -------------------------------------------------------------------------
function getStatusColor(status) {
    const colors = {
        active: 'var(--accent-green)',
        connected: 'var(--accent-green)',
        healthy: 'var(--accent-green)',
        good: 'var(--accent-green)',
        paused: 'var(--accent-yellow)',
        partial: 'var(--accent-orange)',
        warning: 'var(--accent-orange)',
        needs_attention: 'var(--accent-orange)',
        error: 'var(--accent-red)',
        critical: 'var(--accent-red)',
        offline: 'var(--accent-red)'
    };
    return colors[status] || 'var(--text-muted)';
}

function getPlatformColor(platform) {
    const colors = {
        meta: '#0081FB',
        google: '#EA4335',
        tiktok: '#000000',
        snapchat: '#FFFC00',
        linkedin: '#0A66C2'
    };
    return colors[platform] || '#8b5cf6';
}

// -------------------------------------------------------------------------
// URL Utilities
// -------------------------------------------------------------------------
function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    const result = {};
    for (const [key, value] of params) {
        result[key] = value;
    }
    return result;
}

function setQueryParams(params) {
    const url = new URL(window.location);
    Object.entries(params).forEach(([key, value]) => {
        if (value !== null && value !== undefined && value !== '') {
            url.searchParams.set(key, value);
        } else {
            url.searchParams.delete(key);
        }
    });
    window.history.pushState({}, '', url);
}

// -------------------------------------------------------------------------
// Storage Utilities
// -------------------------------------------------------------------------
function getLocalStorage(key, defaultValue = null) {
    try {
        const item = localStorage.getItem(key);
        return item ? JSON.parse(item) : defaultValue;
    } catch {
        return defaultValue;
    }
}

function setLocalStorage(key, value) {
    try {
        localStorage.setItem(key, JSON.stringify(value));
    } catch (e) {
        console.error('localStorage error:', e);
    }
}

// -------------------------------------------------------------------------
// Validation Utilities
// -------------------------------------------------------------------------
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

function validatePhone(phone) {
    const re = /^\+?[1-9]\d{1,14}$/;
    return re.test(phone.replace(/[\s-()]/g, ''));
}

// -------------------------------------------------------------------------
// Export
// -------------------------------------------------------------------------
if (typeof window !== 'undefined') {
    window.formatCurrency = formatCurrency;
    window.formatNumber = formatNumber;
    window.formatPercent = formatPercent;
    window.formatDate = formatDate;
    window.formatRelativeTime = formatRelativeTime;
    window.capitalize = capitalize;
    window.animateValue = animateValue;
    window.animateProgressBar = animateProgressBar;
    window.debounce = debounce;
    window.throttle = throttle;
    window.createElement = createElement;
    window.clearElement = clearElement;
    window.getDateRange = getDateRange;
    window.formatDateForAPI = formatDateForAPI;
    window.createSparkline = createSparkline;
    window.createDonutChart = createDonutChart;
    window.getStatusColor = getStatusColor;
    window.getPlatformColor = getPlatformColor;
    window.getQueryParams = getQueryParams;
    window.setQueryParams = setQueryParams;
    window.getLocalStorage = getLocalStorage;
    window.setLocalStorage = setLocalStorage;
    window.validateEmail = validateEmail;
    window.validatePhone = validatePhone;
}
