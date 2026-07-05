(function () {
  function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value == null ? "" : String(value);
    return div.innerHTML;
  }

  function formatMoney(value) {
    const num = Number(value);
    if (Number.isNaN(num)) return String(value);
    return num.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
  }

  function formatDate(isoDateString) {
    if (!isoDateString) return "N/A";
    const d = new Date(isoDateString);
    if (Number.isNaN(d.getTime())) return isoDateString;
    return d.toLocaleDateString("en-US");
  }

  function timeAgo(isoDateString) {
    if (!isoDateString) return "";
    const then = new Date(isoDateString).getTime();
    if (Number.isNaN(then)) return "";
    const days = Math.max(0, Math.floor((Date.now() - then) / 86400000));
    if (days === 0) return "Today";
    if (days === 1) return "1 day ago";
    return `${days} days ago`;
  }

  /** A 1x1 gray placeholder so <img> never shows a broken-image icon when a listing/user has no photo yet. */
  const PLACEHOLDER_IMAGE =
    "data:image/svg+xml;charset=UTF-8," +
    encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect width="100%" height="100%" fill="#dee2e6"/>' +
        '<text x="50%" y="50%" font-family="sans-serif" font-size="20" fill="#868e96" text-anchor="middle" dy=".3em">No Image</text></svg>'
    );

  /** Renders a dismissible Bootstrap alert into the given container element (by id or element ref). */
  function showAlert(container, message, type = "danger") {
    const el = typeof container === "string" ? document.getElementById(container) : container;
    if (!el) return;
    el.innerHTML = `
      <div class="alert alert-${escapeHtml(type)} alert-dismissible fade show" role="alert">
        ${escapeHtml(message)}
        <button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>
      </div>`;
  }

  function clearAlert(container) {
    const el = typeof container === "string" ? document.getElementById(container) : container;
    if (el) el.innerHTML = "";
  }

  /** Flattens DRF-style field error objects/arrays into one readable string. */
  function flattenErrors(errors) {
    if (!errors) return null;
    if (typeof errors === "string") return errors;
    if (Array.isArray(errors)) return errors.join(" ");
    return Object.entries(errors)
      .map(([field, msgs]) => `${field}: ${Array.isArray(msgs) ? msgs.join(" ") : msgs}`)
      .join(" | ");
  }

  window.BTUi = { escapeHtml, formatMoney, formatDate, timeAgo, showAlert, clearAlert, flattenErrors, PLACEHOLDER_IMAGE };
})();
