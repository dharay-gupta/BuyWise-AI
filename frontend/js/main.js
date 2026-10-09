/**
 * BuyWise AI — Phase 4 Frontend
 * Structured, no-framework vanilla JS
 * All data comes from the BuyWise backend API — no secrets in this file.
 */

'use strict';

// ============================================================
// Global State
// ============================================================
const state = {
  allProducts:      [],   // All products from the last API response
  filteredProducts: [],   // Products after filters applied
  compareList:      [],   // Product IDs selected for comparison (max 3)
  currentData:      null, // Full API response object
  currentMode:      'balanced',
  priceChartInst:   null,
  scatterChartInst: null,
};

// ============================================================
// Mode Metadata
// ============================================================
const MODE_META = {
  balanced:      { label: 'Balanced',      icon: '⚖️', desc: 'Price 35% · Rating 30% · Review Confidence 15% · Market Position 20%' },
  cheapest:      { label: 'Cheapest',      icon: '💰', desc: 'Price 60% · Market Position 25% · Rating 10% · Review Confidence 5%' },
  best_value:    { label: 'Best Value',    icon: '🔥', desc: 'Price 40% · Rating 30% · Review Confidence 15% · Market Position 15%' },
  quality_first: { label: 'Quality First', icon: '👑', desc: 'Rating 45% · Review Confidence 30% · Market Position 15% · Price 10%' },
};

// ============================================================
// DOM Ready
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  checkApiHealth();
  updateModeDescription();

  // Search
  document.getElementById('searchBtn').addEventListener('click', performSearch);
  document.getElementById('searchInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') performSearch();
  });

  // Mode selector
  document.getElementById('modeSelect').addEventListener('change', () => {
    state.currentMode = document.getElementById('modeSelect').value;
    updateModeDescription();
  });

  // Filters
  ['filterMaxPrice','filterMinRating','filterMerchant','filterTag','filterSort'].forEach(id => {
    document.getElementById(id).addEventListener('input', applyFilters);
    document.getElementById(id).addEventListener('change', applyFilters);
  });
  document.getElementById('clearFiltersBtn').addEventListener('click', clearFilters);

  // Modal close
  document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
  document.getElementById('productModal').addEventListener('click', (e) => {
    if (e.target === document.getElementById('productModal')) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });

  // Home link
  document.getElementById('homeLink').addEventListener('click', (e) => {
    e.preventDefault();
    document.getElementById('resultsContainer').style.display = 'none';
    document.getElementById('loadingState').style.display = 'none';
  });
});

// ============================================================
// Mode Description
// ============================================================
function updateModeDescription() {
  const mode = document.getElementById('modeSelect').value;
  state.currentMode = mode;
  const m = MODE_META[mode] || {};
  document.getElementById('modeDescription').textContent =
    m.desc ? `Decision Mode: ${m.icon} ${m.label} — ${m.desc}` : '';
}

// ============================================================
// API Health Check
// ============================================================
async function checkApiHealth() {
  const el = document.getElementById('apiStatus');
  try {
    const res = await fetch('http://localhost:8000/api/health');
    if (res.ok) {
      const data = await res.json();
      el.innerHTML = `<span class="status-dot online"></span> API Connected`;
    } else {
      el.innerHTML = `<span class="status-dot offline"></span> API Error (${res.status})`;
    }
  } catch {
    el.innerHTML = `<span class="status-dot offline"></span> API Offline`;
  }
}

// ============================================================
// Search
// ============================================================
async function performSearch() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) {
    document.getElementById('searchInput').focus();
    return;
  }

  const mode = document.getElementById('modeSelect').value;
  state.currentMode = mode;

  // Reset compare list when new search
  state.compareList = [];

  showLoading('Analysing current observed market...');

  try {
    const url = `http://localhost:8000/api/search?q=${encodeURIComponent(query)}&mode=${encodeURIComponent(mode)}`;
    const res = await fetch(url);

    if (!res.ok) {
      let msg = 'An error occurred during search.';
      try { const d = await res.json(); msg = d.detail || msg; } catch {}
      showError(msg);
      return;
    }

    const data = await res.json();
    state.currentData = data;

    if (!data.products || data.products.length === 0) {
      showEmpty(data.query || query);
      return;
    }

    state.allProducts = data.products;
    state.filteredProducts = [...data.products];

    showResults();
    renderAll(data);
    updateLoadingText(`Analysed ${data.count} products`);

  } catch (err) {
    console.error('Search error:', err);
    showError('Failed to connect to the BuyWise API. Please make sure the server is running on port 8000.');
  }
}

// ============================================================
// Loading / State Helpers
// ============================================================
function showLoading(text) {
  document.getElementById('loadingState').style.display = 'block';
  document.getElementById('loadingText').textContent = text;
  document.getElementById('resultsContainer').style.display = 'none';
}

function updateLoadingText(text) {
  document.getElementById('loadingText').textContent = text;
  setTimeout(() => {
    document.getElementById('loadingState').style.display = 'none';
  }, 800);
}

function showResults() {
  document.getElementById('loadingState').style.display = 'none';
  document.getElementById('resultsContainer').style.display = 'block';
}

function showError(msg) {
  document.getElementById('loadingState').style.display = 'none';
  document.getElementById('resultsContainer').style.display = 'block';
  document.getElementById('productGrid').innerHTML =
    `<div class="bw-error-state" style="grid-column:1/-1">⚠️ ${escHtml(msg)}</div>`;
  // Hide optional sections
  ['intentSection','picksSection','filtersSection','comparisonSection','insightsSection','merchantSection','chartsSection'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
}

function showEmpty(query) {
  document.getElementById('loadingState').style.display = 'none';
  document.getElementById('resultsContainer').style.display = 'block';
  document.getElementById('productGrid').innerHTML =
    `<div class="bw-empty-state" style="grid-column:1/-1">
       <div class="bw-empty-icon">🔍</div>
       <div>No products found for <strong>${escHtml(query)}</strong></div>
       <div style="font-size:0.82rem;color:var(--text-muted);margin-top:0.5rem;">Try a broader search term or different budget range.</div>
     </div>`;
  ['intentSection','picksSection','filtersSection','comparisonSection','insightsSection','merchantSection','chartsSection'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  });
}

// ============================================================
// Render All Sections
// ============================================================
function renderAll(data) {
  renderIntent(data.intent);
  renderSummary(data);
  renderPicks(data);
  renderFilters(data.products);
  renderInsights(data.market_insights || []);
  renderMerchants(data.merchant_stats);
  renderCharts(data.products);
  renderProductGrid(state.filteredProducts);
}

// ============================================================
// 1. Summary Cards
// ============================================================
function renderSummary(data) {
  const intent  = data.intent  || {};
  const market  = data.market  || {};
  const mode    = data.decision_mode || 'balanced';
  const modeMeta = MODE_META[mode] || { label: mode, icon: '⚖️' };

  // Search Summary
  const budgetStr = intent.budget_max
    ? `₹${Number(intent.budget_max).toLocaleString('en-IN')}`
    : 'Not specified';
  const modeHtml = `<span class="mode-badge">${modeMeta.icon} ${modeMeta.label}</span>`;

  document.getElementById('summaryContent').innerHTML = `
    <div class="bw-stat-row">
      <span class="bw-stat-label">Products Analysed</span>
      <span class="bw-stat-value success">${data.count}</span>
    </div>
    <div class="bw-stat-row">
      <span class="bw-stat-label">Decision Mode</span>
      <span>${modeHtml}</span>
    </div>
    <div class="bw-stat-row">
      <span class="bw-stat-label">Detected Budget</span>
      <span class="bw-stat-value">${escHtml(budgetStr)}</span>
    </div>
    <div class="bw-stat-row">
      <span class="bw-stat-label">Intent Priority</span>
      <span class="bw-stat-value">${escHtml(intent.priority || 'balanced')}</span>
    </div>
  `;

  document.getElementById('decisionModeLabel').textContent = `${modeMeta.icon} ${modeMeta.label} mode`;

  // Market Overview
  const fmt = (v) => v != null ? `₹${Number(v).toLocaleString('en-IN', {maximumFractionDigits: 0})}` : 'N/A';
  document.getElementById('marketContent').innerHTML = `
    <div class="bw-stat-row">
      <span class="bw-stat-label">Lowest Observed Price</span>
      <span class="bw-stat-value success">${fmt(market.lowest_price)}</span>
    </div>
    <div class="bw-stat-row">
      <span class="bw-stat-label">Highest Observed Price</span>
      <span class="bw-stat-value">${fmt(market.highest_price)}</span>
    </div>
    <div class="bw-stat-row">
      <span class="bw-stat-label">Observed Median Price</span>
      <span class="bw-stat-value accent">${fmt(market.median_price)}</span>
    </div>
    <div class="bw-stat-row">
      <span class="bw-stat-label">Observed Average Price</span>
      <span class="bw-stat-value">${fmt(market.average_price)}</span>
    </div>
    <div class="bw-stat-row">
      <span class="bw-stat-label">Products with Price Data</span>
      <span class="bw-stat-value">${market.valid_prices_count || 0} / ${market.products_analyzed || 0}</span>
    </div>
  `;
}

// ============================================================
// 2. Top Picks (Recommendations)
// ============================================================
function renderPicks(data) {
  const recs = data.recommendations || {};
  const products = data.products || [];
  const picksList = document.getElementById('picksList');

  const picksSection = document.getElementById('picksSection');

  const recEntries = [
    { key: 'best_overall',  badge: 'best-overall',  label: '🏆 Best Overall' },
    { key: 'best_value',    badge: 'best-value',    label: '🔥 Best Value' },
    { key: 'cheapest',      badge: 'cheapest',      label: '💰 Cheapest' },
    { key: 'highest_rated', badge: 'highest-rated', label: '⭐ Highest Rated' },
    { key: 'premium_pick',  badge: 'premium-pick',  label: '👑 Premium Pick' },
    { key: 'hidden_gem',    badge: 'hidden-gem',    label: '💎 Hidden Gem' },
  ];

  let html = '';
  let count = 0;

  recEntries.forEach(({ key, badge, label }) => {
    const rec = recs[key];
    if (!rec) return;
    const p = products.find(
      (prod) => prod.product_id === rec.product_id || prod.title === rec.product_id
    );
    if (!p) return;
    count++;

    const price = p.price || (p.extracted_price != null ? `₹${Number(p.extracted_price).toLocaleString('en-IN')}` : 'N/A');
    const score = p.buywise_score != null ? p.buywise_score.toFixed(1) : '—';
    const imgHtml = p.thumbnail
      ? `<img src="${escAttr(p.thumbnail)}" alt="${escAttr(p.title || '')}" loading="lazy">`
      : `<div class="bw-pick-img-placeholder">No Image</div>`;

    html += `
      <div class="bw-pick-card" onclick="openProductModal('${escAttr(p.product_id || p.title || '')}')">
        <div class="bw-pick-badge ${badge}">${label}</div>
        <div class="bw-pick-img-wrap">${imgHtml}</div>
        <div class="bw-pick-body">
          <div class="bw-pick-title" title="${escAttr(p.title || '')}">${escHtml(p.title || 'Unknown Product')}</div>
          <div class="bw-pick-price">${escHtml(price)}</div>
          <div class="bw-pick-score">BuyWise Score: ${score}/100</div>
          <div class="bw-pick-reason">
            <strong>Why BuyWise Recommends:</strong><br>
            ${p.recommendation_explanation ? escHtml(p.recommendation_explanation.summary) : escHtml(rec.reason)}
          </div>
          <div class="bw-pick-actions">
            <a href="${escAttr(p.product_link || '#')}" target="_blank" rel="noopener" class="bw-btn bw-btn-primary bw-btn-sm" ${!p.product_link ? 'tabindex="-1"' : ''}>View Product ↗</a>
            <button class="bw-btn bw-btn-compare bw-btn-sm" id="cmp-pick-${escAttr(p.product_id || p.title || '')}" onclick="event.stopPropagation();toggleCompare('${escAttr(p.product_id || p.title || '')}')">+ Compare</button>
          </div>
        </div>
      </div>
    `;
  });

  if (count === 0) {
    html = `<div style="color:var(--text-muted);font-size:0.875rem;padding:1rem 0;">No recommendations could be generated from the observed data.</div>`;
  }

  picksList.innerHTML = html;
}

// ============================================================
// 3. Smart Filters
// ============================================================
function renderFilters(products) {
  // Populate merchant dropdown
  const merchantSelect = document.getElementById('filterMerchant');
  const currentMerchant = merchantSelect.value;
  const merchants = [...new Set(products.map(p => p.source).filter(Boolean))].sort();
  merchantSelect.innerHTML = '<option value="">All Merchants</option>' +
    merchants.map(m => `<option value="${escAttr(m)}">${escHtml(m)}</option>`).join('');
  if (merchants.includes(currentMerchant)) merchantSelect.value = currentMerchant;
}

function applyFilters() {
  const maxPrice   = parseFloat(document.getElementById('filterMaxPrice').value)   || Infinity;
  const minRating  = parseFloat(document.getElementById('filterMinRating').value)  || 0;
  const merchant   = document.getElementById('filterMerchant').value;
  const tag        = document.getElementById('filterTag').value;
  const sortBy     = document.getElementById('filterSort').value;

  let filtered = [...state.allProducts];

  if (maxPrice  < Infinity) filtered = filtered.filter(p => p.extracted_price != null && p.extracted_price <= maxPrice);
  if (minRating > 0)        filtered = filtered.filter(p => p.rating != null && p.rating >= minRating);
  if (merchant)             filtered = filtered.filter(p => p.source === merchant);
  if (tag) {
    filtered = filtered.filter(p =>
      (p.recommendation_tags || []).some(t => t.toLowerCase().includes(tag.toLowerCase()))
    );
  }

  // Sort
  if (sortBy === 'price_asc')  filtered.sort((a, b) => (a.extracted_price || Infinity) - (b.extracted_price || Infinity));
  if (sortBy === 'price_desc') filtered.sort((a, b) => (b.extracted_price || 0) - (a.extracted_price || 0));
  if (sortBy === 'rating')     filtered.sort((a, b) => (b.rating || 0) - (a.rating || 0));
  if (sortBy === 'reviews')    filtered.sort((a, b) => (b.reviews || 0) - (a.reviews || 0));
  if (sortBy === 'score')      filtered.sort((a, b) => (b.buywise_score || 0) - (a.buywise_score || 0));

  state.filteredProducts = filtered;

  const total = state.allProducts.length;
  document.getElementById('filterCount').textContent =
    filtered.length === total
      ? `Showing all ${total} products`
      : `Showing ${filtered.length} of ${total} products`;

  renderProductGrid(filtered);
}

function clearFilters() {
  document.getElementById('filterMaxPrice').value  = '';
  document.getElementById('filterMinRating').value = '';
  document.getElementById('filterMerchant').value  = '';
  document.getElementById('filterTag').value       = '';
  document.getElementById('filterSort').value      = 'score';
  document.getElementById('filterCount').textContent = '';
  state.filteredProducts = [...state.allProducts];
  renderProductGrid(state.filteredProducts);
}

// ============================================================
// 4. Product Comparison
// ============================================================
function toggleCompare(productId) {
  if (!productId) return;
  const idx = state.compareList.indexOf(productId);
  if (idx !== -1) {
    state.compareList.splice(idx, 1);
  } else {
    if (state.compareList.length >= 3) {
      alert('You can compare up to 3 products. Remove one first.');
      return;
    }
    state.compareList.push(productId);
  }
  updateCompareButtons();
  renderComparisonTable();
}

function updateCompareButtons() {
  // Update all compare buttons across picks and grid
  document.querySelectorAll('[id^="cmp-"]').forEach(btn => {
    const pid = btn.id.replace(/^cmp-pick-|^cmp-card-/, '');
    const inList = state.compareList.includes(pid);
    btn.textContent = inList ? '✓ Remove' : '+ Compare';
    btn.classList.toggle('active', inList);
  });

  // Highlight card borders
  document.querySelectorAll('.bw-product-card').forEach(card => {
    const pid = card.dataset.pid;
    card.classList.toggle('in-compare', state.compareList.includes(pid));
  });
}

function renderComparisonTable() {
  const section = document.getElementById('comparisonSection');
  const container = document.getElementById('comparisonTable');

  if (state.compareList.length < 2) {
    section.style.display = 'none';
    return;
  }

  section.style.display = 'block';

  const products = state.compareList.map(pid =>
    state.allProducts.find(p => (p.product_id || p.title) === pid)
  ).filter(Boolean);

  if (products.length < 2) { section.style.display = 'none'; return; }

  // Determine best values for highlighting
  const bestScore = Math.max(...products.map(p => p.buywise_score || 0));
  const bestPrice = Math.min(...products.map(p => p.extracted_price || Infinity));
  const bestRating = Math.max(...products.map(p => p.rating || 0));

  const fmt = (v) => v != null ? `₹${Number(v).toLocaleString('en-IN', {maximumFractionDigits: 0})}` : 'N/A';

  let headerHtml = `<th class="row-label">Attribute</th>`;
  products.forEach((p, i) => {
    const isBest = p.buywise_score === bestScore;
    headerHtml += `<th class="product-col">
      ${escHtml((p.title || 'Product').substring(0, 40))}
      ${isBest ? '<br><span class="bw-best-choice-badge">★ Best Choice</span>' : ''}
    </th>`;
  });

  const rows = [
    { label: 'Merchant', getValue: p => p.source || 'N/A', isBest: () => false },
    { label: 'Price',     getValue: p => fmt(p.extracted_price),       isBest: p => p.extracted_price === bestPrice },
    { label: 'BuyWise Score', getValue: p => p.buywise_score != null ? `${p.buywise_score}/100` : 'N/A', isBest: p => p.buywise_score === bestScore },
    { label: 'Rating',   getValue: p => p.rating ? `${p.rating} ⭐` : 'N/A',  isBest: p => p.rating === bestRating },
    { label: 'Reviews',  getValue: p => p.reviews != null ? p.reviews.toLocaleString('en-IN') : 'N/A', isBest: () => false },
    { label: 'vs. Market Median', getValue: p => p.market_savings || 'N/A', isBest: () => false },
    { label: 'Review Confidence', getValue: p => p.review_confidence != null ? `${(p.review_confidence * 100).toFixed(0)}%` : 'N/A', isBest: () => false },
    { label: 'Recommendation', getValue: p => (p.recommendation_tags || []).join(' ') || 'None', isBest: () => false },
    { label: 'Trade-off', getValue: p => p.tradeoff_explanation ? p.tradeoff_explanation.substring(0, 80) + '…' : 'N/A', isBest: () => false },
  ];

  let bodyHtml = '';
  rows.forEach(row => {
    bodyHtml += `<tr><td class="row-label">${escHtml(row.label)}</td>`;
    products.forEach(p => {
      const val = row.getValue(p);
      const best = row.isBest(p);
      bodyHtml += `<td class="${best ? 'best-cell' : ''}">${escHtml(String(val))}</td>`;
    });
    bodyHtml += `</tr>`;
  });

  container.innerHTML = `
    <div class="bw-comparison-hint">${products.length} products selected for comparison (max 3)</div>
    <div class="bw-comparison-table-wrap">
      <table class="bw-comparison-table">
        <thead><tr>${headerHtml}</tr></thead>
        <tbody>${bodyHtml}</tbody>
      </table>
    </div>
  `;
}

// ============================================================
// 5. Score Breakdown
// ============================================================
function renderScoreBreakdown(product) {
  const bd = product.score_breakdown;
  if (!bd) return '';

  const rows = [
    { label: 'Price Competitiveness', value: bd.price, max: bd.price_max || 35 },
    { label: 'Rating Quality',        value: bd.rating, max: bd.rating_max || 30 },
    { label: 'Review Confidence',     value: bd.review_confidence, max: bd.review_confidence_max || 15 },
    { label: 'Market Position',       value: bd.market_position, max: bd.market_position_max || 20 },
  ];

  let html = '<div class="bw-score-breakdown">';
  rows.forEach(row => {
    const pct = row.max > 0 ? Math.min(100, (row.value / row.max) * 100) : 0;
    html += `
      <div class="bw-breakdown-row">
        <div class="bw-breakdown-label">${escHtml(row.label)}</div>
        <div class="bw-breakdown-bar-wrap">
          <div class="bw-breakdown-bar" style="width:${pct.toFixed(1)}%"></div>
        </div>
        <div class="bw-breakdown-value">${row.value.toFixed(1)} / ${row.max.toFixed(1)}</div>
      </div>
    `;
  });
  html += '</div>';
  return html;
}

// ============================================================
// 6. Product Detail Modal
// ============================================================
function openProductModal(productId) {
  if (!productId) return;
  const p = state.allProducts.find(
    (prod) => (prod.product_id || prod.title) === productId
  );
  if (!p) return;

  const price    = p.price || (p.extracted_price != null ? `₹${Number(p.extracted_price).toLocaleString('en-IN')}` : 'N/A');
  const score    = p.buywise_score != null ? p.buywise_score.toFixed(1) : null;
  const scoreClass = score ? (parseFloat(score) >= 75 ? 'high' : parseFloat(score) >= 50 ? 'medium' : 'low') : '';

  // Image
  document.getElementById('modalImgWrap').innerHTML = p.thumbnail
    ? `<img src="${escAttr(p.thumbnail)}" alt="${escAttr(p.title || '')}" style="max-height:200px;max-width:90%;object-fit:contain;">`
    : `<div style="color:var(--text-muted);font-size:0.85rem;">No Image Available</div>`;

  // Tags
  const tagsHtml = (p.recommendation_tags || []).length > 0
    ? `<div class="bw-tags mb-3">${(p.recommendation_tags || []).map(t => `<span class="bw-tag">${escHtml(t)}</span>`).join('')}</div>`
    : '';

  // Score badge
  const scoreBadge = score
    ? `<span class="bw-score-badge ${scoreClass}" title="BuyWise Score">🎯 BuyWise Score: ${score}/100</span>`
    : '';

  // Score breakdown
  const breakdownHtml = renderScoreBreakdown(p);

  // Tradeoff explanation
  const tradeoffHtml = p.tradeoff_explanation
    ? `<div style="background:var(--bg-surface);border-radius:var(--radius-sm);padding:0.75rem 1rem;margin-top:1rem;font-size:0.82rem;color:var(--text-secondary);border-left:3px solid var(--accent-primary);">
         <strong style="color:var(--text-primary);">Market Position:</strong><br>${escHtml(p.tradeoff_explanation)}
       </div>`
    : '';

  // Analysis (Strengths & Weaknesses)
  let swHtml = '';
  if (p.analysis && (p.analysis.strengths.length > 0 || p.analysis.weaknesses.length > 0)) {
    swHtml += `<div style="margin-top:1.5rem;">
      <div style="font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-muted);margin-bottom:0.75rem;">Strengths & Weaknesses</div>
      <div style="display:flex;flex-direction:column;gap:0.5rem;">`;
    p.analysis.strengths.forEach(s => {
      swHtml += `<div style="font-size:0.85rem;color:var(--accent-success);">✓ ${escHtml(s)}</div>`;
    });
    p.analysis.weaknesses.forEach(w => {
      swHtml += `<div style="font-size:0.85rem;color:var(--accent-warning);">⚠ ${escHtml(w)}</div>`;
    });
    swHtml += `</div></div>`;
  }

  // Explanation
  let expHtml = '';
  if (p.recommendation_explanation) {
    const ex = p.recommendation_explanation;
    expHtml += `<div style="margin-top:1.5rem;background:var(--bg-surface);border:1px solid rgba(255,255,255,0.1);border-radius:var(--radius-md);padding:1rem;">
      <div style="font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-muted);margin-bottom:0.75rem;">Why BuyWise Recommends This</div>
      <div style="font-size:0.85rem;margin-bottom:1rem;color:var(--text-primary);">${escHtml(ex.summary)}</div>
      <div style="display:flex;flex-direction:column;gap:0.75rem;">`;
    ex.factors.forEach(f => {
      const icon = f.strength === 'strong' ? '✓' : f.strength === 'weak' ? '⚠' : '•';
      const color = f.strength === 'strong' ? 'var(--accent-success)' : f.strength === 'weak' ? 'var(--accent-warning)' : 'var(--text-secondary)';
      expHtml += `<div style="font-size:0.85rem;">
        <strong style="color:${color};">${icon} ${escHtml(f.name)}</strong><br>
        <span style="color:var(--text-muted);">${escHtml(f.observation)}</span>
      </div>`;
    });
    expHtml += `</div></div>`;
  }

  // Savings
  const savingsHtml = p.market_savings
    ? `<div class="bw-savings-text mt-1">💡 ${escHtml(p.market_savings)}</div>`
    : '';

  // Delivery
  const deliveryHtml = p.delivery
    ? `<div style="font-size:0.8rem;color:var(--text-muted);margin-top:0.5rem;">🚚 ${escHtml(p.delivery)}</div>`
    : '';

  document.getElementById('modalBody').innerHTML = `
    ${tagsHtml}
    <h5 style="font-size:1.1rem;margin-bottom:0.75rem;line-height:1.4;">${escHtml(p.title || 'Product Details')}</h5>
    <div style="font-size:0.82rem;color:var(--text-muted);margin-bottom:0.5rem;">from <strong style="color:var(--text-secondary);">${escHtml(p.source || 'Unknown Merchant')}</strong></div>

    <div style="display:flex;align-items:baseline;gap:0.75rem;margin-bottom:0.5rem;">
      <span style="font-size:1.5rem;font-weight:800;color:var(--accent-success);">${escHtml(price)}</span>
      ${p.old_price ? `<span style="font-size:0.9rem;text-decoration:line-through;color:var(--text-muted);">${escHtml(p.old_price)}</span>` : ''}
    </div>
    ${savingsHtml}
    ${renderVisualPricePosition(p, true)}

    <div style="font-size:0.85rem;color:var(--text-secondary);margin-bottom:0.75rem;">
      ${p.rating ? `⭐ ${p.rating}` : ''}
      ${p.reviews ? `(${p.reviews.toLocaleString('en-IN')} reviews)` : ''}
    </div>
    ${deliveryHtml}

    ${scoreBadge}

    ${breakdownHtml ? `
      <div style="margin-top:1.25rem;">
        <div style="font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em;color:var(--text-muted);margin-bottom:0.75rem;">Score Breakdown</div>
        ${breakdownHtml}
      </div>` : ''}

    ${expHtml}
    ${swHtml}

    ${tradeoffHtml}

    <div style="margin-top:1.5rem;display:flex;gap:0.75rem;">
      ${p.product_link
        ? `<a href="${escAttr(p.product_link)}" target="_blank" rel="noopener" class="bw-btn bw-btn-primary">View Product ↗</a>`
        : '<span style="color:var(--text-muted);font-size:0.82rem;">No product link available</span>'}
      <button class="bw-btn bw-btn-outline" onclick="closeModal()">Close</button>
    </div>
  `;

  document.getElementById('productModal').style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

function closeModal() {
  document.getElementById('productModal').style.display = 'none';
  document.body.style.overflow = '';
}

// ============================================================
// 7. Market Insights
// ============================================================
function renderInsights(insights) {
  const section = document.getElementById('insightsSection');
  const list    = document.getElementById('insightsList');

  if (!insights || insights.length === 0) {
    section.style.display = 'none';
    return;
  }

  section.style.display = 'block';
  const icons = ['📊', '⭐', '💡', '📈', '🔍'];
  list.innerHTML = insights.map((ins, i) => `
    <div class="bw-insight-item">
      <span class="bw-insight-icon">${icons[i % icons.length]}</span>
      <span>${escHtml(ins)}</span>
    </div>
  `).join('');
}

// ============================================================
// 8. Merchant Intelligence
// ============================================================
function renderMerchants(merchantStats) {
  const section = document.getElementById('merchantSection');
  const content = document.getElementById('merchantContent');

  if (!merchantStats || !merchantStats.merchants || merchantStats.merchants.length === 0) {
    section.style.display = 'none';
    return;
  }

  section.style.display = 'block';
  const merchants = merchantStats.merchants;
  const maxCount  = Math.max(...merchants.map(m => m.count));
  const fmt = (v) => v != null ? `₹${Number(v).toLocaleString('en-IN', {maximumFractionDigits: 0})}` : 'N/A';

  let html = `
    <table class="bw-merchant-table">
      <thead>
        <tr>
          <th>Marketplace</th>
          <th>Observed Listings</th>
          <th>Avg. Observed Price</th>
          <th>Lowest Observed Price</th>
        </tr>
      </thead>
      <tbody>
  `;

  merchants.forEach(m => {
    const barWidth = Math.round((m.count / maxCount) * 80);
    html += `
      <tr>
        <td class="merchant-name">${escHtml(m.name)}</td>
        <td>
          ${m.count}
          <span class="bw-merchant-bar" style="width:${barWidth}px;"></span>
        </td>
        <td>${fmt(m.avg_price)}</td>
        <td>${fmt(m.lowest_price)}</td>
      </tr>
    `;
  });

  html += `
      </tbody>
    </table>
    <p class="bw-merchant-note">ℹ️ ${escHtml(merchantStats.note || 'Based on current observed results only')}</p>
  `;

  content.innerHTML = html;
}

// ============================================================
// 9. Charts (Price Distribution + Price vs Rating Scatter)
// ============================================================
function renderCharts(products) {
  if (state.priceChartInst)   { state.priceChartInst.destroy();   state.priceChartInst = null; }
  if (state.scatterChartInst) { state.scatterChartInst.destroy(); state.scatterChartInst = null; }

  const validProducts = products.filter(p => p.extracted_price != null);

  Chart.defaults.color = 'rgba(160, 168, 204, 0.8)';

  // --- Price Distribution (Bar) ---
  if (validProducts.length > 0) {
    const prices   = validProducts.map(p => p.extracted_price);
    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);
    const binCount = 5;
    const binSize  = (maxPrice - minPrice) / binCount || 1;
    const bins     = Array(binCount).fill(0);
    const labels   = [];

    for (let i = 0; i < binCount; i++) {
      const start = Math.round(minPrice + i * binSize);
      const end   = Math.round(minPrice + (i + 1) * binSize);
      labels.push(`₹${start.toLocaleString('en-IN')}–₹${end.toLocaleString('en-IN')}`);
    }

    prices.forEach(price => {
      let idx = Math.floor((price - minPrice) / binSize);
      if (idx >= binCount) idx = binCount - 1;
      bins[idx]++;
    });

    const ctxPrice = document.getElementById('priceChart').getContext('2d');
    state.priceChartInst = new Chart(ctxPrice, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Products',
          data: bins,
          backgroundColor: 'rgba(108, 99, 255, 0.5)',
          borderColor: 'rgba(108, 99, 255, 0.9)',
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          title: { display: true, text: 'Observed Price Distribution', font: { size: 13, weight: '600' } },
          legend: { display: false },
        },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { stepSize: 1 } },
        },
      }
    });
  }

  // --- Price vs Rating (Scatter) ---
  const scatterData = products
    .filter(p => p.extracted_price != null && p.rating != null)
    .map(p => ({ x: p.extracted_price, y: p.rating, title: p.title }));

  if (scatterData.length > 0) {
    const ctxScatter = document.getElementById('scatterChart').getContext('2d');
    state.scatterChartInst = new Chart(ctxScatter, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Price vs Rating',
          data: scatterData,
          backgroundColor: 'rgba(76, 201, 240, 0.6)',
          pointRadius: 5,
          pointHoverRadius: 7,
        }]
      },
      options: {
        responsive: true,
        plugins: {
          title: { display: true, text: 'Price vs. Rating (Observed)', font: { size: 13, weight: '600' } },
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => {
                const t = ctx.raw.title ? ctx.raw.title.substring(0, 40) + '…' : '';
                return `${t}: ₹${ctx.raw.x.toLocaleString('en-IN')} / ${ctx.raw.y}⭐`;
              }
            }
          }
        },
        scales: {
          x: { title: { display: true, text: 'Price (₹)' }, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { title: { display: true, text: 'Rating' }, min: 0, max: 5, grid: { color: 'rgba(255,255,255,0.04)' } },
        }
      }
    });
  }
}

// ============================================================
// 10. Product Grid
// ============================================================
function renderProductGrid(products) {
  const grid = document.getElementById('productGrid');
  const countLabel = document.getElementById('resultCountLabel');
  countLabel.textContent = `${products.length} product${products.length !== 1 ? 's' : ''}`;

  if (products.length === 0) {
    grid.innerHTML = `<div class="bw-empty-state" style="grid-column:1/-1">
      <div class="bw-empty-icon">🔍</div>
      <div>No products match the current filters.</div>
      <button class="bw-btn bw-btn-outline" style="margin-top:1rem;" onclick="clearFilters()">Clear Filters</button>
    </div>`;
    return;
  }

  grid.innerHTML = products.map(p => generateProductCard(p)).join('');
}

function generateProductCard(p) {
  const productId = p.product_id || p.title || '';
  const price    = p.price || (p.extracted_price != null ? `₹${Number(p.extracted_price).toLocaleString('en-IN')}` : 'Price N/A');
  const score    = p.buywise_score != null ? p.buywise_score.toFixed(1) : null;
  const scoreClass = score ? (parseFloat(score) >= 75 ? 'high' : parseFloat(score) >= 50 ? 'medium' : 'low') : '';
  const inCompare = state.compareList.includes(productId);

  const imgHtml = p.thumbnail
    ? `<img src="${escAttr(p.thumbnail)}" alt="${escAttr(p.title || '')}" loading="lazy" onclick="openProductModal('${escAttr(productId)}')">`
    : `<div class="bw-product-img-placeholder" onclick="openProductModal('${escAttr(productId)}')">No Image</div>`;

  const tagsHtml = (p.recommendation_tags || []).length > 0
    ? `<div class="bw-tags">${(p.recommendation_tags || []).map(t => `<span class="bw-tag">${escHtml(t)}</span>`).join('')}</div>`
    : '';

  const scoreBadge = score
    ? `<div class="bw-score-badge ${scoreClass}" onclick="openProductModal('${escAttr(productId)}')" title="Click to see breakdown">🎯 ${score}/100</div>`
    : '';

  const savingsHtml = p.market_savings
    ? `<div class="bw-savings-text">💡 ${escHtml(p.market_savings)}</div>`
    : '';

  const oldPriceHtml = p.old_price
    ? `<span class="bw-product-old-price">${escHtml(p.old_price)}</span>`
    : '';

  return `
    <div class="bw-product-card${inCompare ? ' in-compare' : ''}" data-pid="${escAttr(productId)}">
      <div class="bw-product-img">${imgHtml}</div>
      <div class="bw-product-body">
        <div class="bw-product-source">${escHtml(p.source || '')}</div>
        ${tagsHtml}
        <div class="bw-product-title" title="${escAttr(p.title || '')}" onclick="openProductModal('${escAttr(productId)}')">${escHtml(p.title || 'Unknown Product')}</div>
        <div class="bw-product-price">${escHtml(price)}${oldPriceHtml}</div>
        <div class="bw-product-rating">${p.rating ? `⭐ ${p.rating}` : ''}${p.reviews ? ` (${p.reviews.toLocaleString('en-IN')} reviews)` : ''}</div>
        ${scoreBadge}
        ${savingsHtml}
        ${renderVisualPricePosition(p, false)}
        <div class="bw-product-actions">
          ${p.product_link
            ? `<a href="${escAttr(p.product_link)}" target="_blank" rel="noopener" class="bw-btn bw-btn-primary bw-btn-sm">View ↗</a>`
            : `<span class="bw-btn bw-btn-outline bw-btn-sm" style="opacity:0.4;cursor:default;">No Link</span>`}
          <button class="bw-btn bw-btn-compare bw-btn-sm${inCompare ? ' active' : ''}" id="cmp-card-${escAttr(productId)}" onclick="toggleCompare('${escAttr(productId)}')">
            ${inCompare ? '✓ Remove' : '+ Compare'}
          </button>
          <button class="bw-btn bw-btn-outline bw-btn-sm" onclick="openProductModal('${escAttr(productId)}')">Details</button>
        </div>
      </div>
    </div>
  `;
}

// ============================================================
// Security Helpers — prevent XSS
// ============================================================
function escHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escAttr(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
function renderIntent(intent) {
  const section = document.getElementById('intentSection');
  const content = document.getElementById('intentContent');
  
  if (!intent) {
    section.style.display = 'none';
    return;
  }
  
  section.style.display = 'block';
  
  const bMin = intent.budget_min ? `₹${intent.budget_min.toLocaleString('en-IN')}` : null;
  const bMax = intent.budget_max ? `₹${intent.budget_max.toLocaleString('en-IN')}` : null;
  let budgetStr = 'Not detected';
  if (bMin && bMax) budgetStr = `${bMin} - ${bMax}`;
  else if (bMin) budgetStr = `Above ${bMin}`;
  else if (bMax) budgetStr = `Under ${bMax}`;
  
  const categoryStr = intent.category ? intent.category : 'Not detected';
  
  let useCasesHtml = 'Not detected';
  if (intent.use_case_signals && intent.use_case_signals.length > 0) {
    useCasesHtml = intent.use_case_signals.map(uc => `<span class="badge">${uc}</span>`).join('');
  }
  
  const priorityStr = intent.priority ? intent.priority.replace('_', ' ') : 'Not detected';
  
  content.innerHTML = `
    <div class="bw-intent-item">
      <span class="bw-intent-label">Original Query</span>
      <span class="bw-intent-value" title="${escAttr(intent.product_query || '')}">${escHtml((intent.product_query || '').substring(0, 30))}${(intent.product_query || '').length > 30 ? '...' : ''}</span>
    </div>
    <div class="bw-intent-item">
      <span class="bw-intent-label">Detected Budget</span>
      <span class="bw-intent-value">${budgetStr}</span>
    </div>
    <div class="bw-intent-item">
      <span class="bw-intent-label">Category</span>
      <span class="bw-intent-value" style="text-transform: capitalize;">${categoryStr}</span>
    </div>
    <div class="bw-intent-item">
      <span class="bw-intent-label">Use Cases</span>
      <span class="bw-intent-value">${useCasesHtml}</span>
    </div>
    <div class="bw-intent-item">
      <span class="bw-intent-label">Decision Mode</span>
      <span class="bw-intent-value" style="text-transform: capitalize;">${priorityStr}</span>
    </div>
  `;
}

// ============================================================
// Visual Price Position
// ============================================================
function renderVisualPricePosition(p, isModal) {
  if (p.price_percentile == null || isNaN(p.price_percentile) || p.price == null) return '';
  let pct = p.price_percentile;
  if (pct < 0) pct = 0;
  if (pct > 100) pct = 100;
  
  let label = 'Near Median';
  if (pct <= 33) label = 'Below Median';
  else if (pct >= 67) label = 'Above Median';

  const sizeStyles = isModal 
    ? 'height: 6px; margin: 0.5rem 0; width: 100%;'
    : 'height: 4px; margin: 0.35rem 0; width: 100%;';
    
  const fontStyles = isModal
    ? 'font-size: 0.75rem;'
    : 'font-size: 0.7rem;';
  
  const markerTop = isModal ? '-4px' : '-2px';
  const markerBottom = isModal ? '-4px' : '-2px';
  const markerWidth = isModal ? '4px' : '3px';
  
  return `
    <div style="margin-top:0.75rem; margin-bottom:0.75rem;">
      <div style="display:flex; justify-content:space-between; ${fontStyles} color:var(--text-muted); margin-bottom:4px;">
        <span style="font-weight:600;">Price Position</span>
        <span>${label}</span>
      </div>
      <div style="position:relative; background:linear-gradient(to right, var(--accent-success), var(--text-muted), var(--accent-warning)); border-radius:4px; ${sizeStyles}">
        <div style="position:absolute; top:${markerTop}; bottom:${markerBottom}; left:${pct}%; width:${markerWidth}; background:#fff; border-radius:2px; box-shadow:0 1px 3px rgba(0,0,0,0.4); transform:translateX(-50%);"></div>
      </div>
      ${isModal ? `<div style="font-size:0.65rem; color:var(--text-muted); margin-top:4px;">Based on current observed results</div>` : ''}
    </div>
  `;
}
