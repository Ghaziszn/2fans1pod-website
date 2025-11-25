// Utils
const $ = (id) => document.getElementById(id);
const fmtPct = (x) => (x == null || isNaN(x)) ? "—" : (x * 100).toFixed(1) + "%";
const fmt1 = (x) => (x == null || isNaN(x)) ? "—" : Number(x).toFixed(1);

// State
let SOS = {};
let ALL_STATS = []; // Stores stats for ALL teams to compute rankings
let RANKINGS = {};  // Stores pre-computed rankings for each metric
let REDZONE_DATA = {}; // Stores scraped redzone stats (offense)
let OPPONENT_REDZONE_DATA = {}; // Stores scraped opponent redzone stats (defense)

// Load SOS JSON
async function loadSOS() {
  try {
    const res = await fetch(window.SOS_URL);
    SOS = await res.json();
  } catch (e) {
    console.warn("SOS load failed", e);
  }
}

// Load RedZone data (offense)
async function loadRedZone() {
  try {
    const res = await fetch('/api/redzone');
    if (!res.ok) {
      console.warn("RedZone data not available");
      return;
    }
    const data = await res.json();
    // Store teams data (data.teams is the object with team names as keys)
    REDZONE_DATA = data.teams || {};
    console.log(`[RedZone] Loaded offense data for ${Object.keys(REDZONE_DATA).length} teams`);
  } catch (e) {
    console.warn("RedZone load failed", e);
  }
}

// Load Opponent RedZone data (defense)
async function loadOpponentRedZone() {
  try {
    const res = await fetch('/api/opponent_redzone');
    if (!res.ok) {
      console.warn("Opponent RedZone data not available");
      return;
    }
    const data = await res.json();
    // Store teams data (data.teams is the object with team names as keys)
    OPPONENT_REDZONE_DATA = data.teams || {};
    console.log(`[OpponentRedZone] Loaded defense data for ${Object.keys(OPPONENT_REDZONE_DATA).length} teams`);
  } catch (e) {
    console.warn("Opponent RedZone load failed", e);
  }
}

// API
async function api(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

async function loadTeams(year) {
  const rows = await api(`/api/teams?year=${year}`);
  return rows.map(t => t.school).filter(Boolean).sort((a, b) => a.localeCompare(b));
}

async function loadAllStats(year) {
  // Fetch stats for ALL teams to compute rankings
  ALL_STATS = await api(`/api/stats?year=${year}`);
  computeRankings(ALL_STATS);
}

// Metrics Computation
function computeMetricsFromStats(rows) {
  const bucket = {};

  // Find games count first
  const gamesRow = rows.find(r => String(r.statName || "").trim() === "games");
  const games = gamesRow ? Number(gamesRow.statValue) : 0;

  console.log(`[Debug] Team: ${rows[0]?.team}, Games: ${games}, Rows: ${rows.length}`);

  // Helper to determine if a stat is defensive by default (without Opponent suffix)
  const defStats = ["sacks", "tacklesForLoss", "interceptions", "fumblesRecovered", "interceptionTDs", "interceptionYards"];

  for (const r of rows) {
    const statName = String(r.statName || "").trim();
    if (!statName || statName === "games") continue;

    const val = Number(r.statValue);
    if (isNaN(val)) continue;

    // Determine side (Offense vs Defense)
    const isOpponent = statName.endsWith("Opponent");
    const baseName = statName.replace("Opponent", "");

    // Logic: 
    // - If it's a defensive stat (e.g. sacks) and NOT opponent -> Defense
    // - If it's a defensive stat and IS opponent -> Offense (Allowed)
    // - If it's an offensive stat (e.g. yards) and NOT opponent -> Offense
    // - If it's an offensive stat and IS opponent -> Defense (Allowed)
    const isDefBucket = defStats.includes(baseName) ? !isOpponent : isOpponent;

    // Normalize to per-game if we have games count
    // Note: For percentages (3rd down, etc), dividing numerator and denominator by games 
    // preserves the ratio, so it's safe to normalize everything.
    const perGameVal = games > 0 ? val / games : val;

    if (!bucket[baseName]) bucket[baseName] = {};
    if (isDefBucket) bucket[baseName].def = perGameVal;
    else bucket[baseName].off = perGameVal;
  }

  console.log("[Debug] Bucket Keys:", Object.keys(bucket));

  const getVal = (key, type) => bucket[key]?.[type];

  // Helper to safely divide
  const div = (n, d) => (n != null && d > 0) ? n / d : null;

  // Fix: possessionTimeOpponent is stored in bucket["possessionTime"]["def"]
  const topOff = getVal("possessionTime", "off");
  const topDef = getVal("possessionTime", "def");

  const off = {
    ppg: getVal("points", "off"),
    ypg: getVal("totalYards", "off"),
    rushYdsG: getVal("rushingYards", "off"),
    passYdsG: (getVal("netPassingYards", "off") ?? getVal("passingYards", "off")),
    topPct: div(topOff, (topOff || 0) + (topDef || 0)),
    thirdPct: div(getVal("thirdDownConversions", "off"), getVal("thirdDowns", "off")),
    fourthPct: div(getVal("fourthDownConversions", "off"), getVal("fourthDowns", "off")),
    rzPct: div((getVal("redZoneScores", "off") ?? getVal("redzoneScores", "off")), (getVal("redZoneAttempts", "off") ?? getVal("redzoneAttempts", "off"))),
    ydsPerRush: div(getVal("rushingYards", "off"), getVal("rushingAttempts", "off")), // avg/avg = total/total
    giveaways: getVal("turnovers", "off"),
    penalties: getVal("penalties", "off"),
    havoc: null
  };

  const def = {
    ppg: getVal("points", "def"), // Points allowed
    ypg: getVal("totalYards", "def"),
    rushYdsG: getVal("rushingYards", "def"),
    passYdsG: (getVal("netPassingYards", "def") ?? getVal("passingYards", "def")),
    thirdPct: div(getVal("thirdDownConversions", "def"), getVal("thirdDowns", "def")), // Allowed conversion %
    fourthPct: div(getVal("fourthDownConversions", "def"), getVal("fourthDowns", "def")),
    rzPct: div((getVal("redZoneScores", "def") ?? getVal("redzoneScores", "def")), (getVal("redZoneAttempts", "def") ?? getVal("redzoneAttempts", "def"))),
    ydsPerRush: div(getVal("rushingYards", "def"), getVal("rushingAttempts", "def")),
    takeaways: getVal("turnovers", "def"), // Defense takeaways (from turnoversOpponent)
    tfl: getVal("tacklesForLoss", "def"),
    sacks: getVal("sacks", "def"),
    havoc: null
  };

  console.log("[Debug] Offense Obj:", off);
  console.log("[Debug] Defense Obj:", def);

  // Merge RedZone data if available
  const teamName = rows[0]?.team;

  // Merge offensive red zone data
  if (teamName && REDZONE_DATA[teamName]) {
    const rzData = REDZONE_DATA[teamName];
    console.log(`[RedZone] Merging offense data for ${teamName}:`, rzData);

    // Parse redzone percentage from scraped data
    // The "Score %" field is a string like "90.24" (percentage)
    if (rzData["Score %"]) {
      const rzPct = parseFloat(rzData["Score %"]) / 100; // Convert to decimal
      off.rzPct = rzPct;
      console.log(`[RedZone] Set ${teamName} offense RZ% to ${(rzPct * 100).toFixed(1)}%`);
    }
  }

  // Merge defensive red zone data (opponent conversion rate)
  if (teamName && OPPONENT_REDZONE_DATA[teamName]) {
    const oppRzData = OPPONENT_REDZONE_DATA[teamName];
    console.log(`[OpponentRedZone] Merging defense data for ${teamName}:`, oppRzData);

    // Parse opponent redzone percentage from scraped data
    // The "Score %" field is a string like "61.11" (percentage opponents score)
    if (oppRzData["Score %"]) {
      const oppRzPct = parseFloat(oppRzData["Score %"]) / 100; // Convert to decimal
      def.rzPct = oppRzPct;
      console.log(`[OpponentRedZone] Set ${teamName} defense RZ% to ${(oppRzPct * 100).toFixed(1)}%`);
    }
  }

  return { offense: off, defense: def };
}

// Ranking Logic
function computeRankings(allStatsRaw) {
  // Group by team
  const teamMetrics = {};

  // Process raw stats into metrics for every team
  // This is a bit inefficient (O(N*M)) but N is small (~130 teams)
  // We need to group raw rows by team first
  const teamRows = {};
  for (const r of allStatsRaw) {
    if (!teamRows[r.team]) teamRows[r.team] = [];
    teamRows[r.team].push(r);
  }

  for (const [team, rows] of Object.entries(teamRows)) {
    teamMetrics[team] = computeMetricsFromStats(rows);
  }

  // Now extract arrays for each metric to sort and find ranks
  const metrics = [
    "ppg", "ypg", "rushYdsG", "passYdsG", "topPct", "thirdPct", "fourthPct", "rzPct", "ydsPerRush", "takeaways", "giveaways", "penalties", "tfl", "sacks"
  ];

  RANKINGS = { offense: {}, defense: {} };

  for (const side of ["offense", "defense"]) {
    for (const m of metrics) {
      // Filter irrelevant metrics for each side if needed
      // For now, compute all if available

      // Extract values
      const values = Object.values(teamMetrics)
        .map(tm => tm[side][m])
        .filter(v => v != null)
        .sort((a, b) => {
          // Sort order depends on metric
          // Lower is better for: giveaways, penalties (offense), ppg/ypg/etc (defense)
          const lowerIsBetter = (side === "offense" && ["giveaways", "penalties"].includes(m)) ||
            (side === "defense" && !["tfl", "sacks", "takeaways"].includes(m)); // Def: low yards/pts is good, high sacks/tfl is good
          return lowerIsBetter ? a - b : b - a;
        });

      RANKINGS[side][m] = values;
    }
  }
}

function getRank(side, metric, value) {
  if (value == null) return "-";
  const list = RANKINGS[side][metric];
  if (!list) return "-";
  // Find index (1-based)
  // Handle ties by taking the first occurrence
  // Note: list is already sorted best-to-worst
  // Use a small epsilon for float comparison if needed, but exact match usually works for sorted array
  const idx = list.indexOf(value);
  return idx === -1 ? "-" : idx + 1;
}

// Color Coding
function getColorClass(rank, totalTeams = 134) {
  if (rank === "-") return "";
  const pct = rank / totalTeams;
  if (pct <= 0.10) return "rank-elite";      // Top 10% (Green)
  if (pct <= 0.30) return "rank-good";       // Top 30% (Light Green)
  if (pct <= 0.70) return "rank-avg";        // Middle (Yellow/Neutral - though user wants simple colors)
  if (pct <= 0.90) return "rank-poor";       // Bottom 30% (Orange)
  return "rank-bad";                         // Bottom 10% (Red)
}

// Rendering
function renderComparison(containerId, team1, m1, team2, m2, label1, label2) {
  const container = $(containerId);
  container.innerHTML = "";

  // Header
  const header = document.createElement("div");
  header.className = "comp-header";
  header.innerHTML = `
    <div class="col-rank">Rank</div>
    <div class="col-val">Value</div>
    <div class="col-metric">Metric</div>
    <div class="col-val">Value</div>
    <div class="col-rank">Rank</div>
  `;
  container.appendChild(header);

  const metricsMap = [
    { label: "Points/Game", offKey: "ppg", defKey: "ppg" },
    { label: "Yards/Game", offKey: "ypg", defKey: "ypg" },
    { label: "TOP %", offKey: "topPct", defKey: null }, // Def doesn't usually have TOP
    { label: "3rd Down %", offKey: "thirdPct", defKey: "thirdPct" },
    { label: "4th Down %", offKey: "fourthPct", defKey: "fourthPct" },
    { label: "RZ Scoring %", offKey: "rzPct", defKey: "rzPct" },
    { label: "Rush Yds/Game", offKey: "rushYdsG", defKey: "rushYdsG" },
    { label: "Yds/Rush", offKey: "ydsPerRush", defKey: "ydsPerRush" },
    { label: "Pass Yds/Game", offKey: "passYdsG", defKey: "passYdsG" },
    { label: "Takeaways/G", offKey: null, defKey: "takeaways" },
    { label: "Giveaways/G", offKey: "giveaways", defKey: null },
    { label: "Penalties/G", offKey: "penalties", defKey: null },
    { label: "TFL/Game", offKey: null, defKey: "tfl" },
    { label: "Sacks/Game", offKey: null, defKey: "sacks" },
  ];

  console.log(`[renderComparison] ${team1} (${label1}) vs ${team2} (${label2})`);
  console.log(`[renderComparison] m1:`, m1);
  console.log(`[renderComparison] m2:`, m2);

  metricsMap.forEach(row => {
    const el = document.createElement("div");
    el.className = "comp-row";

    // Left Side (Team 1 - Offense usually)
    // If label1 is "Offense", use offKey. If "Defense", use defKey.
    const side1 = label1.toLowerCase().includes("off") ? "offense" : "defense";
    const key1 = side1 === "offense" ? row.offKey : row.defKey;

    let val1 = "-", rank1 = "-", class1 = "";
    if (key1 && m1[side1][key1] != null) {
      val1 = m1[side1][key1];
      rank1 = getRank(side1, key1, val1);
      class1 = getColorClass(rank1);
      val1 = (key1.includes("Pct") ? fmtPct(val1) : fmt1(val1));
    }

    // Right Side (Team 2 - Defense usually)
    const side2 = label2.toLowerCase().includes("off") ? "offense" : "defense";
    const key2 = side2 === "offense" ? row.offKey : row.defKey;

    let val2 = "-", rank2 = "-", class2 = "";
    if (key2 && m2[side2][key2] != null) {
      val2 = m2[side2][key2];
      rank2 = getRank(side2, key2, val2);
      class2 = getColorClass(rank2);
      val2 = (key2.includes("Pct") ? fmtPct(val2) : fmt1(val2));
    } else {
      console.log(`[renderComparison] Missing: ${row.label}, key2=${key2}, side2=${side2}, m2[${side2}][${key2}]=`, m2[side2]?.[key2]);
    }

    el.innerHTML = `
      <div class="col-rank ${class1}">${rank1}</div>
      <div class="col-val">${val1}</div>
      <div class="col-metric">${row.label}</div>
      <div class="col-val">${val2}</div>
      <div class="col-rank ${class2}">${rank2}</div>
    `;
    container.appendChild(el);
  });
}


// Main Event Listeners
document.addEventListener("DOMContentLoaded", async () => {
  console.log("[App] Version 999999 loaded");
  console.log("[Auto-load] Starting...");
  await loadSOS();
  console.log("[Auto-load] SOS loaded");

  // Load RedZone data (both offense and defense)
  await Promise.all([
    loadRedZone(),
    loadOpponentRedZone()
  ]);
  console.log("[Auto-load] RedZone data loaded (offense + defense)");

  // Auto-load teams on page load
  try {
    $("status").textContent = "Loading teams & stats…";
    const year = Number($("seasonYear").value) || 2025;
    console.log("[Auto-load] Year:", year);

    // Parallel load
    console.log("[Auto-load] Fetching teams and stats...");
    const [names, _] = await Promise.all([
      loadTeams(year),
      loadAllStats(year)
    ]);
    console.log("[Auto-load] Received", names.length, "teams");

    const t1 = $("team1"), t2 = $("team2");
    t1.innerHTML = ""; t2.innerHTML = "";
    for (const n of names) {
      const o1 = document.createElement("option"); o1.value = o1.textContent = n; t1.appendChild(o1);
      const o2 = document.createElement("option"); o2.value = o2.textContent = n; t2.appendChild(o2);
    }
    $("status").textContent = `Ready. Loaded ${names.length} teams.`;
    console.log("[Auto-load] Complete!");

    // Check for URL parameters (from betting page navigation)
    const urlParams = new URLSearchParams(window.location.search);
    const team1ParamRaw = urlParams.get('team1');
    const team2ParamRaw = urlParams.get('team2');

    console.log(`[URL Params] Search: "${window.location.search}"`);
    console.log(`[URL Params] Raw params: team1="${team1ParamRaw}", team2="${team2ParamRaw}"`);

    if (team1ParamRaw && team2ParamRaw) {
      const team1Param = team1ParamRaw.trim();
      const team2Param = team2ParamRaw.trim();
      console.log(`[URL Params] Available teams (first 5):`, names.slice(0, 5));

      // Debug: search for partial matches
      const dukeCheck = names.filter(n => n.toLowerCase().includes("duke"));
      const ncCheck = names.filter(n => n.toLowerCase().includes("north carolina"));
      console.log(`[Debug] Teams containing 'duke':`, dukeCheck);
      console.log(`[Debug] Teams containing 'north carolina':`, ncCheck);

      // Helper to find team (exact or case-insensitive)
      const findTeam = (t) => {
        if (names.includes(t)) return t;
        return names.find(n => n.toLowerCase() === t.toLowerCase());
      };

      const team1Match = findTeam(team1Param);
      const team2Match = findTeam(team2Param);

      console.log(`[URL Params] Matches: team1="${team1Match}", team2="${team2Match}"`);

      if (team1Match && team2Match) {
        // Set the dropdown values
        $("team1").value = team1Match;
        $("team2").value = team2Match;

        console.log(`[URL Params] Set dropdowns to: team1=${$("team1").value}, team2=${$("team2").value}`);

        // Automatically trigger the comparison
        console.log("[URL Params] Auto-triggering comparison...");
        setTimeout(() => {
          runComparison();
        }, 500); // Increased delay to ensure DOM is ready
      } else {
        console.warn(`[URL Params] Teams not found. team1Match=${team1Match}, team2Match=${team2Match}`);
        $("status").textContent = `Could not find teams: "${team1Param}" or "${team2Param}"`;
      }
    }
  } catch (e) {
    $("status").textContent = "Failed to load data";
    console.error("[Auto-load] Error:", e);
  }

  // Comparison function (extracted for reuse)
  function runComparison() {
    const year = Number($("seasonYear").value) || 2025;
    const teamA = $("team1").value;
    const teamB = $("team2").value;
    if (!teamA || !teamB) { $("status").textContent = "Pick both teams"; return; }

    const rowsA = ALL_STATS.filter(r => r.team === teamA);
    const rowsB = ALL_STATS.filter(r => r.team === teamB);

    if (!rowsA.length || !rowsB.length) {
      $("status").textContent = "Stats not found for selected teams.";
      return;
    }

    const mA = computeMetricsFromStats(rowsA);
    const mB = computeMetricsFromStats(rowsB);

    // Update headers with team names and roles (split headers)
    $("grid1HeaderLeft").textContent = `${teamA} Offense`;
    $("grid1HeaderRight").textContent = `${teamB} Defense`;
    $("grid2HeaderLeft").textContent = `${teamB} Offense`;
    $("grid2HeaderRight").textContent = `${teamA} Defense`;

    // Render
    // Grid 1: Team 1 Offense vs Team 2 Defense
    renderComparison("grid1", teamA, mA, teamB, mB, "Offense", "Defense");

    // Grid 2: Team 2 Offense vs Team 1 Defense
    renderComparison("grid2", teamB, mB, teamA, mA, "Offense", "Defense");

    $("status").textContent = `Comparison generated for ${teamA} vs ${teamB}`;
  }

  // Button click handler calls the comparison function
  $("runCompare").addEventListener("click", () => {
    runComparison();
  });
});
