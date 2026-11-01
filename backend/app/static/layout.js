// Disposition du monde v3, transcrite du croquis :
// le STOCK (3 parties) en haut, puis l'USINE (cadre en pointillés) avec 5 blocs et 3 blocs.
// Les blocs viennent du backend (state.blocks) ; ce fichier ne fait que les placer.

// x, z = centre ; w, d = largeur, profondeur ; door = côté de l'entrée (+1 vers le bas de l'écran, -1 vers le haut).
export const ZONES = {
  stock_mp: { block: "stock", part: "MP", title: "Stock de MP", x: -16, z: -10, w: 16, d: 6, door: 1, accent: 0x9cad8d },
  stock_sf: { block: "stock", part: "SF", title: "Stock de semi-finis", x: 0, z: -10, w: 15, d: 6, door: 1, accent: 0xb3a36f },
  stock_pf: { block: "stock", part: "PF", title: "Stock de produits finis", x: 16, z: -10, w: 16, d: 6, door: 1, accent: 0x8eaab8 },

  quai_dechargement: { block: "quai_dechargement", x: -22, z: -0.75, w: 7, d: 8.5, door: 1, accent: 0x8eb7a5, dockSide: -1, dockBays: [0] },
  bureau_reception: { block: "bureau_reception", x: -14.75, z: -0.75, w: 6.5, d: 8.5, door: 1, accent: 0x8eb7a5 },
  chaine_production: { block: "chaine_production", x: -1.5, z: -0.75, w: 19, d: 8.5, door: 1, accent: 0x70c1bb },
  emballage: { block: "emballage", x: 12, z: -0.75, w: 7, d: 8.5, door: 1, accent: 0xd4a45c },
  logistique_transport: { block: "logistique_transport", x: 20.5, z: -0.75, w: 9, d: 8.5, door: 1, accent: 0x9cad8d, dockSide: 1, dockBays: [-1.85, 2.35] },

  controle_qualite: { block: "controle_qualite", x: -16.5, z: 9.25, w: 15, d: 6.5, door: -1, accent: 0x70c1bb },
  bureau_etude: { block: "bureau_etude", x: 0, z: 9.25, w: 15, d: 6.5, door: -1, accent: 0x53766a },
  maintenance_pdr: { block: "maintenance_pdr", x: 16.5, z: 9.25, w: 15, d: 6.5, door: -1, accent: 0x80958d },
};

// Cadre en pointillés de l'usine et limites de déplacement.
export const FACTORY_FRAME = { x1: -26.2, x2: 26.2, z1: -5.5, z2: 12.9 };
export const WALK_BOUNDS = { x1: -27, x2: 27, z1: -13.4, z2: 12.8 };

// Quais vus depuis l'extérieur : où se garent les camions.
export const DOCKS = {
  fournisseur: { x: -29.4, z: -0.75, from: -52, heading: 1 },
  livraison: { x: 28.4, z: -2.6, to: 52, heading: -1 },
  client: { x: 28.4, z: 1.6, from: 52, heading: -1 },
};

// Le chemin de la matière, tel qu'il est écrit dans la v3 (barre de navigation du haut).
export const FLOW = [
  { zone: "quai_dechargement", label: "Quai" },
  { zone: "bureau_reception", label: "Réception" },
  { zone: "stock_mp", label: "Stock MP" },
  { zone: "chaine_production", label: "Production" },
  { zone: "stock_sf", label: "Stock SF" },
  { zone: "controle_qualite", label: "Contrôle qualité" },
  { zone: "emballage", label: "Emballage" },
  { zone: "stock_pf", label: "Stock PF" },
  { zone: "logistique_transport", label: "Logistique & Transport" },
];
export const SUPPORT = [
  { zone: "bureau_etude", label: "Bureau d’étude" },
  { zone: "maintenance_pdr", label: "Maintenance & PDR" },
];

// Rôle de chaque bloc (tableau « Les agents de chaque bloc » de la v3).
export const BLOCK_ROLES = {
  quai_dechargement: "Amener le camion, décharger les palettes.",
  bureau_reception: "Contrôler la livraison, l’enregistrer, étiqueter les palettes.",
  stock: "Ranger, sortir dans l’ordre d’arrivée, préparer les kits, suivre les 3 stocks.",
  chaine_production: "Lancer et suivre la production, faire tourner les machines.",
  controle_qualite: "Contrôler et trier : conforme, à retoucher, rebut.",
  emballage: "Mettre en carton, étiqueter et peser, monter et filmer la palette, l’envoyer au stock PF.",
  bureau_etude: "Définir les gammes, les nomenclatures et les temps.",
  maintenance_pdr: "Réparer les pannes, faire le préventif, gérer les pièces de rechange.",
  logistique_transport: "Préparer les expéditions, charger les camions (les siens et ceux des clients venus au quai), livrer le client.",
};

// Tenue par rôle : un modèle de personnage de base, décliné en couleurs.
export const ROLE_OUTFITS = {
  chauffeur_fournisseur: { jacket: 0x6d7a8a, helmet: 0xe6e3d6 },
  receptionnaire: { jacket: 0x4f8c7c, helmet: 0xe4bd54 },
  magasinier_cariste: { jacket: 0x4b718a, helmet: 0xe4bd54 },
  chef_de_ligne: { jacket: 0x2f5f74, helmet: 0xffffff },
  operateur_machine: { jacket: 0x7d8153, helmet: 0xe4bd54 },
  controleur_qualite: { jacket: 0xe8e8e0, helmet: 0x6fb5d8 },
  emballeur: { jacket: 0xb27c54, helmet: 0xe4bd54 },
  responsable_production: { jacket: 0x31443f, helmet: 0xffffff },
  technicien_maintenance: { jacket: 0xc4622f, helmet: 0xe4bd54 },
  magasinier_logistique: { jacket: 0x71875b, helmet: 0xe4bd54 },
  chauffeur_livreur: { jacket: 0x3f6d5e, helmet: 0xe6e3d6 },
  chauffeur_client: { jacket: 0x8a5d7a, helmet: 0xe6e3d6 },
};
