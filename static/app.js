/* AI Estimator — frontend */
(function () {
  'use strict';

  // ── DOM references ──────────────────────────────────────────────────────
  const form         = document.getElementById('estimate-form');
  const submitBtn    = document.getElementById('submit-btn');
  const formSection  = document.getElementById('form-section');
  const progressSec  = document.getElementById('progress-section');
  const progressMsg  = document.getElementById('progress-message');
  const resultSec    = document.getElementById('result-section');
  const reportDiv    = document.getElementById('report-content');
  const downloadBtn  = document.getElementById('download-btn');
  const newEstBtn    = document.getElementById('new-estimate-btn');
  const errorBanner  = document.getElementById('error-banner');
  const errorMsg     = document.getElementById('error-message');
  const dismissErr   = document.getElementById('dismiss-error');

  // Tab switcher
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
  });

  // File name display
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
  let currentJobId = null;
  let pollTimer    = null;
  let rawMarkdown  = '';

  // ── UI helpers ──────────────────────────────────────────────────────────
  function showError(msg) {
    errorMsg.textContent = msg;
    errorBanner.classList.remove('hidden');
  }

  function resetUI() {
    clearInterval(pollTimer);
    currentJobId = null;
    rawMarkdown  = '';
    formSection.classList.remove('hidden');
    progressSec.classList.add('hidden');
    resultSec.classList.add('hidden');
    errorBanner.classList.add('hidden');
    submitBtn.disabled = false;
    reportDiv.innerHTML = '';
  }

  function showProgress(msg) {
    progressMsg.textContent = msg;
    formSection.classList.add('hidden');
    progressSec.classList.remove('hidden');
    resultSec.classList.add('hidden');
  }

  function showResult(markdown) {
    progressSec.classList.add('hidden');
    reportDiv.innerHTML = marked.parse(markdown);
    resultSec.classList.remove('hidden');
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
    showProgress('Submitting request…');

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

    try {
      const res = await fetch('/api/estimate', { method: 'POST', body: fd });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `HTTP ${res.status}`);
      }
      const { job_id } = await res.json();
      currentJobId = job_id;
      startPolling();
    } catch (err) {
      showError(err.message);
      formSection.classList.remove('hidden');
      progressSec.classList.add('hidden');
      submitBtn.disabled = false;
    }
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

})();
