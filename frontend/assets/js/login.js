(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#login form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      window.BTUi.clearAlert("form-alert");

      const payload = {
        username: form.username.value.trim(),
        password: form.password.value,
        remember_me: !!(form.remember_me && form.remember_me.checked),
      };

      const submitBtn = form.querySelector('input[type="submit"]');
      submitBtn.disabled = true;

      try {
        const data = await window.BTApi.post("/auth/login/", payload, { auth: false });
        window.BTApi.setTokens({ access: data.access, refresh: data.refresh });
        window.location.href = "dashboard.html";
      } catch (err) {
        window.BTUi.showAlert("form-alert", err.message || "Login failed. Please check your credentials.");
      } finally {
        submitBtn.disabled = false;
      }
    });
  });
})();
