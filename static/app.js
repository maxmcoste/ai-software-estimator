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

  // ── State ───────────────────────────────────────────────────────────────
  let currentJobId    = null;
  let pollTimer       = null;
  let elapsedTimer    = null;
  let elapsedSeconds  = 0;
  let lastLogMessage  = null;
  let rawMarkdown     = '';

  // ── UI helpers ──────────────────────────────────────────────────────────
  function showError(msg) {
    errorMsg.textContent = msg;
    errorBanner.classList.remove('hidden');
  }

  function resetUI() {
    clearInterval(pollTimer);
    clearInterval(elapsedTimer);
    currentJobId   = null;
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
    } catch (err) {
      showError('Report ready but could not be loaded: ' + err.message);
      submitBtn.disabled = false;
    }
  }

  // ── Download ─────────────────────────────────────────────────────────────
  downloadBtn.addEventListener('click', () => {
    if (!currentJobId) return;
    const link = document.createElement('a');
    link.href  = `/api/estimate/${currentJobId}/report`;
    link.download = `estimate-${currentJobId.slice(0, 8)}.md`;
    link.click();
  });

  // ── Save ──────────────────────────────────────────────────────────────────
  const saveBtn        = document.getElementById('save-btn');
  const savePanel      = document.getElementById('save-panel');
  const saveNameInput  = document.getElementById('save-name-input');
  const saveConfirmBtn = document.getElementById('save-confirm-btn');
  const saveCancelBtn  = document.getElementById('save-cancel-btn');

  saveBtn.addEventListener('click', () => {
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
      savePanel.classList.add('hidden');
      saveBtn.textContent = 'Saved ✓';
      saveBtn.disabled = true;
    } catch (err) {
      showError('Save failed: ' + err.message);
      saveConfirmBtn.disabled = false;
    }
  });

  saveNameInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') saveConfirmBtn.click();
    if (e.key === 'Escape') saveCancelBtn.click();
  });

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
    rerunConfirmBtn.disabled = !file;
  });

  rerunConfirmBtn.addEventListener('click', async () => {
    const file = rerunModelFile.files[0];
    if (!file || !currentJobId) return;

    rerunConfirmBtn.disabled = true;
    rerunToggleBtn.disabled  = true;
    rerunPanel.classList.add('hidden');

    // Transition to progress view (reuse existing infrastructure)
    resultSec.classList.add('hidden');
    document.querySelector('.container').classList.remove('wide');
    uploadTransitionedGlobal = false;
    showUploadProgress();

    const fd = new FormData();
    fd.append('model_file', file);

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

})();
