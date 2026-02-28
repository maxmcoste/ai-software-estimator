/* Shared timeline Gantt rendering — used by app.js and history.js */
(function (global) {
  'use strict';

  function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function getRoleActiveWeeks(roles, planPhases) {
    const map = {};
    roles.forEach(r => { map[r.role] = new Set(); });
    planPhases.forEach(phase => {
      phase.roles.forEach(pr => {
        if (!map[pr.role]) map[pr.role] = new Set();
        for (let w = phase.start_week; w <= phase.end_week; w++) {
          map[pr.role].add(w);
        }
      });
    });
    return map;
  }

  function buildTable(roles, colHeaders, activeMap) {
    const rows = ['<div class="timeline-scroll"><table class="timeline-table"><thead><tr>',
      '<th class="tl-role-col">Role</th><th class="tl-md-col">Mandays</th>'];
    colHeaders.forEach(h => rows.push(`<th class="tl-period-col">${escHtml(h)}</th>`));
    rows.push('</tr></thead><tbody>');
    roles.forEach(r => {
      rows.push('<tr>');
      rows.push(`<td class="tl-role-name">${escHtml(r.role)}</td>`);
      rows.push(`<td class="tl-md-val">${Number(r.mandays).toFixed(1)}</td>`);
      colHeaders.forEach((_, i) => {
        const active = activeMap[r.role] && activeMap[r.role].has(i + 1);
        rows.push(`<td class="tl-cell${active ? ' tl-active' : ''}"></td>`);
      });
      rows.push('</tr>');
    });
    rows.push('</tbody></table></div>');
    return rows.join('');
  }

  function render(container, roles, planPhases, unit) {
    if (!roles || !roles.length || !planPhases || !planPhases.length) {
      container.innerHTML = '<p class="tl-empty">No timeline data available.</p>';
      return;
    }

    const WEEKS_PER_MONTH = 4.33;
    const totalWeeks = Math.max(...planPhases.map(p => p.end_week));
    const weekMap = getRoleActiveWeeks(roles, planPhases);

    if (unit === 'weeks') {
      const headers = Array.from({ length: totalWeeks }, (_, i) => `W${i + 1}`);
      container.innerHTML = buildTable(roles, headers, weekMap);
    } else {
      const totalMonths = Math.ceil(totalWeeks / WEEKS_PER_MONTH);
      // Convert week-active sets to month-active sets
      const monthMap = {};
      roles.forEach(r => {
        monthMap[r.role] = new Set();
        if (weekMap[r.role]) {
          weekMap[r.role].forEach(w => monthMap[r.role].add(Math.ceil(w / WEEKS_PER_MONTH)));
        }
      });
      const headers = Array.from({ length: totalMonths }, (_, i) => `M${i + 1}`);
      container.innerHTML = buildTable(roles, headers, monthMap);
    }
  }

  global.TimelineWidget = { render };
})(window);
