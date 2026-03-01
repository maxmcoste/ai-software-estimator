/* Satellite accordion post-processor for rendered markdown reports */
(function () {
  'use strict';

  /**
   * Walk the rendered HTML inside `container`, find every <h3> whose text
   * starts with "Satellite N:", and wrap it together with its following
   * siblings (until the next satellite <h3> or an <hr>) inside a native
   * <details>/<summary> accordion element.
   *
   * Active satellites (Status: ACTIVE) are expanded by default.
   * Inactive satellites (Status: NOT REQUIRED) start collapsed.
   *
   * @param {Element} container - The DOM element containing rendered markdown.
   */
  function apply(container) {
    if (!container) return;

    // Collect all h3 elements whose text matches "Satellite N: ..."
    const h3List = Array.from(container.querySelectorAll('h3')).filter(h3 =>
      /^Satellite\s+\d+:/i.test(h3.textContent.trim())
    );

    if (h3List.length === 0) return;

    // Set for O(1) satellite-h3 lookup when collecting siblings
    const satH3Set = new Set(h3List);

    h3List.forEach(h3 => {
      // Collect all following siblings until the next satellite h3 or <hr>
      const siblings = [];
      let node = h3.nextElementSibling;
      while (node && !satH3Set.has(node) && node.tagName !== 'HR') {
        siblings.push(node);
        node = node.nextElementSibling;
      }

      // Detect active state: look for "Status: ACTIVE" text without "NOT"
      const allText = siblings.map(s => s.textContent).join(' ');
      const isActive = /Status:\s*ACTIVE/i.test(allText) && !/Status:\s*NOT/i.test(allText);

      const badgeLabel = isActive ? 'ACTIVE' : 'NOT REQUIRED';
      const badgeClass = isActive ? 'sat-badge sat-active' : 'sat-badge sat-inactive';

      // Build <details>
      const details = document.createElement('details');
      details.className = 'satellite-section';
      if (isActive) details.open = true;

      // Build <summary> with the original h3 content + status badge
      const summary = document.createElement('summary');
      summary.className = 'satellite-summary';
      summary.innerHTML = h3.innerHTML + ' <span class="' + badgeClass + '">' + badgeLabel + '</span>';

      // Build body <div> and move siblings into it
      const body = document.createElement('div');
      body.className = 'satellite-body';
      siblings.forEach(s => body.appendChild(s));

      details.appendChild(summary);
      details.appendChild(body);

      // Replace the original h3 with the new details element
      h3.parentNode.replaceChild(details, h3);
    });
  }

  window.SatelliteAccordion = { apply };
})();

window.CostTable = (function () {
  'use strict';

  function recalcTotal(table) {
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    let totalMd = 0, totalCost = 0;

    rows.forEach(tr => {
      const cb = tr.querySelector('.cost-row-cb');
      if (!cb || !cb.checked) return;
      const cells = tr.querySelectorAll('td');
      if (cells.length < 4) return;
      const md   = parseFloat(cells[2].textContent.replace(/,/g, ''));
      const cost = parseFloat(cells[3].textContent.replace(/,/g, ''));
      if (!isNaN(md))   totalMd   += md;
      if (!isNaN(cost)) totalCost += cost;
    });

    // TOTAL row = the tbody row without a .cost-row-cb
    const totalRow = rows.find(tr => !tr.querySelector('.cost-row-cb'));
    if (!totalRow) return;
    const cells = totalRow.querySelectorAll('td');
    if (cells.length < 4) return;

    const mdStrong   = cells[2].querySelector('strong');
    const costStrong = cells[3].querySelector('strong');
    const mdText   = totalMd.toFixed(1);
    const costText = totalCost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    if (mdStrong)   mdStrong.textContent   = mdText;   else cells[2].textContent = mdText;
    if (costStrong) costStrong.textContent = costText; else cells[3].textContent = costText;
  }

  function apply(container, inclusions) {
    const inc = Object.assign({}, inclusions || {});

    const h3 = Array.from(container.querySelectorAll('h3'))
      .find(h => h.textContent.trim() === 'Cost Overview');
    if (!h3) return { getInclusions: () => ({}) };

    let table = h3.nextElementSibling;
    while (table && table.tagName !== 'TABLE') table = table.nextElementSibling;
    if (!table) return { getInclusions: () => ({}) };

    const headerRow = table.querySelector('thead tr');
    if (!headerRow) return { getInclusions: () => ({}) };
    const thCb = document.createElement('th');
    thCb.className = 'cost-cb-col';
    headerRow.insertBefore(thCb, headerRow.firstChild);

    Array.from(table.querySelectorAll('tbody tr')).forEach(tr => {
      const firstCell = tr.querySelector('td');
      if (!firstCell) return;
      const key = firstCell.textContent.trim();
      const td  = document.createElement('td');
      td.className = 'cost-cb-col';

      if (key === 'TOTAL') {
        tr.insertBefore(td, tr.firstChild);
        return;
      }

      const checked = key in inc ? inc[key] : true;
      inc[key] = checked;

      const cb = document.createElement('input');
      cb.type      = 'checkbox';
      cb.className = 'cost-row-cb';
      cb.checked   = checked;
      cb.dataset.rowKey = key;
      td.appendChild(cb);
      tr.insertBefore(td, tr.firstChild);

      if (!checked) tr.classList.add('cost-row-excluded');

      cb.addEventListener('change', () => {
        inc[key] = cb.checked;
        tr.classList.toggle('cost-row-excluded', !cb.checked);
        recalcTotal(table);
      });
    });

    recalcTotal(table);
    return { getInclusions: () => Object.assign({}, inc) };
  }

  return { apply };
})();
