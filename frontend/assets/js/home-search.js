(function () {
  document.addEventListener("DOMContentLoaded", () => {
    const form = document.querySelector("#showcase form");
    if (!form) return;

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const params = new URLSearchParams();

      const keywords = form.keywords.value.trim();
      const city = form.city.value.trim();
      const state = form.state.value;
      const bedrooms = form.bedrooms.value;
      const price = form.price.value;

      if (keywords) params.set("search", keywords);
      if (city) params.set("city", city);
      if (/^[A-Z]{2}$/.test(state)) params.set("state", state);
      if (/^\d+$/.test(bedrooms)) params.set("min_bedrooms", bedrooms);
      if (/^\d+$/.test(price)) params.set("max_price", price);

      window.location.href = `listings.html?${params.toString()}`;
    });
  });
})();
