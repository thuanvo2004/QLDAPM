document.addEventListener('DOMContentLoaded', function () {
  const locInput = document.getElementById('location-input');
  const locDropdown = document.getElementById('location-dropdown');
  const provinceList = document.getElementById('province-list');
  const locationHidden = document.getElementById('location-hidden');
  const locationHiddenQuick = document.getElementById('location-hidden-quick');
  const jobTypeSelect = document.getElementById('job_type_select');

  // Khai báo các checkbox/radio trong bộ lọc
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
      Toastify({
        text: 'Không thể tải danh sách tỉnh/thành phố',
        duration: 3000,
        gravity: 'top',
        position: 'right',
        backgroundColor: '#dc3545',
        className: 'toastify-custom-error',
      }).showToast();
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

  // Sync filter inputs with hidden inputs and auto-submit
  const mainForm = document.getElementById('main-search');

  // Handle job_type (single-select)
  jobTypeFilters.forEach(checkbox => {
    checkbox.addEventListener('change', function () {
      if (mainForm) {
        const selectedValue = this.value;
        const jobTypeHidden = document.getElementById('job-type-hidden');
        if (jobTypeHidden) {
          jobTypeHidden.value = selectedValue || "";
        }

        // Cập nhật dropdown
        if (jobTypeSelect) {
          jobTypeSelect.value = selectedValue || "";
        }

        mainForm.submit();
      }
    });
  });

  // Handle work_type (multi-check)
  workTypeFilters.forEach(checkbox => {
    checkbox.addEventListener('change', function () {
      if (mainForm) {
        const workTypeChecks = document.querySelectorAll('#work-type-filter input[name="work_type"]:checked');
        const workTypeHidden = document.getElementById('work-type-hidden');
        if (workTypeHidden) {
          const selectedWorkTypes = Array.from(workTypeChecks).map(cb => cb.value);
          workTypeHidden.value = selectedWorkTypes.join(",");
        }

        mainForm.submit();
      }
    });
  });

  // Sync dropdown with job_type when dropdown changes
  if (jobTypeSelect) {
    jobTypeSelect.addEventListener('change', function () {
      const selectedValue = this.value;
      if (mainForm) {
        const jobTypeHidden = document.getElementById('job-type-hidden');
        if (jobTypeHidden) {
          jobTypeHidden.value = selectedValue || "";
        }

        // Cập nhật radio button
        jobTypeFilters.forEach(cb => {
          cb.checked = cb.value === selectedValue;
        });

        mainForm.submit();
      }
    });
  }

  // Sync filter inputs with hidden inputs before manual submit
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
        document.getElementById('work-type-hidden').value = selectedWorkTypes.join(",");
      }
    });
  }

  // Kiểm tra trạng thái ban đầu của các nút save
  document.querySelectorAll('.save-btn').forEach(button => {
    const jobId = button.getAttribute('data-job-id');
    if (!jobId) {
      console.warn('Missing data-job-id on save-btn', button);
      return;
    }
    // Chỉ kiểm tra trạng thái nếu đã đăng nhập
    if (!button.classList.contains('unauthenticated')) {
      fetch(`/candidate/check_saved/${jobId}`, {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
      })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          if (data.is_saved) {
            button.classList.add('saved');
            const buttonIcon = button.querySelector('i');
            if (buttonIcon) buttonIcon.className = 'fa-solid fa-bookmark solid-icon';
          }
        })
        .catch(error => {
          console.error('Lỗi kiểm tra trạng thái:', error);
          Toastify({
            text: 'Lỗi khi kiểm tra trạng thái lưu việc',
            duration: 3000,
            gravity: 'top',
            position: 'right',
            backgroundColor: '#dc3545',
            className: 'toastify-custom-error',
          }).showToast();
        });
    }
  });

  // Xử lý save/unsave job với AJAX
  document.querySelectorAll('.save-btn').forEach(button => {
    button.addEventListener('click', function (e) {
      e.preventDefault();
      if (this.disabled) return;

      if (this.classList.contains('unauthenticated')) {
        // Lấy URL đăng nhập từ data attribute
        const loginUrl = this.getAttribute('data-login-url');
        window.location.href = loginUrl;
        return;
      }

      const jobId = this.getAttribute('data-job-id');
      const isSaved = this.classList.contains('saved');
      const url = isSaved ? `/candidate/unsave_job/${jobId}` : `/candidate/save_job/${jobId}`;
      const buttonIcon = this.querySelector('i');

      fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Requested-With': 'XMLHttpRequest'
        },
      })
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
        })
        .then(data => {
          console.log('Response:', data);
          if (data.success) {
            if (data.action === 'saved') {
              this.classList.add('saved');
              if (buttonIcon) buttonIcon.className = 'fa-solid fa-bookmark solid-icon';
              Toastify({
                text: data.message,
                duration: 3000,
                gravity: 'bottom',
                position: 'right',
                className: 'toastify-custom-success',
              }).showToast();
            } else if (data.action === 'unsaved') {
              this.classList.remove('saved');
              if (buttonIcon) buttonIcon.className = 'fa-regular fa-bookmark regular-icon';
              Toastify({
                text: data.message,
                duration: 3000,
                gravity: 'bottom',
                position: 'right',
                className: 'toastify-custom-success',
              }).showToast();
            }
          } else {
            Toastify({
              text: data.message || 'Lỗi khi xử lý job',
              duration: 3000,
              gravity: 'top',
              position: 'right',
              className: 'toastify-custom-error',
            }).showToast();
          }
        })
        .catch(error => {
          console.error('Lỗi:', error);
          Toastify({
            text: 'Lỗi kết nối',
            duration: 3000,
            gravity: 'top',
            position: 'right',
            className: 'toastify-custom-error',
          }).showToast();
        });
    });
  });

  // init load
  loadProvinces();
});