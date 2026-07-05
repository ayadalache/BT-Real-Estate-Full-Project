(function () {
  const { escapeHtml, formatDate } = window.BTUi;
  const STATUSES = ["NEW", "CONTACTED", "CLOSED"];

  function statusSelect(inquiry) {
    const options = STATUSES.map(
      (s) => `<option value="${s}" ${s === inquiry.status ? "selected" : ""}>${s}</option>`
    ).join("");
    return `<select class="form-control form-control-sm status-select" data-id="${inquiry.id}">${options}</select>`;
  }

  function renderRow(inquiry) {
    return `
      <tr>
        <td>${escapeHtml(inquiry.listing.address_line)}, ${escapeHtml(inquiry.listing.city)} ${escapeHtml(inquiry.listing.state)}</td>
        <td>${escapeHtml(inquiry.name)}<br><small class="text-secondary">${escapeHtml(inquiry.email)}${inquiry.phone ? " · " + escapeHtml(inquiry.phone) : ""}</small></td>
        <td>${escapeHtml(inquiry.message)}</td>
        <td>${statusSelect(inquiry)}</td>
        <td>${formatDate(inquiry.created_at)}</td>
      </tr>`;
  }

  async function updateStatus(id, status) {
    try {
      await window.BTApi.patch(`/inquiries/${id}/`, { status });
      window.BTUi.showAlert("form-alert", "Status updated.", "success");
    } catch (err) {
      window.BTUi.showAlert("form-alert", err.message || "Could not update status.");
    }
  }

  async function loadInbox() {
    if (!window.BTApi.isLoggedIn()) {
      window.location.href = "login.html";
      return;
    }

    const tbody = document.getElementById("inbox-tbody");

    try {
      const me = await window.BTApi.get("/auth/me/");
      if (me.role !== "STAFF" && me.role !== "ADMIN") {
        window.location.href = "dashboard.html";
        return;
      }
    } catch (err) {
      window.BTApi.clearTokens();
      window.location.href = "login.html";
      return;
    }

    try {
      const data = await window.BTApi.get("/inquiries/inbox/");
      const results = data.results || [];

      if (results.length === 0) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-center text-secondary py-4">No inquiries yet.</td></tr>`;
        return;
      }

      tbody.innerHTML = results.map(renderRow).join("");
      tbody.querySelectorAll(".status-select").forEach((select) => {
        select.addEventListener("change", (e) => {
          updateStatus(e.target.getAttribute("data-id"), e.target.value);
        });
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Could not load your inbox right now.</td></tr>`;
    }
  }

  document.addEventListener("DOMContentLoaded", loadInbox);
})();
