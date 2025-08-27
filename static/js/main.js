function formatNumberString(s) {
  if (!s) return "";
  const digits = s.toString().replace(/\D/g, "");
  if (!digits) return "";
  return Number(digits).toLocaleString("en-US");
}

function stripNonDigits(s) {
  if (!s) return "";
  return s.toString().replace(/\D/g, "");
}

document.addEventListener("DOMContentLoaded", function() {
  // Format input lương
  const minInputs = document.querySelectorAll('#min_salary, #flt_min');
  const maxInputs = document.querySelectorAll('#max_salary, #flt_max');

  function attachFormat(el) {
    if (!el) return;
    el.addEventListener('input', function(){
      const formatted = formatNumberString(el.value);
      el.value = formatted;
      el.selectionStart = el.selectionEnd = el.value.length;
    });
  }
  minInputs.forEach(attachFormat);
  maxInputs.forEach(attachFormat);

  const mainForm = document.getElementById('main-search');
  if (mainForm) {
    mainForm.addEventListener('submit', function(){
      const min = mainForm.querySelector('input[name="min_salary"]');
      const max = mainForm.querySelector('input[name="max_salary"]');
      if (min) min.value = stripNonDigits(min.value);
      if (max) max.value = stripNonDigits(max.value);
    });
  }

  // Location dropdown
  const input = document.getElementById("location-input");
  const dropdown = document.getElementById("location-dropdown");
  const provinceList = document.getElementById("province-list");

  input.addEventListener("click", () => {
    dropdown.classList.toggle("active");
  });

  document.addEventListener("click", (e) => {
    if (!document.querySelector(".location-select").contains(e.target)) {
      dropdown.classList.remove("active");
    }
  });

  // Load provinces từ Flask API
  fetch("/provinces")
    .then(res => res.json())
    .then(data => {
      data.provinces.forEach(province => {
        const li = document.createElement("li");
        li.textContent = province;
        li.dataset.province = province;

        li.addEventListener("click", () => {
          document.getElementById("location-input").value = province;
          dropdown.classList.remove("active");
        });

        provinceList.appendChild(li);
      });
    })
    .catch(err => console.error("Lỗi load provinces:", err));
});
