// Travel Concierge Dashboard — app.js

// ─── Security helpers ──────────────────────────────────────────────────────
function esc(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;');
}

// ─── Tab routing ───────────────────────────────────────────────────────────
const tabs = document.querySelectorAll('.tab');
const panels = document.querySelectorAll('.tab-panel');

tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    tabs.forEach(t => t.classList.remove('active'));
    panels.forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
    loadTabData(tab.dataset.tab);
  });
});

function loadTabData(tab) {
  switch (tab) {
    case 'trips':     loadTrips(); break;
    case 'scout':     loadScoutSelector(); break;
    case 'hotels':    loadHotelSelector(); break;
    case 'itinerary': loadItinerarySelector(); break;
    case 'budget':    loadBudget(); break;
    case 'crons':     loadCrons(); break;
  }
}

// ─── SSE live updates ──────────────────────────────────────────────────────
const indicator = document.getElementById('live-indicator');
let eventSource;

function connectSSE() {
  eventSource = new EventSource('/events');

  eventSource.onopen = () => {
    indicator.textContent = '\uD83D\uDFE2 live';
  };

  eventSource.onmessage = (e) => {
    try {
      const event = JSON.parse(e.data);
      if (event.type === 'trips_updated') {
        const activeTab = document.querySelector('.tab.active')?.dataset.tab;
        if (activeTab) loadTabData(activeTab);
      }
    } catch (err) {
      // ignore parse errors on keepalive comments
    }
  };

  eventSource.onerror = () => {
    indicator.textContent = '\uD83D\uDD34 disconnected';
    eventSource.close();
    setTimeout(connectSSE, 5000);
  };
}

connectSSE();

// ─── Price classification ──────────────────────────────────────────────────
function classifyPrice(current, history) {
  const prices = history
    .filter(p => p.best_price || p.price_per_night || p.price)
    .map(p => p.best_price || p.price_per_night || p.price);
  if (prices.length < 3) return { badge: '\u23F3', label: 'No data yet', cls: 'badge-grey' };
  const avg = prices.reduce((a, b) => a + b, 0) / prices.length;
  const pct = ((current - avg) / avg) * 100;
  if (pct <= -15) return { badge: '\uD83D\uDFE2', label: 'Buy now',    cls: 'badge-green'  };
  if (pct <= -5)  return { badge: '\uD83D\uDFE1', label: 'Good deal',  cls: 'badge-yellow' };
  if (pct <= 5)   return { badge: '\uD83D\uDFE0', label: 'Fair',       cls: 'badge-orange' };
  return              { badge: '\uD83D\uDD34', label: 'Above avg', cls: 'badge-red'    };
}

function phaseBadge(phase) {
  const map = {
    '1-complete':       ['Phase 1',       'badge-grey'   ],
    '2-running':        ['Phase 2 \u27F3', 'badge-blue'   ],
    '2-complete':       ['Phase 2',        'badge-blue'   ],
    '2.5-checkpoint':   ['Review',         'badge-yellow' ],
    '3-complete':       ['Phase 3',        'badge-orange' ],
    '4-active':         ['Active \u2713',  'badge-green'  ],
    'active':           ['Active \u2713',  'badge-green'  ],
  };
  const [label, cls] = map[phase] || ['Unknown', 'badge-grey'];
  return `<span class="badge ${cls}">${label}</span>`;
}

// ─── Trips tab ─────────────────────────────────────────────────────────────
async function loadTrips() {
  const grid = document.getElementById('trips-grid');
  try {
    const res = await fetch('/api/trips');
    const { trips } = await res.json();

    if (!trips.length) {
      grid.innerHTML = '<p class="empty-state">No trips yet. Run <code>/plan-trip</code> in Claude Code to create one.</p>';
      return;
    }

    grid.innerHTML = trips.map(trip => {
      const id = trip._trip_id;
      const route = trip.cities ? trip.cities.map(c => esc(c.name)).join(' \u2192 ') : esc(id);
      const firstCity = trip.cities?.[0];
      const lastCity = trip.cities?.[trip.cities.length - 1];
      const dates = firstCity ? `${esc(firstCity.arrive)} \u2013 ${esc(lastCity?.depart || '')}` : '';
      const phase = phaseBadge(trip.phase || 'active');
      const budget = trip.budget_usd ? `$${esc(trip.budget_usd)} USD` : '\u2014';
      return `
        <div class="trip-card" data-trip-id="${esc(id)}">
          <div class="trip-card-header">
            <span class="trip-id">${esc(id)}</span>
            ${phase}
          </div>
          <div class="trip-route">${route}</div>
          <div class="trip-meta">${dates}${dates ? ' \u00B7 ' : ''}${esc(trip.travellers || 1)} traveller(s) \u00B7 Budget: ${budget}</div>
        </div>`;
    }).join('');
  } catch (e) {
    grid.innerHTML = `<p class="error">Failed to load trips: ${e.message}</p>`;
  }
}

// Trip card clicks use event delegation to avoid onclick injection
document.getElementById('trips-grid').addEventListener('click', (e) => {
  const card = e.target.closest('[data-trip-id]');
  if (card) selectTrip(card.dataset.tripId);
});

function selectTrip(tripId) {
  // Switch to itinerary tab with this trip pre-selected
  document.querySelector('[data-tab="itinerary"]').click();
  loadItinerary(tripId);
}

// ─── Scout tab ─────────────────────────────────────────────────────────────
let currentScoutTrip = null;

async function loadScoutSelector() {
  const sel = document.getElementById('scout-trip-selector');
  try {
    const { trips } = await (await fetch('/api/trips')).json();
    if (!trips.length) {
      sel.innerHTML = '';
      document.getElementById('scout-content').innerHTML = '<p class="empty-state">No trips yet.</p>';
      return;
    }
    sel.innerHTML = `<select id="scout-select">
      <option value="">All trips</option>
      ${trips.map(t => `<option value="${esc(t._trip_id)}"${currentScoutTrip === t._trip_id ? ' selected' : ''}>${esc(t._trip_id)}</option>`).join('')}
    </select>`;
    document.getElementById('scout-select').addEventListener('change', function () {
      currentScoutTrip = this.value || null;
      loadScout(currentScoutTrip);
    });
    loadScout(currentScoutTrip);
  } catch (e) {
    sel.innerHTML = `<p class="error">Failed to load trips</p>`;
  }
}

async function loadScout(filterTripId) {
  const el = document.getElementById('scout-content');
  el.innerHTML = '<p class="empty-state">Loading...</p>';
  try {
    const { flights } = await (await fetch('/api/flights/all')).json();

    const items = filterTripId ? flights.filter(f => f._trip_id === filterTripId) : flights;

    if (!items.length) {
      el.innerHTML = '<p class="empty-state">No flight routes tracked yet. Run <code>/check-flights</code> in Claude Code.</p>';
      return;
    }

    el.innerHTML = items.map(leg => {
      const history = leg.price_history || [];
      const currentPrice = history.filter(h => h.price).slice(-1)[0]?.price || null;
      const classification = currentPrice && history.filter(h => h.price).length >= 3
        ? classifyPrice(currentPrice, history)
        : null;
      const prices = history.map(p => p.price).filter(Boolean);
      const minP = prices.length ? Math.min(...prices) : null;
      const maxP = prices.length ? Math.max(...prices) : null;
      const isTracked = leg._source === 'tracked';

      return `
        <div class="route-card">
          <div class="route-header">
            <span class="route-label">${esc(leg.from) || '?'} \u2192 ${esc(leg.to) || '?'}</span>
            <span class="route-date">${esc(leg.date)}</span>
            <span class="trip-ref">${esc(leg._trip_id || '\u2014')}</span>
          </div>
          <div class="route-price">
            ${currentPrice ? `<span class="price-current">$${esc(currentPrice)}</span>` : '<span class="price-na">No price data</span>'}
            ${classification ? `<span class="badge ${esc(classification.cls)}">${esc(classification.badge)} ${esc(classification.label)}</span>` : ''}
            ${!isTracked ? '<span class="badge badge-grey">Research</span>' : ''}
          </div>
          ${minP && maxP ? `<div class="price-range">Range: $${esc(minP)} \u2013 $${esc(maxP)} (${esc(history.length)} checks)</div>` : ''}
          ${leg.booked ? '<div class="booked-badge">\u2705 Booked</div>' : ''}
        </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<p class="error">Failed to load flight data: ${e.message}</p>`;
  }
}

// ─── Hotels tab ────────────────────────────────────────────────────────────
// Single source of truth: /api/hotels/tracked (reads hotelclaw/data/tracked.json)
// Same file the cron job uses — always in sync.

let currentHotelsTrip = null;

async function loadHotelSelector() {
  const sel = document.getElementById('hotels-trip-selector');
  try {
    const { trips } = await (await fetch('/api/trips')).json();
    if (!trips.length) {
      sel.innerHTML = '';
      document.getElementById('hotels-content').innerHTML = '<p class="empty-state">No trips yet.</p>';
      return;
    }
    sel.innerHTML = `<select id="hotels-select">
      <option value="">All trips</option>
      ${trips.map(t => `<option value="${esc(t._trip_id)}"${currentHotelsTrip === t._trip_id ? ' selected' : ''}>${esc(t._trip_id)}</option>`).join('')}
    </select>`;
    document.getElementById('hotels-select').addEventListener('change', function() {
      currentHotelsTrip = this.value || null;
      loadHotels(currentHotelsTrip);
    });
    loadHotels(currentHotelsTrip);
  } catch (e) {
    sel.innerHTML = `<p class="error">Failed to load trips</p>`;
  }
}

async function loadHotels(filterTripId) {
  const el = document.getElementById('hotels-content');
  el.innerHTML = '<p class="empty-state">Loading...</p>';
  try {
    // Source: /api/hotels/all — merges accommodation.json research options + hotelclaw tracked prices
    const { hotels } = await fetch('/api/hotels/all').then(r => r.json());

    const props = filterTripId ? hotels.filter(h => h._trip_id === filterTripId) : hotels;

    if (!props.length) {
      el.innerHTML = '<p class="empty-state">No hotels found. Use <code>/find-hotels</code> to research properties.</p>';
      return;
    }

    el.innerHTML = props.map(prop => {
      const history = prop.price_history || [];
      const latest = history.filter(h => h.price_per_night).slice(-1)[0];
      const trackedPrice = latest?.price_per_night || null;
      const displayPrice = trackedPrice || prop.nightly_rate_usd || null;
      const isTracked = prop._source === 'tracked';
      const classification = isTracked && trackedPrice && history.filter(h => h.price_per_night).length >= 3
        ? classifyPrice(trackedPrice, history.map(p => ({ price: p.price_per_night })))
        : null;
      const checks = history.filter(h => h.price_per_night).length;
      const lastChecked = history.slice(-1)[0]?.timestamp
        ? new Date(history.slice(-1)[0].timestamp).toLocaleString('en-GB', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
        : null;
      const tripLabel = prop._trip_id || prop.city || '';

      return `
        <div class="route-card">
          <div class="route-header">
            <span class="route-label">${esc(prop.name)}</span>
            <span class="route-date">${esc(prop.city)} \u00B7 ${esc(prop.nights)} nights</span>
            <span class="trip-ref">${esc(tripLabel)}</span>
          </div>
          <div class="route-price">
            ${displayPrice
              ? `<span class="price-current">$${esc(displayPrice)}/night${!isTracked ? ' <small>(est.)</small>' : ''}</span>`
              : '<span class="price-na">No price data</span>'}
            ${classification
              ? `<span class="badge ${esc(classification.cls)}">${esc(classification.badge)} ${esc(classification.label)}</span>`
              : isTracked
                ? '<span class="badge badge-grey">\u23F3 Tracking</span>'
                : '<span class="badge badge-grey">Research</span>'}
          </div>
          ${isTracked
            ? `<div class="price-range">${esc(checks)} checks${lastChecked ? ' \u00B7 last ' + esc(lastChecked) : ''}${prop.target_price ? ' \u00B7 target $' + esc(prop.target_price) + '/night' : ''}</div>`
            : prop.notes ? `<div class="price-range">${esc(prop.notes.length > 120 ? prop.notes.slice(0, 120) + '\u2026' : prop.notes)}</div>` : ''}
          ${prop.url ? `<a class="book-link" href="${esc(prop.url)}" target="_blank" rel="noopener">Book \u2192</a>` : ''}
          ${prop.booked ? '<div class="booked-badge">\u2705 Booked</div>' : ''}
        </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<p class="error">Failed to load hotel data: ${e.message}</p>`;
  }
}

// ─── Itinerary tab ─────────────────────────────────────────────────────────
let currentItineraryTrip = null;

async function loadItinerarySelector() {
  const sel = document.getElementById('itinerary-trip-selector');
  try {
    const { trips } = await (await fetch('/api/trips')).json();
    if (!trips.length) {
      sel.innerHTML = '';
      document.getElementById('itinerary-view').innerHTML = '<p class="empty-state">No trips yet.</p>';
      return;
    }
    sel.innerHTML = `<select id="trip-select" onchange="loadItinerary(this.value)">
      <option value="">Select a trip...</option>
      ${trips.map(t => `<option value="${esc(t._trip_id)}"${currentItineraryTrip === t._trip_id ? ' selected' : ''}>${esc(t._trip_id)}</option>`).join('')}
    </select>`;
    // Restore previous selection, or auto-select first trip with an itinerary
    if (currentItineraryTrip) {
      document.getElementById('trip-select').value = currentItineraryTrip;
      loadItinerary(currentItineraryTrip);
    } else {
      // Try trips in order until we find one with an itinerary
      for (const trip of trips) {
        try {
          const res = await fetch(`/api/trips/${trip._trip_id}/itinerary`);
          if (res.ok) {
            document.getElementById('trip-select').value = trip._trip_id;
            loadItinerary(trip._trip_id);
            break;
          }
        } catch (e) {
          // skip
        }
      }
    }
  } catch (e) {
    sel.innerHTML = `<p class="error">Failed to load trips</p>`;
  }
}

async function loadItinerary(tripId) {
  if (!tripId) return;
  currentItineraryTrip = tripId;
  const view = document.getElementById('itinerary-view');
  const editDiv = document.getElementById('itinerary-edit');

  try {
    const res = await fetch(`/api/trips/${tripId}/itinerary`);
    if (!res.ok) {
      view.innerHTML = '<p class="empty-state">No itinerary yet for this trip.</p>';
      view.style.display = 'block';
      editDiv.style.display = 'none';
      return;
    }
    const { content } = await res.json();
    view.innerHTML = `
      <div class="itinerary-content" id="itinerary-rendered">${markdownToHtml(content)}</div>
      <button class="btn-secondary" id="edit-itinerary-btn">Edit</button>`;
    // Use stored reference — no inline data in attributes
    document.getElementById('edit-itinerary-btn').addEventListener('click', () => {
      startEditItinerary(tripId, content);
    });
    view.style.display = 'block';
    editDiv.style.display = 'none';
  } catch (e) {
    view.innerHTML = `<p class="error">Failed to load itinerary: ${e.message}</p>`;
  }
}

function startEditItinerary(tripId, content) {
  document.getElementById('itinerary-view').style.display = 'none';
  const editDiv = document.getElementById('itinerary-edit');
  editDiv.style.display = 'block';
  document.getElementById('itinerary-textarea').value = content;

  document.getElementById('save-itinerary').onclick = async () => {
    const newContent = document.getElementById('itinerary-textarea').value;
    try {
      const res = await fetch(`/api/trips/${tripId}/itinerary`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newContent }),
      });
      if (!res.ok) throw new Error('Save failed');
      loadItinerary(tripId);
    } catch (e) {
      alert('Failed to save: ' + e.message);
    }
  };

  document.getElementById('cancel-edit').onclick = () => loadItinerary(tripId);
}

// Minimal markdown to HTML: headers, bold, bullet lists, line breaks
// HTML-escapes raw text first to prevent XSS from itinerary content
function markdownToHtml(md) {
  if (!md) return '';
  // Escape HTML entities before applying markdown transforms
  const safe = md
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  return safe
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
    .replace(/\n\n/g, '<br><br>')
    .replace(/\n/g, '<br>');
}

// ─── Budget tab ─────────────────────────────────────────────────────────────
async function loadBudget() {
  const el = document.getElementById('budget-content');
  try {
    const { trips } = await (await fetch('/api/trips')).json();
    if (!trips.length) {
      el.innerHTML = '<p class="empty-state">No trips yet.</p>';
      return;
    }

    const sections = await Promise.all(trips.map(async (trip) => {
      try {
        const res = await fetch(`/api/trips/${trip._trip_id}/budget`);
        if (!res.ok) {
          return `<div class="budget-card"><h3>${trip._trip_id}</h3><p class="empty-state">No budget data yet.</p></div>`;
        }
        const budget = await res.json();
        const confirmed  = (budget.items || []).filter(i => i.type === 'confirmed');
        const estimates  = (budget.items || []).filter(i => i.type === 'estimate');
        const totalConfirmed  = confirmed.reduce((s, i) => s + (i.amount || 0), 0);
        const totalEstimated  = (budget.items || []).reduce((s, i) => s + (i.amount || 0), 0);
        const remaining = (budget.budget_usd || 0) - totalEstimated;
        const pct = budget.budget_usd
          ? Math.min(100, (totalEstimated / budget.budget_usd) * 100)
          : 0;

        return `
          <div class="budget-card">
            <div class="budget-header">
              <h3>${trip._trip_id}</h3>
              <span>Budget: ${budget.budget_usd ? '$' + budget.budget_usd + ' USD' : '—'}</span>
            </div>
            <div class="budget-bar-wrap">
              <div class="budget-bar" style="width:${pct}%"></div>
            </div>
            <div class="budget-summary">
              <span>Committed: <strong>$${totalConfirmed}</strong></span>
              <span>Estimated total: <strong>$${totalEstimated}</strong></span>
              <span>Remaining: <strong>$${remaining}</strong></span>
            </div>
            ${confirmed.length ? `
              <h4>Confirmed bookings</h4>
              <ul>${confirmed.map(i => `<li>${i.description || ''} \u2014 $${i.amount} (${i.category || ''})</li>`).join('')}</ul>
            ` : ''}
            ${estimates.length ? `
              <h4>Estimates</h4>
              <ul>${estimates.map(i => `<li>${i.description || ''} \u2014 $${i.amount} (${i.category || ''})</li>`).join('')}</ul>
            ` : ''}
          </div>`;
      } catch (e) {
        return `<div class="budget-card"><h3>${trip._trip_id}</h3><p class="error">Failed to load: ${e.message}</p></div>`;
      }
    }));

    el.innerHTML = sections.join('');
  } catch (e) {
    el.innerHTML = `<p class="error">Failed to load budget: ${e.message}</p>`;
  }
}

// ─── Crons tab ──────────────────────────────────────────────────────────────
async function loadCrons() {
  const el = document.getElementById('crons-content');
  el.innerHTML = '<p class="empty-state">Loading...</p>';
  try {
    const { jobs } = await fetch('/api/crons').then(r => r.json());

    if (!jobs || !jobs.length) {
      el.innerHTML = '<p class="empty-state">No cron jobs registered.</p>';
      return;
    }

    const travelActive  = jobs.filter(j => j.type === 'system' && j.project === 'travel');
    const otherActive   = jobs.filter(j => j.type === 'system' && j.project !== 'travel');
    const planned       = jobs.filter(j => j.type === 'planned');

    function systemRow(job) {
      return `<tr>
        <td><code>${esc(job.schedule)}</code></td>
        <td><code class="cmd-truncate" title="${esc(job.command)}">${esc(job.command.length > 80 ? job.command.slice(0, 80) + '…' : job.command)}</code></td>
        <td><span class="badge badge-green">Active</span></td>
      </tr>`;
    }

    function plannedRow(job) {
      const badge = job.status === 'ready'
        ? '<span class="badge badge-yellow">Ready</span>'
        : '<span class="badge badge-grey">Pending</span>';
      return `<tr>
        <td><code>${esc(job.schedule_human || job.schedule)}</code></td>
        <td>
          <strong>${esc(job.name)}</strong><br>
          <small class="muted">${esc(job.description || '')}</small>
          ${job.condition_human ? `<br><small class="muted">Condition: ${esc(job.condition_human)}</small>` : ''}
          ${job.note ? `<br><small class="muted">Note: ${esc(job.note)}</small>` : ''}
        </td>
        <td>${badge}</td>
      </tr>`;
    }

    let html = '';

    if (travelActive.length) {
      html += `<h4 class="crons-section-title">Travel Concierge — Active</h4>
        <table class="crons-table"><thead><tr><th>Schedule</th><th>Command</th><th>Status</th></tr></thead>
        <tbody>${travelActive.map(systemRow).join('')}</tbody></table>`;
    }

    if (planned.length) {
      html += `<h4 class="crons-section-title">Travel Concierge — Planned</h4>
        <table class="crons-table"><thead><tr><th>When</th><th>Job</th><th>Status</th></tr></thead>
        <tbody>${planned.map(plannedRow).join('')}</tbody></table>`;
    }

    if (otherActive.length) {
      html += `<h4 class="crons-section-title">Other Projects</h4>
        <table class="crons-table"><thead><tr><th>Schedule</th><th>Command</th><th>Status</th></tr></thead>
        <tbody>${otherActive.map(systemRow).join('')}</tbody></table>`;
    }

    el.innerHTML = html || '<p class="empty-state">No cron jobs found.</p>';
  } catch (e) {
    el.innerHTML = `<p class="error">Failed to load cron status: ${e.message}</p>`;
  }
}

// ─── Init ───────────────────────────────────────────────────────────────────
loadTrips();
