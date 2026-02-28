/* History page */
(function () {
  'use strict';

  const listView        = document.getElementById('list-view');
  const detailView      = document.getElementById('detail-view');
  const savesGrid       = document.getElementById('saves-grid');
  const emptyState      = document.getElementById('empty-state');
  const backBtn         = document.getElementById('back-btn');
  const detailName      = document.getElementById('detail-name');
  const detailDates     = document.getElementById('detail-dates');
  const detailReport    = document.getElementById('detail-report');
  const detailBadge     = document.getElementById('detail-status-badge');
  const detailDownload  = document.getElementById('detail-download-btn');
  const detailChange    = document.getElementById('detail-change-btn');
  const detailFinalize  = document.getElementById('detail-finalize-btn');
  const detailDelete    = document.getElementById('detail-delete-btn');
  const confirmModal    = document.getElementById('confirm-modal');
  const confirmMsg      = document.getElementById('confirm-message');
  const confirmYes      = document.getElementById('confirm-yes');
  const confirmNo       = document.getElementById('confirm-no');
  const detailTimeline        = document.getElementById('detail-timeline');
  const detailTimelineContent = document.getElementById('detail-timeline-content');

  let currentSave = null;

  // ── Helpers ───────────────────────────────────────────────────────────────
  function fmt(iso) {
    return new Date(iso).toLocaleString(undefined, {
      dateStyle: 'medium', timeStyle: 'short'
    });
  }

  function fmtNum(n) {
    return Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 });
  }

  function confirm(message) {
    return new Promise(resolve => {
      confirmMsg.textContent = message;
      confirmModal.classList.remove('hidden');
      const cleanup = (result) => {
        confirmModal.classList.add('hidden');
        confirmYes.removeEventListener('click', onYes);
        confirmNo.removeEventListener('click', onNo);
        resolve(result);
      };
      const onYes = () => cleanup(true);
      const onNo  = () => cleanup(false);
      confirmYes.addEventListener('click', onYes);
      confirmNo.addEventListener('click', onNo);
    });
  }

  // ── Load list ─────────────────────────────────────────────────────────────
  async function loadList() {
    const res   = await fetch('/api/saves');
    const saves = await res.json();

    savesGrid.innerHTML = '';

    if (saves.length === 0) {
      emptyState.classList.remove('hidden');
      return;
    }
    emptyState.classList.add('hidden');

    saves.forEach(s => {
      const card = document.createElement('div');
      card.className = 'save-card';
      card.innerHTML = `
        <div class="save-card-top">
          <span class="status-badge status-${s.status}">${s.status === 'final' ? '🔒 Final' : '✏️ Draft'}</span>
          <span class="save-date">${fmt(s.updated_at)}</span>
        </div>
        <h3 class="save-card-name">${escHtml(s.name)}</h3>
        <p class="save-card-project">${escHtml(s.project_name)}</p>
        <div class="save-card-numbers">
          <span>${fmtNum(s.grand_mandays)} mandays</span>
          <span>${fmtNum(s.grand_cost)} ${escHtml(s.currency)}</span>
        </div>`;
      card.addEventListener('click', () => openDetail(s.save_id));
      savesGrid.appendChild(card);
    });
  }

  // ── Open detail ───────────────────────────────────────────────────────────
  async function openDetail(save_id) {
    const res  = await fetch(`/api/saves/${save_id}`);
    if (!res.ok) { alert('Could not load estimate.'); return; }
    const data = await res.json();
    currentSave = data;

    detailName.textContent  = data.name;
    detailDates.textContent = `Created ${fmt(data.created_at)}  ·  Last updated ${fmt(data.updated_at)}`;
    detailReport.innerHTML  = marked.parse(data.report_markdown);

    // Render timeline if plan data is available
    detailTimeline.classList.add('hidden');
    detailTimelineContent.innerHTML = '';
    if (data.roles && data.roles.length && data.plan_phases && data.plan_phases.length) {
      let tlUnit = 'weeks';
      // Reset toggle buttons
      detailTimeline.querySelectorAll('.timeline-unit-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.unit === 'weeks');
        // Remove old listeners by replacing each button with a clone
        const clone = btn.cloneNode(true);
        btn.parentNode.replaceChild(clone, btn);
      });
      // Add fresh listeners
      detailTimeline.querySelectorAll('.timeline-unit-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          tlUnit = btn.dataset.unit;
          detailTimeline.querySelectorAll('.timeline-unit-btn')
            .forEach(b => b.classList.toggle('active', b === btn));
          TimelineWidget.render(detailTimelineContent, data.roles, data.plan_phases, tlUnit);
        });
      });
      TimelineWidget.render(detailTimelineContent, data.roles, data.plan_phases, tlUnit);
      detailTimeline.classList.remove('hidden');
    }

    const isFinal = data.status === 'final';
    detailBadge.textContent  = isFinal ? '🔒 Final' : '✏️ Draft';
    detailBadge.className    = `status-badge status-${data.status}`;
    detailChange.classList.toggle('hidden', isFinal);
    detailFinalize.classList.toggle('hidden', isFinal);
    detailDelete.classList.toggle('hidden', isFinal);

    listView.classList.add('hidden');
    detailView.classList.remove('hidden');
    window.scrollTo(0, 0);
  }

  // ── Back ──────────────────────────────────────────────────────────────────
  backBtn.addEventListener('click', () => {
    detailView.classList.add('hidden');
    listView.classList.remove('hidden');
    currentSave = null;
    detailTimeline.classList.add('hidden');
    detailTimelineContent.innerHTML = '';
  });

  // ── Change (open draft for editing) ───────────────────────────────────────
  detailChange.addEventListener('click', async () => {
    if (!currentSave) return;
    detailChange.disabled = true;
    detailChange.textContent = 'Opening…';

    const res = await fetch(`/api/saves/${currentSave.save_id}/open`, { method: 'POST' });
    if (!res.ok) {
      alert('Could not open estimate for editing.');
      detailChange.disabled = false;
      detailChange.textContent = 'Change';
      return;
    }
    const { job_id, save_id } = await res.json();
    window.location.href = `/?job=${job_id}&save=${save_id}`;
  });

  // ── Download ──────────────────────────────────────────────────────────────
  detailDownload.addEventListener('click', () => {
    if (!currentSave) return;
    const blob = new Blob([currentSave.report_markdown], { type: 'text/markdown' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `${currentSave.name.replace(/[^a-z0-9]/gi, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
  });

  // ── Finalize ──────────────────────────────────────────────────────────────
  detailFinalize.addEventListener('click', async () => {
    if (!currentSave) return;
    const ok = await confirm(`Finalize "${currentSave.name}"? This will lock the estimate permanently and prevent any further changes.`);
    if (!ok) return;

    const res = await fetch(`/api/saves/${currentSave.save_id}/finalize`, { method: 'POST' });
    if (!res.ok) { alert('Failed to finalize.'); return; }
    const updated = await res.json();
    currentSave.status = updated.status;
    detailBadge.textContent = '🔒 Final';
    detailBadge.className   = 'status-badge status-final';
    detailFinalize.classList.add('hidden');
    detailDelete.classList.add('hidden');
  });

  // ── Delete ────────────────────────────────────────────────────────────────
  detailDelete.addEventListener('click', async () => {
    if (!currentSave) return;
    const ok = await confirm(`Delete "${currentSave.name}"? This cannot be undone.`);
    if (!ok) return;

    const res = await fetch(`/api/saves/${currentSave.save_id}`, { method: 'DELETE' });
    if (!res.ok) { alert('Failed to delete.'); return; }
    detailView.classList.add('hidden');
    listView.classList.remove('hidden');
    currentSave = null;
    loadList();
  });

  // ── Util ──────────────────────────────────────────────────────────────────
  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  loadList();
})();
