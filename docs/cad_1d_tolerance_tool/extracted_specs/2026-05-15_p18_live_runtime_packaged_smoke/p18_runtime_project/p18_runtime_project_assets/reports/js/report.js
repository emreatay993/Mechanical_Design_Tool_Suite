document.addEventListener("DOMContentLoaded", () => {
  const links = Array.from(document.querySelectorAll(".left-nav a"));
  const byId = new Map(links.map((link) => [link.getAttribute("href"), link]));
  const setActive = () => {
    const hash = window.location.hash || "#summary";
    links.forEach((link) => link.classList.remove("active"));
    const active = byId.get(hash);
    if (active) active.classList.add("active");
  };
  window.addEventListener("hashchange", setActive);
  setActive();
});
