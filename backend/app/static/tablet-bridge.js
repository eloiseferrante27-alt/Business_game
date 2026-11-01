// Keep the original tablet.js and its public identifiers available to old clients.
// The 3D stage now opens the same live tablet as the standalone /tablet route.
export const DEPARTMENT_BY_ZONE = {
  quai_dechargement: "quai-dechargement", bureau_reception: "reception",
  stock_mp: "stock", stock_sf: "stock", stock_pf: "stock", stock: "stock",
  chaine_production: "production", bureau_etude: "production", controle_qualite: "qualite",
  emballage: "emballage", maintenance_pdr: "maintenance", logistique_transport: "logistique",
};

export function createTablet({ refreshState, onAction = () => {} }) {
  const overlay = document.createElement("section");
  overlay.className = "live-tablet-overlay";
  overlay.hidden = true;
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-label", "Tablette de l’usine");
  overlay.innerHTML = '<div class="live-tablet-frame"><header><span><i></i> Tablette</span><button type="button" aria-label="Fermer la tablette et revenir à l’usine">Ranger la tablette <kbd>T</kbd></button></header><iframe title="Tablette G-MIX : départements et décisions" loading="lazy"></iframe></div>';
  document.body.append(overlay);
  const frame = overlay.querySelector("iframe");
  const closeButton = overlay.querySelector("button");
  let previousFocus;
  let opened = false;

  async function close() {
    // La tablette redescend : l'attribut hidden est posé tout de suite, le CSS garde l'animation de sortie.
    if (opened) overlay.setAttribute("data-etat", "fermeture");
    overlay.hidden = true;
    opened = false;
    document.body.classList.remove("live-tablet-open");
    document.querySelector("#game").inert = false;
    previousFocus?.focus?.();
    try { await refreshState(); } catch { /* Parent's existing refresh handles API errors. */ }
  }

  function open(tab = "accueil", options = {}) {
    const page = { fournisseurs: "fournisseurs", comparateur: "fournisseurs", achats: "fournisseurs", clients: "clients", of: "production", stocks: "stock" }[tab];
    const department = options.department || DEPARTMENT_BY_ZONE[tab] || page;
    const url = new URL("/tablet", window.location.origin);
    if (department) url.hash = `departement/${department}/kpis`;
    else url.hash = tab === "regles" ? "regles" : "accueil";
    for (const [key, value] of Object.entries(options)) {
      if (key !== "department" && value !== undefined) url.searchParams.set(key, value);
    }
    // Reload on every opening: a week may have advanced in the 3D view.
    frame.src = url.href;
    previousFocus = document.activeElement;
    overlay.setAttribute("data-etat", "ouverte");
    overlay.hidden = false;
    opened = true;
    document.body.classList.add("live-tablet-open");
    document.querySelector("#game").inert = true;
    closeButton.focus();
    onAction("inspect");
  }

  closeButton.addEventListener("click", close);
  overlay.addEventListener("animationend", () => { if (overlay.hidden) overlay.setAttribute("data-etat", "fermee"); });
  frame.addEventListener("load", () => {
    const document = frame.contentDocument;
    if (!document) return;
    document.addEventListener("click", (event) => {
      const link = event.target.closest('a[href="/"]');
      if (link) { event.preventDefault(); close(); }
    });
    document.addEventListener("keydown", (event) => {
      const hasOpenDialog = [...document.querySelectorAll('[role="dialog"]')]
        .some((dialog) => dialog.getClientRects().length > 0);
      if (event.key !== "Escape" || hasOpenDialog) return;
      event.preventDefault();
      close();
    }, true);
  });
  overlay.addEventListener("pointerdown", (event) => { if (event.target === overlay) close(); });
  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || event.source !== frame.contentWindow) return;
    if (event.data?.type === "GMIX_CLOSE_TABLET") close();
    if (event.data?.type === "GMIX_STATE_CHANGED") refreshState();
  });
  document.addEventListener("keydown", (event) => {
    if (!opened) return;
    if (event.key === "Escape") { event.preventDefault(); close(); }
  });
  return { open, close, render() {}, isOpen: () => opened };
}
