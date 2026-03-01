/* Settings page */
(function () {
  'use strict';

  const form     = document.getElementById('settings-form');
  const saveBtn  = document.getElementById('save-btn');
  const feedback = document.getElementById('settings-feedback');

  function setHint(el, isSet, hint) {
    if (isSet) {
      el.textContent = `Current: ${hint}`;
      el.className = 'key-hint key-set';
    } else {
      el.textContent = 'Not configured';
      el.className = 'key-hint key-unset';
    }
  }

  function showFeedback(msg, isError) {
    feedback.textContent = msg;
    feedback.className = 'settings-feedback ' + (isError ? 'feedback-error' : 'feedback-ok');
    feedback.classList.remove('hidden');
    setTimeout(() => feedback.classList.add('hidden'), 4000);
  }

  async function loadSettings() {
    try {
      const res  = await fetch('/api/settings');
      if (!res.ok) return;
      const data = await res.json();
      setHint(document.getElementById('anthropic_hint'), data.anthropic_api_key_set, data.anthropic_api_key_hint);
      setHint(document.getElementById('github_hint'),    data.github_token_set,       data.github_token_hint);
      document.getElementById('estimation_prompt').value = data.estimation_prompt || '';
      document.getElementById('chat_prompt').value       = data.chat_prompt       || '';
    } catch { /* ignore — hints stay blank */ }
  }

  form.addEventListener('submit', async e => {
    e.preventDefault();
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';

    const body = {
      anthropic_api_key: document.getElementById('anthropic_api_key').value,
      github_token:      document.getElementById('github_token').value,
      estimation_prompt: document.getElementById('estimation_prompt').value,
      chat_prompt:       document.getElementById('chat_prompt').value,
    };

    try {
      const res = await fetch('/api/settings', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(body),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `HTTP ${res.status}`);
      }
      document.getElementById('anthropic_api_key').value = '';
      document.getElementById('github_token').value      = '';
      await loadSettings();
      showFeedback('Settings saved successfully.', false);
    } catch (err) {
      showFeedback('Save failed: ' + err.message, true);
    } finally {
      saveBtn.disabled    = false;
      saveBtn.textContent = 'Save Settings';
    }
  });

  loadSettings();
})();
