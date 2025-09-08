document.addEventListener('DOMContentLoaded', function () {
  const locInput = document.getElementById('location-input');
  const locDropdown = document.getElementById('location-dropdown');
  const provinceList = document.getElementById('province-list');
  const locationHidden = document.getElementById('location-hidden');
  const locationHiddenQuick = document.getElementById('location-hidden-quick');
  const jobTypeSelect = document.getElementById('job_type_select');

  // Khai báo các checkbox trong bộ lọc
  const jobTypeFilters = document.querySelectorAll('#job-type-filter input[name="job_type"]');
  const workTypeFilters = document.querySelectorAll('#work-type-filter input[name="work_type"]');

  // Hàm helper
  function formatNumberStringForDisplay(s) {
    if (!s) return '';
    const digits = s.toString().replace(/\D/g, '');
    return digits ? Number(digits).toLocaleString('en-US') : '';
  }

  function stripNonDigits(s) {
    return s ? s.toString().replace(/\D/g, '') : '';
  }

  async function loadProvinces() {
    if (!provinceList) return;
    if (provinceList.children.length > 0) {
      Array.from(provinceList.querySelectorAll('li')).forEach(li => {
        const cb = li.querySelector('input[type="checkbox"]');
        const nameSpan = li.querySelector('.pname');
        if (cb && !cb.value && nameSpan) cb.value = nameSpan.textContent.trim();
        if (!li.querySelector('.box')) {
          const input = cb;
          const box = document.createElement('span');
          box.className = 'box';
          if (input) {
            input.insertAdjacentElement('afterend', box);
          } else {
            li.insertBefore(box, nameSpan);
          }
        }
      });
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
        li.innerHTML = `<label>
          <input type="checkbox" data-name="${p}" value="${p}">
          <span class="box" aria-hidden="true"></span>
          <span class="pname">${p}</span>
        </label>`;
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
      const nameEl = document.createElement('span');
      nameEl.className = 'name';
      nameEl.textContent = name;
      const removeEl = document.createElement('span');
      removeEl.className = 'remove';
      removeEl.dataset.name = name;
      removeEl.innerHTML = '&times;';
      chip.appendChild(nameEl);
      chip.appendChild(removeEl);
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
    if (!hv) {
      renderChips();
      syncHidden();
      return;
    }
    const arr = hv.split(',').map(s => s.trim()).filter(Boolean);
    const checks = provinceList.querySelectorAll('input[type="checkbox"]');
    checks.forEach(cb => {
      cb.checked = arr.includes(cb.dataset.name);
    });
    renderChips();
    syncHidden();
  }

  // Toggle dropdown when clicking the visible container
  if (locInput && locDropdown) {
    locInput.addEventListener('click', (e) => {
      locDropdown.classList.toggle('active');
      const expanded = locDropdown.classList.contains('active');
      locInput.setAttribute('aria-expanded', expanded ? 'true' : 'false');
    });
    locInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        locDropdown.classList.toggle('active');
      }
    });
  }

  // When a checkbox changes, re-render chips + sync hidden
  if (provinceList) {
    provinceList.addEventListener('change', (e) => {
      renderChips();
      syncHidden();
    });
  }

  // Remove chip via delegation
  if (locInput) {
    locInput.addEventListener('click', (e) => {
      if (e.target && e.target.classList.contains('remove')) {
        const name = e.target.dataset.name;
        const cb = provinceList.querySelector(`input[data-name="${name}"]`);
        if (cb) {
          cb.checked = false;
          renderChips();
          syncHidden();
        }
      }
    });
  }

  // Close on outside click
  document.addEventListener('click', (e) => {
    const sel = document.querySelector('.location-select');
    if (!sel) return;
    if (!sel.contains(e.target)) {
      locDropdown.classList.remove('active');
      if (locInput) locInput.setAttribute('aria-expanded', 'false');
    }
  });

  // Number format helpers
  const minInput = document.querySelector('input[name="salary_min"]');
  const maxInput = document.querySelector('input[name="salary_max"]');
  [minInput, maxInput].forEach(el => {
    if (!el) return;
    el.addEventListener('input', () => {
      el.value = formatNumberStringForDisplay(el.value);
      el.selectionStart = el.selectionEnd = el.value.length;
    });
  });

  // Sync filter checkboxes with hidden inputs and auto-submit
  const mainForm = document.getElementById('main-search');
  const jobTypeMapping = {
    "Full-time": "Full-time",
    "Part-time": "Part-time",
    "Contract": "Contract",
    "Intern": "Intern",
    "": "All" // Mapping cho "All"
  };

  [jobTypeFilters].forEach((filterGroup) => {
    filterGroup.forEach(checkbox => {
      checkbox.addEventListener('change', function () {
        if (mainForm) {
          // Chỉ lấy giá trị của checkbox được chọn (single-select)
          const selectedValue = this.value;
          const jobTypeHidden = document.getElementById('job-type-hidden');
          if (jobTypeHidden) {
            jobTypeHidden.value = selectedValue || "";
          }

          // Cập nhật dropdown
          if (jobTypeSelect) {
            jobTypeSelect.value = selectedValue || "";
          }

          // Tự động submit form
          mainForm.submit();
        }
      });
    });
  });

  // Sync dropdown with checkboxes when dropdown changes (single-select)
  if (jobTypeSelect) {
    jobTypeSelect.addEventListener('change', function () {
      const selectedValue = this.value;
      if (mainForm) {
        const jobTypeHidden = document.getElementById('job-type-hidden');
        if (jobTypeHidden) {
          jobTypeHidden.value = selectedValue || "";
        }

        // Cập nhật checkbox dựa trên dropdown
        jobTypeFilters.forEach(cb => {
          cb.checked = (jobTypeMapping[cb.value] === selectedValue) || (selectedValue === "" && cb.value === "");
        });

        mainForm.submit();
      }
    });
  }

  // Sync filter checkboxes with hidden inputs before manual submit
  if (mainForm) {
    mainForm.addEventListener('submit', () => {
      if (minInput) minInput.value = stripNonDigits(minInput.value);
      if (maxInput) maxInput.value = stripNonDigits(maxInput.value);
      if (locationHidden && locationHiddenQuick) locationHiddenQuick.value = locationHidden.value;
      const jobTypeChecks = document.querySelectorAll('#job-type-filter input[name="job_type"]:checked');
      if (document.getElementById('job-type-hidden')) {
        const selectedJobTypes = Array.from(jobTypeChecks).map(cb => cb.value)[0] || "";
        document.getElementById('job-type-hidden').value = selectedJobTypes;
      }
      const workTypeChecks = document.querySelectorAll('#work-type-filter input[name="work_type"]:checked');
      if (document.getElementById('work-type-hidden')) {
        const selectedWorkTypes = Array.from(workTypeChecks).map(cb => cb.value);
        if (selectedWorkTypes.includes("All") && selectedWorkTypes.length > 1) {
          selectedWorkTypes.splice(selectedWorkTypes.indexOf("All"), 1);
        }
        document.getElementById('work-type-hidden').value = selectedWorkTypes.join(",");
      }
    });
  }

  // init load
  loadProvinces();
});