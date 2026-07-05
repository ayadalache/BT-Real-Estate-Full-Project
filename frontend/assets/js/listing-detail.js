(function () {
  const { escapeHtml, formatMoney, formatDate, PLACEHOLDER_IMAGE } = window.BTUi;

  function getListingIdFromUrl() {
    return new URLSearchParams(window.location.search).get("id");
  }

  function renderThumbs(images) {
    const container = document.getElementById("thumbs-container");
    if (!container) return;
    if (!images || images.length <= 1) {
      container.innerHTML = "";
      return;
    }
    // First image is already shown as the main image; the rest become thumbnails.
    container.innerHTML = images
      .slice(1)
      .map(
        (img) => `
        <div class="col-md-2">
          <a href="${escapeHtml(img.image)}" data-lightbox="home-images">
            <img src="${escapeHtml(img.image)}" alt="" class="img-fluid">
          </a>
        </div>`
      )
      .join("");
  }

  function populateListing(listing) {
    document.title = `${listing.title} — BT Real Estate`;

    const titleEl = document.getElementById("listing-title");
    if (titleEl) titleEl.textContent = listing.title;

    const locationEl = document.getElementById("listing-location");
    if (locationEl) {
      locationEl.innerHTML = `<i class="fas fa-map-marker"></i> ${escapeHtml(listing.city)} ${escapeHtml(listing.state)}, ${escapeHtml(listing.zip_code)}`;
    }

    const breadcrumbEl = document.getElementById("breadcrumb-title");
    if (breadcrumbEl) breadcrumbEl.textContent = listing.address_line;

    const images = listing.images || [];
    const mainImage = images.find((i) => i.is_main) || images[0];
    const mainImageEl = document.getElementById("main-image");
    if (mainImageEl) mainImageEl.src = mainImage ? mainImage.image : PLACEHOLDER_IMAGE;
    renderThumbs(images);

    const priceLabelEl = document.getElementById("field-price-label");
    if (priceLabelEl) priceLabelEl.textContent = listing.listing_type === "RENT" ? "Monthly Rent:" : "Asking Price:";

    const set = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };
    set("field-price", formatMoney(listing.price) + (listing.listing_type === "RENT" ? "/mo" : ""));
    set("field-bedrooms", listing.bedrooms);
    set("field-bathrooms", listing.bathrooms);
    set("field-garage", listing.garage_spaces);
    set("field-sqft", listing.square_feet);
    set("field-lot", listing.lot_size_acres ? `${listing.lot_size_acres} Acres` : "N/A");
    set("field-listing-date", formatDate(listing.listing_date));

    const realtorName = listing.realtor ? `${listing.realtor.first_name} ${listing.realtor.last_name}`.trim() : "BT Realty";
    set("field-realtor", realtorName);
    set("realtor-name", realtorName);

    const descEl = document.getElementById("listing-description");
    if (descEl) descEl.textContent = listing.description || "No description provided.";

    const photoEl = document.getElementById("realtor-photo");
    if (photoEl) photoEl.src = (listing.realtor && listing.realtor.profile_photo) || PLACEHOLDER_IMAGE;

    const propertyField = document.getElementById("inquiry-property-field");
    if (propertyField) propertyField.value = `${listing.address_line}, ${listing.city} ${listing.state}`;
  }

  async function loadListing() {
    const publicId = getListingIdFromUrl();
    const container = document.getElementById("listing");
    if (!publicId) {
      if (container) container.innerHTML = `<div class="container py-5 text-center text-danger">No listing specified.</div>`;
      return null;
    }
    try {
      const listing = await window.BTApi.get(`/listings/${encodeURIComponent(publicId)}/`, { auth: false });
      populateListing(listing);
      return listing;
    } catch (err) {
      if (container) {
        container.innerHTML = `<div class="container py-5 text-center text-danger">This listing could not be found or is no longer available.</div>`;
      }
      return null;
    }
  }

  function wireInquiryForm(listing) {
    const form = document.querySelector("#inquiryModal form");
    if (!form || !listing) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      window.BTUi.clearAlert("inquiry-alert");

      const payload = {
        listing: listing.public_id,
        name: form.name.value.trim(),
        email: form.email.value.trim(),
        phone: form.phone.value.trim(),
        message: form.message.value.trim(),
      };

      const submitBtn = form.querySelector('input[type="submit"]');
      submitBtn.disabled = true;

      try {
        await window.BTApi.post("/inquiries/", payload, { auth: window.BTApi.isLoggedIn() });
        window.BTUi.showAlert("inquiry-alert", "Your inquiry has been sent. The realtor will be in touch soon!", "success");
        form.reset();
        setTimeout(() => {
          if (window.jQuery) window.jQuery("#inquiryModal").modal("hide");
        }, 1500);
      } catch (err) {
        window.BTUi.showAlert("inquiry-alert", window.BTUi.flattenErrors(err.errors) || err.message);
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  document.addEventListener("DOMContentLoaded", async () => {
    const listing = await loadListing();
    wireInquiryForm(listing);
  });
})();
