// Travel Concierge Dashboard — app.js

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
    case 'trips': loadTrips(); break;
    case 'scout': loadScout(); break;
    case 'hotels': loadHotels(); break;
    case 'itinerary': loadItinerarySelector(); break;
    case 'budget': loadBudget(); break;
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
      const route = trip.cities ? trip.cities.map(c => c.name).join(' \u2192 ') : id;
      const firstCity = trip.cities?.[0];
      const lastCity = trip.cities?.[trip.cities.length - 1];
      const dates = firstCity ? `${firstCity.arrive} \u2013 ${lastCity?.depart || ''}` : '';
      const phase = phaseBadge(trip.phase || 'active');
      const budget = trip.budget_usd ? `$${trip.budget_usd} USD` : '\u2014';
      return `
        <div class="trip-card" onclick="selectTrip('${id}')">
          <div class="trip-card-header">
            <span class="trip-id">${id}</span>
            ${phase}
          </div>
          <div class="trip-route">${route}</div>
          <div class="trip-meta">${dates}${dates ? ' \u00B7 ' : ''}${trip.travellers || 1} traveller(s) \u00B7 Budget: ${budget}</div>
        </div>`;
    }).join('');
  } catch (e) {
    grid.innerHTML = `<p class="error">Failed to load trips: ${e.message}</p>`;
  }
}

function selectTrip(tripId) {
  // Switch to itinerary tab with this trip pre-selected
  document.querySelector('[data-tab="itinerary"]').click();
  loadItinerary(tripId);
}

// ─── Scout tab ─────────────────────────────────────────────────────────────
async function loadScout() {
  const el = document.getElementById('scout-content');
  try {
    const { trips } = await (await fetch('/api/trips')).json();
    const allFlights = [];

    for (const trip of trips) {
      try {
        const flights = await (await fetch(`/api/trips/${trip._trip_id}/flights`)).json();
        if (flights.legs) {
          flights.legs.forEach(leg => { leg._trip_id = trip._trip_id; });
          allFlights.push(...flights.legs);
        }
      } catch (e) {
        // trip has no flights.json yet — skip silently
      }
    }

    if (!allFlights.length) {
      el.innerHTML = '<p class="empty-state">No flight routes tracked yet. Run <code>/check-flights</code> in Claude Code.</p>';
      return;
    }

    el.innerHTML = allFlights.map(leg => {
      const history = leg.price_history || [];
      const currentPrice = history.length ? history[history.length - 1].price : null;
      const classification = currentPrice ? classifyPrice(currentPrice, history) : null;
      const prices = history.map(p => p.price).filter(Boolean);
      const minP = prices.length ? Math.min(...prices) : null;
      const maxP = prices.length ? Math.max(...prices) : null;

      return `
        <div class="route-card">
          <div class="route-header">
            <span class="route-label">${leg.from || '?'} \u2192 ${leg.to || '?'}</span>
            <span class="route-date">${leg.date || ''}</span>
            <span class="trip-ref">${leg._trip_id}</span>
          </div>
          <div class="route-price">
            ${currentPrice ? `<span class="price-current">$${currentPrice}</span>` : '<span class="price-na">No price data</span>'}
            ${classification ? `<span class="badge ${classification.cls}">${classification.badge} ${classification.label}</span>` : ''}
          </div>
          ${minP && maxP ? `<div class="price-range">Range: $${minP} \u2013 $${maxP} (${history.length} checks)</div>` : ''}
          ${leg.booked ? '<div class="booked-badge">\u2705 Booked</div>' : ''}
        </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<p class="error">Failed to load flight data: ${e.message}</p>`;
  }
}

// ─── Hotels tab ────────────────────────────────────────────────────────────
async function loadHotels() {
  const el = document.getElementById('hotels-content');
  try {
    const { trips } = await (await fetch('/api/trips')).json();
    const allProps = [];

    for (const trip of trips) {
      try {
        const accomm = await (await fetch(`/api/trips/${trip._trip_id}/accommodation`)).json();
        if (accomm.cities) {
          accomm.cities.forEach(city => {
            (city.options || []).forEach(opt => {
              opt._trip_id = trip._trip_id;
              opt._city = city.city;
              opt._nights = city.nights;
              allProps.push(opt);
            });
          });
        }
      } catch (e) {
        // no accommodation.json yet — skip silently
      }
    }

    if (!allProps.length) {
      el.innerHTML = '<p class="empty-state">No accommodation tracked yet. Run <code>/find-hotels</code> in Claude Code.</p>';
      return;
    }

    el.innerHTML = allProps.map(prop => {
      const history = prop.price_history || [];
      const currentPrice = prop.price_per_night;
      const classification =
        currentPrice && history.length >= 3
          ? classifyPrice(currentPrice, history.map(p => ({ price: p.price })))
          : null;

      return `
        <div class="route-card">
          <div class="route-header">
            <span class="route-label">${prop.name}</span>
            <span class="route-date">${prop._city} \u00B7 ${prop._nights} nights</span>
            <span class="trip-ref">${prop._trip_id}</span>
          </div>
          <div class="route-price">
            ${currentPrice ? `<span class="price-current">$${currentPrice}/night</span>` : '<span class="price-na">No price data</span>'}
            ${classification
              ? `<span class="badge ${classification.cls}">${classification.badge} ${classification.label}</span>`
              : '<span class="badge badge-grey">\u23F3 No data yet</span>'}
          </div>
          <div class="price-range">${prop.area || ''} \u00B7 ${prop.type || 'hotel'} \u00B7 ${history.length} checks</div>
          ${prop.booked ? '<div class="booked-badge">\u2705 Booked</div>' : ''}
        </div>`;
    }).join('');
  } catch (e) {
    el.innerHTML = `<p class="error">Failed to load accommodation data: ${e.message}</p>`;
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
      ${trips.map(t => `<option value="${t._trip_id}">${t._trip_id}</option>`).join('')}
    </select>`;
    if (currentItineraryTrip) {
      const selectEl = document.getElementById('trip-select');
      if (selectEl) {
        selectEl.value = currentItineraryTrip;
        loadItinerary(currentItineraryTrip);
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
    // Encode content for safe inline attribute passing
    const encodedContent = encodeURIComponent(content);
    view.innerHTML = `
      <div class="itinerary-content" id="itinerary-rendered">${markdownToHtml(content)}</div>
      <button class="btn-secondary" onclick="startEditItinerary('${tripId}', decodeURIComponent('${encodedContent}'))">Edit</button>`;
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
function markdownToHtml(md) {
  if (!md) return '';
  return md
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
              <span>Budget: $${budget.budget_usd || '?'} USD</span>
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

// ─── Init ───────────────────────────────────────────────────────────────────
loadTrips();
