(function () {
  const { escapeHtml, formatMoney, timeAgo, PLACEHOLDER_IMAGE } = window.BTUi;

  function buildQueryFromParams(params) {
    const qs = new URLSearchParams();
    for (const key of ["search", "city", "state", "min_bedrooms", "max_price", "listing_type", "page"]) {
      const value = params.get(key);
      if (value) qs.set(key, value);
    }
    return qs;
  }

  function renderCard(listing) {
    const location = `${escapeHtml(listing.city)}, ${escapeHtml(listing.state)}`;
    const priceSuffix = listing.listing_type === "RENT" ? "/mo" : "";
    const realtorName = listing.realtor ? `${listing.realtor.first_name} ${listing.realtor.last_name}`.trim() : "BT Realty";
    const image = listing.main_image || PLACEHOLDER_IMAGE;
    const detailUrl = `listing.html?id=${encodeURIComponent(listing.public_id)}`;

    return `
      <div class="col-md-6 col-lg-4 mb-4">
        <div class="card listing-preview">
          <img class="card-img-top" src="${escapeHtml(image)}" alt="${escapeHtml(listing.title)}">
          <div class="card-img-overlay">
            <h2><span class="badge badge-secondary text-white">${formatMoney(listing.price)}${priceSuffix}</span></h2>
          </div>
          <div class="card-body">
            <div class="listing-heading text-center">
              <h4 class="text-primary">${escapeHtml(listing.address_line)}</h4>
              <p><i class="fas fa-map-marker text-secondary"></i> ${location}</p>
            </div>
            <hr>
            <div class="row py-2 text-secondary">
              <div class="col-6"><i class="fas fa-th-large"></i> Sqft: ${escapeHtml(listing.square_feet)}</div>
              <div class="col-6"><i class="fas fa-car"></i> Garage: ${escapeHtml(listing.garage_spaces)}</div>
            </div>
            <div class="row py-2 text-secondary">
              <div class="col-6"><i class="fas fa-bed"></i> Bedrooms: ${escapeHtml(listing.bedrooms)}</div>
              <div class="col-6"><i class="fas fa-bath"></i> Bathrooms: ${escapeHtml(listing.bathrooms)}</div>
            </div>
            <hr>
            <div class="row py-2 text-secondary">
              <div class="col-12"><i class="fas fa-user"></i> ${escapeHtml(realtorName)}</div>
            </div>
            <div class="row text-secondary pb-2">
              <div class="col-6"><i class="fas fa-clock"></i> ${timeAgo(listing.created_at)}</div>
            </div>
            <hr>
            <a href="${detailUrl}" class="btn btn-primary btn-block">More Info</a>
          </div>
        </div>
      </div>`;
  }

  function renderPagination(container, data, params) {
    if (!container) return;
    if (!data.next && !data.previous) {
      container.innerHTML = "";
      return;
    }

    const currentPage = data.current_page || 1;
    const totalPages = data.total_pages || 1;

    function pageLink(page, label, disabled, active) {
      return `<li class="page-item ${disabled ? "disabled" : ""} ${active ? "active" : ""}">
        <a class="page-link" href="#" data-page="${page}">${label}</a></li>`;
    }

    let html = pageLink(currentPage - 1, "&laquo;", currentPage <= 1, false);
    for (let p = 1; p <= totalPages; p++) {
      html += pageLink(p, String(p), false, p === currentPage);
    }
    html += pageLink(currentPage + 1, "&raquo;", currentPage >= totalPages, false);

    container.innerHTML = `<ul class="pagination">${html}</ul>`;
    container.querySelectorAll("a[data-page]").forEach((a) => {
      a.addEventListener("click", (e) => {
        e.preventDefault();
        const page = e.currentTarget.getAttribute("data-page");
        const newParams = buildQueryFromParams(params);
        newParams.set("page", page);
        window.location.search = newParams.toString();
      });
    });
  }

  async function loadListings() {
    const container = document.getElementById("listings-container");
    if (!container) return;

    const params = new URLSearchParams(window.location.search);
    container.innerHTML = `<div class="col-12 text-center py-5"><i class="fas fa-spinner fa-spin fa-2x text-secondary"></i></div>`;

    try {
      const qs = buildQueryFromParams(params);
      const data = await window.BTApi.get(`/listings/?${qs.toString()}`, { auth: false });
      const results = data.results || [];

      if (results.length === 0) {
        container.innerHTML = `<div class="col-12 text-center py-5 text-secondary">No listings matched your search. Try broadening your criteria.</div>`;
      } else {
        container.innerHTML = results.map(renderCard).join("");
      }
      renderPagination(document.getElementById("pagination-container"), data, params);
    } catch (err) {
      container.innerHTML = `<div class="col-12 text-center py-5 text-danger">Could not load listings right now. Please try again shortly.</div>`;
    }
  }

  function prefillSearchForm() {
    const form = document.getElementById("search-form");
    if (!form) return;
    const params = new URLSearchParams(window.location.search);

    if (params.get("search")) form.keywords.value = params.get("search");
    if (params.get("city")) form.city.value = params.get("city");
    if (params.get("state")) form.state.value = params.get("state");
    if (params.get("min_bedrooms")) form.bedrooms.value = params.get("min_bedrooms");
    if (params.get("max_price")) form.price.value = params.get("max_price");

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const newParams = new URLSearchParams();
      const keywords = form.keywords.value.trim();
      const city = form.city.value.trim();
      const state = form.state.value;
      const bedrooms = form.bedrooms.value;
      const price = form.price.value;

      if (keywords) newParams.set("search", keywords);
      if (city) newParams.set("city", city);
      if (/^[A-Z]{2}$/.test(state)) newParams.set("state", state);
      if (/^\d+$/.test(bedrooms)) newParams.set("min_bedrooms", bedrooms);
      if (/^\d+$/.test(price)) newParams.set("max_price", price);

      window.location.search = newParams.toString();
    });
  }

  window.BTListings = { renderCard };

  document.addEventListener("DOMContentLoaded", () => {
    prefillSearchForm();
    loadListings();
  });
})();
