(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#register form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      window.BTUi.clearAlert("form-alert");

      const payload = {
        first_name: form.first_name.value.trim(),
        last_name: form.last_name.value.trim(),
        username: form.username.value.trim(),
        email: form.email.value.trim(),
        password: form.password.value,
        password2: form.password2.value,
      };

      const submitBtn = form.querySelector('input[type="submit"]');
      submitBtn.disabled = true;

      try {
        await window.BTApi.post("/auth/register/", payload, { auth: false });
        window.BTUi.showAlert(
          "form-alert",
          "Registration successful! Please check your email to verify your account, then log in.",
          "success"
        );
        form.reset();
        setTimeout(() => (window.location.href = "login.html"), 2500);
      } catch (err) {
        window.BTUi.showAlert("form-alert", window.BTUi.flattenErrors(err.errors) || err.message);
      } finally {
        submitBtn.disabled = false;
      }
    });
  });
})();
