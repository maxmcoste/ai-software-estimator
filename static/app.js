/* AI Estimator — frontend */
(function () {
  'use strict';

  // ── DOM references ──────────────────────────────────────────────────────
  const form                  = document.getElementById('estimate-form');
  const submitBtn             = document.getElementById('submit-btn');
  const formSection           = document.getElementById('form-section');
  const progressSec           = document.getElementById('progress-section');
  const progressMsg           = document.getElementById('progress-message');
  const resultSec             = document.getElementById('result-section');
  const reportDiv             = document.getElementById('report-content');
  const downloadBtn           = document.getElementById('download-btn');
  const newEstBtn             = document.getElementById('new-estimate-btn');
  const errorBanner           = document.getElementById('error-banner');
  const errorMsg              = document.getElementById('error-message');
  const dismissErr            = document.getElementById('dismiss-error');
  const uploadProgressWrap     = document.getElementById('upload-progress-wrap');
  const estimationProgressWrap = document.getElementById('estimation-progress-wrap');
  const uploadPct              = document.getElementById('upload-pct');
  const uploadBarFill          = document.getElementById('upload-bar-fill');
  const requirementsPanel      = document.getElementById('requirements-panel');
  const reqPanelBody           = document.getElementById('req-panel-body');
  const reqPanelToggle         = document.getElementById('req-panel-toggle');
  const reqPanelContent        = document.getElementById('req-panel-content');
  const reqEditBtn             = document.getElementById('req-edit-btn');
  const reqPreviewWrap         = document.getElementById('req-preview-wrap');
  const reqEditWrap            = document.getElementById('req-edit-wrap');
  const reqEditTextarea        = document.getElementById('req-edit-textarea');
  const reqFileInput           = document.getElementById('req-file-input');
  const reqFileLoaded          = document.getElementById('req-file-loaded');
  const timelineSection    = document.getElementById('timeline-section');
  const timelineContent    = document.getElementById('timeline-content');

  // Tab switcher
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
  });

  // File name display on selection
  document.getElementById('requirements_file').addEventListener('change', e => {
    document.getElementById('req-file-name').textContent = e.target.files[0]?.name ?? '';
  });
  document.getElementById('estimation_model_file').addEventListener('change', e => {
    document.getElementById('model-file-name').textContent = e.target.files[0]?.name ?? '';
  });

  // Default model toggle
  document.getElementById('use-default-model').addEventListener('change', e => {
    document.getElementById('custom-model-panel').classList.toggle('hidden', e.target.checked);
  });

  // Error banner dismiss
  dismissErr.addEventListener('click', () => errorBanner.classList.add('hidden'));

  // New estimate button
  newEstBtn.addEventListener('click', resetUI);

  // Requirements panel — show/hide toggle
  reqPanelToggle.addEventListener('click', () => {
    const isHidden = reqPanelBody.classList.toggle('hidden');
    reqPanelToggle.textContent = isHidden ? 'Show' : 'Hide';
  });

  // Requirements panel — edit/preview toggle
  reqEditBtn.addEventListener('click', () => {
    const editing = !reqEditWrap.classList.contains('hidden');
    if (editing) {
      // Switch back to preview; re-render whatever is in the textarea
      const text = reqEditTextarea.value;
      reqPanelContent.innerHTML = marked.parse(text);
      requirementsModified = text !== rawRequirementsText;
      updateRerunConfirmBtn();
      reqPreviewWrap.classList.remove('hidden');
      reqEditWrap.classList.add('hidden');
      reqEditBtn.textContent = requirementsModified ? 'Edit ●' : 'Edit';
    } else {
      // Ensure body is visible, populate textarea if empty
      reqPanelBody.classList.remove('hidden');
      reqPanelToggle.textContent = 'Hide';
      if (!reqEditTextarea.value) reqEditTextarea.value = rawRequirementsText;
      reqPreviewWrap.classList.add('hidden');
      reqEditWrap.classList.remove('hidden');
      reqEditBtn.textContent = 'Preview';
    }
  });

  // Requirements panel — load new file
  reqFileInput.addEventListener('change', e => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = ev => {
      reqEditTextarea.value = ev.target.result;
      reqFileLoaded.textContent = file.name;
      requirementsModified = true;
      updateRerunConfirmBtn();
    };
    reader.readAsText(file);
  });

  // Track modifications as the user types
  reqEditTextarea.addEventListener('input', () => {
    requirementsModified = reqEditTextarea.value !== rawRequirementsText;
    updateRerunConfirmBtn();
  });

  // Timeline unit toggle
  document.querySelectorAll('#timeline-section .timeline-unit-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      if (!currentPlanData) return;
      currentTimelineUnit = btn.dataset.unit;
      document.querySelectorAll('#timeline-section .timeline-unit-btn')
        .forEach(b => b.classList.toggle('active', b === btn));
      TimelineWidget.render(timelineContent, currentPlanData.roles, currentPlanData.plan_phases, currentTimelineUnit);
    });
  });

  // ── State ───────────────────────────────────────────────────────────────
  let currentJobId         = null;
  let currentSaveId        = null;
  let rawRequirementsText  = '';
  let requirementsModified = false;
  let pollTimer            = null;
  let elapsedTimer    = null;
  let elapsedSeconds  = 0;
  let lastLogMessage  = null;
  let rawMarkdown     = '';
  let currentPlanData      = null;
  let currentTimelineUnit  = 'weeks';

  // ── UI helpers ──────────────────────────────────────────────────────────
  function showError(msg) {
    errorMsg.textContent = msg;
    errorBanner.classList.remove('hidden');
  }

  let _toastTimer = null;
  function showToast(msg) {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.classList.add('toast-visible');
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => toast.classList.remove('toast-visible'), 3000);
  }

  function resetUI() {
    clearInterval(pollTimer);
    clearInterval(elapsedTimer);
    currentJobId   = null;
    currentSaveId  = null;
    rawMarkdown    = '';
    elapsedSeconds = 0;
    lastLogMessage = null;
    formSection.classList.remove('hidden');
    progressSec.classList.add('hidden');
    resultSec.classList.add('hidden');
    errorBanner.classList.add('hidden');
    submitBtn.disabled = false;
    reportDiv.innerHTML = '';
    document.querySelector('.container').classList.remove('wide');
    // Reset requirements panel
    rawRequirementsText  = '';
    requirementsModified = false;
    requirementsPanel.classList.add('hidden');
    reqPanelBody.classList.add('hidden');
    reqPanelContent.innerHTML = '';
    reqPanelToggle.textContent = 'Show';
    reqEditBtn.textContent = 'Edit';
    reqEditTextarea.value = '';
    reqFileLoaded.textContent = '';
    reqPreviewWrap.classList.remove('hidden');
    reqEditWrap.classList.add('hidden');
    // Reset timeline
    currentPlanData = null;
    currentTimelineUnit = 'weeks';
    timelineSection.classList.add('hidden');
    timelineContent.innerHTML = '';
    // Reset save
    savePanel.classList.add('hidden');
    saveNameInput.value = '';
    saveBtn.textContent = 'Save';
    saveBtn.disabled = false;
    // Reset re-run panel
    rerunPanel.classList.add('hidden');
    rerunModelFile.value = '';
    rerunFileName.textContent = '';
    rerunConfirmBtn.disabled = true;
    rerunToggleBtn.disabled  = false;
    // Reset chat
    const chatMessages = document.getElementById('chat-messages');
    chatMessages.innerHTML = '<div class="chat-bubble assistant">Hi! I can explain any reasoning behind this estimate, or help you adjust specific values. What would you like to change?</div>';
    document.getElementById('chat-input').value = '';
    uploadPct.textContent = '0%';
    uploadBarFill.style.width = '0%';
    uploadProgressWrap.classList.remove('hidden');
    estimationProgressWrap.classList.add('hidden');
    document.getElementById('activity-log').innerHTML = '';
    document.getElementById('elapsed-timer').textContent = '0:00';
  }

  // ── Timer & log helpers ──────────────────────────────────────────────────
  function startElapsedTimer() {
    elapsedSeconds = 0;
    const el = document.getElementById('elapsed-timer');
    elapsedTimer = setInterval(() => {
      elapsedSeconds++;
      const m = Math.floor(elapsedSeconds / 60);
      const s = String(elapsedSeconds % 60).padStart(2, '0');
      el.textContent = `${m}:${s}`;
    }, 1000);
  }

  function appendLog(msg, type = '') {
    const log = document.getElementById('activity-log');
    const m   = Math.floor(elapsedSeconds / 60);
    const s   = String(elapsedSeconds % 60).padStart(2, '0');
    const entry = document.createElement('div');
    entry.className = 'log-entry' + (type ? ' log-' + type : '');
    entry.innerHTML = `<span class="log-time">${m}:${s}</span><span class="log-msg">${msg}</span>`;
    log.appendChild(entry);
    log.scrollTop = log.scrollHeight;
  }

  function showUploadProgress() {
    uploadProgressWrap.classList.remove('hidden');
    estimationProgressWrap.classList.add('hidden');
    uploadPct.textContent = '0%';
    uploadBarFill.style.width = '0%';
    formSection.classList.add('hidden');
    progressSec.classList.remove('hidden');
    resultSec.classList.add('hidden');
  }

  function switchToEstimationProgress(msg) {
    uploadProgressWrap.classList.add('hidden');
    estimationProgressWrap.classList.remove('hidden');
    progressMsg.textContent = msg;
    startElapsedTimer();
    appendLog(msg);
    lastLogMessage = msg;
  }

  function showProgress(msg) {
    progressMsg.textContent = msg;
    // Only append to log when message actually changes
    if (msg !== lastLogMessage) {
      const isDone  = msg.toLowerCase().includes('ready');
      const isError = msg.toLowerCase().includes('fail') || msg.toLowerCase().includes('error');
      appendLog(msg, isDone ? 'done' : isError ? 'error' : '');
      lastLogMessage = msg;
    }
    uploadProgressWrap.classList.add('hidden');
    estimationProgressWrap.classList.remove('hidden');
    formSection.classList.add('hidden');
    progressSec.classList.remove('hidden');
    resultSec.classList.add('hidden');
  }

  function showResult(markdown) {
    progressSec.classList.add('hidden');
    reportDiv.innerHTML = marked.parse(markdown);
    resultSec.classList.remove('hidden');
    document.querySelector('.container').classList.add('wide');
  }

  // ── Form submission ─────────────────────────────────────────────────────
  form.addEventListener('submit', async e => {
    e.preventDefault();
    errorBanner.classList.add('hidden');

    // Validate requirements
    const useUpload = document.querySelector('.tab-btn.active').dataset.tab === 'upload';
    const reqFile   = document.getElementById('requirements_file').files[0];
    const reqText   = document.getElementById('requirements_text').value.trim();

    if (useUpload && !reqFile) {
      showError('Please upload a requirements file or paste your requirements.');
      return;
    }
    if (!useUpload && !reqText) {
      showError('Please paste your project requirements.');
      return;
    }

    submitBtn.disabled = true;
    showUploadProgress();

    const fd = new FormData();

    if (useUpload && reqFile) {
      fd.append('requirements_file', reqFile);
    } else {
      fd.append('requirements_text', reqText);
    }

    const useDefault = document.getElementById('use-default-model').checked;
    const modelFile  = document.getElementById('estimation_model_file').files[0];
    if (!useDefault && modelFile) {
      fd.append('estimation_model_file', modelFile);
    }

    const githubUrl   = document.getElementById('github_url').value.trim();
    const githubToken = document.getElementById('github_token').value.trim();
    const mandayCost  = document.getElementById('manday_cost').value;
    const currency    = document.getElementById('currency').value;

    if (githubUrl)   fd.append('github_url',   githubUrl);
    if (githubToken) fd.append('github_token', githubToken);
    fd.append('manday_cost', mandayCost);
    fd.append('currency',    currency);

    const xhr = new XMLHttpRequest();
    let uploadTransitioned = false;

    function ensureEstimationPhase() {
      if (!uploadTransitioned) {
        uploadTransitioned = true;
        uploadPct.textContent = '100%';
        uploadBarFill.style.width = '100%';
        switchToEstimationProgress('Request received — starting estimation…');
      }
    }

    xhr.upload.addEventListener('progress', e => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        uploadPct.textContent = pct + '%';
        uploadBarFill.style.width = pct + '%';
      }
    });

    // upload.load fires when request body is fully sent — not always reliable
    // for small payloads on Safari/macOS, so ensureEstimationPhase() is also
    // called in xhr.load as a guaranteed fallback.
    xhr.upload.addEventListener('load', ensureEstimationPhase);

    xhr.addEventListener('load', () => {
      ensureEstimationPhase(); // no-op if upload.load already fired
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const { job_id } = JSON.parse(xhr.responseText);
          currentJobId = job_id;
          startPolling();
        } catch {
          showError('Unexpected server response.');
          formSection.classList.remove('hidden');
          progressSec.classList.add('hidden');
          submitBtn.disabled = false;
        }
      } else {
        let detail = `HTTP ${xhr.status}`;
        try { detail = JSON.parse(xhr.responseText).detail ?? detail; } catch { /* ignore */ }
        showError(detail);
        formSection.classList.remove('hidden');
        progressSec.classList.add('hidden');
        submitBtn.disabled = false;
      }
    });

    xhr.addEventListener('error', () => {
      showError('Network error — could not reach the server.');
      formSection.classList.remove('hidden');
      progressSec.classList.add('hidden');
      submitBtn.disabled = false;
    });

    xhr.open('POST', '/api/estimate');
    xhr.send(fd);
  });

  // ── Polling ─────────────────────────────────────────────────────────────
  function startPolling() {
    pollTimer = setInterval(poll, 2000);
  }

  async function poll() {
    if (!currentJobId) return;
    try {
      const res  = await fetch(`/api/estimate/${currentJobId}/status`);
      const data = await res.json();

      showProgress(data.progress_message ?? 'Working…');

      if (data.status === 'done') {
        clearInterval(pollTimer);
        await fetchReport();
      } else if (data.status === 'error') {
        clearInterval(pollTimer);
        showError(data.error_detail ?? 'An unknown error occurred.');
        formSection.classList.remove('hidden');
        progressSec.classList.add('hidden');
        submitBtn.disabled = false;
      }
    } catch (err) {
      // Network hiccup — keep polling
      console.warn('Poll error:', err);
    }
  }

  async function fetchReport() {
    try {
      const res = await fetch(`/api/estimate/${currentJobId}/report`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      rawMarkdown = await res.text();
      showResult(rawMarkdown);
      fetchAndRenderPlan();
      // Sync requirements panel if it was modified for this re-run
      if (requirementsModified && reqEditTextarea.value.trim()) {
        rawRequirementsText = reqEditTextarea.value.trim();
        requirementsModified = false;
        reqEditBtn.textContent = 'Edit';
        // Switch back to preview with updated content
        reqPanelContent.innerHTML = marked.parse(rawRequirementsText);
        reqPreviewWrap.classList.remove('hidden');
        reqEditWrap.classList.add('hidden');
        updateRerunConfirmBtn();
      }
      // Re-enable "Update draft" after a re-run completes
      if (currentSaveId) {
        saveBtn.textContent = 'Update draft';
        saveBtn.disabled = false;
      }
    } catch (err) {
      showError('Report ready but could not be loaded: ' + err.message);
      submitBtn.disabled = false;
    }
  }

  async function fetchAndRenderPlan() {
    if (!currentJobId) return;
    try {
      const res = await fetch(`/api/estimate/${currentJobId}/plan`);
      if (!res.ok) return;
      currentPlanData = await res.json();
      if (currentPlanData.roles.length || currentPlanData.plan_phases.length) {
        // Reset toggle to weeks
        currentTimelineUnit = 'weeks';
        document.querySelectorAll('#timeline-section .timeline-unit-btn')
          .forEach(b => b.classList.toggle('active', b.dataset.unit === 'weeks'));
        TimelineWidget.render(timelineContent, currentPlanData.roles, currentPlanData.plan_phases, currentTimelineUnit);
        timelineSection.classList.remove('hidden');
      }
    } catch { /* non-blocking */ }
  }

  // ── Download ─────────────────────────────────────────────────────────────
  downloadBtn.addEventListener('click', () => {
    if (!currentJobId) return;
    const link = document.createElement('a');
    link.href  = `/api/estimate/${currentJobId}/report`;
    link.download = `estimate-${currentJobId.slice(0, 8)}.md`;
    link.click();
  });

  // ── Save / Update draft ───────────────────────────────────────────────────
  const saveBtn        = document.getElementById('save-btn');
  const savePanel      = document.getElementById('save-panel');
  const saveNameInput  = document.getElementById('save-name-input');
  const saveConfirmBtn = document.getElementById('save-confirm-btn');
  const saveCancelBtn  = document.getElementById('save-cancel-btn');

  saveBtn.addEventListener('click', async () => {
    if (currentSaveId) { await updateDraft(); return; }
    savePanel.classList.toggle('hidden');
    if (!savePanel.classList.contains('hidden')) saveNameInput.focus();
  });

  saveCancelBtn.addEventListener('click', () => {
    savePanel.classList.add('hidden');
  });

  saveConfirmBtn.addEventListener('click', async () => {
    if (!currentJobId) return;
    const name = saveNameInput.value.trim();
    saveConfirmBtn.disabled = true;

    try {
      const res = await fetch('/api/saves', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: currentJobId, name }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `HTTP ${res.status}`);
      }
      const saved = await res.json();
      currentSaveId = saved.save_id;
      savePanel.classList.add('hidden');
      saveBtn.textContent = 'Update draft';
      saveBtn.disabled = false;
      showToast('Draft saved successfully');
    } catch (err) {
      showError('Save failed: ' + err.message);
      saveConfirmBtn.disabled = false;
    }
  });

  saveNameInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') saveConfirmBtn.click();
    if (e.key === 'Escape') saveCancelBtn.click();
  });

  async function updateDraft() {
    if (!currentJobId || !currentSaveId) return;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';
    try {
      const res = await fetch(`/api/saves/${currentSaveId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: currentJobId }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `HTTP ${res.status}`);
      }
      saveBtn.textContent = 'Updated ✓';
    } catch (err) {
      showError('Update failed: ' + err.message);
      saveBtn.textContent = 'Update draft';
      saveBtn.disabled = false;
    }
  }

  function updateRerunConfirmBtn() {
    const hasNewModel = !!(rerunModelFile && rerunModelFile.files[0]);
    rerunConfirmBtn.disabled = !hasNewModel && !requirementsModified;
  }

  // ── Re-run with new model ────────────────────────────────────────────────
  const rerunToggleBtn  = document.getElementById('rerun-toggle-btn');
  const rerunPanel      = document.getElementById('rerun-panel');
  const rerunModelFile  = document.getElementById('rerun-model-file');
  const rerunFileName   = document.getElementById('rerun-file-name');
  const rerunConfirmBtn = document.getElementById('rerun-confirm-btn');

  rerunToggleBtn.addEventListener('click', () => {
    rerunPanel.classList.toggle('hidden');
  });

  rerunModelFile.addEventListener('change', e => {
    const file = e.target.files[0];
    rerunFileName.textContent = file?.name ?? '';
    updateRerunConfirmBtn();
  });

  rerunConfirmBtn.addEventListener('click', async () => {
    if (!currentJobId) return;
    const file = rerunModelFile.files[0];
    if (!file && !requirementsModified) return;

    rerunConfirmBtn.disabled = true;
    rerunToggleBtn.disabled  = true;
    rerunPanel.classList.add('hidden');

    // Transition to progress view (reuse existing infrastructure)
    resultSec.classList.add('hidden');
    document.querySelector('.container').classList.remove('wide');
    showUploadProgress();

    const fd = new FormData();
    if (file) fd.append('rerun_model', file);
    // Include edited requirements if modified (textarea wins over file input)
    if (requirementsModified && reqEditTextarea.value.trim()) {
      fd.append('rerun_requirements_text', reqEditTextarea.value.trim());
    }

    const xhr = new XMLHttpRequest();
    let uploadTransitioned = false;

    function ensureEstimationPhase() {
      if (!uploadTransitioned) {
        uploadTransitioned = true;
        uploadPct.textContent = '100%';
        uploadBarFill.style.width = '100%';
        switchToEstimationProgress('Re-running with new model…');
      }
    }

    xhr.upload.addEventListener('progress', e => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        uploadPct.textContent = pct + '%';
        uploadBarFill.style.width = pct + '%';
      }
    });
    xhr.upload.addEventListener('load', ensureEstimationPhase);

    xhr.addEventListener('load', () => {
      ensureEstimationPhase();
      if (xhr.status >= 200 && xhr.status < 300) {
        startPolling();   // job_id unchanged — poll same job
      } else {
        let detail = `HTTP ${xhr.status}`;
        try { detail = JSON.parse(xhr.responseText).detail ?? detail; } catch { /* ignore */ }
        showError(detail);
        resultSec.classList.remove('hidden');
        document.querySelector('.container').classList.add('wide');
        progressSec.classList.add('hidden');
        rerunConfirmBtn.disabled = false;
        rerunToggleBtn.disabled  = false;
      }
    });

    xhr.addEventListener('error', () => {
      showError('Network error during re-run.');
      resultSec.classList.remove('hidden');
      document.querySelector('.container').classList.add('wide');
      progressSec.classList.add('hidden');
      rerunConfirmBtn.disabled = false;
      rerunToggleBtn.disabled  = false;
    });

    xhr.open('POST', `/api/estimate/${currentJobId}/rerun`);
    xhr.send(fd);
  });

  // ── Chat ──────────────────────────────────────────────────────────────────
  const chatInput     = document.getElementById('chat-input');
  const chatSendBtn   = document.getElementById('chat-send-btn');
  const chatMessages  = document.getElementById('chat-messages');
  const chatThinking  = document.getElementById('chat-thinking');

  function appendChatBubble(text, role, updated = false) {
    const div = document.createElement('div');
    div.className = 'chat-bubble ' + role + (updated ? ' updated' : '');
    div.innerHTML = role === 'assistant' ? marked.parse(text) : escapeHtml(text);
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    return div;
  }

  function escapeHtml(str) {
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  }

  async function sendChatMessage() {
    const message = chatInput.value.trim();
    if (!message || !currentJobId) return;

    chatInput.value = '';
    chatInput.disabled = true;
    chatSendBtn.disabled = true;
    appendChatBubble(message, 'user');
    chatThinking.classList.remove('hidden');
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
      const res = await fetch(`/api/estimate/${currentJobId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();

      chatThinking.classList.add('hidden');
      appendChatBubble(data.reply, 'assistant', data.estimate_updated);

      if (data.estimate_updated && data.report_markdown) {
        reportDiv.innerHTML = marked.parse(data.report_markdown);
        reportDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // Re-enable "Update draft" so the user can sync the change
        if (currentSaveId) {
          saveBtn.textContent = 'Update draft';
          saveBtn.disabled = false;
        }
      }
    } catch (err) {
      chatThinking.classList.add('hidden');
      appendChatBubble('Sorry, something went wrong: ' + err.message, 'assistant');
    } finally {
      chatInput.disabled = false;
      chatSendBtn.disabled = false;
      chatInput.focus();
    }
  }

  chatSendBtn.addEventListener('click', sendChatMessage);
  chatInput.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendChatMessage();
    }
  });

  // ── Restore from URL params (?job=...&save=...) ───────────────────────────
  async function restoreJobFromUrl(jobId, saveId) {
    currentJobId  = jobId;
    currentSaveId = saveId;
    formSection.classList.add('hidden');
    document.querySelector('.container').classList.add('wide');

    // Clean URL so a reload doesn't re-restore a stale job
    history.replaceState(null, '', '/');

    try {
      // Fetch job context (requirements, save name)
      const ctxRes = await fetch(`/api/estimate/${jobId}/context`);
      if (ctxRes.ok) {
        const ctx = await ctxRes.json();
        currentSaveId = ctx.save_id || saveId;

        if (ctx.requirements_md) {
          rawRequirementsText = ctx.requirements_md;
          reqPanelContent.innerHTML = marked.parse(ctx.requirements_md);
          requirementsPanel.classList.remove('hidden');
        }
      }

      // Update Save button to "Update draft"
      if (currentSaveId) {
        saveBtn.textContent = 'Update draft';
      }

      // Fetch and display the report
      const reportRes = await fetch(`/api/estimate/${jobId}/report`);
      if (!reportRes.ok) throw new Error(`HTTP ${reportRes.status}`);
      rawMarkdown = await reportRes.text();
      showResult(rawMarkdown);
    } catch (err) {
      showError('Could not restore estimation session: ' + err.message);
      formSection.classList.remove('hidden');
      document.querySelector('.container').classList.remove('wide');
    }
  }

  const _p = new URLSearchParams(window.location.search);
  const _job  = _p.get('job');
  const _save = _p.get('save');
  if (_job) restoreJobFromUrl(_job, _save);

})();
