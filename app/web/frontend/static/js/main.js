// Common Utility Functions

function formatCurrency(value) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(value);
}

function formatPercentage(value) {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`;
}

function getStatusClass(status) {
    switch (status.toUpperCase()) {
        case 'COMPLETE':
        case 'RUNNING':
        case 'OPEN':
            return 'text-success';
        case 'CANCELLED':
        case 'REJECTED':
        case 'STOPPED':
        case 'ERROR':
            return 'text-danger';
        default:
            return 'text-secondary';
    }
}

function getColorClass(value) {
    if (value > 0) return 'text-success';
    if (value < 0) return 'text-danger';
    return 'text-secondary';
}
