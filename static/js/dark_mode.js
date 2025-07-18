const body = document.body;
const toggleBtn = document.getElementById("toggle-theme");
if (localStorage.getItem("theme") === "dark") {
    body.classList.add("dark-mode");
    toggleBtn.textContent = "☀️ الوضع الفاتح";
}

  toggleBtn.addEventListener("click", () => {
    body.classList.toggle("dark-mode");
    if (body.classList.contains("dark-mode")) {
      localStorage.setItem("theme", "dark");
      toggleBtn.textContent = "☀️ الوضع الفاتح";
    } else {
      localStorage.setItem("theme", "light");
      toggleBtn.textContent = "🌙 الوضع الليلي";
    }
  });