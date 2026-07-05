(function () {
  const { escapeHtml } = window.BTUi;

  async function loadDashboard() {
    if (!window.BTApi.isLoggedIn()) {
      window.location.href = "login.html";
      return;
    }

    const welcomeEl = document.getElementById("dashboard-welcome");
    const tbody = document.getElementById("dashboard-tbody");

    try {
      const me = await window.BTApi.get("/auth/me/");
      if (welcomeEl) welcomeEl.textContent = `Welcome ${me.first_name || me.username}`;
    } catch (err) {
      window.BTApi.clearTokens();
      window.location.href = "login.html";
      return;
    }

    try {
      const data = await window.BTApi.get("/inquiries/dashboard/");
      const results = data.results || [];

      if (!tbody) return;
      if (results.length === 0) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-secondary py-4">You haven't inquired about any listings yet. <a href="listings.html">Browse listings</a> to get started.</td></tr>`;
        return;
      }

      tbody.innerHTML = results
        .map(
          (inquiry, index) => `
        <tr>
          <td>${index + 1}</td>
          <td>${escapeHtml(inquiry.listing.address_line)}, ${escapeHtml(inquiry.listing.city)} ${escapeHtml(inquiry.listing.state)}</td>
          <td><a class="btn btn-light" href="listing.html?id=${encodeURIComponent(inquiry.listing.public_id)}">View Listing</a></td>
        </tr>`
        )
        .join("");
    } catch (err) {
      if (tbody) {
        tbody.innerHTML = `<tr><td colspan="3" class="text-center text-danger py-4">Could not load your inquiries right now.</td></tr>`;
      }
    }
  }

  document.addEventListener("DOMContentLoaded", loadDashboard);
})();
