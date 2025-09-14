document.addEventListener('DOMContentLoaded', function () {
  // Elements
  const locInput = document.getElementById('location-input');
  const locDropdown = document.getElementById('location-dropdown');
  const provinceList = document.getElementById('province-list');
  const locationHidden = document.getElementById('location-hidden');
  const locationHiddenQuick = document.getElementById('location-hidden-quick');

  // Load provinces from server if not rendered server-side
  async function loadProvinces() {
    if (provinceList && provinceList.children.length > 0) {
      initFromHidden();
      return;
    }
    try {
      const res = await fetch('/provinces');
      if (!res.ok) throw new Error('no provinces');
      const data = await res.json();
      const arr = Array.isArray(data) ? data : (data.provinces || []);
      provinceList.innerHTML = '';
      arr.forEach(p => {
        const li = document.createElement('li');
        li.innerHTML = `<label><input type="checkbox" data-name="${p}"> <span class="pname">${p}</span></label>`;
        provinceList.appendChild(li);
      });
      initFromHidden();
    } catch (e) {
      console.warn('Could not load provinces', e);
    }
  }

  function getSelected() {
    if (!provinceList) return [];
    return Array.from(provinceList.querySelectorAll('input[type="checkbox"]'))
      .filter(cb => cb.checked)
      .map(cb => cb.dataset.name);
  }

  function renderChips() {
    if (!locInput) return;
    locInput.innerHTML = '';
    const selected = getSelected();
    if (!selected.length) {
      const ph = document.createElement('span');
      ph.className = 'location-placeholder';
      ph.textContent = 'Chọn Tỉnh/Thành phố';
      locInput.appendChild(ph);
      return;
    }
    selected.forEach(name => {
      const chip = document.createElement('span');
      chip.className = 'location-chip';
      chip.innerHTML = `<span class="name">${name}</span><span class="remove" data-name="${name}">&times;</span>`;
      locInput.appendChild(chip);
    });
  }

  function syncHidden() {
    const csv = getSelected().join(',');
    if (locationHidden) locationHidden.value = csv;
    if (locationHiddenQuick) locationHiddenQuick.value = csv;
  }

  function initFromHidden() {
    const hv = (locationHidden && locationHidden.value) || (locationHiddenQuick && locationHiddenQuick.value) || '';
    if (!hv) { renderChips(); syncHidden(); return; }
    const arr = hv.split(',').map(s => s.trim()).filter(Boolean);
    const checks = provinceList.querySelectorAll('input[type="checkbox"]');
    checks.forEach(cb => { cb.checked = arr.includes(cb.dataset.name); });
    renderChips(); syncHidden();
  }

  function filterJobs() {
  // Lấy danh sách checkbox được chọn
  const checkedBoxes = document.querySelectorAll('.province-list input[type="checkbox"]:checked');
  const selectedProvinces = Array.from(checkedBoxes).map(cb => cb.value);

  // Lấy keyword từ search
  const keyword = document.getElementById('searchInput').value.toLowerCase();

  // Lọc job
  const filtered = jobs.filter(job => {
    const matchKeyword = job.title.toLowerCase().includes(keyword);
    const matchProvince = selectedProvinces.length === 0 || selectedProvinces.includes(job.province);
    return matchKeyword && matchProvince;
  });

  renderJobs(filtered);
}


  // Toggle dropdown
  if (locInput) {
    locInput.addEventListener('click', (e) => {
      locDropdown.classList.toggle('active');
    });
  }

  // Delegate changes
  if (provinceList) {
    provinceList.addEventListener('change', (e) => {
      renderChips();
      syncHidden();
    });

    // allow clicking label row to toggle checkbox (usually native)
    provinceList.addEventListener('click', (e) => {
      const li = e.target.closest('li');
      if (!li) return;
      // if clicked on label text, let checkbox toggle; we handle via change event
    });
  }

  // remove chip
  if (locInput) {
    locInput.addEventListener('click', (e) => {
      if (e.target && e.target.matches('.remove')) {
        const name = e.target.dataset.name;
        const cb = provinceList.querySelector(`input[data-name="${name}"]`);
        if (cb) { cb.checked = false; renderChips(); syncHidden(); }
      }
    });
  }

  // close on outside click
  document.addEventListener('click', (e) => {
    const sel = document.querySelector('.location-select');
    if (!sel) return;
    if (!sel.contains(e.target)) locDropdown.classList.remove('active');
  });

  // Salary inputs formatting and strip on submit
  function formatNumberString(s) {
    if (!s) return '';
    const digits = s.toString().replace(/\D/g, '');
    return digits ? Number(digits).toLocaleString('en-US') : '';
  }
  function stripNonDigits(s) { return s ? s.toString().replace(/\D/g, '') : ''; }

  const minInput = document.getElementById('min_salary');
  const maxInput = document.getElementById('max_salary');
  [minInput, maxInput].forEach(el => {
    if (!el) return;
    el.addEventListener('input', () => {
      const pos = el.selectionStart;
      el.value = formatNumberString(el.value);
      el.selectionStart = el.selectionEnd = el.value.length;
    });
  });

  // quick filters formatting
  const qmin = document.getElementById('flt_min');
  const qmax = document.getElementById('flt_max');
  [qmin, qmax].forEach(el => {
    if (!el) return;
    el.addEventListener('input', () => el.value = formatNumberString(el.value));
  });

  // sync hidden before submit
  const mainForm = document.getElementById('main-search');
  if (mainForm) mainForm.addEventListener('submit', () => {
    if (minInput) minInput.value = stripNonDigits(minInput.value);
    if (maxInput) maxInput.value = stripNonDigits(maxInput.value);
    if (locationHidden && locationHiddenQuick) locationHiddenQuick.value = locationHidden.value;
  });

  const quickForm = document.getElementById('quick-filters');
  if (quickForm) quickForm.addEventListener('submit', () => {
    if (qmin) qmin.value = stripNonDigits(qmin.value);
    if (qmax) qmax.value = stripNonDigits(qmax.value);
    if (locationHidden && locationHiddenQuick) locationHidden.value = locationHiddenQuick.value;
  });

  // reset filters
  const resetBtn = document.getElementById('reset-filters');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      const checks = provinceList.querySelectorAll('input[type="checkbox"]');
      checks.forEach(cb => cb.checked = false);
      if (qmin) qmin.value = '';
      if (qmax) qmax.value = '';
      if (document.getElementById('flt_job_type')) document.getElementById('flt_job_type').selectedIndex = 0;
      renderChips(); syncHidden();
    });
  }

  // init
  loadProvinces();
});
