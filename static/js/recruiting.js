// Recruiting JavaScript

let allRecruits = [];
let filteredRecruits = [];
let currentSort = { field: 'ranking', direction: 'asc' };

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadRecruitingData();
    setupEventListeners();
});

function setupEventListeners() {
    // Search input
    document.getElementById('searchInput').addEventListener('input', debounce(applyFilters, 300));

    // Filter dropdowns
    document.getElementById('yearFilter').addEventListener('change', handleYearChange);
    document.getElementById('positionFilter').addEventListener('change', applyFilters);
    document.getElementById('starsFilter').addEventListener('change', applyFilters);
    document.getElementById('teamFilter').addEventListener('change', applyFilters);
    document.getElementById('sortBy').addEventListener('change', handleSortChange);

    // Table header sorting
    document.querySelectorAll('.recruiting-table th.sortable').forEach(th => {
        th.addEventListener('click', () => handleColumnSort(th.dataset.sort));
    });
}

async function loadRecruitingData(year = null) {
    const loadingSpinner = document.getElementById('loadingSpinner');
    const recruitingTable = document.getElementById('recruitingTable');
    const noResults = document.getElementById('noResults');

    loadingSpinner.style.display = 'flex';
    recruitingTable.style.display = 'none';
    noResults.style.display = 'none';

    try {
        const url = year ? `/api/recruiting?year=${year}` : '/api/recruiting';
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        allRecruits = data.recruits || [];
        filteredRecruits = [...allRecruits];

        // Populate year filter if not already done
        if (!year) {
            populateYearFilter(data.year);
        }

        // Populate team filter
        populateTeamFilter();

        // Update last updated timestamp
        if (data.fetched_at) {
            const date = new Date(data.fetched_at);
            document.getElementById('lastUpdated').textContent = date.toLocaleString();
        }

        // Apply initial filters and render
        applyFilters();

        loadingSpinner.style.display = 'none';
        recruitingTable.style.display = 'table';

    } catch (error) {
        console.error('Error loading recruiting data:', error);
        loadingSpinner.innerHTML = `
            <div style="text-align: center; color: #ef4444;">
                <p style="font-size: 1.25rem; margin-bottom: 0.5rem;">❌ Error Loading Data</p>
                <p style="font-size: 0.875rem;">${error.message}</p>
                <p style="font-size: 0.875rem; margin-top: 1rem;">
                    Try running: <code style="background: rgba(255,255,255,0.1); padding: 0.25rem 0.5rem; border-radius: 0.25rem;">python -m scrapers.recruiting_fetcher</code>
                </p>
            </div>
        `;
    }
}

function populateYearFilter(currentYear) {
    const yearFilter = document.getElementById('yearFilter');
    yearFilter.innerHTML = '';

    // Generate years from 2020 to current year + 1
    const startYear = 2020;
    const endYear = new Date().getFullYear() + 1;

    for (let year = endYear; year >= startYear; year--) {
        const option = document.createElement('option');
        option.value = year;
        option.textContent = `${year} Class`;
        if (year === currentYear) {
            option.selected = true;
        }
        yearFilter.appendChild(option);
    }
}

function populateTeamFilter() {
    const teamFilter = document.getElementById('teamFilter');

    // Get unique teams from recruits
    const teams = new Set();
    allRecruits.forEach(recruit => {
        if (recruit.committed_to) {
            teams.add(recruit.committed_to);
        }
    });

    // Sort teams alphabetically
    const sortedTeams = Array.from(teams).sort();

    // Clear existing options except "All Teams"
    teamFilter.innerHTML = '<option value="">All Teams</option>';

    // Add team options
    sortedTeams.forEach(team => {
        const option = document.createElement('option');
        option.value = team;
        option.textContent = team;
        teamFilter.appendChild(option);
    });
}

function handleYearChange(event) {
    const year = parseInt(event.target.value);
    loadRecruitingData(year);
}

function applyFilters() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const positionFilter = document.getElementById('positionFilter').value;
    const starsFilter = document.getElementById('starsFilter').value;
    const teamFilter = document.getElementById('teamFilter').value;

    filteredRecruits = allRecruits.filter(recruit => {
        // Search filter
        const searchMatch = !searchTerm ||
            (recruit.name && recruit.name.toLowerCase().includes(searchTerm)) ||
            (recruit.position && recruit.position.toLowerCase().includes(searchTerm)) ||
            (recruit.school && recruit.school.toLowerCase().includes(searchTerm)) ||
            (recruit.committed_to && recruit.committed_to.toLowerCase().includes(searchTerm)) ||
            (recruit.city && recruit.city.toLowerCase().includes(searchTerm)) ||
            (recruit.state_province && recruit.state_province.toLowerCase().includes(searchTerm));

        // Position filter
        const positionMatch = !positionFilter || recruit.position === positionFilter;

        // Stars filter
        let starsMatch = true;
        if (starsFilter) {
            const minStars = parseInt(starsFilter);
            starsMatch = recruit.stars && recruit.stars >= minStars;
        }

        // Team filter
        const teamMatch = !teamFilter || recruit.committed_to === teamFilter;

        return searchMatch && positionMatch && starsMatch && teamMatch;
    });

    sortRecruits();
    renderTable();
    updateStats();
}

function handleSortChange(event) {
    const sortValue = event.target.value;
    const [field, direction] = sortValue.split('_');

    currentSort = { field, direction };
    sortRecruits();
    renderTable();
}

function handleColumnSort(field) {
    // Toggle direction if same field, otherwise default to asc
    if (currentSort.field === field) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        currentSort.field = field;
        currentSort.direction = field === 'ranking' ? 'asc' : 'desc';
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

    sortRecruits();
    renderTable();
}

function sortRecruits() {
    const { field, direction } = currentSort;

    filteredRecruits.sort((a, b) => {
        let aVal, bVal;

        switch (field) {
            case 'name':
                aVal = (a.name || '').toLowerCase();
                bVal = (b.name || '').toLowerCase();
                break;
            case 'ranking':
                aVal = a.ranking || 99999;
                bVal = b.ranking || 99999;
                break;
            case 'rating':
                aVal = parseFloat(a.rating) || 0;
                bVal = parseFloat(b.rating) || 0;
                break;
            case 'stars':
                aVal = a.stars || 0;
                bVal = b.stars || 0;
                break;
            case 'position':
                aVal = (a.position || '').toLowerCase();
                bVal = (b.position || '').toLowerCase();
                break;
            case 'school':
                aVal = (a.school || '').toLowerCase();
                bVal = (b.school || '').toLowerCase();
                break;
            case 'location':
                aVal = `${a.city || ''} ${a.state_province || ''}`.toLowerCase();
                bVal = `${b.city || ''} ${b.state_province || ''}`.toLowerCase();
                break;
            case 'height':
                aVal = parseFloat(a.height) || 0;
                bVal = parseFloat(b.height) || 0;
                break;
            case 'weight':
                aVal = a.weight || 0;
                bVal = b.weight || 0;
                break;
            case 'committed_to':
                aVal = (a.committed_to || 'Uncommitted').toLowerCase();
                bVal = (b.committed_to || 'Uncommitted').toLowerCase();
                break;
            case 'current_team':
                aVal = (a.current_team || a.committed_to || 'Unknown').toLowerCase();
                bVal = (b.current_team || b.committed_to || 'Unknown').toLowerCase();
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
    document.querySelectorAll('.recruiting-table th.sortable').forEach(th => {
        th.classList.remove('active', 'asc', 'desc');
    });

    // Add active class to current sort column
    const activeHeader = document.querySelector(`.recruiting-table th[data-sort="${currentSort.field}"]`);
    if (activeHeader) {
        activeHeader.classList.add('active', currentSort.direction);
    }
}

function renderTable() {
    const tableBody = document.getElementById('tableBody');
    const noResults = document.getElementById('noResults');
    const recruitingTable = document.getElementById('recruitingTable');

    if (filteredRecruits.length === 0) {
        recruitingTable.style.display = 'none';
        noResults.style.display = 'block';
        return;
    }

    recruitingTable.style.display = 'table';
    noResults.style.display = 'none';

    tableBody.innerHTML = filteredRecruits.map(recruit => {
        const name = recruit.name || 'Unknown';
        const ranking = recruit.ranking || '-';
        const position = recruit.position || '-';
        const school = recruit.school || 'Unknown';
        const city = recruit.city || '';
        const state = recruit.state_province || '';
        const location = `${city}${city && state ? ', ' : ''}${state}` || '-';
        const height = recruit.height || '-';
        const weight = recruit.weight || '-';
        const stars = recruit.stars || 0;
        const rating = recruit.rating ? parseFloat(recruit.rating).toFixed(4) : '-';
        const committedTo = recruit.committed_to || 'Uncommitted';
        const currentTeam = recruit.current_team || committedTo || 'Unknown';
        const transferred = recruit.transferred || false;

        // Determine rating class
        let ratingClass = 'low';
        if (rating !== '-') {
            const ratingNum = parseFloat(rating);
            if (ratingNum >= 0.98) ratingClass = 'high';
            else if (ratingNum >= 0.90) ratingClass = 'medium';
        }

        // Determine rank badge class
        let rankClass = '';
        if (ranking !== '-' && ranking <= 10) rankClass = 'top10';
        else if (ranking !== '-' && ranking <= 50) rankClass = 'top50';

        return `
            <tr>
                <td><span class="rank-badge ${rankClass}">${ranking}</span></td>
                <td><span class="player-name">${name}</span></td>
                <td><span class="position-badge">${position}</span></td>
                <td><span class="school-name">${school}</span></td>
                <td>${location}</td>
                <td>${height}</td>
                <td>${weight}</td>
                <td>${renderStars(stars)}</td>
                <td><span class="rating-value ${ratingClass}">${rating}</span></td>
                <td><span class="school-name ${committedTo === 'Uncommitted' ? 'unknown' : ''}">${committedTo}</span></td>
                <td>
                    <div class="current-team-cell">
                        <span class="school-name ${currentTeam === 'Unknown' ? 'unknown' : ''}">${currentTeam}</span>
                        ${transferred ? '<span class="transfer-badge">Transferred</span>' : ''}
                    </div>
                </td>
            </tr>
        `;
    }).join('');

    document.getElementById('totalCount').textContent = filteredRecruits.length;
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
    // Total recruits
    document.getElementById('totalRecruits').textContent = filteredRecruits.length.toLocaleString();

    // Average stars
    const recruitsWithStars = filteredRecruits.filter(r => r.stars && r.stars > 0);
    const avgStars = recruitsWithStars.length > 0
        ? (recruitsWithStars.reduce((sum, r) => sum + r.stars, 0) / recruitsWithStars.length).toFixed(1)
        : '-';
    document.getElementById('avgStars').textContent = avgStars !== '-' ? `${avgStars}★` : '-';

    // Top committed team
    const teamCounts = {};
    filteredRecruits.forEach(recruit => {
        const team = recruit.committed_to || 'Uncommitted';
        teamCounts[team] = (teamCounts[team] || 0) + 1;
    });

    const topTeam = Object.entries(teamCounts)
        .filter(([team]) => team !== 'Uncommitted')
        .sort((a, b) => b[1] - a[1])[0];

    document.getElementById('topTeam').textContent = topTeam
        ? `${topTeam[0]} (${topTeam[1]})`
        : '-';

    // Top position
    const positionCounts = {};
    filteredRecruits.forEach(recruit => {
        const pos = recruit.position || 'Unknown';
        positionCounts[pos] = (positionCounts[pos] || 0) + 1;
    });

    const topPosition = Object.entries(positionCounts)
        .sort((a, b) => b[1] - a[1])[0];

    document.getElementById('topPosition').textContent = topPosition
        ? `${topPosition[0]} (${topPosition[1]})`
        : '-';
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
