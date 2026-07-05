(function () {
  document.addEventListener("DOMContentLoaded", async () => {
    const container = document.getElementById("latest-listings-container");
    if (!container) return;

    try {
      const data = await window.BTApi.get("/listings/?ordering=-listing_date&page_size=3", { auth: false });
      const results = data.results || [];
      container.innerHTML = results.length
        ? results.map(window.BTListings.renderCard).join("")
        : `<div class="col-12 text-center text-secondary">No listings available yet.</div>`;
    } catch (err) {
      container.innerHTML = `<div class="col-12 text-center text-danger">Could not load listings right now.</div>`;
    }
  });
})();
