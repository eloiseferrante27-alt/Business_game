// Monde 3D G-mix — version v3 (« Mon monde v3 – blocs, agents et assets »).
// Le STOCK (MP, semi-finis, PF) est en haut ; l'USINE (cadre en pointillés) regroupe 8 blocs.
// Le joueur n'a pas de bureau : il pilote l'usine avec sa tablette.
import * as THREE from "./three.module.js";
import { createKit } from "./kit.js";
import { createAssets } from "./assets.js";
import { ZONES, FACTORY_FRAME, WALK_BOUNDS, DOCKS, FLOW, SUPPORT, BLOCK_ROLES, ROLE_OUTFITS } from "./layout.js";
import { createTablet, DEPARTMENT_BY_ZONE } from "./tablet-bridge.js";

const $ = (selector) => document.querySelector(selector);
const canvas = $("#world");
const loading = $("#loading");
const scene = new THREE.Scene();
// Ciel en dégradé (plus « jeu ») et brume assortie à l'horizon.
{
  const ciel = document.createElement("canvas");
  ciel.width = 4; ciel.height = 256;
  const c = ciel.getContext("2d");
  const g = c.createLinearGradient(0, 0, 0, 256);
  g.addColorStop(0, "#6aaeea"); g.addColorStop(0.55, "#bfe0f6"); g.addColorStop(1, "#f4efe1");
  c.fillStyle = g; c.fillRect(0, 0, 4, 256);
  const texture = new THREE.CanvasTexture(ciel);
  texture.colorSpace = THREE.SRGBColorSpace;
  scene.background = texture;
}
scene.fog = new THREE.Fog(0xdde9ef, 70, 175);

const camera = new THREE.PerspectiveCamera(50, innerWidth / innerHeight, 0.1, 240);
const CAMERA_HOME = { yaw: 0.35, distance: 30 };
// Deux vues : 3e personne (par défaut, la caméra suit le joueur) ou vue d'ensemble (touche 3).
let vueHaute = false;
let distance3p = 11;
let orbite = 0; // décalage de la souris autour du joueur, revient derrière lui quand il marche
const camPos = new THREE.Vector3();
const camCible = new THREE.Vector3();
let cameraYaw = CAMERA_HOME.yaw;
let cameraDistance = CAMERA_HOME.distance;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.1;

scene.add(new THREE.HemisphereLight(0xdcefff, 0x7d9b6a, 1.35));
const sun = new THREE.DirectionalLight(0xfff0d4, 2.9);
sun.position.set(-20, 34, 16);
sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
Object.assign(sun.shadow.camera, { left: -44, right: 44, top: 34, bottom: -34 });
sun.shadow.bias = -0.00015;
sun.shadow.normalBias = 0.025;
scene.add(sun);

const kit = createKit(renderer);
const { box, cylinder, floorMark, labelSprite } = kit;
const assets = createAssets(kit);

const world = new THREE.Group();
scene.add(world);
const obstacles = [];
const interactables = [];
const workers = [];
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0.02);
const clock = new THREE.Clock();
const keys = new Set();

// Ce que le monde doit refléter quand l'état change.
const visuals = { racks: [], sfCarts: [], lines: new Map(), quarantine: null, pdrLabel: null, conformParts: [], reworkParts: [], shipping: [], dockDoors: {} };
const truckActors = [];
const dockQueues = { fournisseur: [], livraison: [], client: [] };
let forklift = null;
let roof = null;
// Aménagement choisi sur la tablette (onglet Configuration) : forme du stock et tampons.
let amenagement = { stock: { forme: "I" }, production: { tampons: {} } };
const stockRacks = [];      // { group, zone, obstacle }
const stockProps = {};      // petits objets du stock déplacés selon la forme
const buffers = new Map();  // ligne -> [{ table, pieces, belt }]
let stockHeader = null;
let focusApresTablette = null;

let state = null;
let savedState = null;
let tabletSnapshot = null;
let lastTruckPeriod = null;
let playerPath = [];
let dragging = false;
let lastPointer = { x: 0, y: 0 };
let currentSelection = null;
let toastTimer = 0;
let tutorialIndex = 0;
const tutorialSteps = [
  { action: "move", title: "Déplace-toi dans l’usine", copy: "Z et S pour avancer ou reculer, Q et D pour tourner (ou les flèches), ou un clic sur le sol. Touche 3 : vue d’ensemble. Le stock est en haut, l’usine en dessous, dans le cadre en pointillés." },
  { action: "inspect", title: "Inspecte un bloc", copy: "Clique sur un bloc, un rack, une machine ou un agent. La barre du haut suit le chemin de la matière." },
  { action: "order", title: "Achète de la matière avec ta tablette", copy: "Tu n’as pas de bureau : ouvre la tablette (touche 1 ou T), compare les fournisseurs puis passe une commande dans Achats MP." },
  { action: "production", title: "Lance un ordre de fabrication", copy: "Toujours depuis la tablette, onglet Ordres de fabrication : choisis le produit et la quantité." },
  { action: "week", title: "Fais avancer la semaine", copy: "Clique sur Lancer la semaine : camions fournisseurs au quai, production, contrôle, emballage, puis expéditions." },
];

const stocksOf = (...categories) => (state?.stocks || []).filter((item) => categories.includes(item.category));
const stockBySku = (sku) => (state?.stocks || []).find((item) => item.sku === sku);
const spareCount = () => stockBySku("MAT-PDR")?.quantity || 0;
const blockName = (id) => state?.blocks?.find((block) => block.id === id)?.name || id;
const canonicalBlock = (blockId) => blockId === "bureau_etude" ? "chaine_production" : blockId;
const agentsIn = (blockId) => (state?.agents || []).filter((agent) => canonicalBlock(agent.block_id) === canonicalBlock(blockId) || agent.also_in?.includes(blockId));
const fmt = (value, digits = 0) => new Intl.NumberFormat("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value ?? 0);

function addObstacle(x, z, width, depth) { obstacles.push({ x, z, width, depth }); }
function addClickable(group, info) { group.userData.interaction = info; interactables.push(group); }

// Coordonnées locales d'un bloc : lx vers la droite, lz positif vers son entrée.
function toWorld(zone, lx, lz) { return [zone.x + lx, zone.z + zone.door * lz]; }
function facing(zone) { return zone.door === 1 ? 0 : Math.PI; }

function place(id, x, z, opts = {}) {
  const g = assets.make(id, opts);
  g.position.set(x, opts.y || 0, z);
  g.rotation.y = opts.rot || 0;
  (opts.parent || world).add(g);
  if (opts.solid) addObstacle(x, z, opts.solid[0], opts.solid[1]);
  if (opts.click !== false) addClickable(g, { type: "asset", title: g.userData.asset.label, subtitle: g.userData.asset.block, ...(opts.info || {}) });
  return g;
}
function placeIn(zoneId, id, lx, lz, opts = {}) {
  const zone = ZONES[zoneId];
  const [x, z] = toWorld(zone, lx, lz);
  const solid = opts.solid && (opts.turn ? [opts.solid[1], opts.solid[0]] : opts.solid);
  return place(id, x, z, { flipText: zone.door === -1, ...opts, solid, rot: facing(zone) + (opts.turn || 0), info: { zone: zoneId, ...(opts.info || {}) } });
}

// ------------------------------------------------------------------- bâtiment
// Murs « coupés » : bas côté caméra (vers +z) pour voir l'intérieur des blocs.
function wallHeightAt(zWall, zCenter, axis) {
  if (axis === "z") return 2.2;
  return zWall > zCenter + 0.1 ? 1.0 : 3.2;
}
function wall(x1, z1, x2, z2, height = 3.2, color = 0xd6d9d0) {
  const horizontal = Math.abs(z2 - z1) < 0.01;
  const length = horizontal ? Math.abs(x2 - x1) : Math.abs(z2 - z1);
  if (length < 0.05) return;
  const cx = (x1 + x2) / 2, cz = (z1 + z2) / 2;
  box(world, horizontal ? length : 0.2, height, horizontal ? 0.2 : length, color, cx, height / 2, cz, { roughness: 0.92 });
  addObstacle(cx, cz, horizontal ? length : 0.28, horizontal ? 0.28 : length);
}
// Mur avec ouvertures : `openings` = [[centre, largeur], ...] le long du mur.
function wallWithOpenings(fixed, from, to, openings, axis, height, color) {
  let cursor = from;
  for (const [center, width] of [...openings].sort((a, b) => a[0] - b[0])) {
    const start = center - width / 2;
    if (axis === "x") wall(cursor, fixed, start, fixed, height, color); else wall(fixed, cursor, fixed, start, height, color);
    if (height > 2) { if (axis === "x") box(world, width, 0.35, 0.2, 0x4d665e, center, height - 0.17, fixed); else box(world, 0.2, 0.35, width, 0x4d665e, fixed, height - 0.17, center); }
    cursor = center + width / 2;
  }
  if (axis === "x") wall(cursor, fixed, to, fixed, height, color); else wall(fixed, cursor, fixed, to, height, color);
}

function makeGround() {
  const grass = new THREE.Mesh(new THREE.PlaneGeometry(320, 240), kit.material(0x9cc97a));
  grass.rotation.x = -Math.PI / 2;
  grass.position.y = -0.2;
  grass.receiveShadow = true;
  world.add(grass);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(68, 34), kit.material(0xffffff, 0.93, 0, "concrete"));
  floor.rotation.x = -Math.PI / 2;
  floor.position.set(0, 0, -0.5);
  floor.receiveShadow = true;
  world.add(floor);
  // Cours camions : à gauche les fournisseurs, à droite les expéditions.
  for (const side of [-1, 1]) {
    const yard = new THREE.Mesh(new THREE.PlaneGeometry(30, 12), kit.material(0x6f7873, 0.95));
    yard.rotation.x = -Math.PI / 2;
    yard.position.set(side * 48, -0.03, -0.5);
    yard.receiveShadow = true;
    world.add(yard);
    for (let x = 35; x < 62; x += 3) box(world, 1.4, 0.02, 0.12, 0xf2df9e, side * x, 0, -0.5, { castShadow: false });
  }
  // Marquage des allées : voie engins (jaune) et passage piétons (vert).
  for (const z of [-7, 5.5]) {
    box(world, 62, 0.02, 0.08, 0xe8c54a, 0, 0.01, z - 0.55, { castShadow: false });
    box(world, 62, 0.02, 0.08, 0xe8c54a, 0, 0.01, z + 0.55, { castShadow: false });
    for (let x = -30; x <= 30; x += 2.4) box(world, 1.1, 0.022, 0.5, 0x7fb08f, x, 0.011, z, { castShadow: false });
  }
  // Cadre en pointillés de l'USINE (comme sur le croquis).
  const { x1, x2, z1, z2 } = FACTORY_FRAME;
  for (let x = x1; x < x2; x += 1.2) { box(world, 0.6, 0.03, 0.12, 0x2f5d50, x + 0.3, 0.02, z1, { castShadow: false }); box(world, 0.6, 0.03, 0.12, 0x2f5d50, x + 0.3, 0.02, z2, { castShadow: false }); }
  for (let z = z1; z < z2; z += 1.2) { box(world, 0.12, 0.03, 0.6, 0x2f5d50, x1, 0.02, z + 0.3, { castShadow: false }); box(world, 0.12, 0.03, 0.6, 0x2f5d50, x2, 0.02, z + 0.3, { castShadow: false }); }
  const usine = labelSprite("USINE", "#f3f1df", "#2f5d50");
  usine.scale.set(2.6, 0.62, 1);
  usine.position.set(x1 + 1.6, 0.5, z2 + 0.6);
  world.add(usine);
  // Toit : masqué par défaut pour voir l'intérieur ; la touche R l'affiche.
  roof = new THREE.Group();
  for (const x of [-33, -16.5, 0, 16.5, 33]) for (const z of [-16.8, 15.8]) cylinder(roof, 0.16, 0.16, 6.2, 0x55615c, x, 3.1, z, 8, { metalness: 0.4 });
  for (const x of [-33, -16.5, 0, 16.5, 33]) box(roof, 0.3, 0.4, 32.6, 0x55615c, x, 6.2, -0.5, { metalness: 0.4 });
  for (const [z, tilt] of [[-8.6, 0.08], [7.6, -0.08]]) {
    const panel = box(roof, 67, 0.12, 16.6, 0x8f9c96, 0, 6.9, z, { texture: "ribbed", metalness: 0.3 });
    panel.rotation.x = tilt;
  }
  roof.visible = false;
  world.add(roof);
}

function makeBlockShell(zoneId) {
  const zone = ZONES[zoneId];
  const { x, z, w, d, door: s } = zone;
  const front = z + s * d / 2, back = z - s * d / 2;
  const hBack = wallHeightAt(back, z, "x"), hFront = wallHeightAt(front, z, "x"), hSide = wallHeightAt(0, 0, "z");
  const floorPlate = box(world, w - 0.2, 0.02, d - 0.2, 0xe5e6dc, x, 0.012, z, { castShadow: false, texture: "concrete" });
  floorPlate.material = kit.material(0xffffff, 0.9, 0, "concrete", { unique: true });
  floorPlate.material.color.setHex(0xf1f1ea).lerp(new THREE.Color(zone.accent), 0.24);
  // Pas de murs : une clôture virtuelle basse et translucide, à la couleur du bloc, qu'on traverse librement.
  const accent = new THREE.Color(zone.accent);
  const trait = accent.clone().multiplyScalar(0.78).getHex();
  const cotes = [[x, back, w, true], [x, front, w, true], [x - w / 2, z, d, false], [x + w / 2, z, d, false]];
  for (const [cx, cz, longueur, horizontal] of cotes) {
    const [lx, lz] = horizontal ? [longueur, 0.05] : [0.05, longueur];
    box(world, horizontal ? longueur : 0.14, 0.03, horizontal ? 0.14 : longueur, trait, cx, 0.02, cz, { castShadow: false });
    const voile = box(world, lx, 0.9, lz, zone.accent, cx, 0.47, cz, { opacity: 0.16, roughness: 0.3, castShadow: false });
    voile.material.depthWrite = false;
    box(world, horizontal ? longueur : 0.06, 0.05, horizontal ? 0.06 : longueur, trait, cx, 0.94, cz, { castShadow: false });
  }
  // Panneau de signalisation du bloc, avec ses agents.
  const blockId = zone.block;
  const title = zone.title || blockName(blockId);
  const agentNames = zone.block === "stock" ? "" : agentsIn(blockId).filter((agent) => !agent.external).map((agent) => agent.role_label).filter((v, i, a) => a.indexOf(v) === i).join(" · ");
  place("panneau_bloc", x, front, { text: title, width: Math.min(w - 0.5, 4.4), agents: agentNames, click: false });
  // Extincteur près de chaque entrée.
  placeIn(zoneId, "extincteur", 1.9, d / 2 - 0.35, {});
  // Le sol du bloc est cliquable : il ouvre la fiche du bloc.
  addClickable(floorPlate, { type: "block", zone: zoneId, title });
}

function makeDock(zoneId, offset, kind) {
  const zone = ZONES[zoneId];
  const x = zone.x + zone.dockSide * zone.w / 2;
  const z = zone.z + offset;
  const rot = zone.dockSide === -1 ? -Math.PI / 2 : Math.PI / 2;
  const door = place("quai_porte_sectionnelle", x, z, { rot, info: { zone: zoneId } });
  visuals.dockDoors[kind] = door.getObjectByName("sectional-door");
  place("niveleur_quai", x - zone.dockSide * 1.05, z, { rot, click: false });
  const label = labelSprite(kind === "fournisseur" ? "QUAI DE DÉCHARGEMENT" : kind === "client" ? "QUAI D’EXPÉDITION · CLIENTS" : "QUAI D’EXPÉDITION · NOS CAMIONS", "#fff9dc", "#34465d");
  label.scale.set(3.2, 0.5, 1);
  label.position.set(x + zone.dockSide * 0.8, 3.85, z);
  world.add(label);
}

// ---------------------------------------------------------------- intérieurs
function rackLabel(group, text, y = 3.75) {
  const label = labelSprite(text, "#fff9dc", "#183a36");
  label.scale.set(2.4, 0.5, 1);
  label.position.set(0, y, 0);
  group.add(label);
  return label;
}

function furnishStock() {
  // Commun aux 3 stocks : panneau de zone, racks ; le magasinier-cariste les suit tous.
  const mp = stocksOf("MP");
  [-6.1, -3.05, 0, 3.05, 6.1].forEach((lx, index) => {
    const item = mp[index];
    if (!item) return;
    const rack = placeIn("stock_mp", "rack_palettes", lx, -1.85, { bays: 2, color: [0xb88a55, 0xc79c63, 0xa98450, 0x9c7b52, 0xc9a874][index], info: { type: "stock", sku: item.sku, title: item.name } });
    visuals.racks.push({ group: rack, sku: item.sku, label: rackLabel(rack, item.sku) });
    stockRacks.push({ group: rack, zone: "stock_mp", obstacle: rackObstacle(rack) });
  });
  stockProps.etagere = placeIn("stock_mp", "etagere_bacs", -7.2, 0.6, { turn: Math.PI / 2 });
  stockProps.paletteMp = placeIn("stock_mp", "palette_mp", -6, 2.2, { info: { subtitle: "Stock de MP (réutilisée du quai)" } });
  stockProps.borne = placeIn("stock_mp", "borne_recharge", 6.6, 1.6, {});
  placeIn("stock_mp", "panneau_zone", 0, 0.6, { lines: ["MP", "Matières premières"], bg: "#5e7a4f", click: false });
  forklift = placeIn("stock_mp", "chariot_elevateur", 2, 0.9, { info: { type: "forklift", title: "Chariot élévateur", subtitle: "Magasinier-cariste · Stock" } });
  forklift.userData.patrol = { zone: "stock_mp", points: [[-4, 0.9], [4.8, 0.9], [5.4, 1.4], [-4, 0.9]], index: 0 };

  const sf = stocksOf("SF");
  [-5.25, -1.75, 1.75, 5.25].forEach((lx, index) => {
    const item = sf[index];
    if (!item) return;
    const cart = placeIn("stock_sf", "chariot_semi_finis", lx, -0.6, { solid: [1.1, 0.7], info: { type: "stock", sku: item.sku, title: item.name } });
    visuals.sfCarts.push({ group: cart, sku: item.sku, label: rackLabel(cart, item.sku, 1.7) });
  });
  placeIn("stock_sf", "etagere_bacs", -4, -2.4, { color: 0xd9a441, solid: [1.9, 0.6] });
  placeIn("stock_sf", "etagere_bacs", 4, -2.4, { color: 0xd9a441, solid: [1.9, 0.6] });
  placeIn("stock_sf", "bac_plastique", 0, -2.5, {});
  placeIn("stock_sf", "panneau_zone", 0, 1, { lines: ["SF", "Produits semi-finis"], bg: "#8a7340", click: false });

  const pf = stocksOf("PF");
  [-5.7, -1.9, 1.9, 5.7].forEach((lx, index) => {
    const item = pf[index];
    if (!item) return;
    const rack = placeIn("stock_pf", "rack_palettes", lx, -1.85, { bays: 2, color: 0xa9a37c, wrapped: true, info: { type: "stock", sku: item.sku, title: item.name } });
    visuals.racks.push({ group: rack, sku: item.sku, label: rackLabel(rack, item.sku) });
    stockRacks.push({ group: rack, zone: "stock_pf", obstacle: rackObstacle(rack) });
  });
  placeIn("stock_pf", "palette_pf_filmee", 4.2, 1.9, { solid: [1.2, 1.1] });
  placeIn("stock_pf", "panneau_zone", 0, 0.6, { lines: ["PF", "Produits finis"], bg: "#3f6577", click: false });

  const header = labelSprite("STOCK · rangement en ligne (I)", "#fff9dc", "#2f5d50");
  header.scale.set(7, 0.62, 1);
  header.position.set(0, 5.2, -15.3);
  world.add(header);
  stockHeader = header;
}

function furnishQuai() {
  placeIn("quai_dechargement", "zone_depose", 0.8, -1.6, { w: 3.6, d: 2.6 });
  placeIn("quai_dechargement", "palette_mp", 0.1, -1.7, { solid: [1.2, 1.1] });
  placeIn("quai_dechargement", "palette_mp", 1.6, -1.7, { solid: [1.2, 1.1] });
  placeIn("quai_dechargement", "transpalette", 0.6, 1.6, { turn: Math.PI / 2 });
}

function furnishReception() {
  placeIn("bureau_reception", "bureau_chaise", 0, -3.2, { solid: [1.7, 0.9] });
  placeIn("bureau_reception", "ordinateur", -0.35, -3.2, {});
  placeIn("bureau_reception", "lecteur_code_barres", 0.25, -3.1, {});
  placeIn("bureau_reception", "imprimante_etiquettes", 0.6, -3.35, {});
  placeIn("bureau_reception", "bon_livraison", 0.05, -2.95, {});
  placeIn("bureau_reception", "balance_sol", -1.9, 0.4, {});
  placeIn("bureau_reception", "zone_quarantaine", 1.5, 0.2, { w: 2.2, d: 2 });
  visuals.quarantine = placeIn("bureau_reception", "palette_mp", 1.5, 0.2, { info: { subtitle: "Palette en quarantaine (non conforme)" } });
}

function furnishProduction() {
  const lines = state?.production_lines || [];
  const rows = [-3.25, -1.75, -0.25, 1.25];
  const accents = [0x77a99c, 0xdaa05d, 0x93ad6f, 0x8aa8bd];
  rows.forEach((lz, row) => {
    const line = lines[row];
    if (!line) return;
    const info = { type: "line", lineId: line.id, title: line.name };
    placeIn("chaine_production", "convoyeur", -8.2, lz, { length: 1.4, click: false });
    const machines = [];
    [-6.3, -3.4, -0.5, 2.4].forEach((lx, index) => {
      const machine = line.machines[index];
      machines.push(placeIn("chaine_production", "machine", lx, lz, { rank: index + 1, accent: accents[row], tag: machine?.id || `M${index + 1}`, info }));
      if (index < 3) {
        // Entre deux machines : un convoyeur court, ou une table tampon (1 à 3 pièces) si le joueur en a ajouté une.
        const belt = placeIn("chaine_production", "convoyeur", lx + 1.45, lz, { length: 1.0, click: false });
        const table = placeIn("chaine_production", "table_attente", lx + 1.45, lz, { click: false });
        const mark = floorMark(world, 1.25, 1.05, 0xd8f18a, ...toWorld(ZONES.chaine_production, lx + 1.45, lz));
        if (mark) { mark.material = mark.material.clone(); mark.material.transparent = true; mark.material.opacity = 0.55; table.userData.mark = mark; }
        const pieces = [0, 1, 2].map((k) => placeIn("chaine_production", "piece_en_cours", lx + 1.45 - 0.25 + k * 0.25, lz, { y: 0.78, click: false }));
        if (!buffers.has(line.id)) buffers.set(line.id, []);
        buffers.get(line.id).push({ table, pieces, belt });
      }
    });
    placeIn("chaine_production", "convoyeur", 4.3, lz, { length: 1.6, click: false });
    addObstacle(...toWorld(ZONES.chaine_production, -1.9, lz), 13.4, 1.05);
    const tag = labelSprite(`L${row + 1} · ${stockBySku(line.product_sku)?.name || line.product_sku}`, "#fff9dc", "#245149");
    tag.scale.set(2.3, 0.42, 1);
    const [tx, tz] = toWorld(ZONES.chaine_production, -8.2, lz);
    tag.position.set(tx, 1.45, tz);
    world.add(tag);
    visuals.lines.set(line.id, machines);
  });
  placeIn("chaine_production", "tableau_ligne", -6.5, 3.75, { solid: [1.8, 0.3] });
  placeIn("chaine_production", "etabli", 7.4, -2.6, { turn: -Math.PI / 2, solid: [1.6, 0.8] });
  placeIn("chaine_production", "bac_dechets", 6.6, 3.4, { solid: [0.6, 0.6] });
  placeIn("chaine_production", "chariot_semi_finis", 7.5, 1.2, { solid: [1.1, 0.7], info: { subtitle: "Transfert vers le stock de semi-finis" } });
}

function furnishQuality() {
  placeIn("controle_qualite", "table_controle", -4.2, -2.2, { solid: [1.8, 0.9] });
  placeIn("controle_qualite", "instruments_mesure", -4.4, -2.2, {});
  placeIn("controle_qualite", "ordinateur", -3.6, -2.25, { y: 0.1, info: { subtitle: "Ordinateur de saisie (réutilisé du bureau de réception)" } });
  placeIn("controle_qualite", "banc_essai", -0.6, -2.3, { solid: [1.5, 0.8] });
  placeIn("controle_qualite", "zone_conforme", 3.2, -1.3, { w: 2.6, d: 2.2 });
  placeIn("controle_qualite", "zone_retouche", 6.1, -1.3, { w: 2.2, d: 2.2 });
  placeIn("controle_qualite", "bac_rebut", -6.4, 1.4, { solid: [0.6, 0.6] });
  for (let i = 0; i < 6; i++) visuals.conformParts.push(placeIn("controle_qualite", "piece_en_cours", 2.5 + (i % 3) * 0.6, -1.7 + Math.floor(i / 3) * 0.6, { click: false }));
  for (let i = 0; i < 3; i++) visuals.reworkParts.push(placeIn("controle_qualite", "piece_en_cours", 5.6 + i * 0.5, -1.5, { click: false }));
}

function furnishPackaging() {
  placeIn("emballage", "table_emballage", -1.4, -3, { solid: [2, 1] });
  placeIn("emballage", "carton_ruban", -1.3, -3, {});
  placeIn("emballage", "imprimante_etiquettes", -0.3, -3.2, { y: 0.1, info: { subtitle: "Emballage (réutilisée du bureau de réception)" } });
  placeIn("emballage", "balance_table", -2.1, -3.1, {});
  placeIn("emballage", "filmeuse", 1.6, -1.6, { solid: [2.2, 1.9] });
  placeIn("emballage", "palette_pf_filmee", 1.6, 1.6, { solid: [1.2, 1.1], info: { subtitle: "Vers le stock PF (même modèle que le stock PF)" } });
}

function furnishLogistics() {
  placeIn("logistique_transport", "zone_preparation", -1.6, -0.3, { w: 3.6, d: 3.2 });
  for (let i = 0; i < 4; i++) {
    visuals.shipping.push(placeIn("logistique_transport", "palette_pf_filmee", -2.4 + (i % 2) * 1.5, -1 + Math.floor(i / 2) * 1.35, { click: false }));
  }
  placeIn("logistique_transport", "transpalette", -1.4, 2.6, { turn: Math.PI / 2, info: { subtitle: "Logistique (réutilisé du quai)" } });
}

function furnishEngineering() {
  // v3 folds methods into production. Keep the legacy ID as a navigation alias.
  placeIn("chaine_production", "bureau_chaise", 6.8, 3.1, { solid: [1.7, 0.9] });
  placeIn("chaine_production", "ordinateur", 6.5, 3.1, {});
  placeIn("chaine_production", "tableau_planning", 4.3, 3.8, { solid: [2.2, 0.3] });
  placeIn("chaine_production", "armoire_dossiers", 8.5, 3.6, { solid: [0.9, 0.5] });
}

function furnishMaintenance() {
  placeIn("maintenance_pdr", "etabli_etau", -4.6, -2.65, { solid: [1.6, 0.8] });
  placeIn("maintenance_pdr", "piece_rechange", -4.9, -2.6, { y: 0.92 });
  placeIn("maintenance_pdr", "servante_outils", -2.4, -1.4, { solid: [0.8, 0.5] });
  const cabinet = placeIn("maintenance_pdr", "armoire_pdr", 0.8, -2.8, { solid: [1.4, 0.6] });
  visuals.pdrLabel = rackLabel(cabinet, "PDR", 2.5);
  placeIn("maintenance_pdr", "kit_consignation", 3.2, -3.05, {});
  placeIn("maintenance_pdr", "tableau_interventions", 5.8, -2.95, { solid: [1.8, 0.3] });
}

// --------------------------------------------------------------- personnages
function makePerson(name, outfit, info, isPlayer = false) {
  const person = new THREE.Group();
  const jacket = kit.material(outfit.jacket, 0.8, 0, null, { unique: true });
  const skin = kit.material(0xdcae88, 0.9);
  const dark = kit.material(0x34413d, 0.9);
  const pant = kit.material(0x334b4a, 0.9);
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.3, 0.73, 10), jacket);
  body.position.y = 0.96;
  body.castShadow = true;
  person.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 10), skin);
  head.position.y = 1.51;
  head.castShadow = true;
  person.add(head);
  const hardhat = new THREE.Mesh(new THREE.SphereGeometry(0.245, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), kit.material(outfit.helmet));
  hardhat.position.y = 1.65;
  person.add(hardhat);
  const reflective = kit.material(isPlayer ? 0xd8ef83 : 0xf1d36b, 0.38, 0.12);
  for (const y of [0.91, 1.12]) {
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.245, 0.022, 6, 18), reflective);
    band.rotation.x = Math.PI / 2;
    band.position.y = y;
    person.add(band);
  }
  const legs = [], arms = [];
  for (const side of [-1, 1]) {
    const legPivot = new THREE.Group();
    legPivot.position.set(side * 0.12, 0.65, 0);
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.075, 0.57, 8), pant);
    leg.position.y = -0.27;
    legPivot.add(leg);
    const shoe = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.1, 0.32), dark);
    shoe.position.set(0, -0.52, 0.07);
    legPivot.add(shoe);
    person.add(legPivot);
    legs.push(legPivot);
    const armPivot = new THREE.Group();
    armPivot.position.set(side * 0.27, 1.18, 0);
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.07, 0.48, 8), jacket);
    arm.position.y = -0.22;
    armPivot.add(arm);
    person.add(armPivot);
    arms.push(armPivot);
  }
  if (isPlayer) {
    // Le joueur tient sa tablette.
    arms[1].rotation.x = -1.0;
    const tablet = assets.make("tablette");
    tablet.position.set(0.12, 1.02, 0.36);
    tablet.rotation.x = -0.9;
    person.add(tablet);
    person.userData.fixedArm = true;
  }
  Object.assign(person.userData, { jacket, legs, arms, walkPhase: Math.random() * Math.PI * 2, route: [] });
  const tag = labelSprite(name, "#f5f2e3", isPlayer ? "#526d39" : "#294940");
  tag.scale.set(isPlayer ? 1.55 : 2.2, 0.48, 1);
  tag.position.y = 2.22;
  person.add(tag);
  addClickable(person, info);
  return person;
}

const player = makePerson("Vous · tablette", { jacket: 0x557c59, helmet: 0xd8ed82 }, { type: "player", title: "Vous", subtitle: "Pilote de l’usine, sans bureau : tout passe par la tablette." }, true);
player.position.set(-2, 0, 5);
world.add(player);
const marker = new THREE.Mesh(new THREE.TorusGeometry(0.48, 0.035, 8, 36), new THREE.MeshBasicMaterial({ color: 0xd8f18a, transparent: true, opacity: 0.9 }));
marker.rotation.x = Math.PI / 2;
marker.position.y = 0.035;
marker.visible = false;
world.add(marker);
const hoverRing = new THREE.Mesh(new THREE.TorusGeometry(0.58, 0.025, 8, 40), new THREE.MeshBasicMaterial({ color: 0xd9ef83, transparent: true, opacity: 0.78 }));
hoverRing.rotation.x = Math.PI / 2;
hoverRing.visible = false;
world.add(hoverRing);

function zoneOfBlock(blockId) {
  return Object.keys(ZONES).filter((id) => id !== "bureau_etude" && ZONES[id].block === canonicalBlock(blockId));
}
function insidePoints(zoneId) {
  const zone = ZONES[zoneId];
  const points = [];
  for (const lx of [-zone.w / 2 + 1.5, -1, 1, zone.w / 2 - 1.5]) points.push(toWorld(zone, lx, zone.d / 2 - 1.1));
  points.push(toWorld(zone, 0, zone.d / 2 + 0.9));
  return points;
}
function makeAgents() {
  for (const agent of state?.agents || []) {
    if (agent.external) continue; // les chauffeurs externes arrivent avec leur camion
    const zones = [...zoneOfBlock(agent.block_id), ...(agent.also_in || []).flatMap(zoneOfBlock)];
    if (!zones.length) continue;
    const targets = zones.flatMap(insidePoints).map(([x, z]) => new THREE.Vector3(Math.round(x), 0, Math.round(z)));
    const outfit = ROLE_OUTFITS[agent.role] || { jacket: 0x4f8c7c, helmet: 0xe4bd54 };
    const worker = makePerson(`${agent.name} · ${agent.role_label}`, outfit, {
      type: "worker", agentId: agent.id, role: agent.role, title: agent.name, roleLabel: agent.role_label, zone: zones[0],
      subtitle: `${agent.role_label} · ${blockName(canonicalBlock(agent.block_id))}`,
    });
    const start = targets[workers.length % targets.length];
    worker.position.copy(start);
    worker.userData.targets = targets;
    worker.userData.targetIndex = workers.length;
    worker.userData.agentId = agent.id;
    workers.push(worker);
    world.add(worker);
  }
}

// ------------------------------------------------------------------- camions
function makeExternalDriver(role, label) {
  const outfit = ROLE_OUTFITS[role];
  const driver = makePerson(label, outfit, { type: "worker", role, title: label.split(" · ")[0], roleLabel: label.split(" · ")[1] || label, subtitle: "Agent externe : arrive et repart avec son camion." });
  driver.visible = false;
  world.add(driver);
  return driver;
}
const drivers = {
  fournisseur: makeExternalDriver("chauffeur_fournisseur", "Chauffeur · fournisseur"),
  client: makeExternalDriver("chauffeur_client", "Chauffeur · client"),
};

function spawnTruck(kind, label, cargo, mode) {
  const dock = DOCKS[kind];
  const assetId = kind === "fournisseur" ? "camion_fournisseur" : kind === "client" ? "camion_client" : "camion_livraison";
  const truck = place(assetId, dock.x, dock.z, { label, cargo, rot: kind === "fournisseur" ? Math.PI : 0, info: { type: "truck", kind, title: label } });
  truck.userData.actor = { kind, mode, phase: mode === "parked" ? "docked" : "arrive", t: 0 };
  const start = mode === "depart" ? dock.x : (dock.from ?? dock.to);
  if (mode !== "parked" && mode !== "depart") truck.position.x = start;
  truck.visible = mode === "parked" || mode === "depart";
  truckActors.push(truck);
  return truck;
}

function queueTrucks(trucks) {
  for (const truck of trucks || []) {
    const sku = truck.sku ? stockBySku(truck.sku)?.name || truck.sku : "";
    const label = truck.kind === "fournisseur" ? `${truck.label}` : truck.kind === "client" ? `${truck.label}` : "Livraison client";
    dockQueues[truck.kind].push({ label, cargo: true, info: `${truck.quantity} · ${sku}`.trim() });
  }
}

function updateTrucks(delta) {
  for (const kind of ["fournisseur", "client", "livraison"]) {
    const busy = truckActors.some((truck) => truck.userData.actor.kind === kind && truck.userData.actor.phase !== "docked-idle" && truck.userData.actor.mode !== "parked");
    if (!busy && dockQueues[kind].length) {
      const next = dockQueues[kind].shift();
      if (kind === "livraison") {
        const parked = truckActors.find((truck) => truck.userData.actor.kind === "livraison" && truck.userData.actor.mode === "parked");
        if (parked) { parked.userData.actor.mode = "depart"; parked.userData.actor.phase = "leave"; parked.userData.actor.t = 0; }
      } else spawnTruck(kind, next.label, next.cargo, "visit");
    }
  }
  const door = (kind, open) => {
    const mesh = visuals.dockDoors[kind === "livraison" ? "livraison" : kind];
    if (mesh) mesh.position.y += ((open ? 2.85 : 2.3) - mesh.position.y) * Math.min(1, delta * 3);
  };
  for (const truck of [...truckActors]) {
    const actor = truck.userData.actor;
    const dock = DOCKS[actor.kind];
    actor.t += delta;
    const speed = 9;
    if (actor.phase === "arrive") {
      truck.visible = true;
      const dir = Math.sign(dock.x - truck.position.x);
      truck.position.x += dir * speed * delta;
      if (Math.sign(dock.x - truck.position.x) !== dir) { truck.position.x = dock.x; actor.phase = "docked"; actor.t = 0; }
    } else if (actor.phase === "docked") {
      door(actor.kind, true);
      if (actor.mode === "parked") continue;
      const driver = drivers[actor.kind];
      if (driver) { driver.visible = true; driver.position.set(dock.x + (actor.kind === "fournisseur" ? 0.3 : -0.3), 0, dock.z + 1.6); }
      if (actor.t > 4) { actor.phase = "leave"; actor.t = 0; if (driver) driver.visible = false; }
    } else if (actor.phase === "leave") {
      door(actor.kind, false);
      const away = actor.kind === "fournisseur" ? -60 : 60;
      truck.position.x += Math.sign(away - truck.position.x) * speed * delta;
      if (Math.abs(truck.position.x) > 58) {
        if (actor.mode === "depart") { actor.mode = "return"; actor.phase = "arrive"; truck.position.x = 58; }
        else { world.remove(truck); truckActors.splice(truckActors.indexOf(truck), 1); const i = interactables.indexOf(truck); if (i >= 0) interactables.splice(i, 1); }
      }
    }
    if (actor.mode === "return" && actor.phase === "docked") actor.mode = "parked";
  }
}

// ---------------------------------------------------------------- construction
// ------------------------------------------------------- aménagement (tablette)
function rackObstacle(rack) {
  const o = { x: rack.position.x, z: rack.position.z, width: 2.9, depth: 1.2 };
  obstacles.push(o);
  return o;
}
// Positions locales des racks d'une partie du stock selon la forme choisie (I, L, U, V).
function positionsRacks(forme, n) {
  const ligne = (count, from, to, lz = -1.85) => Array.from({ length: count }, (_, i) => ({ lx: count === 1 ? (from + to) / 2 : from + (i * (to - from)) / (count - 1), lz, turn: 0 }));
  const cote = (side) => ({ lx: side * 6.65, lz: 0.45, turn: Math.PI / 2 });
  if (forme === "L") return [cote(-1), ...ligne(n - 1, -3.6, 6.2)];
  if (forme === "U") return [cote(-1), ...ligne(Math.max(1, n - 2), -3.4, 3.4), cote(1)].slice(0, n);
  if (forme === "V") {
    const pas = Math.min(3, 12 / Math.max(1, n - 1));
    return Array.from({ length: n }, (_, i) => {
      const lx = (i - (n - 1) / 2) * pas;
      const angle = Math.abs(lx) < 0.1 ? 0 : (lx < 0 ? -0.6 : 0.6);
      return { lx, lz: -1.3, turn: angle };
    });
  }
  const pas = Math.min(3.05, 12.2 / Math.max(1, n - 1));
  return ligne(n, -((n - 1) * pas) / 2, ((n - 1) * pas) / 2);
}
function appliquerAmenagement(nouveau, { anime = true } = {}) {
  if (nouveau) amenagement = { stock: { ...amenagement.stock, ...(nouveau.stock || {}) }, production: { tampons: { ...(nouveau.production?.tampons || {}) } } };
  const forme = amenagement.stock.forme || "I";
  for (const zoneId of ["stock_mp", "stock_pf"]) {
    const racks = stockRacks.filter((r) => r.zone === zoneId);
    const places = positionsRacks(forme, racks.length);
    const zone = ZONES[zoneId];
    racks.forEach((r, i) => {
      const p = places[i];
      const [x, z] = toWorld(zone, p.lx, p.lz);
      const rot = facing(zone) + p.turn;
      r.group.userData.cible = { x, z, rot };
      if (!anime) { r.group.position.set(x, 0, z); r.group.rotation.y = rot; }
      const c = Math.abs(Math.cos(p.turn)), sn = Math.abs(Math.sin(p.turn));
      Object.assign(r.obstacle, { x, z, width: c * 2.9 + sn * 1.2, depth: sn * 2.9 + c * 1.2 });
    });
  }
  const deplacer = (objet, zoneId, lx, lz) => { if (!objet) return; const [x, z] = toWorld(ZONES[zoneId], lx, lz); objet.userData.cible = { x, z, rot: objet.rotation.y }; if (!anime) objet.position.set(x, objet.position.y, z); };
  if (stockProps.etagere) stockProps.etagere.visible = forme === "I";
  deplacer(stockProps.paletteMp, "stock_mp", forme === "L" || forme === "U" ? -4.3 : -6, forme === "L" || forme === "U" ? 2.35 : 2.2);
  deplacer(stockProps.borne, "stock_mp", forme === "U" ? 4.6 : 6.6, forme === "U" ? 2.4 : 1.6);
  const noms = { I: "en ligne (I)", L: "en L", U: "en U", V: "en V (épi)" };
  if (stockHeader) swapLabel(stockHeader, `STOCK · rangement ${noms[forme] || forme}`, "#fff9dc", "#2f5d50");
  for (const [ligne, slots] of buffers) {
    const valeurs = amenagement.production.tampons[ligne] || [];
    slots.forEach((slot, i) => {
      const n = Math.max(0, Math.min(3, Number(valeurs[i]) || 0));
      const avant = slot.table.visible;
      slot.table.visible = n > 0;
      if (slot.table.userData.mark) slot.table.userData.mark.visible = n > 0;
      slot.belt.visible = n === 0;
      slot.pieces.forEach((piece, k) => { piece.visible = k < n; });
      if (anime && n > 0 && !avant) { slot.table.scale.setScalar(0.01); slot.table.userData.pop = 0; }
    });
  }
}
function animerAmenagement(delta) {
  const k = Math.min(1, delta * 4);
  for (const r of stockRacks) {
    const c = r.group.userData.cible;
    if (!c) continue;
    r.group.position.x += (c.x - r.group.position.x) * k;
    r.group.position.z += (c.z - r.group.position.z) * k;
    r.group.rotation.y += (c.rot - r.group.rotation.y) * k;
  }
  for (const objet of Object.values(stockProps)) {
    const c = objet?.userData.cible;
    if (!c) continue;
    objet.position.x += (c.x - objet.position.x) * k;
    objet.position.z += (c.z - objet.position.z) * k;
  }
  for (const slots of buffers.values()) for (const slot of slots) {
    if (slot.table.userData.pop === undefined) continue;
    slot.table.userData.pop = Math.min(1, slot.table.userData.pop + delta * 2.5);
    const t = slot.table.userData.pop;
    slot.table.scale.setScalar(t < 1 ? Math.max(0.01, 1 + 1.7 * (t - 1) ** 3 + 0.7 * (t - 1) ** 2) : 1);
    if (t >= 1) delete slot.table.userData.pop;
  }
}
async function chargerAmenagement() {
  try {
    const r = await fetch("/api/v2/tablet/layout");
    if (r.ok) return await r.json();
  } catch { /* aménagement par défaut */ }
  return null;
}

// Décor autour de l'usine, façon city-builder : route périphérique, arbres, maisons.
// Purement visuel : rien ici n'est lu par le moteur.
function makeScenery() {
  const asphalte = 0x5f666b;
  const route = (w, d, x, z) => { box(world, w, 0.04, d, asphalte, x, -0.12, z, { castShadow: false }); };
  route(140, 4, 0, -23); route(140, 4, 0, 22); route(4, 49, -68, -0.5); route(4, 49, 68, -0.5);
  route(3.2, 4, -64.5, -0.5); route(3.2, 4, 64.5, -0.5);
  for (let x = -64; x <= 64; x += 4) { box(world, 1.6, 0.05, 0.14, 0xf4f1e6, x, -0.1, -23, { castShadow: false }); box(world, 1.6, 0.05, 0.14, 0xf4f1e6, x, -0.1, 22, { castShadow: false }); }
  // Hachage déterministe : le décor est le même à chaque chargement.
  const h = (i, k) => { const v = Math.sin(i * 127.1 + k * 311.7) * 43758.5453; return v - Math.floor(v); };
  const places = [];
  for (let i = 0; places.length < 240 && i < 3000; i++) {
    const x = (h(i, 1) - 0.5) * 230, z = (h(i, 2) - 0.5) * 170;
    if (Math.abs(x) < 72 && Math.abs(z) < 27) continue;
    places.push([x, z, 0.7 + h(i, 3) * 0.8, h(i, 4)]);
  }
  const tronc = new THREE.InstancedMesh(new THREE.CylinderGeometry(0.14, 0.2, 1.2, 6), kit.material(0x8a6a4a), places.length);
  const feuilles = new THREE.InstancedMesh(new THREE.IcosahedronGeometry(1.1, 0), new THREE.MeshStandardMaterial({ roughness: 0.9, flatShading: true }), places.length);
  const verts = [0x6fae5c, 0x5d9e57, 0x82bd66, 0x4f8f52].map((c) => new THREE.Color(c));
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler();
  places.forEach(([x, z, taille, t], i) => {
    m.compose(new THREE.Vector3(x, 0.4 * taille, z), q, new THREE.Vector3(taille, taille, taille));
    tronc.setMatrixAt(i, m);
    q.setFromEuler(e.set(0, t * 6, 0));
    m.compose(new THREE.Vector3(x, 1.75 * taille, z), q, new THREE.Vector3(taille, taille * 1.25, taille));
    feuilles.setMatrixAt(i, m);
    feuilles.setColorAt(i, verts[Math.floor(t * verts.length)]);
    q.identity();
  });
  for (const mesh of [tronc, feuilles]) { mesh.castShadow = true; mesh.receiveShadow = true; world.add(mesh); }
  // Quelques maisons au loin, pour l'échelle.
  const murs = [0xf2e6d0, 0xe9d8c4, 0xdfe7ea, 0xf4ddd0], toits = [0xc8644a, 0x8a5a44, 0x5f7380];
  for (let i = 0; i < 16; i++) {
    const cote = i % 2 ? 1 : -1, x = -70 + (i >> 1) * 20 + h(i, 5) * 6, z = cote * (38 + h(i, 6) * 18);
    const maison = new THREE.Group();
    box(maison, 6, 3, 5, murs[i % murs.length], 0, 1.5, 0);
    const toit = new THREE.Mesh(new THREE.ConeGeometry(4.6, 2.2, 4), new THREE.MeshStandardMaterial({ color: toits[i % toits.length], roughness: 0.85, flatShading: true }));
    toit.position.y = 4.1; toit.rotation.y = Math.PI / 4; toit.scale.set(1, 1, 0.8); toit.castShadow = true;
    maison.add(toit);
    maison.position.set(x, 0, z); maison.rotation.y = h(i, 7) * 0.6 - 0.3;
    world.add(maison);
  }
}

function buildWorld() {
  makeGround();
  makeScenery();
  Object.keys(ZONES).filter((id) => id !== "bureau_etude").forEach(makeBlockShell);
  makeDock("quai_dechargement", 0, "fournisseur");
  makeDock("logistique_transport", ZONES.logistique_transport.dockBays[0], "livraison");
  makeDock("logistique_transport", ZONES.logistique_transport.dockBays[1], "client");
  furnishStock();
  furnishQuai();
  furnishReception();
  furnishProduction();
  furnishQuality();
  furnishPackaging();
  furnishLogistics();
  furnishEngineering();
  furnishMaintenance();
  makeAgents();
  spawnTruck("livraison", "G-MIX · LIVRAISON", true, "parked");
  buildFlowBar();
  appliquerAmenagement(null, { anime: false });
  refreshWorld();
}

// Le monde suit l'état : racks remplis selon le stock, voyants des machines, quarantaine…
function refreshWorld() {
  if (!state) return;
  for (const rack of visuals.racks) {
    const item = stockBySku(rack.sku);
    if (!item) continue;
    const slots = rack.group.userData.slots || [];
    const filled = item.quantity <= 0 ? 0 : Math.max(1, Math.round((item.quantity / item.capacity_max) * slots.length));
    slots.forEach((slot, index) => { slot.visible = index < filled; });
    swapLabel(rack.label, `${item.sku} · ${fmt(item.quantity)}`, item.quantity <= item.reorder_point ? "#ffe2a8" : "#fff9dc", item.quantity < item.minimum ? "#7a3b26" : "#183a36");
  }
  for (const cart of visuals.sfCarts) {
    const item = stockBySku(cart.sku);
    if (!item) continue;
    swapLabel(cart.label, `${item.sku} · ${fmt(item.quantity)}`, "#fff9dc", item.quantity < item.minimum ? "#7a3b26" : "#5f5530");
  }
  if (visuals.quarantine) visuals.quarantine.visible = (state.last_week?.quarantined || 0) > 0;
  if (visuals.pdrLabel) swapLabel(visuals.pdrLabel, `PDR · ${spareCount()} pièce(s)`, "#fff9dc", spareCount() ? "#183a36" : "#7a3b26");
  const produced = state.last_week?.produced || 0;
  visuals.conformParts.forEach((part, index) => { part.visible = index < Math.ceil(Math.min(6, produced / 300)); });
  visuals.reworkParts.forEach((part, index) => { part.visible = index < Math.min(3, Math.ceil((state.last_week?.reworked || 0) / 20)); });
  const toShip = (state.customer_orders || []).filter((order) => order.status === "ouverte" || order.status === "en retard").length;
  visuals.shipping.forEach((pallet, index) => { pallet.visible = index < Math.min(4, toShip); });
  for (const line of state.production_lines || []) {
    const machines = visuals.lines.get(line.id) || [];
    const busy = (state.production_orders || []).some((order) => order.sku === line.product_sku);
    line.machines.forEach((machine, index) => {
      const lights = machines[index]?.userData.lights;
      if (!lights) return;
      const color = !line.operational ? (machine.state === "panne" ? "rouge" : "orange") : busy ? "vert" : "orange";
      for (const [name, mesh] of Object.entries(lights)) mesh.material.emissiveIntensity = name === color ? 1.6 : 0.08;
    });
  }
}

function buildFlowBar() {
  const nav = $("#factory-flow");
  nav.innerHTML = [...FLOW.map((step) => ({ ...step, kind: "flow" })), ...SUPPORT.filter((step) => step.zone !== "bureau_etude").map((step) => ({ ...step, kind: "support" }))]
    .map((step) => `<button type="button" data-zone="${step.zone}" class="flow-step ${step.kind === "support" ? "flow-support" : ""} ${step.zone.startsWith("stock_") ? "flow-stock" : ""}">${step.label}</button>`).join("");
  nav.querySelectorAll(".flow-step").forEach((button) => button.addEventListener("click", () => {
    nav.querySelectorAll(".flow-step").forEach((step) => step.classList.toggle("active", step === button));
    const zone = ZONES[button.dataset.zone];
    selectInteraction({ type: "block", zone: button.dataset.zone, title: zone.title || blockName(zone.block) });
    tablet?.open(button.dataset.zone, { department: DEPARTMENT_BY_ZONE[button.dataset.zone] });
  }));
}

// ------------------------------------------------------------ déplacements
function keyFor(x, z) { return `${x},${z}`; }
function walkable(x, z) {
  if (x < WALK_BOUNDS.x1 || x > WALK_BOUNDS.x2 || z < WALK_BOUNDS.z1 || z > WALK_BOUNDS.z2) return false;
  return !obstacles.some((item) => Math.abs(x - item.x) < item.width / 2 + 0.38 && Math.abs(z - item.z) < item.depth / 2 + 0.38);
}
function nearestWalkable(x, z) {
  const cx = Math.round(x), cz = Math.round(z);
  for (let radius = 0; radius <= 5; radius++) {
    for (let dx = -radius; dx <= radius; dx++) for (let dz = -radius; dz <= radius; dz++) {
      if (Math.abs(dx) !== radius && Math.abs(dz) !== radius) continue;
      if (walkable(cx + dx, cz + dz)) return [cx + dx, cz + dz];
    }
  }
  return [cx, cz];
}
function findPath(start, end) {
  const [sx, sz] = nearestWalkable(start.x, start.z);
  const [ex, ez] = nearestWalkable(end.x, end.z);
  const startKey = keyFor(sx, sz), endKey = keyFor(ex, ez);
  const queue = [startKey];
  const cameFrom = new Map([[startKey, ""]]);
  for (let head = 0; head < queue.length && head < 6000; head++) {
    const current = queue[head];
    if (current === endKey) break;
    const [cx, cz] = current.split(",").map(Number);
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nextKey = keyFor(cx + dx, cz + dz);
      if (cameFrom.has(nextKey) || !walkable(cx + dx, cz + dz)) continue;
      cameFrom.set(nextKey, current);
      queue.push(nextKey);
    }
  }
  if (!cameFrom.has(endKey)) return [];
  const path = [];
  for (let key = endKey; key && key !== startKey; key = cameFrom.get(key)) {
    const [x, z] = key.split(",").map(Number);
    path.unshift(new THREE.Vector3(x, 0, z));
  }
  return path;
}
function animateLimbs(actor, delta, speed) {
  actor.userData.walkPhase = (actor.userData.walkPhase || 0) + delta * speed * 5.2;
  const swing = Math.sin(actor.userData.walkPhase) * 0.42;
  actor.userData.legs?.forEach((leg, index) => { leg.rotation.x = swing * (index === 0 ? 1 : -1); });
  actor.userData.arms?.forEach((arm, index) => { if (!(actor.userData.fixedArm && index === 1)) arm.rotation.x = swing * (index === 0 ? -1 : 1); });
}
function updateActor(actor, delta, speed) {
  const route = actor.userData.route || [];
  if (!route.length) return false;
  const direction = route[0].clone().sub(actor.position);
  direction.y = 0;
  if (direction.length() < 0.14) { route.shift(); return route.length > 0; }
  direction.normalize();
  actor.position.addScaledVector(direction, speed * delta);
  actor.rotation.y = Math.atan2(direction.x, direction.z);
  animateLimbs(actor, delta, speed);
  return true;
}
function setDestination(point) {
  const destination = new THREE.Vector3(point.x, 0, point.z);
  playerPath = findPath(player.position, destination);
  player.userData.route = playerPath;
  marker.position.set(destination.x, 0.035, destination.z);
  marker.visible = true;
  advanceTutorial("move");
}
function updateForklift(delta) {
  if (!forklift) return;
  const patrol = forklift.userData.patrol;
  const zone = ZONES[patrol.zone];
  const [tx, tz] = toWorld(zone, ...patrol.points[patrol.index]);
  const target = new THREE.Vector3(tx, 0, tz);
  const direction = target.sub(forklift.position).setY(0);
  if (direction.length() < 0.1) { patrol.index = (patrol.index + 1) % patrol.points.length; return; }
  direction.normalize();
  forklift.position.addScaledVector(direction, 1.4 * delta);
  forklift.rotation.y = Math.atan2(-direction.z, direction.x);
}

// ------------------------------------------------------------ interactions
function cameraPosition(delta = 1) {
  const target = player.position.clone().add(new THREE.Vector3(0, vueHaute ? 0.8 : 1.5, 0));
  const voulue = new THREE.Vector3();
  if (vueHaute) voulue.set(target.x + Math.sin(cameraYaw) * cameraDistance * 0.62, target.y + cameraDistance * 0.8, target.z + Math.cos(cameraYaw) * cameraDistance * 0.62);
  else {
    const cap = player.rotation.y, yaw = cap + Math.PI + orbite;
    voulue.set(target.x + Math.sin(yaw) * distance3p * 0.86, target.y + distance3p * 0.48, target.z + Math.cos(yaw) * distance3p * 0.86);
    target.x += Math.sin(cap) * 2; target.z += Math.cos(cap) * 2; // on regarde un peu devant le joueur
  }
  const k = 1 - Math.exp(-delta * 6);
  camPos.lerp(voulue, k);
  camCible.lerp(target, k);
  camera.position.copy(camPos);
  camera.lookAt(camCible);
}
function basculerVue(haute = !vueHaute) {
  vueHaute = haute;
  cameraDistance = CAMERA_HOME.distance; cameraYaw = CAMERA_HOME.yaw; orbite = 0;
  showToast(vueHaute ? "Vue d’ensemble (touche 3 pour revenir derrière le joueur)." : "Vue joueur : Z/S pour avancer, Q/D pour tourner.");
}
// Les étiquettes n'apparaissent que près du joueur : l'usine reste lisible.
let etiquettes = [], prochainTriEtiquettes = 0;
function majEtiquettes(delta) {
  prochainTriEtiquettes -= delta;
  if (prochainTriEtiquettes <= 0) {
    etiquettes = [];
    world.traverse((o) => { if (o.isSprite) etiquettes.push(o); });
    prochainTriEtiquettes = 1;
  }
  const p = player.position, w = new THREE.Vector3(), dJoueur = camera.position.distanceTo(p);
  for (const s of etiquettes) {
    s.getWorldPosition(w);
    // Vue joueur : étiquettes proches seulement, et jamais entre la caméra et le joueur.
    const proche = vueHaute || (s.parent !== player && w.distanceTo(p) < 10 && w.distanceTo(camera.position) > dJoueur + 1);
    s.material.opacity += ((proche ? 1 : 0) - s.material.opacity) * Math.min(1, delta * 8);
  }
}
function findInteraction(object) {
  let current = object;
  while (current && !current.userData.interaction) current = current.parent;
  return current?.userData.interaction && current.userData.interaction.type !== "none" ? { group: current, info: current.userData.interaction } : null;
}

function blockDetails(zoneId) {
  const zone = ZONES[zoneId];
  const report = state?.last_week || {};
  const lines = state?.production_lines || [];
  switch (zoneId) {
    case "quai_dechargement": {
      const next = (state?.purchase_orders || []).filter((order) => order.arrival_week <= (state?.current_week || 0) + 1);
      return `Cette semaine : ${report.received_orders || 0} camion(s) fournisseur déchargé(s). ${next.length ? `${next.length} livraison(s) attendue(s) la semaine prochaine.` : "Aucune livraison attendue la semaine prochaine."}`;
    }
    case "bureau_reception":
      return `Réceptionné : ${fmt(report.received_units)} unité(s) · en quarantaine : ${fmt(report.quarantined)}.`;
    case "stock_mp": case "stock_sf": case "stock_pf":
      return stocksOf(zone.part, ...(zone.part === "MP" ? [] : [])).map((item) => `${item.name} ${fmt(item.quantity)} (pt cde ${fmt(item.reorder_point)}, cap. ${fmt(item.capacity_max)})`).join(" · ");
    case "chaine_production":
      return `${lines.map((line) => `${line.name} : ${line.operational ? `${fmt(line.efficiency)} %` : "EN PANNE"}`).join(" · ")}. OF en cours : ${(state?.production_orders || []).length}. Semi-finis faits : ${fmt(report.semi_finished)}.`;
    case "controle_qualite":
      return `Conformes : ${fmt(report.produced)} · retouchés : ${fmt(report.reworked)} · rebut : ${fmt(report.quality_losses)} · qualité ${fmt(state?.kpis?.quality_rate, 1)} %.`;
    case "emballage":
      return `Emballés : ${fmt(report.packed)} produit(s), ${fmt(report.pallets)} palette(s) filmée(s). En attente : ${fmt(Object.values(state?.packing_queue || {}).reduce((a, b) => a + b, 0))}.`;
    case "logistique_transport": {
      const open = (state?.customer_orders || []).filter((order) => order.status === "ouverte" || order.status === "en retard");
      return `Expédiés : ${fmt(report.delivered)} · commandes à servir : ${open.length} (dont ${open.filter((order) => order.status === "en retard").length} en retard) · OTIF ${fmt(state?.kpis?.otif, 1)} %.`;
    }
    case "bureau_etude": {
      const line = lines[0];
      return line ? `Gamme : ${line.machines.map((machine) => `${machine.id.split("-")[1]} ${machine.operation} ${fmt(machine.cycle_minutes, 1)} min`).join(" → ")}. Passage au stock SF après M${line.semi_finished_after}. Nomenclature : 1 composant + 1 carton par colis.` : "";
    }
    case "maintenance_pdr":
      return `Pièces de rechange : ${spareCount()}. Lignes en panne : ${lines.filter((line) => !line.operational).map((line) => line.name).join(", ") || "aucune"}. Interventions prévues : ${(state?.maintenance_queue || []).length}.`;
    default:
      return "";
  }
}

const BLOCK_ACTIONS = {
  quai_dechargement: ["Voir les achats en cours (tablette) →", "achats"],
  bureau_reception: ["Voir les achats en cours (tablette) →", "achats"],
  stock_mp: ["Acheter de la MP (tablette) →", "achats"],
  stock_sf: ["Voir les stocks (tablette) →", "stocks"],
  stock_pf: ["Lancer un OF (tablette) →", "of"],
  chaine_production: ["Lancer un OF (tablette) →", "of"],
  controle_qualite: ["Voir les OF (tablette) →", "of"],
  emballage: ["Voir les stocks (tablette) →", "stocks"],
  logistique_transport: ["Commandes clients (tablette) →", "clients"],
  bureau_etude: ["Lancer un OF (tablette) →", "of"],
  maintenance_pdr: ["Stocks et pannes (tablette) →", "stocks"],
};

function selectInteraction(info) {
  currentSelection = info;
  $("#inspector-title").textContent = info.title || "Sélection";
  $("#inspector-subtitle").textContent = { block: "Bloc", stock: "Référence du stock", line: "Ligne de production", worker: info.roleLabel || "Agent", player: "Joueur", truck: "Camion", asset: "Asset", forklift: "Engin" }[info.type] || "";
  $("#inspector").classList.remove("closed");
  const copy = $("#inspector-copy");
  const action = $("#inspector-action");
  action.hidden = true;
  if (info.type === "block") {
    const zone = ZONES[info.zone];
    const blockId = zone.block;
    const people = agentsIn(blockId).map((agent) => `${agent.name === agent.role_label.split(" ")[0] ? "" : `${agent.name}, `}${agent.role_label.toLowerCase()}`).join(" ; ");
    copy.textContent = `${info.title}. ${BLOCK_ROLES[blockId] || ""} Agents : ${people || "—"}. ${blockDetails(info.zone)}`;
    const [label, tab] = BLOCK_ACTIONS[info.zone] || [];
    if (label) { action.textContent = label; action.hidden = false; action.onclick = () => tablet.open(tab); }
  } else if (info.type === "stock") {
    const item = stockBySku(info.sku);
    copy.textContent = item ? `${item.name} · ${item.sku}. ${fmt(item.quantity)} ${item.unit}(s) · stock initial ${fmt(item.initial)} · minimum ${fmt(item.minimum)} · point de commande ${fmt(item.reorder_point)} · quantité commandée ${fmt(item.reorder_qty)} · capacité ${fmt(item.capacity_max)}.` : info.title;
    if (item?.category === "MP") { action.textContent = "Comparer les fournisseurs (tablette) →"; action.hidden = false; action.onclick = () => tablet.open("comparateur", { sku: item.sku, quantity: item.reorder_qty }); }
    if (item?.category === "PF") { action.textContent = "Lancer un OF (tablette) →"; action.hidden = false; action.onclick = () => tablet.open("of", { product: item.sku }); }
  } else if (info.type === "line") {
    const line = state?.production_lines?.find((item) => item.id === info.lineId);
    copy.textContent = line ? `${line.name} fabrique ${stockBySku(line.product_sku)?.name || line.product_sku} · ${line.operational ? `efficacité ${line.efficiency} %` : "en panne"}. ${line.machines.map((machine) => `${machine.id} ${machine.operation} ${machine.cycle_minutes} min (${machine.state})`).join(" → ")}. Voyant vert : en production · orange : à l’arrêt · rouge : panne.` : info.title;
    if (line && !line.operational) {
      action.textContent = spareCount() > 0 ? "Planifier l’intervention (tablette) →" : "Commander une pièce de rechange →";
      action.hidden = false;
      action.onclick = () => spareCount() > 0 ? tablet.open("maintenance_pdr") : tablet.open("achats", { sku: "MAT-PDR" });
    }
  } else if (info.type === "worker") {
    copy.textContent = `${info.title} · ${info.subtitle}. Approchez-vous et appuyez sur E pour lui parler.`;
    action.textContent = `Parler avec ${info.title} →`;
    action.hidden = false;
    action.onclick = () => openNpcDialog(info);
  } else if (info.type === "player") {
    copy.textContent = `${info.subtitle} Commandes clients, achats de MP et lancement des OF.`;
    action.textContent = "Ouvrir la tablette →";
    action.hidden = false;
    action.onclick = () => tablet.open();
  } else if (info.type === "truck") {
    copy.textContent = info.kind === "fournisseur" ? `Camion fournisseur · ${info.title}. Il décharge au quai de déchargement puis repart.` : info.kind === "client" ? `Camion du client ${info.title}, venu charger au quai d’expédition.` : "Notre camion de livraison : il part livrer les clients depuis le quai d’expédition.";
  } else if (info.type === "forklift") {
    copy.textContent = "Chariot élévateur du magasinier-cariste : il range les palettes et sort la matière dans l’ordre d’arrivée.";
  } else {
    copy.textContent = `${info.title}${info.subtitle ? ` · ${info.subtitle}` : ""}.`;
  }
  advanceTutorial("inspect");
}

function openNpcDialog(info) {
  const report = state?.last_week || {};
  const lowMp = stocksOf("MP").filter((item) => item.quantity <= item.reorder_point);
  const lowPf = stocksOf("PF").filter((item) => item.quantity < item.minimum);
  const down = (state?.production_lines || []).filter((line) => !line.operational);
  const openOrders = (state?.customer_orders || []).filter((order) => order.status === "ouverte" || order.status === "en retard");
  const talk = {
    chauffeur_fournisseur: [["Qu’apportes-tu ?", "Les palettes de MP commandées, avec le bon de livraison. Je repars dès que le camion est vide."], ["Et si le quai est occupé ?", "J’attends mon tour : il n’y a qu’un quai de déchargement."]],
    receptionnaire: [["Comment s’est passée la réception ?", `${fmt(report.received_units)} unité(s) entrées en stock, ${fmt(report.quarantined)} mise(s) en quarantaine.`], ["Que fais-tu d’une palette ?", "Je compare au bon de livraison, je l’enregistre et je l’étiquette. Si elle n’est pas conforme, elle part en quarantaine."]],
    magasinier_cariste: [["Un stock est-il bas ?", lowMp.length ? `${lowMp.map((item) => `${item.name} (${fmt(item.quantity)})`).join(", ")} sous le point de commande. Passe par ta tablette pour commander.` : "Toutes les MP sont au-dessus du point de commande."], ["Comment sors-tu la matière ?", "Dans l’ordre d’arrivée. Je prépare un kit par OF et je suis les trois stocks : MP, semi-finis et PF."]],
    chef_de_ligne: [["Où en est la production ?", `${(state?.production_orders || []).length} OF en cours. ${down.length ? `${down.map((line) => line.name).join(", ")} en panne.` : "Les quatre lignes tournent."}`], ["Qui fixe la cadence ?", "La machine la plus lente de la ligne : M3, la finition. Les autres l’attendent."]],
    operateur_machine: [["Que fais-tu ?", "Je charge la matière, je fais tourner ma machine et je signale les pannes au chef de ligne."], ["Et après M2 ?", "Les pièces passent par le stock de semi-finis avant la finition."]],
    controleur_qualite: [["Combien de pièces conformes ?", `${fmt(report.produced)} conformes, ${fmt(report.reworked)} à retoucher, ${fmt(report.quality_losses)} au rebut.`], ["Comment tries-tu ?", "Zone verte : conforme. Zone orange : à retoucher. Bac rouge : rebut."]],
    emballeur: [["Combien de palettes ?", `${fmt(report.pallets)} palette(s) filmée(s) cette semaine, soit ${fmt(report.packed)} produits.`], ["Ton travail ?", "Mettre en carton, étiqueter et peser, monter et filmer la palette, puis l’envoyer au stock PF."]],
    responsable_production: [["Que définis-tu ici ?", "Les gammes, les nomenclatures et les temps : M1 2 min, M2 1,5 min, M3 3 min, M4 1 min."], ["Qui lance les OF ?", "Toi, depuis ta tablette. Moi, je fournis les méthodes au chef de ligne."]],
    technicien_maintenance: [["Une ligne est en panne ?", down.length ? `${down.map((line) => line.name).join(", ")} attend une intervention. Planifie-la depuis la tablette.` : "Toutes les lignes tournent."], ["Combien de pièces de rechange ?", `${spareCount()} en stock PDR. Une réparation en consomme une.`]],
    magasinier_logistique: [["Que reste-t-il à expédier ?", `${openOrders.length} commande(s) client à servir. ${lowPf.length ? `Stock PF bas : ${lowPf.map((item) => item.name).join(", ")}.` : ""}`], ["Comment partent les produits ?", "Soit avec nos camions de livraison, soit le client vient charger au quai d’expédition."]],
    chauffeur_livreur: [["Tu livres combien ?", `${fmt(report.delivered)} produits expédiés cette semaine.`], ["Combien de camions ?", "Trois camions de 600 produits chacun."]],
    chauffeur_client: [["Tu viens chercher quoi ?", "Ma commande, préparée par la logistique. Je charge au quai d’expédition et je repars."], ["Et si elle n’est pas prête ?", "Je repars sans, et la commande passe en retard."]],
  };
  const topics = talk[info.role] || talk.receptionnaire;
  $("#npc-name").textContent = info.title;
  $("#npc-role").textContent = info.roleLabel || info.subtitle || "";
  $("#npc-dialogue").textContent = `${info.title} : Bonjour ! Que veux-tu savoir ?`;
  ["#npc-question-one", "#npc-question-two"].forEach((selector, index) => {
    const button = $(selector);
    button.textContent = topics[index][0];
    button.onclick = () => { $("#npc-dialogue").textContent = `${info.title} : ${topics[index][1]}`; };
  });
  $("#npc-modal").hidden = false;
}

function showToast(message, isError = false) {
  const el = $("#toast");
  el.textContent = message;
  el.className = `visible${isError ? " error" : ""}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.className = ""; }, 3200);
}

function updateHUD(newState) {
  state = newState;
  $("#company-name").textContent = state.company_name || "L’atelier";
  $("#week").textContent = `SEMAINE ${String(state.current_week).padStart(2, "0")}`;
  const service = tabletSnapshot?.globalKpis?.find((metric) => metric.id === "otif");
  $("#otif").textContent = service ? (service.value == null ? "—" : Number(service.value).toFixed(1).replace(".", ",")) : "—";
  $("#trs").textContent = Number(state.kpis.trs).toFixed(1).replace(".", ",");
  $("#stock-value").textContent = fmt(state.kpis.stock_value);
  $("#quality").textContent = Number(state.kpis.quality_rate ?? 100).toFixed(1).replace(".", ",");
  $("#delivered").textContent = fmt(state.kpis.delivered || 0);
  const lowMaterial = stocksOf("MP", "PDR").find((item) => item.quantity <= item.reorder_point);
  const lowFinished = stocksOf("PF").find((item) => item.quantity < item.minimum);
  const late = (state.customer_orders || []).filter((order) => order.status === "en retard").length;
  $("#objective").textContent = late ? `${late} commande(s) client en retard. Lancez des OF et servez la logistique.`
    : lowFinished ? `${lowFinished.name} passe sous son stock minimum PF. Lancez un OF depuis la tablette.`
      : lowMaterial ? `${lowMaterial.name} est sous son point de commande. Commandez depuis la tablette.`
        : "Pilotez l’usine depuis votre tablette : achats de MP, OF et commandes clients.";
  $("#objective-status").textContent = state.alerts?.length ? `${state.alerts.length} alerte(s) stock · ${state.alerts[0]}` : "Aucune alerte de stock.";
  $("#event-summary").textContent = state.events?.length ? state.events.join(" · ") : "Marché stable cette semaine.";
  const busy = (state.agents || []).filter((agent) => agent.state === "occupé").length;
  $("#people-label").textContent = `${(state.agents || []).length} agents · ${busy} occupé(s)`;
  refreshWorld();
  tablet?.render();
  if (["stock", "line", "block"].includes(currentSelection?.type)) selectInteraction(currentSelection);
}

async function refreshState() {
  const response = await fetch("/api/v2/tablet");
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  tabletSnapshot = await response.json();
  savedState = tabletSnapshot.raw;
  updateHUD(tabletSnapshot.raw);
  syncPeriodTrucks();
  const nouveau = await chargerAmenagement();
  if (nouveau) appliquerAmenagement(nouveau);
  if (focusApresTablette && !tablet?.isOpen?.()) {
    const zone = ZONES[focusApresTablette];
    player.position.set(zone.x, 0, zone.z + zone.door * (zone.d / 2 + 1.6));
    playerPath = [];
    cameraDistance = Math.min(cameraDistance, 21);
    showToast(focusApresTablette === "chaine_production" ? "Les tampons sont en place dans l’atelier." : "Le stock a été réaménagé.");
    focusApresTablette = null;
  }
}

function syncPeriodTrucks() {
  const period = `${tabletSnapshot.gameId}:${tabletSnapshot.clock.period}`;
  if (lastTruckPeriod !== null && period !== lastTruckPeriod) {
    queueTrucks(tabletSnapshot.raw.trucks);
  }
  lastTruckPeriod = period;
}

function raycastFromPointer(event) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
}
function isShown(object) {
  for (let current = object; current; current = current.parent) if (!current.visible) return false;
  return true;
}
function swapLabel(sprite, text, color, bg) {
  sprite.material.map?.dispose();
  sprite.material.dispose();
  sprite.material = labelSprite(text, color, bg).material;
}
function onCanvasClick(event) {
  if (dragging || event.button !== 0) return;
  raycastFromPointer(event);
  const hits = raycaster.intersectObjects(interactables, true);
  for (const hit of hits) {
    if (!isShown(hit.object)) continue;
    const target = findInteraction(hit.object);
    if (!target) continue;
    selectInteraction(target.info);
    if (target.info.type === "worker") openNpcDialog(target.info);
    if (target.info.type === "block") { tablet?.open(target.info.zone, { department: DEPARTMENT_BY_ZONE[target.info.zone] }); return; }
    const closePoint = target.group.getWorldPosition(new THREE.Vector3());
    const approach = closePoint.add(player.position.clone().sub(closePoint).setY(0).normalize().multiplyScalar(1.8));
    setDestination(approach);
    return;
  }
  const point = new THREE.Vector3();
  if (raycaster.ray.intersectPlane(groundPlane, point)) setDestination(point);
}
function setupControls() {
  canvas.addEventListener("pointerdown", (event) => {
    if (event.button === 2 || event.button === 1) { dragging = true; lastPointer = { x: event.clientX, y: event.clientY }; canvas.setPointerCapture(event.pointerId); }
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!dragging) {
      raycastFromPointer(event);
      const hit = raycaster.intersectObjects(interactables, true).find((item) => isShown(item.object) && findInteraction(item.object));
      const target = hit ? findInteraction(hit.object) : null;
      if (target && target.info.type !== "block") {
        const point = target.group.getWorldPosition(new THREE.Vector3());
        hoverRing.position.set(point.x, 0.04, point.z);
        hoverRing.visible = true;
      } else hoverRing.visible = false;
      canvas.style.cursor = target ? "pointer" : "default";
      return;
    }
    if (vueHaute) cameraYaw -= (event.clientX - lastPointer.x) * 0.008;
    else orbite -= (event.clientX - lastPointer.x) * 0.008;
    lastPointer = { x: event.clientX, y: event.clientY };
  });
  canvas.addEventListener("pointerup", (event) => { if (dragging) { dragging = false; return; } onCanvasClick(event); });
  canvas.addEventListener("contextmenu", (event) => event.preventDefault());
  canvas.addEventListener("wheel", (event) => {
    if (vueHaute) cameraDistance = Math.max(10, Math.min(62, cameraDistance + Math.sign(event.deltaY) * 2));
    else distance3p = Math.max(5, Math.min(24, distance3p + Math.sign(event.deltaY)));
  }, { passive: true });
  window.addEventListener("keydown", (event) => {
    if (event.target.closest?.("input, select, textarea")) return;
    const key = event.key.toLowerCase();
    const move = TOUCHES_MOUVEMENT[event.code];
    if (move) { keys.add(move); if (move !== "shift") playerPath.length = 0; if (event.code.startsWith("Arrow")) event.preventDefault(); }
    if (key === "1" || key === "t") tablet.isOpen() ? tablet.close() : tablet.open();
    if (key === "2") $("#inspector").classList.remove("closed");
    if (key === "3") basculerVue();
    if (key === "escape") { tablet.close(); $("#npc-modal").hidden = true; }
    if (key === "e") interactNearest();
    if (key === "r" && roof) { roof.visible = !roof.visible; showToast(roof.visible ? "Toit affiché (R pour le masquer)." : "Toit masqué."); }
  });
  window.addEventListener("keyup", (event) => { if (TOUCHES_MOUVEMENT[event.code]) keys.delete(TOUCHES_MOUVEMENT[event.code]); });
  window.addEventListener("blur", () => keys.clear());
  window.addEventListener("resize", () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
  });
}
// Touches physiques : ZQSD sur clavier AZERTY, WASD sur QWERTY, et les flèches.
const TOUCHES_MOUVEMENT = { KeyW: "w", KeyA: "a", KeyS: "s", KeyD: "d", ArrowUp: "arrowup", ArrowDown: "arrowdown", ArrowLeft: "arrowleft", ArrowRight: "arrowright", ShiftLeft: "shift", ShiftRight: "shift" };
function moveByKeyboard(delta) {
  if (tablet?.isOpen()) return false;
  if (!vueHaute) {
    // Vue joueur : avancer/reculer dans l'axe du regard, tourner à gauche/droite.
    const avance = (keys.has("w") || keys.has("arrowup") ? 1 : 0) - (keys.has("s") || keys.has("arrowdown") ? 1 : 0);
    const tourne = (keys.has("a") || keys.has("arrowleft") ? 1 : 0) - (keys.has("d") || keys.has("arrowright") ? 1 : 0);
    if (!avance && !tourne) return false;
    advanceTutorial("move");
    player.rotation.y += tourne * 2.4 * delta;
    orbite *= Math.exp(-delta * 3);
    const speed = (keys.has("shift") ? 6.2 : 4.1) * (avance < 0 ? 0.55 : 1);
    const nextX = player.position.x + Math.sin(player.rotation.y) * avance * speed * delta;
    const nextZ = player.position.z + Math.cos(player.rotation.y) * avance * speed * delta;
    if (walkable(Math.round(nextX), Math.round(player.position.z))) player.position.x = nextX;
    if (walkable(Math.round(player.position.x), Math.round(nextZ))) player.position.z = nextZ;
    animateLimbs(player, delta, avance ? speed : 2);
    return true;
  }
  const forward = new THREE.Vector3();
  camera.getWorldDirection(forward);
  forward.y = 0;
  forward.normalize();
  const right = new THREE.Vector3(-forward.z, 0, forward.x);
  const direction = new THREE.Vector3();
  if (keys.has("w") || keys.has("arrowup")) direction.add(forward);
  if (keys.has("s") || keys.has("arrowdown")) direction.sub(forward);
  if (keys.has("d") || keys.has("arrowright")) direction.add(right);
  if (keys.has("a") || keys.has("arrowleft")) direction.sub(right);
  if (direction.lengthSq() === 0) return false;
  advanceTutorial("move");
  direction.normalize();
  const speed = keys.has("shift") ? 6.2 : 4.1;
  const step = direction.multiplyScalar(speed * delta);
  const nextX = player.position.x + step.x, nextZ = player.position.z + step.z;
  if (walkable(Math.round(nextX), Math.round(player.position.z))) player.position.x = nextX;
  if (walkable(Math.round(player.position.x), Math.round(nextZ))) player.position.z = nextZ;
  player.rotation.y = Math.atan2(step.x, step.z);
  animateLimbs(player, delta, speed);
  return true;
}
function interactNearest() {
  let closest = null;
  let closestDistance = 3.2;
  for (const group of interactables) {
    const info = group.userData.interaction;
    if (!info || ["none", "block", "player"].includes(info.type)) continue;
    const distance = player.position.distanceTo(group.getWorldPosition(new THREE.Vector3()));
    if (distance < closestDistance) { closest = info; closestDistance = distance; }
  }
  if (closest) { selectInteraction(closest); if (closest.type === "worker") openNpcDialog(closest); }
  else showToast("Approchez-vous d’un agent, d’une machine ou d’un équipement.");
}

// ------------------------------------------------------------------ tutoriel
function renderTutorial() {
  const step = tutorialSteps[tutorialIndex];
  if (!step) { $("#tutorial").hidden = true; return; }
  $("#tutorial-count").textContent = `ÉTAPE ${tutorialIndex + 1} / ${tutorialSteps.length}`;
  $("#tutorial-title").textContent = step.title;
  $("#tutorial-copy").textContent = step.copy;
  $("#tutorial-next").textContent = tutorialIndex === tutorialSteps.length - 1 ? "Terminer" : "Compris →";
}
function beginTutorial() { tutorialIndex = 0; $("#tutorial").hidden = false; renderTutorial(); }
function advanceTutorial(action, force = false) {
  if ($("#tutorial").hidden) return;
  if (!force && tutorialSteps[tutorialIndex]?.action !== action) return;
  tutorialIndex++;
  renderTutorial();
}

// ------------------------------------------------------------------- partie
function addSupplierRow() {
  const list = $("#custom-supplier-list");
  if (list.children.length >= 20) return;
  const row = document.createElement("div");
  row.className = "supplier-entry";
  row.innerHTML = '<input data-field="name" aria-label="Nom du fournisseur" placeholder="Nom" maxlength="40" required><input data-field="lead_time_weeks" aria-label="Délai en semaines" title="Délai en semaines" type="number" min="1" max="8" value="2" required><input data-field="reliability" aria-label="Fiabilité en pourcentage" title="Fiabilité en pourcentage" type="number" min="0" max="100" value="92" required><input data-field="unit_cost" aria-label="Prix unitaire en euros pour toutes les MP" title="Prix unitaire (€) pour toutes les MP" type="number" min="0" step="0.01" value="3" required><button class="remove-supplier" type="button" aria-label="Supprimer ce fournisseur">×</button>';
  row.querySelector(".remove-supplier").addEventListener("click", () => row.remove());
  list.append(row);
}
async function loadState() {
  try {
    const response = await fetch("/api/v2/tablet");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    tabletSnapshot = await response.json();
    savedState = tabletSnapshot.raw;
    lastTruckPeriod = `${tabletSnapshot.gameId}:${tabletSnapshot.clock.period}`;
    state = savedState;
    if (savedState.started) {
      $("#company-input").value = savedState.company_name || "G-mix";
      $("#resume-game").hidden = false;
      $("#setup-note").textContent = `Sauvegarde disponible · semaine ${savedState.current_week}. Une nouvelle partie l’écrasera.`;
    }
  } catch (error) {
    showToast(`API indisponible : ${error.message}`, true);
  }
}
async function createNewGame(event) {
  event.preventDefault();
  if (savedState?.started && !window.confirm("Créer une nouvelle partie remplacera la sauvegarde actuelle. Continuer ?")) return;
  const button = $("#start-new-game");
  button.disabled = true;
  try {
    const response = await fetch("/api/v2/tablet/new-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: $("#company-input").value.trim(),
        difficulty: $("#difficulty-input").value,
        rules_confirmed: $("#rules-confirmed").checked,
        additional_suppliers: [...$("#custom-supplier-list").querySelectorAll(".supplier-entry")].map((row) => ({
          name: row.querySelector('[data-field="name"]').value.trim(),
          lead_time_weeks: Number(row.querySelector('[data-field="lead_time_weeks"]').value),
          reliability: Number(row.querySelector('[data-field="reliability"]').value),
          unit_cost: Number(row.querySelector('[data-field="unit_cost"]').value),
        })),
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail?.[0]?.msg || result.detail || `HTTP ${response.status}`);
    tabletSnapshot = result;
    lastTruckPeriod = `${result.gameId}:${result.clock.period}`;
    savedState = result.raw;
    updateHUD(result.raw);
    $("#setup-screen").hidden = true;
    if ($("#tutorial-enabled").checked) beginTutorial();
    tablet?.open();
  } catch (error) {
    $("#setup-note").textContent = `Impossible de créer la partie : ${error.message}`;
  } finally {
    button.disabled = false;
  }
}
function resumeGame() {
  if (!savedState?.started) return;
  updateHUD(savedState);
  $("#setup-screen").hidden = true;
  if ($("#tutorial-enabled").checked) beginTutorial();
}
async function nextWeek() {
  const button = $("#next-turn");
  button.disabled = true;
  try {
    const response = await fetch("/api/v2/tablet/next-turn", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    tabletSnapshot = result;
    const nextState = result.raw;
    updateHUD(nextState);
    syncPeriodTrucks();
    const r = nextState.last_week || {};
    showToast(`Semaine ${nextState.current_week} · reçu ${fmt(r.received_units)} · fabriqué ${fmt(r.produced)} · emballé ${fmt(r.packed)} · expédié ${fmt(r.delivered)} · ${fmt(r.customer_orders_late)} commande(s) en retard.`);
    advanceTutorial("week");
  } catch (error) {
    showToast(`Impossible de simuler la semaine : ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

let tablet = null;
// Pour le débogage depuis la console du navigateur.
window.gmixDebug = {
  voir: (zoneId, distance = 22, yaw = 0.35) => { const z = ZONES[zoneId]; player.position.set(z.x, 0, z.z + z.door * 1.5); playerPath = []; vueHaute = true; cameraDistance = distance; cameraYaw = yaw; },
  trucks: () => truckActors.map((truck) => ({ kind: truck.userData.actor.kind, phase: truck.userData.actor.phase, mode: truck.userData.actor.mode, x: Math.round(truck.position.x * 10) / 10 })),
  queues: () => Object.fromEntries(Object.entries(dockQueues).map(([kind, queue]) => [kind, queue.length])),
};

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.04);
  const keyboardMoving = moveByKeyboard(delta);
  if (!keyboardMoving && playerPath.length) updateActor(player, delta, 3.7);
  if (!keyboardMoving && !playerPath.length) {
    player.userData.legs.forEach((limb) => { limb.rotation.x *= 0.82; });
    player.userData.arms[0].rotation.x *= 0.82;
    marker.visible = false;
  }
  for (const worker of workers) {
    if (!worker.userData.route.length) {
      const points = worker.userData.targets;
      worker.userData.route = findPath(worker.position, points[worker.userData.targetIndex % points.length]);
      worker.userData.targetIndex++;
    }
    if (!updateActor(worker, delta, 1.1)) worker.rotation.y += delta * 0.4;
  }
  updateForklift(delta);
  updateTrucks(delta);
  animerAmenagement(delta);
  majEtiquettes(delta);
  cameraPosition(delta);
  renderer.render(scene, camera);
}

async function startGame() {
  await loadState();
  amenagement = (await chargerAmenagement()) || amenagement;
  window.addEventListener("message", (event) => {
    if (event.origin !== window.location.origin || event.data?.type !== "GMIX_LAYOUT_CHANGED") return;
    const avant = JSON.stringify(amenagement.stock);
    appliquerAmenagement(event.data.layout);
    focusApresTablette = JSON.stringify(amenagement.stock) !== avant ? "stock_mp" : "chaine_production";
  });
  tablet = createTablet({ getState: () => state, refreshState, toast: showToast, onAction: advanceTutorial });
  buildWorld();
  setupControls();
  $("#next-turn").addEventListener("click", nextWeek);
  $("#tablet-open").addEventListener("click", () => tablet.open());
  $("#inspect-open").addEventListener("click", () => $("#inspector").classList.toggle("closed"));
  $("#home-camera").addEventListener("click", () => basculerVue());
  $("#close-inspector").addEventListener("click", () => $("#inspector").classList.add("closed"));
  $("#npc-close").addEventListener("click", () => { $("#npc-modal").hidden = true; });
  $("#npc-modal").addEventListener("pointerdown", (event) => { if (event.target.id === "npc-modal") event.currentTarget.hidden = true; });
  $("#setup-form").addEventListener("submit", createNewGame);
  $("#resume-game").addEventListener("click", resumeGame);
  $("#add-supplier").addEventListener("click", addSupplierRow);
  $("#tutorial-next").addEventListener("click", () => advanceTutorial("", true));
  $("#tutorial-skip").addEventListener("click", () => { $("#tutorial").hidden = true; });
  if (state) updateHUD(state);
  cameraPosition();
  animate();
  setTimeout(() => loading.classList.add("hidden"), 700);
}

startGame().catch((error) => {
  console.error(error);
  loading.innerHTML = `<div class="loading-mark">!</div><b>Le monde 3D n’a pas pu démarrer.</b><span>${String(error.message).replace(/[<>&]/g, "")}</span>`;
});
