// Transfer Portal JavaScript

let allTransfers = [];
let filteredTransfers = [];
let currentSort = { field: 'rating', direction: 'desc' };

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadTransferData();
    setupEventListeners();
});

function setupEventListeners() {
    // Search input
    document.getElementById('searchInput').addEventListener('input', debounce(applyFilters, 300));

    // Filter dropdowns
    document.getElementById('yearFilter').addEventListener('change', handleYearChange);
    document.getElementById('positionFilter').addEventListener('change', applyFilters);
    document.getElementById('starsFilter').addEventListener('change', applyFilters);
    document.getElementById('sortBy').addEventListener('change', handleSortChange);

    // Table header sorting
    document.querySelectorAll('.transfer-table th.sortable').forEach(th => {
        th.addEventListener('click', () => handleColumnSort(th.dataset.sort));
    });
}

async function loadTransferData(year = null) {
    const loadingSpinner = document.getElementById('loadingSpinner');
    const transferTable = document.getElementById('transferTable');
    const noResults = document.getElementById('noResults');

    loadingSpinner.style.display = 'flex';
    transferTable.style.display = 'none';
    noResults.style.display = 'none';

    try {
        const url = year ? `/api/transfer-portal?year=${year}` : '/api/transfer-portal';
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        allTransfers = data.transfers || [];
        filteredTransfers = [...allTransfers];

        // Populate year filter if not already done
        if (!year) {
            populateYearFilter(data.year);
        }

        // Update last updated timestamp
        if (data.fetched_at) {
            const date = new Date(data.fetched_at);
            document.getElementById('lastUpdated').textContent = date.toLocaleString();
        }

        // Apply initial filters and render
        applyFilters();

        loadingSpinner.style.display = 'none';
        transferTable.style.display = 'table';

    } catch (error) {
        console.error('Error loading transfer data:', error);
        loadingSpinner.innerHTML = `
            <div style="text-align: center; color: #ef4444;">
                <p style="font-size: 1.25rem; margin-bottom: 0.5rem;">❌ Error Loading Data</p>
                <p style="font-size: 0.875rem;">${error.message}</p>
                <p style="font-size: 0.875rem; margin-top: 1rem;">
                    Try running: <code style="background: rgba(255,255,255,0.1); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">python -m scrapers.transfer_portal_fetcher</code>
                </p>
            </div>
        `;
    }
}

function populateYearFilter(currentYear) {
    const yearFilter = document.getElementById('yearFilter');
    yearFilter.innerHTML = '';

    // Generate years from 2021 to current year
    const startYear = 2021;
    const endYear = 2026;

    for (let year = endYear; year >= startYear; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = `${year} Season`;
        if (year === currentYear) {
            option.selected = true;
        }
        yearFilter.appendChild(option);
    }
}

function handleYearChange(event) {
    const year = parseInt(event.target.value);
    loadTransferData(year);
}

function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const positionFilter = document.getElementById('positionFilter').value;
    const starsFilter = document.getElementById('starsFilter').value;

    filteredTransfers = allTransfers.filter(transfer => {
        // Search filter
        const searchMatch = !searchTerm ||
            (transfer.first_name && transfer.first_name.toLowerCase().includes(searchTerm)) ||
            (transfer.last_name && transfer.last_name.toLowerCase().includes(searchTerm)) ||
            (transfer.position && transfer.position.toLowerCase().includes(searchTerm)) ||
            (transfer.origin && transfer.origin.toLowerCase().includes(searchTerm)) ||
            (transfer.destination && transfer.destination.toLowerCase().includes(searchTerm));

        // Position filter
        const positionMatch = !positionFilter || transfer.position === positionFilter;

        // Stars filter
        let starsMatch = true;
        if (starsFilter) {
            const minStars = parseInt(starsFilter);
            starsMatch = transfer.stars && transfer.stars >= minStars;
        }

        return searchMatch && positionMatch && starsMatch;
    });

    sortTransfers();
    renderTable();
    updateStats();
}

function handleSortChange(event) {
    const sortValue = event.target.value;
    const [field, direction] = sortValue.split('_');

    currentSort = { field, direction };
    sortTransfers();
    renderTable();
}

function handleColumnSort(field) {
    // Toggle direction if same field, otherwise default to desc
    if (currentSort.field === field) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.field = field;
        currentSort.direction = 'desc';
    }

    // Update sort dropdown to match
    const sortBy = document.getElementById('sortBy');
    const matchingOption = Array.from(sortBy.options).find(opt => {
        const [f, d] = opt.value.split('_');
        return f === field && d === currentSort.direction;
    });
    if (matchingOption) {
        sortBy.value = matchingOption.value;
    }

    sortTransfers();
    renderTable();
}

function sortTransfers() {
    const { field, direction } = currentSort;

    filteredTransfers.sort((a, b) => {
        let aVal, bVal;

        switch (field) {
            case 'name':
                aVal = `${a.last_name || ''} ${a.first_name || ''}`.toLowerCase();
                bVal = `${b.last_name || ''} ${b.first_name || ''}`.toLowerCase();
                break;
            case 'rating':
                aVal = parseFloat(a.rating) || 0;
                bVal = parseFloat(b.rating) || 0;
                break;
            case 'stars':
                aVal = a.stars || 0;
                bVal = b.stars || 0;
                break;
            case 'date':
            case 'transfer_date':
                aVal = a.transfer_date ? new Date(a.transfer_date).getTime() : 0;
                bVal = b.transfer_date ? new Date(b.transfer_date).getTime() : 0;
                break;
            case 'position':
                aVal = (a.position || '').toLowerCase();
                bVal = (b.position || '').toLowerCase();
                break;
            case 'origin':
                aVal = (a.origin || '').toLowerCase();
                bVal = (b.origin || '').toLowerCase();
                break;
            case 'destination':
                aVal = (a.destination || '').toLowerCase();
                bVal = (b.destination || '').toLowerCase();
                break;
            case 'eligibility':
                aVal = (a.eligibility || '').toLowerCase();
                bVal = (b.eligibility || '').toLowerCase();
                break;
            default:
                return 0;
        }

        if (aVal < bVal) return direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return direction === 'asc' ? 1 : -1;
        return 0;
    });

    updateSortIndicators();
}

function updateSortIndicators() {
    // Remove all active classes
    document.querySelectorAll('.transfer-table th.sortable').forEach(th => {
        th.classList.remove('active', 'asc', 'desc');
    });

    // Add active class to current sort column
    const activeHeader = document.querySelector(`.transfer-table th[data-sort="${currentSort.field}"]`);
    if (activeHeader) {
        activeHeader.classList.add('active', currentSort.direction);
    }
}

function renderTable() {
    const tableBody = document.getElementById('tableBody');
    const noResults = document.getElementById('noResults');
    const transferTable = document.getElementById('transferTable');

    if (filteredTransfers.length === 0) {
        transferTable.style.display = 'none';
        noResults.style.display = 'block';
        return;
    }

    transferTable.style.display = 'table';
    noResults.style.display = 'none';

    tableBody.innerHTML = filteredTransfers.map(transfer => {
        const playerName = `${transfer.first_name || ''} ${transfer.last_name || ''}`.trim() || 'Unknown';
        const position = transfer.position || '-';
        const origin = transfer.origin || 'Unknown';
        const destination = transfer.destination || 'TBD';
        const transferDate = transfer.transfer_date ? formatDate(transfer.transfer_date) : '-';
        const rating = transfer.rating ? parseFloat(transfer.rating).toFixed(2) : '-';
        const stars = transfer.stars || 0;
        const eligibility = transfer.eligibility || '-';

        // Determine rating class
        let ratingClass = 'low';
        if (rating !== '-') {
            const ratingNum = parseFloat(rating);
            if (ratingNum >= 0.9) ratingClass = 'high';
            else if (ratingNum >= 0.8) ratingClass = 'medium';
        }

        return `
            <tr>
                <td><span class="player-name">${playerName}</span></td>
                <td><span class="position-badge">${position}</span></td>
                <td><span class="school-name ${origin === 'Unknown' ? 'unknown' : ''}">${origin}</span></td>
                <td><span class="school-name ${destination === 'TBD' ? 'unknown' : ''}">${destination}</span></td>
                <td><span class="transfer-date">${transferDate}</span></td>
                <td><span class="rating-value ${ratingClass}">${rating}</span></td>
                <td>${renderStars(stars)}</td>
                <td><span class="eligibility-badge">${eligibility}</span></td>
            </tr>
        `;
    }).join('');

    document.getElementById('totalCount').textContent = filteredTransfers.length;
}

function renderStars(count) {
    if (!count || count === 0) return '<span class="stars">-</span>';

    const maxStars = 5;
    let starsHtml = '<span class="stars">';

    for (let i = 1; i <= maxStars; i++) {
        if (i <= count) {
            starsHtml += '<span class="star">★</span>';
        } else {
            starsHtml += '<span class="star empty">★</span>';
        }
    }

    starsHtml += '</span>';
    return starsHtml;
}

function updateStats() {
    // Total transfers
    document.getElementById('totalTransfers').textContent = filteredTransfers.length.toLocaleString();

    // Average stars
    const transfersWithStars = filteredTransfers.filter(t => t.stars && t.stars > 0);
    const avgStars = transfersWithStars.length > 0
        ? (transfersWithStars.reduce((sum, t) => sum + t.stars, 0) / transfersWithStars.length).toFixed(1)
        : '-';
    document.getElementById('avgStars').textContent = avgStars !== '-' ? `${avgStars}★` : '-';

    // Top position
    const positionCounts = {};
    filteredTransfers.forEach(transfer => {
        const pos = transfer.position || 'Unknown';
        positionCounts[pos] = (positionCounts[pos] || 0) + 1;
    });

    const topPosition = Object.entries(positionCounts)
        .sort((a, b) => b[1] - a[1])[0];

    document.getElementById('topPosition').textContent = topPosition
        ? `${topPosition[0]} (${topPosition[1]})`
        : '-';
}

function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    } catch {
        return dateString;
    }
}

// Debounce helper
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
