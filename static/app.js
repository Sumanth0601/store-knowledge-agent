/* ──────────────────────────────────────────────
   State
────────────────────────────────────────────── */
let currentStoreId = null;
let missingCount = 0;

/* ──────────────────────────────────────────────
   Store loading
────────────────────────────────────────────── */
async function loadStore() {
  const btn = document.getElementById('btn-load');
  btn.textContent = 'Loading…';
  btn.disabled = true;

  try {
    const res = await fetch('/api/load-store', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ store_json_path: 'sample_data/sample_store.json' }),
    });
    const data = await res.json();

    if (!res.ok) {
      showToast(`Error: ${data.error}`, 'error');
      return;
    }

    currentStoreId = data.store_id;
    document.getElementById('store-status').innerHTML =
      `<span class="text-green-400 font-medium">${data.store_name}</span>` +
      `<span class="text-gray-500 ml-2 text-xs">${data.products_ingested} products · ` +
      `${data.faqs_ingested} FAQs · ${data.policies_ingested} policies loaded</span>`;

    btn.textContent = 'Reload Store';
    btn.disabled = false;

    document.getElementById('empty-chat').classList.add('hidden');
    showToast(`Store loaded: ${data.store_name}`, 'success');
  } catch (err) {
    showToast('Failed to load store. Is the server running?', 'error');
    btn.textContent = 'Load Store';
    btn.disabled = false;
  }
}

/* ──────────────────────────────────────────────
   Chat
────────────────────────────────────────────── */
function askQuestion(q) {
  document.getElementById('chat-input').value = q;
  sendMessage();
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const question = input.value.trim();
  if (!question) return;

  if (!currentStoreId) {
    showToast('Load the store first.', 'error');
    return;
  }

  input.value = '';
  appendUserBubble(question);

  const thinkingId = appendThinkingBubble();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ store_id: currentStoreId, question }),
    });
    const data = await res.json();
    removeThinkingBubble(thinkingId);

    if (!res.ok) {
      appendErrorBubble(data.error || 'Something went wrong.');
      return;
    }

    appendAgentBubble(data);

    if (data.confidence.flagged_missing) {
      missingCount++;
      updateMissingBadge();
      refreshMissingList();
    }
  } catch (err) {
    removeThinkingBubble(thinkingId);
    appendErrorBubble('Network error — is the server running?');
  }
}

/* ──────────────────────────────────────────────
   Chat bubble renderers
────────────────────────────────────────────── */
function appendUserBubble(text) {
  const container = document.getElementById('chat-messages');
  const el = document.createElement('div');
  el.className = 'flex justify-end';
  el.innerHTML = `
    <div class="bg-gray-900 text-white text-sm rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-xs lg:max-w-sm shadow-sm">
      ${escapeHtml(text)}
    </div>`;
  container.appendChild(el);
  scrollChat();
}

function appendThinkingBubble() {
  const container = document.getElementById('chat-messages');
  const id = 'thinking-' + Date.now();
  const el = document.createElement('div');
  el.id = id;
  el.className = 'flex justify-start';
  el.innerHTML = `
    <div class="bg-gray-100 text-gray-400 text-sm rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-xs shadow-sm animate-pulse">
      Thinking…
    </div>`;
  container.appendChild(el);
  scrollChat();
  return id;
}

function removeThinkingBubble(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function appendAgentBubble(data) {
  const container = document.getElementById('chat-messages');
  const el = document.createElement('div');
  el.className = 'flex justify-start';

  const conf = data.confidence;
  const confPct = Math.round(conf.score * 100);
  const confColor = confPct >= 70
    ? 'bg-green-100 text-green-800 border-green-200'
    : confPct >= 50
      ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
      : 'bg-red-100 text-red-800 border-red-200';

  const typeColor = {
    product_query: 'bg-blue-100 text-blue-700',
    policy_query:  'bg-purple-100 text-purple-700',
    faq_query:     'bg-green-100 text-green-700',
    mixed:         'bg-gray-100 text-gray-700',
  }[data.question_type] || 'bg-gray-100 text-gray-700';

  const typeLabel = {
    product_query: 'product',
    policy_query:  'policy',
    faq_query:     'faq',
    mixed:         'mixed',
  }[data.question_type] || data.question_type;

  const sourcesHtml = data.sources.length > 0
    ? `<details class="source-details mt-2">
        <summary class="text-xs text-gray-400 cursor-pointer hover:text-gray-600 select-none">
          ${data.sources.length} source${data.sources.length > 1 ? 's' : ''} used
        </summary>
        <div class="mt-1 space-y-1">
          ${data.sources.map(s => `
            <div class="text-xs bg-gray-50 border border-gray-100 rounded p-2">
              <span class="font-medium text-gray-500">${s.chunk_type}</span>
              <span class="text-gray-400 ml-1">${(s.relevance_score * 100).toFixed(0)}% match</span>
              <p class="text-gray-500 mt-0.5 line-clamp-2">${escapeHtml(s.text.substring(0, 120))}…</p>
            </div>`).join('')}
        </div>
      </details>`
    : '';

  el.innerHTML = `
    <div class="bg-white border border-gray-200 text-gray-800 text-sm rounded-2xl rounded-tl-sm px-4 py-3 max-w-sm lg:max-w-md shadow-sm">
      <p class="leading-relaxed">${escapeHtml(data.answer)}</p>
      <div class="flex items-center gap-2 mt-2.5 flex-wrap">
        <span class="text-xs px-2 py-0.5 rounded-full font-medium ${typeColor}">${typeLabel}</span>
        <span class="text-xs px-2 py-0.5 rounded-full font-bold border ${confColor}">${confPct}% confident</span>
        ${conf.flagged_missing ? '<span class="text-xs text-red-500">⚠ logged as gap</span>' : ''}
      </div>
      <p class="text-xs text-gray-400 mt-1">${escapeHtml(conf.reason)}</p>
      ${sourcesHtml}
    </div>`;

  container.appendChild(el);
  scrollChat();
}

function appendErrorBubble(msg) {
  const container = document.getElementById('chat-messages');
  const el = document.createElement('div');
  el.className = 'flex justify-start';
  el.innerHTML = `
    <div class="bg-red-50 border border-red-200 text-red-700 text-sm rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-sm shadow-sm">
      ${escapeHtml(msg)}
    </div>`;
  container.appendChild(el);
  scrollChat();
}

function scrollChat() {
  const container = document.getElementById('chat-messages');
  container.scrollTop = container.scrollHeight;
}

/* ──────────────────────────────────────────────
   Missing info panel
────────────────────────────────────────────── */
function updateMissingBadge() {
  const badge = document.getElementById('missing-count-badge');
  badge.textContent = missingCount;
  badge.classList.remove('hidden');
}

async function refreshMissingList() {
  try {
    const res = await fetch('/api/missing-info');
    const data = await res.json();
    renderMissingList(data.questions || []);
  } catch (_) {}
}

function renderMissingList(questions) {
  const emptyEl = document.getElementById('empty-missing');
  const listEl = document.getElementById('missing-list');
  const clusterEl = document.getElementById('cluster-list');

  if (questions.length === 0) {
    emptyEl.classList.remove('hidden');
    listEl.innerHTML = '';
    return;
  }

  emptyEl.classList.add('hidden');
  clusterEl.innerHTML = ''; // clear clusters when refreshing raw list

  listEl.innerHTML = questions.map(q => {
    const confPct = Math.round(q.confidence_score * 100);
    const timeStr = new Date(q.asked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    return `
      <div class="bg-white border border-amber-200 rounded-lg px-3 py-2.5 shadow-sm">
        <p class="text-sm text-gray-800">${escapeHtml(q.question)}</p>
        <div class="flex items-center gap-2 mt-1">
          <span class="text-xs text-gray-400">${timeStr}</span>
          <span class="text-xs bg-red-100 text-red-700 border border-red-200 font-bold px-1.5 py-0.5 rounded-full">${confPct}%</span>
          <span class="text-xs text-amber-600">${q.question_type.replace('_', ' ')}</span>
        </div>
      </div>`;
  }).join('');
}

async function clusterGaps() {
  const btn = document.getElementById('btn-cluster');
  btn.textContent = 'Clustering…';
  btn.disabled = true;

  try {
    const res = await fetch('/api/cluster-gaps', { method: 'POST' });
    const data = await res.json();

    btn.textContent = 'Cluster Gaps';
    btn.disabled = false;

    if (!res.ok) {
      showToast(`Clustering failed: ${data.error}`, 'error');
      return;
    }

    if (data.total_unanswered === 0) {
      showToast('No unanswered questions to cluster yet.', 'info');
      return;
    }

    renderClusters(data.clusters);
  } catch (err) {
    btn.textContent = 'Cluster Gaps';
    btn.disabled = false;
    showToast('Clustering failed — check server logs.', 'error');
  }
}

function renderClusters(clusters) {
  const listEl = document.getElementById('missing-list');
  const clusterEl = document.getElementById('cluster-list');
  const emptyEl = document.getElementById('empty-missing');

  listEl.innerHTML = '';
  emptyEl.classList.add('hidden');

  const maxGap = Math.max(...clusters.map(c => c.gap_score), 1);

  clusterEl.innerHTML = clusters.map(c => {
    const barWidth = Math.round((c.gap_score / maxGap) * 100);
    return `
      <div class="bg-white border border-amber-300 rounded-xl px-4 py-3 shadow-sm">
        <div class="flex items-center justify-between mb-1">
          <h3 class="font-semibold text-gray-800 text-sm">${escapeHtml(c.topic)}</h3>
          <span class="text-xs text-gray-500">${c.count} question${c.count !== 1 ? 's' : ''}</span>
        </div>
        <div class="w-full bg-amber-100 rounded-full h-1.5 mb-2">
          <div class="bg-amber-500 h-1.5 rounded-full gap-bar" style="width: ${barWidth}%"></div>
        </div>
        <p class="text-xs text-gray-500 mb-2">Gap score: <span class="font-medium text-amber-700">${c.gap_score.toFixed(2)}</span></p>
        <div class="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-2">
          <p class="text-xs font-medium text-amber-800">Recommendation</p>
          <p class="text-xs text-amber-700 mt-0.5">${escapeHtml(c.recommendation)}</p>
        </div>
        <details>
          <summary class="text-xs text-gray-400 cursor-pointer hover:text-gray-600 select-none">
            View questions (${c.count})
          </summary>
          <ul class="mt-1 space-y-0.5 pl-2">
            ${c.questions.map(q => `<li class="text-xs text-gray-600">• ${escapeHtml(q)}</li>`).join('')}
          </ul>
        </details>
      </div>`;
  }).join('');
}

/* ──────────────────────────────────────────────
   Toast notifications
────────────────────────────────────────────── */
function showToast(message, type = 'info') {
  const colors = {
    success: 'bg-green-800 text-white',
    error:   'bg-red-700 text-white',
    info:    'bg-gray-800 text-white',
  };
  const toast = document.createElement('div');
  toast.className = `fixed bottom-5 left-1/2 -translate-x-1/2 px-4 py-2 rounded-lg text-sm shadow-lg z-50 ${colors[type] || colors.info}`;
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 3000);
}

/* ──────────────────────────────────────────────
   Utilities
────────────────────────────────────────────── */
function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
