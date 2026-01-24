// Betting Lines Page JavaScript

const $ = (id) => document.getElementById(id);

let ATS_DATA = {}; // Stores ATS records by team name
let VSIN_SPLITS = {}; // Stores VSIN betting splits by matchup key
const YEAR = 2025;

// Load ATS data on page load
async function loadATSData() {
    try {
        const res = await fetch(`/api/ats?year=${YEAR}`);
        if (!res.ok) {
            console.warn("ATS data not available");
            return;
        }
        const data = await res.json();

        // Convert array to object keyed by team name for easy lookup
        data.forEach(team => {
            ATS_DATA[team.team] = {
                wins: team.atsWins || 0,
                losses: team.atsLosses || 0,
                pushes: team.atsPushes || 0
            };
        });

        console.log(`[ATS] Loaded data for ${Object.keys(ATS_DATA).length} teams`);
    } catch (e) {
        console.error("Failed to load ATS data:", e);
    }
}

// Load VSIN betting splits data
async function loadVSINSplits() {
    try {
        const res = await fetch('/api/vsin_splits');
        if (!res.ok) {
            console.warn("VSIN splits data not available");
            return;
        }
        const data = await res.json();

        // Convert array to object keyed by matchup (away@home)
        data.games.forEach(game => {
            const key = `${normalizeTeamName(game.away_team)}@${normalizeTeamName(game.home_team)}`;
            VSIN_SPLITS[key] = game;
        });

        console.log(`[VSIN] Loaded splits for ${Object.keys(VSIN_SPLITS).length} games`);
    } catch (e) {
        console.error("Failed to load VSIN splits:", e);
    }
}

// Normalize team names for matching between CFBD and VSIN
function normalizeTeamName(name) {
    // Special case mappings that don't follow patterns
    const mapping = {
        // Miami variations
        'Miami': 'Miami FL',
        'Miami (OH)': 'Miami OH',

        // Other common variations
        'UMass': 'Massachusetts',
        'Massachusetts': 'UMass',
        'UCF': 'Central Florida',
        'Central Florida': 'UCF',
        'SMU': 'Southern Methodist',
        'Southern Methodist': 'SMU',
        'BYU': 'Brigham Young',
        'Brigham Young': 'BYU',
        'USC': 'Southern California',
        'Southern California': 'USC',
        'UNLV': 'Nevada Las Vegas',
        'Nevada Las Vegas': 'UNLV',
        'LSU': 'Louisiana ST',
        'FIU': 'Florida International',
        'UAB': 'Alabama Birmingham',
        'UTEP': 'Texas El Paso',
        'UTSA': 'Texas San Antonio',
        'ULM': 'Louisiana Monroe',
    };

    // Try direct mapping first
    if (mapping[name]) return mapping[name];

    // Automatically convert any team ending in "State" to "ST"
    // CFBD uses "Florida State", VSIN uses "Florida ST"
    if (name.endsWith(' State')) {
        return name.replace(' State', ' ST');
    }

    // Return original if no mapping found
    return name;
}

// Get VSIN splits for a matchup
function getVSINSplits(awayTeam, homeTeam) {
    const key = `${normalizeTeamName(awayTeam)}@${normalizeTeamName(homeTeam)}`;
    return VSIN_SPLITS[key] || null;
}

// Load betting lines for a specific week
async function loadLines(weekIdentifier) {
    try {
        let title = `Week ${weekIdentifier}`;
        let seasonType = "regular";
        let week = weekIdentifier;

        // Handle postseason identifiers (e.g., "postseason-1")
        if (typeof weekIdentifier === 'string' && weekIdentifier.includes('postseason')) {
            const parts = weekIdentifier.split('-');
            seasonType = parts[0];
            week = parts[1];
            title = "Bowls / CFP";
        }

        $("status").textContent = `Loading ${title} betting lines...`;
        $("status").className = "loading";
        $("matchupsContainer").innerHTML = "";

        const res = await fetch(`/api/lines?year=${YEAR}&week=${week}&seasonType=${seasonType}`);
        if (!res.ok) {
            throw new Error(`Failed to fetch lines: ${res.status}`);
        }

        const data = await res.json();
        console.log(`[Lines] Loaded ${data.length} matchups for week ${week}`);

        if (data.length === 0) {
            $("status").textContent = `No betting lines available for Week ${week}`;
            $("status").className = "no-data";
            return;
        }

        renderMatchups(data);
        $("status").style.display = "none";
    } catch (e) {
        console.error("Failed to load lines:", e);
        $("status").textContent = "Failed to load betting lines. Please try again.";
        $("status").className = "error";
    }
}

// Get ATS record string for a team
function getATSRecord(teamName) {
    const ats = ATS_DATA[teamName];
    if (!ats) return "N/A";

    const total = ats.wins + ats.losses;
    if (total === 0) return "0-0 ATS";

    const record = `${ats.wins}-${ats.losses}`;
    if (ats.pushes > 0) {
        return `${record}-${ats.pushes} ATS`;
    }
    return `${record} ATS`;
}

// Get CSS class for ATS record (good/bad)
function getATSClass(teamName) {
    const ats = ATS_DATA[teamName];
    if (!ats) return "";

    const total = ats.wins + ats.losses;
    if (total === 0) return "";

    const winPct = ats.wins / total;
    if (winPct >= 0.6) return "ats-good";
    if (winPct <= 0.4) return "ats-bad";
    return "";
}

// Render matchups in scoreboard format
function renderMatchups(matchups) {
    const container = $("matchupsContainer");
    container.innerHTML = "";

    matchups.forEach(game => {
        const awayTeam = game.awayTeam;
        const homeTeam = game.homeTeam;

        const card = document.createElement("div");
        card.className = "matchup-card";
        card.style.cursor = "pointer";
        card.title = "Click to view matchup analysis";

        // Add click handler to navigate to calculator
        card.addEventListener("click", () => {
            const team1 = encodeURIComponent(awayTeam);
            const team2 = encodeURIComponent(homeTeam);
            window.location.href = `/calculator?team1=${team1}&team2=${team2}`;
        });

        // Build matchup header
        let headerHTML = `<div class="matchup-header">`;

        // Away team
        headerHTML += `
      <div class="team-row">
        <span class="team-name">${awayTeam}</span>
        <span class="ats-record ${getATSClass(awayTeam)}">${getATSRecord(awayTeam)}</span>
      </div>
    `;

        // VS divider
        headerHTML += `<div class="vs-divider">@</div>`;

        // Home team
        headerHTML += `
      <div class="team-row">
        <span class="team-name">${homeTeam}</span>
        <span class="ats-record ${getATSClass(homeTeam)}">${getATSRecord(homeTeam)}</span>
      </div>
    `;

        headerHTML += `</div>`;

        // Build betting info section
        let bettingHTML = `<div class="betting-info">`;

        // Get VSIN splits for this matchup
        const vsinSplits = getVSINSplits(awayTeam, homeTeam);

        // Find specific provider lines
        const draftKingsLine = game.lines?.find(l => l.provider === "DraftKings");
        const espnBetLine = game.lines?.find(l => l.provider === "ESPN Bet");

        let hasAnyData = false;

        // Spread from DraftKings with VSIN percentages
        if (draftKingsLine) {
            const spread = draftKingsLine.formattedSpread || draftKingsLine.spread;
            const spreadOpen = draftKingsLine.spreadOpen;

            if (spread) {
                hasAnyData = true;
                let spreadPercentages = '';

                if (vsinSplits && vsinSplits.spread) {
                    const awayBets = vsinSplits.spread.away_bets_pct;
                    const homeBets = vsinSplits.spread.home_bets_pct;
                    const awayHandle = vsinSplits.spread.away_handle_pct;
                    const homeHandle = vsinSplits.spread.home_handle_pct;

                    spreadPercentages = `
                        <div class="inline-splits">
                            <span class="split-label">Public:</span>
                            <span class="split-value">${awayBets}% / ${homeBets}%</span>
                            <span class="split-separator">•</span>
                            <span class="split-label">Sharp:</span>
                            <span class="split-value">${awayHandle}% / ${homeHandle}%</span>
                        </div>
                    `;
                }

                bettingHTML += `
          <div class="betting-line">
            <div class="line-main">
              <span class="line-label">Spread (DraftKings):</span>
              <span class="line-value spread-value">${spread}${spreadOpen ? ` (Open: ${spreadOpen})` : ""}</span>
            </div>
            ${spreadPercentages}
          </div>
        `;
            }
        }

        // Over/Under from ESPN Bet with VSIN percentages
        if (espnBetLine) {
            const overUnder = espnBetLine.overUnder;
            const overUnderOpen = espnBetLine.overUnderOpen;

            if (overUnder) {
                hasAnyData = true;
                let totalPercentages = '';

                if (vsinSplits && vsinSplits.total) {
                    const overBets = vsinSplits.total.over_bets_pct;
                    const underBets = vsinSplits.total.under_bets_pct;
                    const overHandle = vsinSplits.total.over_handle_pct;
                    const underHandle = vsinSplits.total.under_handle_pct;

                    totalPercentages = `
                        <div class="inline-splits">
                            <span class="split-label">Public:</span>
                            <span class="split-value">${overBets}% O / ${underBets}% U</span>
                            <span class="split-separator">•</span>
                            <span class="split-label">Sharp:</span>
                            <span class="split-value">${overHandle}% O / ${underHandle}% U</span>
                        </div>
                    `;
                }

                bettingHTML += `
          <div class="betting-line">
            <div class="line-main">
              <span class="line-label">Over/Under (ESPN Bet):</span>
              <span class="line-value">${overUnder}${overUnderOpen ? ` (Open: ${overUnderOpen})` : ""}</span>
            </div>
            ${totalPercentages}
          </div>
        `;
            }
        }

        // If no data from preferred providers
        if (!hasAnyData) {
            bettingHTML += `<div class="no-data">No betting lines available from DraftKings or ESPN Bet</div>`;
        }

        bettingHTML += `</div>`;

        // Add VSIN betting splits section (keep for moneyline data)
        if (vsinSplits) {
            const splitsHTML = renderVSINSplits(vsinSplits, awayTeam, homeTeam);
            bettingHTML += splitsHTML;
        }

        card.innerHTML = headerHTML + bettingHTML;
        container.appendChild(card);
    });
}

// Render VSIN betting splits section
function renderVSINSplits(splits, awayTeam, homeTeam) {
    const spread = splits.spread;
    const awayBets = spread.away_bets_pct;
    const homeBets = spread.home_bets_pct;
    const awayHandle = spread.away_handle_pct;
    const homeHandle = spread.home_handle_pct;

    // Determine if public and sharp money agree
    const publicFavorsAway = awayBets > homeBets;
    const sharpFavorsAway = awayHandle > homeHandle;
    const agreement = publicFavorsAway === sharpFavorsAway;

    // Color coding based on agreement
    let indicatorClass = 'splits-neutral';
    let indicatorText = '';

    if (agreement) {
        const strongAgreement = Math.abs(awayBets - homeBets) > 20 && Math.abs(awayHandle - homeHandle) > 20;
        if (strongAgreement) {
            indicatorClass = 'splits-strong-agree';
            indicatorText = '🟢 Public & Sharp Agree';
        } else {
            indicatorClass = 'splits-agree';
            indicatorText = '✓ Aligned';
        }
    } else {
        indicatorClass = 'splits-disagree';
        indicatorText = '⚠️ Public vs Sharp';
    }

    return `
        <div class="vsin-splits">
            <div class="splits-header ${indicatorClass}">
                <span class="splits-title">Betting Splits</span>
                <span class="splits-indicator">${indicatorText}</span>
            </div>
            <div class="splits-content">
                <div class="splits-row">
                    <span class="splits-label">Public (Bets):</span>
                    <span class="splits-values">
                        <span class="split-pct ${awayBets > homeBets ? 'split-favorite' : ''}">${awayTeam}: ${awayBets}%</span>
                        <span class="split-separator">|</span>
                        <span class="split-pct ${homeBets > awayBets ? 'split-favorite' : ''}">${homeTeam}: ${homeBets}%</span>
                    </span>
                </div>
                <div class="splits-row">
                    <span class="splits-label">Sharp (Handle):</span>
                    <span class="splits-values">
                        <span class="split-pct ${awayHandle > homeHandle ? 'split-favorite' : ''}">${awayTeam}: ${awayHandle}%</span>
                        <span class="split-separator">|</span>
                        <span class="split-pct ${homeHandle > awayHandle ? 'split-favorite' : ''}">${homeTeam}: ${homeHandle}%</span>
                    </span>
                </div>
            </div>
        </div>
    `;
}

// Calculate current week based on season start date
function getCurrentWeek() {
    // TODO: Implement proper date-based week calculation
    // For now, returning week 14 as specified by user
    return 14;

    /* Original calculation - needs season start date verification
    const seasonStart = new Date('2025-08-31T00:00:00');
    const now = new Date();
    const daysSinceStart = Math.floor((now - seasonStart) / (1000 * 60 * 60 * 24));
    const weeksSinceStart = Math.floor(daysSinceStart / 7);
    let currentWeek = weeksSinceStart + 1;
    currentWeek = Math.max(1, Math.min(15, currentWeek));
    return currentWeek;
    */
}

// Event listeners
document.addEventListener("DOMContentLoaded", async () => {
    console.log("[Betting] Page loaded");

    // Load ATS data and VSIN splits in parallel
    await Promise.all([
        loadATSData(),
        loadVSINSplits()
    ]);

    // Calculate and set current week
    const weekSelect = $("weekSelect");
    const currentWeek = getCurrentWeek();
    weekSelect.value = currentWeek;

    // Load current week
    await loadLines(currentWeek);

    // Week selector change handler
    weekSelect.addEventListener("change", (e) => {
        const week = e.target.value;
        loadLines(week);
    });
});
