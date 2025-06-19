document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("loginForm");
  const errorMsg = document.getElementById("errorMsg");

  form.addEventListener("submit", async (e) => {
    e.preventDefault(); // Stop normal form behavior

    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    if (username === "admin" && password === "admin") {
      try {
        const res = await fetch("/admin_login", {
          method: "POST"
        });

        if (res.ok) {
          window.location.href = "/xhSHIH720nshADMIN";
        } else {
          errorMsg.style.display = "block";
        }
      } catch (err) {
        errorMsg.textContent = "Network error";
        errorMsg.style.display = "block";
      }
    } else {
      errorMsg.textContent = "Invalid username or password";
      errorMsg.style.display = "block";
    }
  });
});
