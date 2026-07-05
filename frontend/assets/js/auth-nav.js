(function () {
  document.addEventListener("DOMContentLoaded", async () => {
    const nav = document.getElementById("auth-nav");
    if (!nav) return;

    if (!window.BTApi.isLoggedIn()) return; // leave the default Register/Login links as-is

    let me = null;
    try {
      me = await window.BTApi.get("/auth/me/");
    } catch (e) {
      // Access token invalid/expired and refresh failed - treat as logged out.
      window.BTApi.clearTokens();
      return;
    }

    const isStaffOrAdmin = me && (me.role === "STAFF" || me.role === "ADMIN");
    const firstName = (me && me.first_name) || "Account";

    nav.innerHTML = `
      ${isStaffOrAdmin ? `
      <li class="nav-item mr-3">
        <a class="nav-link" href="inbox.html"><i class="fas fa-inbox"></i> Inbox</a>
      </li>` : ""}
      <li class="nav-item mr-3">
        <a class="nav-link" href="dashboard.html"><i class="fas fa-tachometer-alt"></i> ${window.BTUi.escapeHtml(firstName)}</a>
      </li>
      <li class="nav-item mr-3">
        <a class="nav-link" href="#" id="logout-link"><i class="fas fa-sign-out-alt"></i> Logout</a>
      </li>`;

    document.getElementById("logout-link").addEventListener("click", async (e) => {
      e.preventDefault();
      const tokens = window.BTApi.getTokens();
      try {
        if (tokens && tokens.refresh) {
          await window.BTApi.post("/auth/logout/", { refresh: tokens.refresh });
        }
      } catch (err) {
        // Best-effort: even if the blacklist call fails, clear local tokens and proceed.
      }
      window.BTApi.clearTokens();
      window.location.href = "index.html";
    });
  });
})();
