/**
 * Number formatting utilities for Vietnamese currency (VND)
 */

// Format number with thousand separators for VND
function formatVND(amount) {
    if (!amount && amount !== 0) return '0';
    
    // Convert to number if string
    const num = typeof amount === 'string' ? parseFloat(amount.replace(/[^\d.-]/g, '')) : amount;
    
    if (isNaN(num)) return '0';
    
    // Format with Vietnamese locale
    return new Intl.NumberFormat('vi-VN').format(Math.round(num));
}

// Format currency with VND suffix
function formatCurrency(amount) {
    return formatVND(amount) + ' VND';
}

// Parse formatted number back to raw number
function parseVND(formattedAmount) {
    if (!formattedAmount) return 0;
    
    // Remove all non-digit characters except decimal point and minus
    const cleaned = formattedAmount.toString().replace(/[^\d.-]/g, '');
    const num = parseFloat(cleaned);
    
    return isNaN(num) ? 0 : num;
}

// Format input field with thousand separators as user types
function formatNumberInput(inputElement) {
    inputElement.addEventListener('input', function(e) {
        const cursorPosition = e.target.selectionStart;
        const oldValue = e.target.value;
        const oldLength = oldValue.length;
        
        // Get raw number
        const rawValue = parseVND(oldValue);
        
        // Format the number
        const formattedValue = formatVND(rawValue);
        
        // Update input value
        e.target.value = formattedValue;
        
        // Restore cursor position
        const newLength = formattedValue.length;
        const lengthDiff = newLength - oldLength;
        const newCursorPosition = cursorPosition + lengthDiff;
        
        // Set cursor position after formatting
        setTimeout(() => {
            e.target.setSelectionRange(newCursorPosition, newCursorPosition);
        }, 0);
    });
    
    // Handle paste events
    inputElement.addEventListener('paste', function(e) {
        setTimeout(() => {
            const rawValue = parseVND(e.target.value);
            e.target.value = formatVND(rawValue);
        }, 0);
    });
}

// Auto-format all elements with class 'format-vnd'
document.addEventListener('DOMContentLoaded', function() {
    // Format existing numbers on page load
    document.querySelectorAll('.format-vnd').forEach(element => {
        if (element.tagName === 'INPUT') {
            // For input fields, add formatting behavior
            formatNumberInput(element);
            
            // Format initial value if exists
            if (element.value) {
                element.value = formatVND(parseVND(element.value));
            }
        } else {
            // For display elements, format the content
            const rawValue = parseVND(element.textContent || element.innerText);
            element.textContent = formatCurrency(rawValue);
        }
    });
    
    // Format elements with data-amount attribute
    document.querySelectorAll('[data-amount]').forEach(element => {
        const amount = parseFloat(element.dataset.amount);
        if (!isNaN(amount)) {
            element.textContent = formatCurrency(amount);
        }
    });
});

// Export functions for use in other scripts
window.VNDFormatter = {
    format: formatVND,
    formatCurrency: formatCurrency,
    parse: parseVND,
    formatInput: formatNumberInput
};
