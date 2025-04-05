/**
 * CSRF protection for AJAX requests
 */

// Function to get CSRF token from meta tag
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}

// Helper function for making fetch requests with CSRF token
async function fetchWithCSRF(url, options = {}) {
    // Set default options
    const defaultOptions = {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': getCSRFToken()
        }
    };

    // Merge options
    const mergedOptions = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };

    // Make the fetch request
    try {
        const response = await fetch(url, mergedOptions);
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.status}`);
        }
        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
} 