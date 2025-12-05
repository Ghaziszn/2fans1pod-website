// Coaching Power Index JavaScript

let allCoaches = [];
let filteredCoaches = [];
let currentSort = { column: 'weighted_score', direction: 'desc' };

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    fetchCoachingData();
    setupEventListeners();
});

// Fetch coaching data from API
async function fetchCoachingData() {
    try {
        const response = await fetch('/api/coaching-power-index');
        const data = await response.json();

        if (data.error) {
            showError(data.error);
            return;
        }

        allCoaches = data.coaches || [];
        filteredCoaches = [...allCoaches];

        // Update UI
        updateStatsSummary(data);
        updateDataInfo(data);
        renderTable();

        // Hide loading spinner, show table
        document.getElementById('loadingSpinner').style.display = 'none';
        document.getElementById('coachingTable').style.display = 'table';

    } catch (error) {
        console.error('Error fetching coaching data:', error);
        showError('Failed to load coaching data. Please try again later.');
    }
}

// Setup event listeners
function setupEventListeners() {
    // Search input
    const searchInput = document.getElementById('searchInput');
    searchInput.addEventListener('input', handleSearch);

    // Division filter
    const divisionFilter = document.getElementById('divisionFilter');
    divisionFilter.addEventListener('change', handleFilter);

    // Sort select
    const sortSelect = document.getElementById('sortBy');
    sortSelect.addEventListener('change', handleSortSelect);

    // Table header sorting
    const headers = document.querySelectorAll('.coaching-table th.sortable');
    headers.forEach(header => {
        header.addEventListener('click', () => handleSort(header.dataset.sort));
    });
}

// Handle search
function handleSearch(e) {
    const searchTerm = e.target.value.toLowerCase().trim();

    if (!searchTerm) {
        filteredCoaches = [...allCoaches];
    } else {
        filteredCoaches = allCoaches.filter(coach => {
            const coachName = (coach.Coach || '').toLowerCase();
            const schoolName = (coach.School || '').toLowerCase();
            const division = (coach.Division || '').toLowerCase();
            const conference = (coach['Conference Ranking'] || '').toString().toLowerCase();

            return coachName.includes(searchTerm) ||
                schoolName.includes(searchTerm) ||
                division.includes(searchTerm) ||
                conference.includes(searchTerm);
        });
    }

    renderTable();
}

// Handle division filter
function handleFilter() {
    const divisionFilter = document.getElementById('divisionFilter').value;
    const searchInput = document.getElementById('searchInput').value.toLowerCase().trim();

    // Start with all coaches
    let coaches = [...allCoaches];

    // Apply division filter
    if (divisionFilter) {
        coaches = coaches.filter(coach => coach.Division === divisionFilter);
    }

    // Apply search filter
    if (searchInput) {
        coaches = coaches.filter(coach => {
            const coachName = (coach.Coach || '').toLowerCase();
            const schoolName = (coach.School || '').toLowerCase();
            const division = (coach.Division || '').toLowerCase();

            return coachName.includes(searchInput) ||
                schoolName.includes(searchInput) ||
                division.includes(searchInput);
        });
    }

    filteredCoaches = coaches;
    renderTable();
}

// Handle sort select dropdown
function handleSortSelect(e) {
    const sortBy = e.target.value;
    let column = sortBy;

    // Map friendly names to data keys
    const columnMap = {
        'weighted_score': 'Weighted Score',
        'total_wins': 'Total Wins',
        'win_percentage': 'Total Win %',
        'tenure': 'Total Tenure'
    };

    column = columnMap[sortBy] || sortBy;
    handleSort(column, true);
}

// Handle sorting
function handleSort(column, fromSelect = false) {
    // Determine sort direction
    if (currentSort.column === column && !fromSelect) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.column = column;
        currentSort.direction = 'desc'; // Default to descending
    }

    // Sort the data
    filteredCoaches.sort((a, b) => {
        let aVal = a[column];
        let bVal = b[column];

        // Handle null/undefined values
        if (aVal === null || aVal === undefined) aVal = -Infinity;
        if (bVal === null || bVal === undefined) bVal = -Infinity;

        // Convert to numbers if possible
        if (typeof aVal === 'string' && !isNaN(aVal)) aVal = parseFloat(aVal);
        if (typeof bVal === 'string' && !isNaN(bVal)) bVal = parseFloat(bVal);

        // Compare
        if (aVal < bVal) return currentSort.direction === 'asc' ? -1 : 1;
        if (aVal > bVal) return currentSort.direction === 'asc' ? 1 : -1;
        return 0;
    });

    // Update header classes
    updateSortHeaders(column);

    // Re-render table
    renderTable();
}

// Update sort header indicators
function updateSortHeaders(activeColumn) {
    const headers = document.querySelectorAll('.coaching-table th.sortable');
    headers.forEach(header => {
        header.classList.remove('active', 'asc', 'desc');
        if (header.dataset.sort === activeColumn || header.textContent.trim() === activeColumn) {
            header.classList.add('active', currentSort.direction);
        }
    });
}

// Render table
function renderTable() {
    const tbody = document.getElementById('tableBody');
    const noResults = document.getElementById('noResults');

    if (filteredCoaches.length === 0) {
        tbody.innerHTML = '';
        document.getElementById('coachingTable').style.display = 'none';
        noResults.style.display = 'block';
        return;
    }

    noResults.style.display = 'none';
    document.getElementById('coachingTable').style.display = 'table';

    tbody.innerHTML = filteredCoaches.map((coach, index) => {
        const rank = index + 1;
        const winPct = coach['Total Win %'] || 0;
        const winPctClass = getWinPctClass(winPct);
        const divisionClass = (coach.Division || '').toLowerCase().replace(/\s+/g, '');

        return `
      <tr class="rank-${rank}">
        <td>${rank}</td>
        <td class="coach-name">${escapeHtml(coach.Coach || '-')}</td>
        <td class="school-name">${escapeHtml(coach.School || '-')}</td>
        <td><span class="division-badge ${divisionClass}">${escapeHtml(coach.Division || '-')}</span></td>
        <td>${formatNumber(coach['Total Tenure'])}</td>
        <td>${formatNumber(coach['Total Wins'])}</td>
        <td>${formatNumber(coach['Total Losses'])}</td>
        <td class="win-pct ${winPctClass}">${formatPercentage(winPct)}</td>
        <td>${formatNumber(coach['T25 Wins'])}</td>
        <td>${formatNumber(coach['# Conference Championship Wins'])}</td>
        <td>${formatNumber(coach['# Bowl Game Wins'])}</td>
        <td class="score">${formatScore(coach['Weighted Score'])}</td>
      </tr>
    `;
    }).join('');
}

// Update stats summary
function updateStatsSummary(data) {
    const coaches = data.coaches || [];
    const totalCoaches = coaches.length;

    // Calculate average win percentage
    const validWinPcts = coaches
        .map(c => c['Total Win %'])
        .filter(pct => pct !== null && pct !== undefined && !isNaN(pct));
    const avgWinPct = validWinPcts.length > 0
        ? validWinPcts.reduce((sum, pct) => sum + pct, 0) / validWinPcts.length
        : 0;

    // Calculate average tenure
    const validTenures = coaches
        .map(c => c['Total Tenure'])
        .filter(t => t !== null && t !== undefined && !isNaN(t));
    const avgTenure = validTenures.length > 0
        ? validTenures.reduce((sum, t) => sum + t, 0) / validTenures.length
        : 0;

    document.getElementById('totalCoaches').textContent = totalCoaches;
    document.getElementById('avgWinPct').textContent = formatPercentage(avgWinPct);
    document.getElementById('avgTenure').textContent = avgTenure.toFixed(1) + ' yrs';
}

// Update data info
function updateDataInfo(data) {
    document.getElementById('lastUpdated').textContent = data.last_updated || 'Unknown';
    document.getElementById('totalCount').textContent = data.total_coaches || 0;
}

// Helper functions
function getWinPctClass(pct) {
    if (pct >= 0.7) return 'excellent';
    if (pct >= 0.6) return 'good';
    if (pct >= 0.5) return 'average';
    return 'poor';
}

function formatNumber(value) {
    if (value === null || value === undefined || value === '') return '-';
    return Math.round(value).toString();
}

function formatPercentage(value) {
    if (value === null || value === undefined || value === '' || isNaN(value)) return '-';
    return (value * 100).toFixed(1) + '%';
}

function formatScore(value) {
    if (value === null || value === undefined || value === '' || isNaN(value)) return '-';
    return value.toFixed(2);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    const spinner = document.getElementById('loadingSpinner');
    spinner.innerHTML = `
    <div style="color: #f87171; font-size: 1.2rem;">
      <p>⚠️ ${message}</p>
    </div>
  `;
}
