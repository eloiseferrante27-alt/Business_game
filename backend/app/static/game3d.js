import * as THREE from "./three.module.js";

const $ = (selector) => document.querySelector(selector);
const canvas = $("#world");
const loading = $("#loading");
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xcbd9d1);
scene.fog = new THREE.Fog(0xcbd9d1, 32, 78);

const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.1, 130);
let cameraYaw = 0.48;
let cameraDistance = 23;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: false });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

scene.add(new THREE.HemisphereLight(0xe5f3ef, 0x52635b, 1.25));
const sun = new THREE.DirectionalLight(0xffedcf, 2.65);
sun.position.set(-13, 24, 11);
sun.castShadow = true;
sun.shadow.mapSize.set(3072, 3072);
sun.shadow.camera.left = -25;
sun.shadow.camera.right = 25;
sun.shadow.camera.top = 25;
sun.shadow.camera.bottom = -25;
sun.shadow.bias = -0.00015;
sun.shadow.normalBias = 0.025;
sun.shadow.radius = 3;
scene.add(sun);

const world = new THREE.Group();
scene.add(world);
const obstacles = [];
const interactables = [];
const workers = [];
const products = new Map();
const raycaster = new THREE.Raycaster();
const pointer = new THREE.Vector2();
const groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0.02);
const clock = new THREE.Clock();
const keys = new Set();
const player = makePerson("Vous", 0x557c59, true);
player.position.set(0, 0, 1.5);
world.add(player);
const marker = new THREE.Mesh(
  new THREE.TorusGeometry(0.48, 0.035, 8, 36),
  new THREE.MeshBasicMaterial({ color: 0xd8f18a, transparent: true, opacity: 0.9 }),
);
marker.rotation.x = Math.PI / 2;
marker.position.y = 0.035;
marker.visible = false;
world.add(marker);
const hoverRing = new THREE.Mesh(new THREE.TorusGeometry(0.58, 0.025, 8, 40), new THREE.MeshBasicMaterial({ color: 0xd9ef83, transparent: true, opacity: 0.78 }));
hoverRing.rotation.x = Math.PI / 2;
hoverRing.position.y = 0.04;
hoverRing.visible = false;
world.add(hoverRing);

let state = null;
let savedState = null;
let tutorialIndex = 0;
const tutorialSteps = [
  { action: "move", title: "Déplace-toi dans l’atelier", copy: "Utilise W, A, S, D ou clique sur le sol pour guider ton personnage." },
  { action: "inspect", title: "Inspecte les opérations", copy: "Clique sur une étagère, une machine ou un ouvrier pour consulter ses informations." },
  { action: "order", title: "Commande la matière première", copy: "Ouvre Commande avec le bouton + ou la touche 1, choisis une matière, un fournisseur et la quantité." },
  { action: "production", title: "Planifie un OF", copy: "Ouvre Ordre fab. avec la touche 4, choisis le produit, le volume et le nombre de lignes." },
  { action: "week", title: "Fais avancer la simulation", copy: "Clique sur Lancer la semaine pour recevoir les commandes échues, exécuter les OF et livrer les clients." },
];
let playerPath = [];
let dragging = false;
let lastPointer = { x: 0, y: 0 };
let currentSelection = null;
let toastTimer = 0;
const npcSessions = new Map();
let activeNpcSession = null;
const helpbotHistory = [];

function makeGrainTexture(base, kind, size = 128) {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = `#${base.toString(16).padStart(6, "0")}`;
  ctx.fillRect(0, 0, size, size);
  for (let i = 0; i < size * size * 0.12; i++) {
    const v = Math.floor(105 + Math.random() * 100);
    ctx.fillStyle = `rgba(${v},${v},${v},${Math.random() * 0.10})`;
    ctx.fillRect(Math.random() * size, Math.random() * size, 1 + Math.random() * 2, 1 + Math.random() * 2);
  }
  if (kind === "concrete") {
    for (let i = 0; i < 180; i++) {
      ctx.fillStyle = `rgba(56,62,58,${Math.random() * 0.09})`;
      ctx.beginPath(); ctx.arc(Math.random() * size, Math.random() * size, Math.random() * 2.4, 0, Math.PI * 2); ctx.fill();
    }
  } else if (kind === "cardboard") {
    ctx.strokeStyle = "rgba(85,57,30,.12)";
    for (let y = 8; y < size; y += 16) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(size, y + Math.random() * 3); ctx.stroke(); }
  }
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  return tex;
}

const textures = {
  concrete: makeGrainTexture(0xb5b8ae, "concrete"),
  cardboard: makeGrainTexture(0xb58958, "cardboard"),
  steel: makeGrainTexture(0x63736e, "steel"),
};

function material(color, roughness = 0.8, metalness = 0, texture = null) {
  const map = texture ? textures[texture] : null;
  if (map) map.repeat.set(texture === "concrete" ? 7 : 1.2, texture === "concrete" ? 5 : 1.2);
  return new THREE.MeshStandardMaterial({ color, map, roughness, metalness });
}

function box(parent, width, height, depth, color, x, y, z, options = {}) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), material(color, options.roughness ?? 0.82, options.metalness ?? 0, options.texture ?? null));
  mesh.position.set(x, y, z);
  mesh.castShadow = options.castShadow !== false;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function cylinder(parent, radiusTop, radiusBottom, height, color, x, y, z, segments = 12) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(radiusTop, radiusBottom, height, segments), material(color));
  mesh.position.set(x, y, z);
  mesh.castShadow = true;
  mesh.receiveShadow = true;
  parent.add(mesh);
  return mesh;
}

function labelSprite(text, color = "#fff9dc", bg = "#183a36") {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 128;
  const context = canvas.getContext("2d");
  context.fillStyle = bg;
  context.beginPath();
  context.roundRect(8, 10, 496, 108, 24);
  context.fill();
  context.fillStyle = color;
  context.font = "600 42px Arial";
  context.textAlign = "center";
  context.textBaseline = "middle";
  context.fillText(text, 256, 64, 460);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, transparent: true, depthWrite: false }));
  sprite.scale.set(2.45, 0.61, 1);
  return sprite;
}

function addObstacle(x, z, width, depth) {
  obstacles.push({ x, z, width, depth });
}

function addClickable(group, info) {
  group.userData.interaction = info;
  interactables.push(group);
}

function makeGround() {
  const grass = new THREE.Mesh(new THREE.PlaneGeometry(100, 75), material(0x9bad8e));
  grass.rotation.x = -Math.PI / 2;
  grass.position.y = -0.2;
  grass.receiveShadow = true;
  world.add(grass);

  const floor = new THREE.Mesh(new THREE.PlaneGeometry(58, 30), material(0xffffff, 0.93, 0, "concrete"));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = 0;
  floor.receiveShadow = true;
  world.add(floor);
  // Open sky above the factory: only low site boundaries and room walls remain.
  box(world, 58, 0.24, 0.24, 0x45665d, 0, 0.12, -15, { metalness: 0.1 });
  box(world, 58, 0.24, 0.24, 0x45665d, 0, 0.12, 15, { metalness: 0.1 });
  box(world, 0.24, 0.24, 30, 0x45665d, -29, 0.12, 0, { metalness: 0.1 });
  box(world, 0.24, 0.24, 30, 0x45665d, 29, 0.12, 0, { metalness: 0.1 });
  box(world, 58, 0.035, 0.12, 0xe5d9ae, 0, 0.02, 1.5, { castShadow: false });
  // Loading apron with marked supplier and client bays.
  const apron = new THREE.Mesh(new THREE.PlaneGeometry(58, 8), material(0xb6c3af));
  apron.rotation.x = -Math.PI / 2;
  apron.position.set(0, -0.035, 19);
  world.add(apron);
  for (let x = -26; x <= 26; x += 4) {
    box(world, 1.5, 0.018, 0.12, 0xe8cb77, x, 0.015, 15.2, { castShadow: false });
  }
  // Marked pedestrian aisle, crossings and loading zones make the open site read as a working factory yard.
  box(world, 58, 0.018, 1.35, 0x87958c, 0, 0.012, 1.65, { castShadow: false });
  for (let x = -28; x <= 28; x += 2.2) box(world, 1.05, 0.025, 0.07, 0xf2df9e, x, 0.025, 1.65, { castShadow: false });
  for (const [x, roomWidth] of [[-21.5, 5], [-16.4, 5], [-10.65, 6.5], [-0.3, 14], [9.7, 6], [16, 6.5], [23, 7]]) {
    const bollardOffset = Math.min(2.6, roomWidth * 0.44) / 2 + 0.32;
    for (let stripe = -2; stripe <= 2; stripe++) box(world, 0.16, 0.026, 0.78, stripe % 2 ? 0xe9ece0 : 0x4f7166, x + stripe * 0.35, 0.027, 0.65, { castShadow: false });
    for (const side of [-1, 1]) {
      const bollard = cylinder(world, 0.09, 0.11, 0.72, 0xd7a943, x + side * bollardOffset, 0.36, 1.2, 12);
      bollard.material.metalness = 0.28;
    }
  }
  for (let x = -26; x <= 26; x += 6.5) box(world, 0.025, 0.009, 30, 0x8d958a, x, 0.008, 0, { castShadow: false });
  box(world, 0.7, 0.018, 0.38, 0x52605a, -18.5, 0.018, 1.65, { castShadow: false });
  for (let x = -18.78; x <= -18.22; x += 0.12) box(world, 0.025, 0.022, 0.34, 0xaeb8ad, x, 0.03, 1.65, { castShadow: false });
}

function makeShelf(x, z, sku, productName, tone, rackIndex) {
  const group = new THREE.Group();
  group.position.set(x, 0, z);
  for (const px of [-1.6, 1.6]) {
    for (const pz of [-0.43, 0.43]) {
      box(group, 0.12, 3.25, 0.12, 0x415c56, px, 1.62, pz, { metalness: 0.35 });
    }
  }
  for (const level of [0.25, 1.22, 2.19, 3.16]) {
    box(group, 3.35, 0.12, 1.02, 0xb78043, 0, level, 0, { metalness: 0.34, texture: "steel" });
    box(group, 3.4, 0.035, 0.055, 0xe0c277, 0, level - 0.035, 0.52, { castShadow: false });
  }
  for (const pz of [-0.48, 0.48]) {
    const braceA = box(group, 0.055, 3.3, 0.055, 0x63746e, 0, 1.6, pz, { metalness: 0.45 });
    const braceB = box(group, 0.055, 3.3, 0.055, 0x63746e, 0, 1.6, pz, { metalness: 0.45 });
    braceA.rotation.z = 0.9;
    braceB.rotation.z = -0.9;
  }
  const tones = [tone, 0xc7905b, 0xe0c16c, 0x78a6a0];
  for (let level = 0; level < 3; level++) {
    for (let slot = 0; slot < 3; slot++) {
      const carton = box(group, 0.72, 0.68, 0.7, tones[(rackIndex + level + slot) % tones.length], -1.08 + slot * 1.08, 0.63 + level * 0.97, 0, { roughness: 0.95, texture: "cardboard" });
      box(group, 0.73, 0.035, 0.71, 0xe8ddc4, -1.08 + slot * 1.08, 0.75 + level * 0.97, 0.01, { castShadow: false });
      box(group, 0.07, 0.69, 0.715, 0xb89b70, -1.08 + slot * 1.08, 0.63 + level * 0.97, 0.004, { castShadow: false });
      if (slot === 1) carton.material.color.setHex(tones[(rackIndex + level) % tones.length]);
    }
  }
  const label = labelSprite(`RACK ${String(rackIndex + 1).padStart(2, "0")} · ${sku}`);
  label.position.set(0, 3.75, 0);
  group.add(label);
  world.add(group);
  addObstacle(x, z, 3.8, 1.25);
  addClickable(group, { type: sku.startsWith("MAT-") ? "material" : "stock", sku, title: productName, subtitle: `Emplacement ${sku}` });
}

function makeMachine(x, z, line, accent) {
  const group = new THREE.Group();
  group.position.set(x, 0, z);
  box(group, 2.65, 1.1, 1.7, 0x455d58, 0, 0.72, 0, { metalness: 0.16 });
  box(group, 2.3, 0.72, 1.32, 0x748a7d, 0, 1.42, 0, { metalness: 0.12 });
  box(group, 2.35, 0.18, 1.36, accent, 0, 1.88, 0, { metalness: 0.08 });
  box(group, 0.82, 0.62, 0.045, 0x314541, -0.72, 1.38, 0.69, { metalness: 0.18, roughness: 0.42 });
  box(group, 0.7, 0.5, 0.025, 0x71857b, -0.72, 1.38, 0.72, { metalness: 0.12, roughness: 0.35 });
  box(group, 0.045, 0.11, 0.04, 0xd7b95e, -0.4, 1.35, 0.75, { metalness: 0.42 });
  for (let i = 0; i < 4; i++) box(group, 0.46, 0.035, 0.035, 0x35433f, 0.22 + i * 0.12, 1.12, 0.69, { castShadow: false });
  for (let i = 0; i < 9; i++) {
    const stripe = box(group, 0.12, 0.035, 0.035, i % 2 ? 0x292f2d : 0xe1b64a, -1.05 + i * 0.26, 0.19, 0.86, { castShadow: false });
    stripe.rotation.y = -0.18;
  }
  box(group, 0.55, 0.38, 0.035, 0x223c3c, 0.55, 1.43, 0.68, { metalness: 0.15 });
  const screen = box(group, 0.35, 0.2, 0.045, 0x8dc38d, 0.55, 1.44, 0.71, { metalness: 0.1 });
  screen.material.emissive.setHex(0x27552c);
  for (const px of [-0.85, 0.85]) {
    cylinder(group, 0.22, 0.22, 0.14, 0x293c3a, px, 0.2, 0.9, 16).rotation.x = Math.PI / 2;
    cylinder(group, 0.22, 0.22, 0.14, 0x293c3a, px, 0.2, -0.9, 16).rotation.x = Math.PI / 2;
  }
  // Short conveyor feeding each line.
  box(group, 1.35, 0.22, 0.8, 0x425b54, 0, 0.57, 1.48);
  for (let i = 0; i < 5; i++) {
    const roller = cylinder(group, 0.08, 0.08, 0.78, 0xbfc4b2, -0.52 + i * 0.26, 0.62, 1.48, 10);
    roller.rotation.z = Math.PI / 2;
  }
  for (const [index, color] of [0x75d28b, 0xe5b74e, 0xd86759].entries()) {
    const light = new THREE.Mesh(new THREE.SphereGeometry(0.065, 10, 8), new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.65, roughness: 0.25 }));
    light.position.set(-0.85 + index * 0.2, 2.0, 0.68);
    group.add(light);
  }
  const label = labelSprite(line.name, "#f3f1df", "#245149");
  label.position.set(0, 2.55, 0);
  group.add(label);
  world.add(group);
  addObstacle(x, z, 3.4, 3.2);
  addClickable(group, { type: "line", lineId: line.id, title: line.name, subtitle: line.product_sku });
}

function makeTruck(x, z, truckLabel = "G-MIX · LIVRAISON", title = "Quai de livraison", subtitle = "Commandes client et expéditions") {
  const truck = new THREE.Group();
  truck.position.set(x, 0, z);
  box(truck, 4.4, 1.5, 2.25, 0x456b61, -0.2, 0.9, 0);
  box(truck, 1.45, 1.65, 2.15, 0xe8e6d8, 2.65, 0.95, 0);
  box(truck, 0.95, 0.57, 0.055, 0xa6c5bd, 2.8, 1.17, 1.1, { metalness: 0.15 });
  for (const wx of [-1.65, 1.3, 3.05]) {
    for (const wz of [-0.85, 0.85]) {
      const wheel = cylinder(truck, 0.42, 0.42, 0.24, 0x293638, wx, 0.42, wz, 18);
      wheel.rotation.x = Math.PI / 2;
    }
  }
  const wordmark = labelSprite(truckLabel, "#fff9dc", "#28594d");
  wordmark.scale.set(2.2, 0.55, 1);
  wordmark.position.set(0, 1.15, 1.15);
  truck.add(wordmark);
  world.add(truck);
  addClickable(truck, { type: "dock", title, subtitle });
}

function makePerson(name, jacketColor, isPlayer = false) {
  const person = new THREE.Group();
  person.userData.name = name;
  person.userData.isPlayer = isPlayer;
  person.userData.role = name.includes("Cariste") ? "Stock MP" : name.includes("Production") || name.includes("Opérateur") || name.includes("ligne") ? "Production" : name.includes("Contrôle") ? "Qualité" : name.includes("Quai") || name.includes("Réception") ? "Réception" : name.includes("Emball") ? "Emballage" : name.includes("Magasinier PF") ? "Entrepôt PF" : name.includes("Technicien") ? "Maintenance" : name.includes("Pilotage") ? "Pilotage" : "Direction";
  const jacket = material(jacketColor, 0.8);
  const skin = material(0xdcae88, 0.9);
  const dark = material(0x34413d, 0.9);
  const pant = material(0x334b4a, 0.9);
  const body = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.3, 0.73, 10), jacket);
  body.position.y = 0.96;
  body.castShadow = true;
  person.add(body);
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 10), skin);
  head.position.y = 1.51;
  head.castShadow = true;
  person.add(head);
  const hardhat = new THREE.Mesh(new THREE.SphereGeometry(0.245, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), material(isPlayer ? 0xd8ed82 : 0xe4bd54));
  hardhat.position.y = 1.65;
  hardhat.castShadow = true;
  person.add(hardhat);
  const helmetBrim = new THREE.Mesh(new THREE.CylinderGeometry(0.27, 0.27, 0.035, 18), material(isPlayer ? 0xc2d86e : 0xc49c43, 0.55));
  helmetBrim.position.y = 1.62;
  person.add(helmetBrim);
  const reflective = material(isPlayer ? 0xd8ef83 : 0xf1d36b, 0.38, 0.12);
  for (const y of [0.91, 1.12]) {
    const band = new THREE.Mesh(new THREE.TorusGeometry(0.245, 0.022, 6, 18), reflective);
    band.rotation.x = Math.PI / 2;
    band.position.y = y;
    person.add(band);
  }
  box(person, 0.12, 0.16, 0.025, 0xe7e4d2, 0.12, 1.27, 0.22, { castShadow: false });
  const legPivots = [];
  const armPivots = [];
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
    legPivots.push(legPivot);

    const armPivot = new THREE.Group();
    armPivot.position.set(side * 0.27, 1.18, 0);
    const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.07, 0.48, 8), jacket);
    arm.position.y = -0.22;
    armPivot.add(arm);
    person.add(armPivot);
    armPivots.push(armPivot);
  }
  person.userData.jacket = jacket;
  person.userData.legs = legPivots;
  person.userData.arms = armPivots;
  person.userData.walkPhase = Math.random() * Math.PI * 2;
  const tag = labelSprite(name, "#f5f2e3", isPlayer ? "#526d39" : "#294940");
  tag.scale.set(isPlayer ? 1.55 : 1.9, 0.48, 1);
  tag.position.y = 2.22;
  person.add(tag);
  addClickable(person, { type: isPlayer ? "player" : "worker", title: name, role: person.userData.role, subtitle: isPlayer ? "Directeur · avatar joueur" : `${person.userData.role} · membre de l’équipe` });
  return person;
}

function makeForklift() {
  const forklift = new THREE.Group();
  box(forklift, 1.4, 0.65, 1.0, 0xd8ad4f, 0, 0.62, 0);
  box(forklift, 0.85, 0.1, 0.8, 0x354947, -0.1, 1.0, 0);
  box(forklift, 0.1, 1.85, 0.12, 0x44534c, 0.62, 1.02, -0.43);
  box(forklift, 0.1, 1.85, 0.12, 0x44534c, 0.62, 1.02, 0.43);
  box(forklift, 0.72, 0.09, 0.9, 0xc6aa72, 1.05, 0.22, 0);
  box(forklift, 0.5, 0.1, 0.38, 0x253b39, -0.18, 0.96, 0);
  box(forklift, 0.12, 0.52, 0.38, 0x253b39, -0.38, 1.18, 0);
  const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.11, 12, 8), new THREE.MeshStandardMaterial({ color: 0xffb339, emissive: 0xff8a18, emissiveIntensity: 1.4, roughness: 0.25 }));
  beacon.position.set(-0.25, 1.42, -0.28);
  forklift.add(beacon);
  for (const x of [-0.42, 0.42]) {
    for (const z of [-0.51, 0.51]) {
      const wheel = cylinder(forklift, 0.23, 0.23, 0.17, 0x293536, x, 0.23, z, 14);
      wheel.rotation.x = Math.PI / 2;
    }
  }
  forklift.position.set(-10.8, 0, -0.4);
  world.add(forklift);
  addClickable(forklift, { type: "forklift", title: "Chariot élévateur", subtitle: "Cariste en déplacement" });
  return forklift;
}

function makeDepartmentStation(x, z, title, subtitle, accent, kind, width = 6.5, depth = 9) {
  const station = new THREE.Group();
  station.position.set(x, 0, z);
  const wallHeight = 3.5;
  const wallThickness = 0.2;
  const doorWidth = Math.min(2.6, width * 0.44);
  const frontZ = depth / 2;
  const frontSegment = (width - doorWidth) / 2;
  box(station, width, 0.12, depth, 0xe5e6dc, 0, 0.06, 0, { texture: "concrete", castShadow: false });
  box(station, width, wallHeight, wallThickness, 0xd6d9d0, 0, wallHeight / 2, -depth / 2, { roughness: 0.92 });
  box(station, wallThickness, wallHeight, depth, 0xd6d9d0, -width / 2, wallHeight / 2, 0, { roughness: 0.92 });
  box(station, wallThickness, wallHeight, depth, 0xd6d9d0, width / 2, wallHeight / 2, 0, { roughness: 0.92 });
  if (frontSegment > 0.4) {
    box(station, frontSegment, wallHeight, wallThickness, 0xd6d9d0, -doorWidth / 2 - frontSegment / 2, wallHeight / 2, frontZ, { roughness: 0.92 });
    box(station, frontSegment, wallHeight, wallThickness, 0xd6d9d0, doorWidth / 2 + frontSegment / 2, wallHeight / 2, frontZ, { roughness: 0.92 });
  }
  box(station, width, 0.16, 0.24, accent, 0, wallHeight - 0.08, -depth / 2, { castShadow: false });
  box(station, 0.24, 0.16, depth, accent, -width / 2, wallHeight - 0.08, 0, { castShadow: false });
  box(station, 0.24, 0.16, depth, accent, width / 2, wallHeight - 0.08, 0, { castShadow: false });
  const paneMaterial = new THREE.MeshStandardMaterial({ color: 0x9bc8c2, emissive: 0x24423d, emissiveIntensity: 0.18, roughness: 0.3, metalness: 0.12 });
  const windowCount = Math.max(1, Math.floor(width / 2.1));
  for (let i = 0; i < windowCount; i++) {
    const wx = -width / 2 + ((i + 1) * width) / (windowCount + 1);
    const pane = new THREE.Mesh(new THREE.BoxGeometry(1.15, 0.78, 0.055), paneMaterial);
    pane.position.set(wx, 2.65, -depth / 2 + 0.13);
    pane.castShadow = false;
    station.add(pane);
    box(station, 1.22, 0.055, 0.09, 0x66756e, wx, 2.65, -depth / 2 + 0.08, { metalness: 0.35, castShadow: false });
    box(station, 0.045, 0.82, 0.09, 0x66756e, wx, 2.65, -depth / 2 + 0.08, { metalness: 0.35, castShadow: false });
  }
  cylinder(station, 0.055, 0.055, Math.max(1, width - 0.8), 0x85948b, 0, 0.42, -depth / 2 + 0.25, 12).rotation.z = Math.PI / 2;
  cylinder(station, 0.035, 0.035, Math.max(1, width - 1), accent, 0, 0.62, -depth / 2 + 0.25, 10).rotation.z = Math.PI / 2;
  box(station, 3.1, 0.14, 2.55, 0xe4e3d8, 0, 0.08, 0, { castShadow: false });
  box(station, 2.45, 0.82, 0.72, 0x63756e, 0, 0.62, -0.48, { metalness: 0.12 });
  box(station, 2.5, 0.08, 0.78, accent, 0, 1.08, -0.48, { metalness: 0.08 });
  if (kind === "quality") {
    box(station, 0.72, 0.58, 0.06, 0x203b3b, 0.55, 1.43, -0.08);
    box(station, 0.62, 0.4, 0.04, 0x72c7c1, 0.55, 1.43, -0.035, { castShadow: false });
    cylinder(station, 0.2, 0.2, 0.26, 0xd6d7cb, -0.78, 1.27, -0.3, 12);
  } else if (kind === "packaging") {
    for (let i = 0; i < 3; i++) box(station, 0.46, 0.42, 0.42, 0xb88a55, -0.68 + i * 0.64, 1.34, 0.48, { texture: "cardboard" });
    box(station, 0.12, 0.66, 0.12, 0xd3d4c7, 1.08, 1.36, 0.44);
  } else if (kind === "storage") {
    for (let level = 0; level < 2; level++) for (let i = 0; i < 2; i++) box(station, 0.62, 0.48, 0.48, 0xb9905d, -0.55 + i * 0.85, 1.28 + level * 0.5, 0.52, { texture: "cardboard" });
  } else if (kind === "maintenance") {
    for (let i = 0; i < 4; i++) cylinder(station, 0.12, 0.12, 0.28, [0x89948a, 0x495a55, 0xd2a64f, 0x879f9a][i], -0.86 + i * 0.56, 1.26, 0.46, 10);
    box(station, 0.55, 0.52, 0.48, 0x283d3a, 0.92, 1.31, 0.42);
  } else {
    for (let i = 0; i < 2; i++) box(station, 0.7, 0.48, 0.62, 0xb9905d, -0.5 + i, 0.42, 0.58, { texture: "cardboard" });
  }
  const sign = labelSprite(title.toUpperCase(), "#f3f1df", "#245149");
  sign.scale.set(Math.min(width - 0.4, 3.8), 0.58, 1);
  sign.position.set(0, wallHeight + 0.62, frontZ + 0.15);
  station.add(sign);
  world.add(station);
  addObstacle(x, z - depth / 2, width, wallThickness + 0.08);
  addObstacle(x - width / 2, z, wallThickness + 0.08, depth);
  addObstacle(x + width / 2, z, wallThickness + 0.08, depth);
  if (frontSegment > 0.4) {
    addObstacle(x - doorWidth / 2 - frontSegment / 2, z + frontZ, frontSegment, wallThickness + 0.08);
    addObstacle(x + doorWidth / 2 + frontSegment / 2, z + frontZ, frontSegment, wallThickness + 0.08);
  }
  addClickable(station, { type: "department", title, subtitle });
}

function buildWorld() {
  makeGround();
  makeDepartmentStation(-21.5, -4.5, "Fournisseur MP", "Le fournisseur prépare les palettes et livre les matières premières commandées.", 0x8eb7a5, "receiving", 5, 10);
  makeDepartmentStation(-16.4, -4.5, "Réception", "Le réceptionnaire décharge les camions, contrôle les palettes et isole les non-conformes.", 0x8eb7a5, "receiving", 5, 10);
  makeDepartmentStation(-10.65, -4.5, "Stock MP", "Le magasinier-cariste range les matières en FIFO, prépare les kits OF et signale les seuils bas.", 0x9cad8d, "storage", 6.5, 10);
  makeDepartmentStation(-0.3, -4.5, "Production", "Le chef de ligne lance les OF. Les machines en série avancent au rythme du goulot.", 0x70c1bb, "production", 14, 10);
  makeDepartmentStation(9.7, -4.5, "Contrôle qualité", "Les produits conformes passent à l’emballage, les retouches reviennent en ligne et les rebuts sont isolés.", 0x70c1bb, "quality", 6, 10);
  makeDepartmentStation(16, -4.5, "Emballage", "Les produits conformes sont mis en carton, étiquetés et regroupés sur une palette.", 0xd4a45c, "packaging", 6.5, 10);
  makeDepartmentStation(23, -4.5, "Entrepôt PF", "Le magasinier PF range les palettes, prépare les commandes client et suit le stock minimum.", 0x9cad8d, "storage", 7, 10);
  makeDepartmentStation(-7, 6.3, "Maintenance et PDR", "Le technicien traite les pannes avec une pièce de rechange par intervention.", 0x80958d, "maintenance", 8, 7);
  makeDepartmentStation(4, 6.3, "Pilotage", "Le responsable suit les indicateurs et transmet les commandes MP et les OF aux équipes.", 0x53766a, "office", 8, 7);
  makeDepartmentStation(20, 6.3, "Client", "Le client passe ses commandes et reçoit les palettes préparées par l’usine.", 0x8eb7a5, "receiving", 8, 7);

  const rawShelfSpots = [-8, -6, -3, -1].map((z) => [-10.65, z]);
  (state?.raw_materials || []).filter((item) => item.sku !== "MAT-PDR").forEach((materialStock, index) => {
    const [x, z] = rawShelfSpots[index];
    makeShelf(x, z, materialStock.sku, materialStock.name, [0x79a69b, 0xd4a064, 0x91a96e, 0x7c98b0][index % 4], index);
  });
  (state?.stocks || []).forEach((stock, index) => {
    const spots = [[21.4, -7], [24.6, -7], [21.4, -3], [24.6, -3]];
    const [x, z] = spots[index % spots.length];
    makeShelf(x, z, stock.sku, stock.name, [0x79a69b, 0xd4a064, 0x91a96e, 0x7c98b0][index % 4], index);
  });
  const spareParts = state?.raw_materials?.find((item) => item.sku === "MAT-PDR");
  if (spareParts) makeShelf(-7, 6.3, spareParts.sku, spareParts.name, 0xd4a064, 5);

  const linePositions = [-5.3, -1.8, 1.8, 5.3];
  linePositions.forEach((x, i) => {
    const line = state?.production_lines?.[i] || { id: `LINE-${i + 1}`, name: `Ligne ${i + 1}`, product_sku: `SKU-${String(i + 1).padStart(2, "0")}` };
    makeMachine(x - 0.3, -4.5, line, [0x77a99c, 0xdaa05d, 0x93ad6f, 0x8aa8bd][i]);
  });
  makeTruck(-22, 13.3, "FOURNISSEUR MP", "Quai fournisseur", "Le chauffeur livre les matières commandées et repart après le déchargement.");
  makeTruck(24, 13.3, "G-MIX · CLIENT", "Quai de livraison", "Le chauffeur charge les palettes destinées au client.");
  const forklift = makeForklift();
  const team = [
    { name: "Noah · Réceptionnaire", position: [-16, -5], targets: [[-17, -5], [-15, -7], [-16, -1]] },
    { name: "Maya · Cariste", position: [-11, -5], targets: [[-11, -5], [-9, -7], [-10, -1]] },
    { name: "Idriss · Chef de ligne", position: [-3, -5], targets: [[-4, -7], [-1, -3], [2, -5]] },
    { name: "Karim · Opérateur", position: [2, -4], targets: [[2, -7], [0, -2], [5, -5]] },
    { name: "Léa · Contrôle qualité", position: [9, -5], targets: [[9, -7], [8, -2], [11, -5]] },
    { name: "Zoé · Emballeuse", position: [16, -5], targets: [[15, -7], [17, -2], [15, -5]] },
    { name: "Amadou · Magasinier PF", position: [23, -5], targets: [[22, -7], [24, -2], [22, -5]] },
    { name: "Sam · Technicien", position: [-7, 6], targets: [[-8, 5], [-6, 8], [-7, 4]] },
    { name: "Alice · Pilotage", position: [4, 6], targets: [[3, 5], [5, 8], [4, 4]] },
  ];
  const teamColors = [0x4f8c7c, 0x4b718a, 0x7d8153, 0x8c6855, 0x648f9d, 0xb27c54, 0x71875b, 0x8a7860, 0x799c88];
  team.forEach((member, i) => {
    const worker = makePerson(member.name, teamColors[i]);
    worker.position.set(member.position[0], 0, member.position[1]);
    worker.userData.targets = member.targets.map(([x, z]) => new THREE.Vector3(x, 0, z));
    worker.userData.targetIndex = i % worker.userData.targets.length;
    worker.userData.route = [];
    workers.push(worker);
    world.add(worker);
  });
  forklift.userData.route = [];
}

function keyFor(x, z) { return `${x},${z}`; }
function cellFromKey(key) { return key.split(",").map(Number); }

function walkable(x, z) {
  if (x < -27 || x > 27 || z < -13 || z > 13) return false;
  return !obstacles.some((item) => Math.abs(x - item.x) < item.width / 2 + 0.38 && Math.abs(z - item.z) < item.depth / 2 + 0.38);
}

function nearestWalkable(x, z) {
  const centerX = Math.round(x);
  const centerZ = Math.round(z);
  for (let radius = 0; radius <= 5; radius++) {
    for (let dx = -radius; dx <= radius; dx++) {
      for (let dz = -radius; dz <= radius; dz++) {
        if (Math.abs(dx) !== radius && Math.abs(dz) !== radius) continue;
        const cx = centerX + dx;
        const cz = centerZ + dz;
        if (walkable(cx, cz)) return [cx, cz];
      }
    }
  }
  return [Math.max(-27, Math.min(27, centerX)), Math.max(-13, Math.min(13, centerZ))];
}

function findPath(start, end) {
  const [sx, sz] = nearestWalkable(start.x, start.z);
  const [ex, ez] = nearestWalkable(end.x, end.z);
  const startKey = keyFor(sx, sz);
  const endKey = keyFor(ex, ez);
  const queue = [startKey];
  const cameFrom = new Map([[startKey, ""]]);
  for (let head = 0; head < queue.length; head++) {
    const current = queue[head];
    if (current === endKey) break;
    const [cx, cz] = cellFromKey(current);
    for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = cx + dx;
      const nz = cz + dz;
      const nextKey = keyFor(nx, nz);
      if (!walkable(nx, nz) || cameFrom.has(nextKey)) continue;
      cameFrom.set(nextKey, current);
      queue.push(nextKey);
    }
  }
  if (!cameFrom.has(endKey)) return [];
  const path = [];
  for (let key = endKey; key && key !== startKey; key = cameFrom.get(key)) {
    const [x, z] = cellFromKey(key);
    path.unshift(new THREE.Vector3(x, 0, z));
  }
  if (path.length) path[path.length - 1].set(ex, 0, ez);
  return path;
}

function updateActor(actor, delta, speed, pathKey = "route") {
  const route = actor.userData[pathKey] || [];
  if (!route.length) return false;
  const target = route[0];
  const direction = target.clone().sub(actor.position);
  direction.y = 0;
  if (direction.length() < 0.14) {
    route.shift();
    if (!route.length) return false;
  } else {
    direction.normalize();
    actor.position.addScaledVector(direction, speed * delta);
    actor.rotation.y = Math.atan2(direction.x, direction.z);
  }
  actor.userData.walkPhase = (actor.userData.walkPhase || 0) + delta * speed * 5.2;
  const swing = Math.sin(actor.userData.walkPhase) * 0.42;
  for (const [index, leg] of (actor.userData.legs || []).entries()) leg.rotation.x = swing * (index === 0 ? 1 : -1);
  for (const [index, arm] of (actor.userData.arms || []).entries()) arm.rotation.x = swing * (index === 0 ? -1 : 1);
  return true;
}

function setDestination(point) {
  const destination = new THREE.Vector3(point.x, 0, point.z);
  playerPath = findPath(player.position, destination);
  player.userData.route = playerPath;
  marker.position.set(destination.x, 0.035, destination.z);
  marker.visible = true;
  advanceTutorial("move");
  showToast("Déplacement en cours…");
}

function renderTutorial() {
  const step = tutorialSteps[tutorialIndex];
  if (!step) { $("#tutorial").hidden = true; return; }
  $("#tutorial-count").textContent = `ÉTAPE ${tutorialIndex + 1} / ${tutorialSteps.length}`;
  $("#tutorial-title").textContent = step.title;
  $("#tutorial-copy").textContent = step.copy;
  $("#tutorial-next").textContent = tutorialIndex === tutorialSteps.length - 1 ? "Terminer" : "Compris →";
}

function beginTutorial() {
  tutorialIndex = 0;
  $("#tutorial").hidden = false;
  renderTutorial();
}

function advanceTutorial(action, force = false) {
  if ($("#tutorial").hidden) return;
  if (!force && tutorialSteps[tutorialIndex]?.action !== action) return;
  tutorialIndex++;
  renderTutorial();
}

function addSupplierRow() {
  const list = $("#custom-supplier-list");
  if (list.children.length >= 20) return;
  const row = document.createElement("div");
  row.className = "supplier-entry";
  row.innerHTML = '<input data-field="name" aria-label="Nom du fournisseur" placeholder="Nom" maxlength="40" required><input data-field="lead_time_weeks" aria-label="Délai en semaines" title="Délai sem." type="number" min="1" max="8" value="2" required><input data-field="reliability" aria-label="Fiabilité en pourcentage" title="Fiabilité %" type="number" min="0" max="100" value="92" required><input data-field="unit_cost" aria-label="Coût unitaire en euros" title="Coût €" type="number" min="0" step="0.01" value="2" required><input data-field="specialty" aria-label="Spécialité" placeholder="Spécialité" value="Fournisseur généraliste" maxlength="50" required><input data-field="region" aria-label="Région" placeholder="Région" value="France" maxlength="50" required><button class="remove-supplier" type="button" aria-label="Supprimer ce fournisseur">×</button>';
  row.querySelector(".remove-supplier").addEventListener("click", () => row.remove());
  list.append(row);
}

function refreshMaterialChoices() {
  const names = [...new Set([...$("#product-list").querySelectorAll('[data-field="name"]')].map((input) => input.value.trim() || "Produit"))];
  $("#material-list").querySelectorAll('[data-field="product_name"]').forEach((select) => {
    const selected = select.value;
    select.innerHTML = names.map((name) => `<option value="${escapeHTML(name)}">${escapeHTML(name)}</option>`).join("");
    if (names.includes(selected)) select.value = selected;
  });
}

function addSetupRow(kind) {
  const configs = {
    product: { container: "#product-list", className: "setup-product-row", fields: [["name","Nom","Produit", "text"],["category","Catégorie","Divers","text"],["unit","Unité","pièce","text"],["unit_value","Valeur €","10","number"],["quantity","Stock","500","number"],["safety_stock","Seuil","100","number"],["demand_per_week","Demande/sem.","100","number"],["weekly_capacity","Capacité/sem.","800","number"]] },
    material: { container: "#material-list", className: "setup-material-row", fields: [["name","Nom","Matière", "text"],["unit","Unité","unité","text"],["unit_value","Valeur €","2","number"],["quantity","Stock","500","number"],["safety_stock","Seuil","100","number"],["product_name","Produit associé","Produit", "text"]] },
  }[kind];
  const list = $(config.container);
  if (list.children.length >= 30) return;
  const row = document.createElement("div"); row.className = config.className;
  row.innerHTML = config.fields.map(([field,label,value,type]) => field === "product_name" ? `<select data-field="${field}" aria-label="${label}" required></select>` : `<input data-field="${field}" aria-label="${label}" placeholder="${label}" value="${value}" type="${type}" ${type === "number" ? 'min="0" step="0.01"' : 'maxlength="50"'} required>`).join("") + '<button class="remove-supplier" type="button" aria-label="Supprimer">×</button>';
  row.querySelector("button").addEventListener("click", () => row.remove()); list.append(row);
  if (kind === "product") {
    const nameField = row.querySelector('[data-field="name"]');
    nameField.addEventListener("input", refreshMaterialChoices);
    row.querySelector("button").addEventListener("click", refreshMaterialChoices);
  }
  if (kind === "material") refreshMaterialChoices();
}

function cameraPosition() {
  const target = player.position.clone().add(new THREE.Vector3(0, 0.8, 0));
  camera.position.set(
    target.x + Math.sin(cameraYaw) * cameraDistance * 0.62,
    target.y + cameraDistance * 0.8,
    target.z + Math.cos(cameraYaw) * cameraDistance * 0.62,
  );
  camera.lookAt(target);
}

function findInteraction(object) {
  let current = object;
  while (current && !current.userData.interaction) current = current.parent;
  return current?.userData.interaction ? { group: current, info: current.userData.interaction } : null;
}

function selectInteraction(info) {
  currentSelection = info;
  $("#inspector").classList.remove("closed");
  const copy = $("#inspector-copy");
  const action = $("#inspector-action");
  action.hidden = true;
  if (info.type === "stock") {
    const stock = state?.stocks?.find((item) => item.sku === info.sku);
    copy.textContent = `${info.title} · ${info.sku}. ${stock ? `${stock.quantity} unités disponibles, seuil de sécurité ${stock.safety_stock}.` : info.subtitle}`;
    action.textContent = "Planifier une fabrication  →";
    action.hidden = false;
    action.onclick = () => { $("#product-sku").value = info.sku; openProduction(); };
  } else if (info.type === "material") {
    const stock = state?.raw_materials?.find((item) => item.sku === info.sku);
    copy.textContent = `${info.title} · ${info.sku}. ${stock ? `${stock.quantity} unités disponibles, seuil de sécurité ${stock.safety_stock}.` : info.subtitle}`;
    action.textContent = "Commander cette matière →";
    action.hidden = false;
    action.onclick = () => openOrder(info.sku);
  } else if (info.type === "line") {
    const line = state?.production_lines?.find((item) => item.id === info.lineId);
    copy.textContent = line ? `${line.name} fabrique ${line.product_sku} · capacité ${line.weekly_capacity} unités par semaine · efficacité ${line.efficiency}%. ${line.machines?.map((machine) => `${machine.operation}: ${machine.cycle_minutes} min, ${machine.state}`).join(" · ") || "Les opérations de la ligne sont en série."}` : info.subtitle;
    if (line && !line.operational) {
      action.textContent = state.spare_parts > 0 ? "Réparer la ligne · 1 PDR →" : "Commander une pièce de rechange →";
      action.hidden = false;
      action.onclick = () => state.spare_parts > 0 ? requestMaintenance(line.id) : openOrder("MAT-PDR");
    }
  } else if (info.type === "worker") {
    copy.textContent = `${info.title} · ${info.subtitle}. Cliquez sur « Parler » ou approchez-vous et appuyez sur E.`;
    action.textContent = `Parler avec ${info.title.split(" · ")[0]} →`;
    action.hidden = false;
    action.onclick = () => openNpcDialog(info);
  } else if (info.type === "department") {
    const liveInfo = info.title === "Stock MP"
      ? ` Matières disponibles : ${(state?.raw_materials || []).map((item) => `${item.name} ${item.quantity}/${item.safety_stock} seuil`).join(" · ")}.`
      : info.title === "Entrepôt PF"
        ? ` Stocks PF : ${(state?.stocks || []).map((item) => `${item.name} ${item.quantity} u.`).join(" · ")}.`
        : info.title === "Maintenance et PDR"
          ? ` ${state?.spare_parts || 0} pièce(s) de rechange disponible(s).`
          : info.title === "Pilotage"
            ? ` OTIF ${Number(state?.kpis?.otif || 0).toFixed(1)}% · TRS ${Number(state?.kpis?.trs || 0).toFixed(1)}% · qualité ${Number(state?.kpis?.quality_rate || 0).toFixed(1)}%.`
            : "";
    copy.textContent = `${info.subtitle}${liveInfo}`;
  } else {
    copy.textContent = `${info.title}. ${info.subtitle}. Cliquez sur un autre élément pour l’inspecter.`;
  }
  advanceTutorial("inspect");
}

function openOrder(sku = "") {
  if (sku) $("#sku").value = sku.replace("SKU-", "MAT-");
  $("#order-modal").hidden = false;
  $("#order-feedback").textContent = "";
}

function openProduction() {
  $("#production-modal").hidden = false;
  $("#production-feedback").textContent = "";
}

async function requestMaintenance(lineId) {
  try {
    const response = await fetch("/api/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ maintenance_line_ids: [lineId] }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    state = await (await fetch("/api/state")).json();
    updateHUD(state);
    showToast("Intervention planifiée pour la prochaine semaine.");
  } catch (error) {
    showToast(`Maintenance impossible : ${error.message}`, true);
  }
}

function openNpcDialog(info) {
  const role = info.role || "Réception";
  const stock = [...(state?.stocks || [])].sort((a, b) => a.quantity - b.quantity)[0];
  const line = [...(state?.production_lines || [])].sort((a, b) => a.efficiency - b.efficiency)[0];
  const conversations = {
    "Stock MP": [
      ["As-tu repéré un stock bas ?", stock ? `${stock.name} est à ${stock.quantity} ${stock.unit || "unités"}, pour un seuil de sécurité de ${stock.safety_stock}. On devrait surveiller cette référence.` : "Les rayonnages sont en cours d’inventaire."],
      ["Comment circule le chariot ?", "Les allées sont dégagées. Approche-toi des rayonnages pour vérifier les références et les quantités."],
    ],
    Production: [
      ["Quelle ligne a besoin d’aide ?", line ? `${line.name} tourne à ${line.efficiency}% avec une capacité de ${line.weekly_capacity} pièces par semaine.` : "Les lignes tournent normalement cette semaine."],
      ["Que faut-il produire ?", stock ? `Nous fabriquons ${stock.name}. Le stock actuel est de ${stock.quantity} unités.` : "Consulte le tableau de bord pour voir les priorités."],
    ],
    Qualité: [
      ["Comment va le service client ?", `L’OTIF est à ${Number(state?.kpis?.otif || 0).toFixed(1)}%. ${state?.kpis?.stockouts ? "Des ruptures pénalisent les livraisons." : "Pas de rupture signalée actuellement."}`],
      ["Quel indicateur surveiller ?", `Le TRS de l’usine est à ${Number(state?.kpis?.trs || 0).toFixed(1)}%. Maintenons les lignes et le contrôle qualité.`],
    ],
    Réception: [
      ["Y a-t-il des livraisons à surveiller ?", state?.events?.length ? `Cette semaine, le marché signale : ${state.events.join(" · ")}` : "Aucun aléa signalé cette semaine. Les délais fournisseurs restent à surveiller."],
      ["Où vérifier les réceptions ?", "Le quai est à l’entrée de l’entrepôt. Consulte les délais de chaque fournisseur avant de lancer une commande."],
    ],
    Emballage: [
      ["Comment préparer une palette ?", "Mets les produits en carton, contrôle l’étiquette et le poids, puis filme une palette de six colis."],
      ["Que se passe-t-il après le contrôle ?", "Les produits conformes arrivent ici. Les pièces à retoucher repartent en production."],
    ],
    "Entrepôt PF": [
      ["Quel stock est le plus bas ?", stock ? `${stock.name} : ${stock.quantity} unités en stock PF, seuil de sécurité ${stock.safety_stock}.` : "Les emplacements PF sont en cours d’inventaire."],
      ["Quand charger le client ?", "Le client est servi à chaque semaine simulée. L’OTIF indique les quantités livrées complètes et à temps."],
    ],
    Maintenance: [
      ["Y a-t-il une ligne en panne ?", state?.production_lines?.some((item) => !item.operational) ? `${state.production_lines.filter((item) => !item.operational).map((item) => item.name).join(", ")} attend une intervention.` : "Toutes les lignes sont opérationnelles."],
      ["Combien de pièces de rechange reste-t-il ?", `${state?.spare_parts || 0} pièce(s) disponible(s). Une réparation consomme une pièce.`],
    ],
    Pilotage: [
      ["Quelle décision prendre ?", state?.kpis?.stockouts ? `${state.kpis.stockouts} référence(s) manquent. Planifie un OF et surveille la matière.` : "Vérifie les matières, passe les OF nécessaires, puis lance la semaine."],
      ["Quels indicateurs suivre ?", `OTIF ${Number(state?.kpis?.otif || 0).toFixed(1)}% · TRS ${Number(state?.kpis?.trs || 0).toFixed(1)}% · qualité ${Number(state?.kpis?.quality_rate || 0).toFixed(1)}%.`],
    ],
  };
  const name = info.title.split(" · ")[0];
  const topics = ({
    "Stock MP": ["Quelle matière faut-il surveiller ?", "Comment éviter une rupture de matière ?"],
    Production: ["Quelle ligne est prioritaire ?", "Comment améliorer la cadence ?"],
    Qualité: ["Que nous apprend le taux de qualité ?", "Comment éviter les défauts ?"],
    Réception: ["Y a-t-il un risque fournisseur ?", "Que contrôler à l’arrivée ?"],
    Emballage: ["Comment préparer une palette conforme ?", "Comment éviter les erreurs d’expédition ?"],
    "Entrepôt PF": ["Quel produit fini faut-il surveiller ?", "Comment préparer la prochaine livraison ?"],
    Maintenance: ["Quelle ligne nécessite une intervention ?", "Comment réduire les pannes ?"],
    Pilotage: ["Quelle décision prendre cette semaine ?", "Quels indicateurs surveiller ?"],
  })[role] || ["Comment se passe le travail cette semaine ?", "Sur quoi devrais-je agir en premier ?"];
  activeNpcSession = npcSessions.get(name) || { name, role, history: [], transcript: `${name} : Bonjour ! Pose-moi une question sur l’usine.` };
  activeNpcSession.role = role;
  npcSessions.set(name, activeNpcSession);
  $("#npc-name").textContent = name;
  $("#npc-role").textContent = role;
  $("#npc-dialogue").textContent = activeNpcSession.transcript;
  ["#npc-question-one", "#npc-question-two"].forEach((selector, index) => {
    const button = $(selector);
    button.textContent = topics[index];
    button.onclick = () => askNpc(topics[index]);
  });
  $("#npc-chat-input").value = "";
  $("#npc-modal").hidden = false;
}

async function askNpc(question) {
  if (!activeNpcSession || !question.trim()) return;
  const session = activeNpcSession;
  const name = session.name;
  const dialogue = $("#npc-dialogue");
  const send = $("#npc-chat-form button");
  const userQuestion = question.trim();
  session.history.push({ role: "user", content: userQuestion });
  session.transcript += `\n\nToi : ${userQuestion}\n${name} : réfléchit…`;
  dialogue.textContent = session.transcript;
  dialogue.scrollTop = dialogue.scrollHeight;
  send.disabled = true;
  try {
    const response = await fetch("/api/npc-chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, role: session.role, question: userQuestion, history: session.history.slice(0, -1) }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    session.history.push({ role: "assistant", content: result.answer });
    session.transcript = session.transcript.replace(`${name} : réfléchit…`, `${name} : ${result.answer}`);
  } catch (error) {
    session.history.pop();
    session.transcript = session.transcript.replace(`${name} : réfléchit…`, `${name} : Je n’arrive pas à joindre le modèle IA. Réessaie dans un instant.`);
    showToast(`Dialogue indisponible : ${error.message}`, true);
  } finally {
    if (activeNpcSession === session && !$("#npc-modal").hidden) {
      dialogue.textContent = session.transcript;
      dialogue.scrollTop = dialogue.scrollHeight;
    }
    send.disabled = false;
  }
}

function showToast(message, isError = false) {
  const box = $("#toast");
  box.textContent = message;
  box.className = `visible${isError ? " error" : ""}`;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { box.className = ""; }, 2800);
}

function updateHUD(newState) {
  state = newState;
  $("#company-name").textContent = state.company_name || "L’atelier";
  $("#week").textContent = `SEMAINE ${String(state.current_week).padStart(2, "0")}`;
  $("#otif").textContent = Number(state.kpis.otif).toFixed(1).replace(".", ",");
  $("#trs").textContent = Number(state.kpis.trs).toFixed(1).replace(".", ",");
  $("#stock-value").textContent = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(state.kpis.stock_value);
  $("#quality").textContent = Number(state.kpis.quality_rate ?? 100).toFixed(1).replace(".", ",");
  $("#delivered").textContent = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(state.kpis.delivered || 0);
  const lowMaterial = (state.raw_materials || []).find((material) => material.quantity < material.safety_stock);
  const lowFinished = (state.stocks || []).find((stock) => stock.quantity < stock.safety_stock);
  const pendingProduction = (state.production_orders || []).length;
  $("#objective").textContent = Number(state.kpis.stockouts) > 0
    ? `${state.kpis.stockouts} référence(s) en rupture. Planifiez un OF et surveillez la matière première.`
    : lowMaterial ? `${lowMaterial.name} approche du seuil de sécurité. Passez une commande fournisseur.`
      : lowFinished ? `${lowFinished.name} passe sous son seuil PF. Planifiez un OF et vérifiez la matière disponible.`
        : pendingProduction ? `${pendingProduction} OF en attente. Lancez la semaine pour produire.`
          : "Planifiez vos OF, surveillez les matières et livrez le client à temps.";
  $("#objective-status").textContent = pendingProduction ? `${pendingProduction} ordre(s) de fabrication en attente` : lowMaterial ? "Action requise : réapprovisionnement MP" : lowFinished ? "Action requise : OF produit fini" : "Décidez les quantités à produire cette semaine.";
  $("#event-summary").textContent = state.events?.length ? state.events.join(" · ") : "Marché stable cette semaine.";
  $("#people-label").textContent = `${workers.length} ouvriers actifs · ${state.kpis.stockouts ? "priorité stocks" : "activité normale"}`;
  $("#sku").innerHTML = (state.raw_materials || []).map((stock) => `<option value="${escapeHTML(stock.sku)}">${escapeHTML(stock.name)} · ${stock.quantity} en stock</option>`).join("");
  $("#product-sku").innerHTML = state.stocks.map((stock) => `<option value="${escapeHTML(stock.sku)}">${escapeHTML(stock.name)} · ${stock.quantity} en stock PF</option>`).join("");
  $("#supplier").innerHTML = state.suppliers.filter((supplier) => supplier.active).map((supplier) => `<option value="${escapeHTML(supplier.id)}">${escapeHTML(supplier.name)} · ${escapeHTML(supplier.specialty || "Fournisseur")}, ${escapeHTML(supplier.region || "France")} · ${supplier.lead_time_weeks} sem.</option>`).join("");
  const selectedProductSku = currentSelection?.type === "stock" ? currentSelection.sku : "";
  if (selectedProductSku) $("#product-sku").value = selectedProductSku;
  const selectedMaterialSku = currentSelection?.type === "material" ? currentSelection.sku : "";
  if (selectedMaterialSku) $("#sku").value = selectedMaterialSku;
  workers.forEach((worker, index) => {
    let color = 0x4f8c7c;
    if (state.kpis.otif < 75 || state.kpis.stockouts > 0) color = 0xb56d54;
    else if (state.kpis.trs < 65) color = 0xc09a47;
    else color = [0x4f8c7c, 0x4b718a, 0x7d8153, 0x8c6855][index % 4];
    worker.userData.jacket.color.setHex(color);
  });
  if (["stock", "material", "line"].includes(currentSelection?.type)) selectInteraction(currentSelection);
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function raycastFromPointer(event) {
  const rect = canvas.getBoundingClientRect();
  pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  pointer.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;
  raycaster.setFromCamera(pointer, camera);
}

function onCanvasClick(event) {
  if (dragging || event.button !== 0) return;
  raycastFromPointer(event);
  const rect = canvas.getBoundingClientRect();
  let nearestWorker = null;
  let nearestWorkerPixels = 44;
  for (const worker of workers) {
    const projected = worker.position.clone().add(new THREE.Vector3(0, 1.05, 0)).project(camera);
    const px = (projected.x * 0.5 + 0.5) * rect.width + rect.left;
    const py = (-projected.y * 0.5 + 0.5) * rect.height + rect.top;
    const distance = Math.hypot(event.clientX - px, event.clientY - py);
    if (distance < nearestWorkerPixels) { nearestWorker = worker; nearestWorkerPixels = distance; }
  }
  if (nearestWorker) {
    const info = nearestWorker.userData.interaction;
    selectInteraction(info);
    openNpcDialog(info);
    const closePoint = nearestWorker.getWorldPosition(new THREE.Vector3());
    const approach = closePoint.add(player.position.clone().sub(closePoint).setY(0).normalize().multiplyScalar(2.1));
    if (walkable(Math.round(approach.x), Math.round(approach.z))) setDestination(approach);
    return;
  }
  const hits = raycaster.intersectObjects(interactables, true);
  if (hits.length) {
    const target = findInteraction(hits[0].object);
    if (target) {
      selectInteraction(target.info);
      if (target.info.type === "worker") openNpcDialog(target.info);
      const closePoint = target.group.getWorldPosition(new THREE.Vector3());
      const direction = player.position.clone().sub(closePoint).setY(0).normalize();
      const approach = closePoint.add(direction.multiplyScalar(2.4));
      if (walkable(Math.round(approach.x), Math.round(approach.z))) setDestination(approach);
      return;
    }
  }
  const point = new THREE.Vector3();
  if (raycaster.ray.intersectPlane(groundPlane, point)) setDestination(point);
}

function setupControls() {
  canvas.addEventListener("pointerdown", (event) => {
    if (event.button === 2 || event.button === 1) {
      dragging = true;
      lastPointer = { x: event.clientX, y: event.clientY };
      canvas.setPointerCapture(event.pointerId);
    }
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!dragging) {
      raycastFromPointer(event);
      const hit = raycaster.intersectObjects(interactables, true).find((item) => findInteraction(item.object));
      const target = hit ? findInteraction(hit.object) : null;
      if (target) {
        const point = target.group.getWorldPosition(new THREE.Vector3());
        hoverRing.position.set(point.x, 0.04, point.z);
        hoverRing.visible = true;
        canvas.style.cursor = "pointer";
      } else {
        hoverRing.visible = false;
        canvas.style.cursor = "default";
      }
      return;
    }
    cameraYaw -= (event.clientX - lastPointer.x) * 0.008;
    lastPointer = { x: event.clientX, y: event.clientY };
  });
  canvas.addEventListener("pointerup", (event) => {
    if (dragging) {
      dragging = false;
      return;
    }
    onCanvasClick(event);
  });
  canvas.addEventListener("contextmenu", (event) => event.preventDefault());
  canvas.addEventListener("wheel", (event) => {
    cameraDistance = Math.max(15, Math.min(34, cameraDistance + Math.sign(event.deltaY) * 1.5));
  }, { passive: true });
  window.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    if (["w", "a", "s", "d", "arrowup", "arrowdown", "arrowleft", "arrowright"].includes(key)) {
      keys.add(key);
      playerPath.length = 0;
    }
    if (key === "1") openOrder();
    if (key === "2") $("#inspector").classList.remove("closed");
    if (key === "3") cameraDistance = 23;
    if (key === "escape") $("#order-modal").hidden = true;
    if (key === "escape") $("#npc-modal").hidden = true;
    if (key === "escape") $("#production-modal").hidden = true;
    if (key === "e") interactNearest();
  });
  window.addEventListener("keyup", (event) => keys.delete(event.key.toLowerCase()));
  window.addEventListener("blur", () => keys.clear());
  window.addEventListener("resize", () => {
    camera.aspect = innerWidth / innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight);
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
  });
}

function moveByKeyboard(delta) {
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
  const nextX = player.position.x + step.x;
  const nextZ = player.position.z + step.z;
  if (walkable(Math.round(nextX), Math.round(player.position.z))) player.position.x = nextX;
  if (walkable(Math.round(player.position.x), Math.round(nextZ))) player.position.z = nextZ;
  player.rotation.y = Math.atan2(step.x, step.z);
  player.userData.walkPhase = (player.userData.walkPhase || 0) + delta * speed * 5;
  const swing = Math.sin(player.userData.walkPhase) * 0.5;
  player.userData.legs.forEach((leg, index) => { leg.rotation.x = swing * (index ? -1 : 1); });
  player.userData.arms.forEach((arm, index) => { arm.rotation.x = swing * (index ? 1 : -1); });
  return true;
}

function interactNearest() {
  let closest = null;
  let closestDistance = 3.2;
  for (const group of interactables) {
    const info = group.userData.interaction;
    if (["worker", "line", "stock", "office", "dock", "forklift"].includes(info.type)) {
      const distance = player.position.distanceTo(group.getWorldPosition(new THREE.Vector3()));
      if (distance < closestDistance) { closest = info; closestDistance = distance; }
    }
  }
  if (closest) {
    selectInteraction(closest);
    if (closest.type === "worker") openNpcDialog(closest);
  }
  else showToast("Approchez-vous d’une machine ou d’un membre de l’équipe.");
}

async function loadState() {
  try {
    const response = await fetch("/api/state");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    savedState = await response.json();
    updateHUD(savedState);
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
  if (!$("#product-list").children.length || !$("#material-list").children.length || !$("#custom-supplier-list").children.length) {
    $("#setup-note").textContent = "Ajoute au moins un fournisseur, un produit fini et sa matière première.";
    return;
  }
  const productNames = [...$("#product-list").querySelectorAll('[data-field="name"]')].map((input) => input.value.trim());
  const mappedMaterials = [...$("#material-list").querySelectorAll('[data-field="product_name"]')].map((input) => input.value.trim());
  if (productNames.some((name) => !mappedMaterials.includes(name))) {
    $("#setup-note").textContent = "Associe chaque matière à un produit : le nom associé doit être identique au nom du produit fini.";
    return;
  }
  if (savedState?.started && !window.confirm("Créer une nouvelle partie remplacera la sauvegarde actuelle. Continuer ?")) return;
  const button = $("#start-new-game");
  button.disabled = true;
  try {
    const response = await fetch("/api/new-game", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        company_name: $("#company-input").value.trim(),
        difficulty: $("#difficulty-input").value,
        suppliers: [...$("#custom-supplier-list").querySelectorAll(".supplier-entry")].map((row) => ({
          name: row.querySelector('[data-field="name"]').value.trim(),
          lead_time_weeks: Number(row.querySelector('[data-field="lead_time_weeks"]').value),
          reliability: Number(row.querySelector('[data-field="reliability"]').value),
          unit_cost: Number(row.querySelector('[data-field="unit_cost"]').value),
          specialty: row.querySelector('[data-field="specialty"]').value.trim(),
          region: row.querySelector('[data-field="region"]').value.trim(),
        })),
        products: [...$("#product-list").children].map((row) => Object.fromEntries([...row.querySelectorAll("[data-field]")].map((input) => [input.dataset.field, input.type === "number" ? Number(input.value) : input.value.trim()]))),
        materials: [...$("#material-list").children].map((row) => Object.fromEntries([...row.querySelectorAll("[data-field]")].map((input) => [input.dataset.field, input.type === "number" ? Number(input.value) : input.value.trim()]))),
      }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail?.[0]?.msg || result.detail || `HTTP ${response.status}`);
    updateHUD(result);
    $("#setup-screen").hidden = true;
    if ($("#tutorial-enabled").checked) beginTutorial();
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
    const response = await fetch("/api/next-turn", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const nextState = await response.json();
    if (!response.ok) throw new Error(nextState.detail || `HTTP ${response.status}`);
    updateHUD(nextState);
    const report = nextState.last_week || {};
    showToast(`Semaine ${nextState.current_week} · ${report.produced || 0} fabriqués · ${report.reworked || 0} retouchés · ${report.quality_losses || 0} rebutés · ${report.delivered || 0} livrés.`);
    advanceTutorial("week");
  } catch (error) {
    showToast(`Impossible de simuler la semaine : ${error.message}`, true);
  } finally {
    button.disabled = false;
  }
}

async function placeOrder(event) {
  event.preventDefault();
  const supplierId = $("#supplier").value;
  const sku = $("#sku").value;
  const quantity = Number($("#quantity").value);
  if (!supplierId || !sku || !Number.isInteger(quantity) || quantity < 1) return;
  try {
    const response = await fetch("/api/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ orders: [{ supplier_id: supplierId, sku, quantity }] }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    const supplier = state.suppliers.find((item) => item.id === supplierId);
    const arrival = state.current_week + Number(supplier?.lead_time_weeks || 0);
    $("#order-feedback").textContent = `Commande confirmée · arrivée estimée semaine ${arrival}.`;
    showToast("Commande passée. Le fournisseur la prépare.");
    state = await (await fetch("/api/state")).json();
    updateHUD(state);
    advanceTutorial("order");
    setTimeout(() => { $("#order-modal").hidden = true; }, 900);
  } catch (error) {
    $("#order-feedback").textContent = `Commande refusée : ${error.message}`;
  }
}

async function placeProductionOrder(event) {
  event.preventDefault();
  const order = {
    sku: $("#product-sku").value,
    quantity: Number($("#production-quantity").value),
    line_count: Number($("#line-count").value),
  };
  try {
    const response = await fetch("/api/decisions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ production_orders: [order] }),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
    const stock = state.stocks.find((item) => item.sku === order.sku);
    $("#production-feedback").textContent = `OF pour ${stock?.name || order.sku} enregistré. Lancez la semaine pour produire.`;
    showToast("Ordre de fabrication transmis à la production.");
    advanceTutorial("production");
    state = await (await fetch("/api/state")).json();
    updateHUD(state);
    setTimeout(() => { $("#production-modal").hidden = true; }, 1100);
  } catch (error) {
    $("#production-feedback").textContent = `OF refusé : ${error.message}`;
  }
}

function animate() {
  requestAnimationFrame(animate);
  const delta = Math.min(clock.getDelta(), 0.04);
  const keyboardMoving = moveByKeyboard(delta);
  if (!keyboardMoving && playerPath.length) updateActor(player, delta, 3.7, "route");
  if (!keyboardMoving && !playerPath.length) {
    for (const limb of [...player.userData.legs, ...player.userData.arms]) limb.rotation.x *= 0.82;
  }
  if (!playerPath.length && !keyboardMoving) marker.visible = false;
  for (const worker of workers) {
    if (!worker.userData.route.length) {
      const points = worker.userData.targets;
      const target = points[worker.userData.targetIndex % points.length];
      worker.userData.route = findPath(worker.position, target);
      worker.userData.targetIndex++;
    }
    if (!updateActor(worker, delta, 1.1, "route")) worker.rotation.y += delta * 0.4;
  }
  cameraPosition();
  renderer.render(scene, camera);
}

async function startGame() {
  await loadState();
  buildWorld();
  setupControls();
  $("#next-turn").addEventListener("click", nextWeek);
  $("#order-open").addEventListener("click", () => openOrder());
  $("#production-open").addEventListener("click", openProduction);
  $("#inspect-open").addEventListener("click", () => $("#inspector").classList.toggle("closed"));
  $("#home-camera").addEventListener("click", () => { cameraDistance = 23; cameraYaw = 0.48; player.position.set(0, 0, 1.5); playerPath = []; });
  $("#close-inspector").addEventListener("click", () => $("#inspector").classList.add("closed"));
  $("#order-close").addEventListener("click", () => { $("#order-modal").hidden = true; });
  $("#production-close").addEventListener("click", () => { $("#production-modal").hidden = true; });
  $("#npc-close").addEventListener("click", () => { $("#npc-modal").hidden = true; });
  $("#npc-chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = $("#npc-chat-input");
    const question = input.value.trim();
    if (!question) return;
    input.value = "";
    askNpc(question);
  });
  const helpPanel = $("#helpbot-panel"), helpLog = $("#helpbot-log");
  $("#helpbot-toggle").addEventListener("click", () => { helpPanel.hidden = !helpPanel.hidden; });
  $("#helpbot-close").addEventListener("click", () => { helpPanel.hidden = true; });
  $("#helpbot-check").addEventListener("click", async () => {
    helpLog.textContent = "Vérification du jeu et du modèle local…";
    try {
      const [health, models] = await Promise.all([fetch("/health"), fetch("http://127.0.0.1:11434/api/tags")]);
      const available = await models.json();
      const modelReady = available.models?.some((model) => model.name === "qwen2.5:1.5b");
      helpLog.textContent = health.ok && models.ok && modelReady
        ? "Tout est connecté : le jeu et le modèle IA local répondent. Si le chat personnage reste bloqué, ferme sa fenêtre et rouvre-la, puis renvoie ta question."
        : "Le jeu répond, mais le modèle IA ne semble pas prêt. Vérifie qu’Ollama est ouvert et que qwen2.5:1.5b est installé.";
    } catch {
      helpLog.textContent = "Connexion IA impossible. Vérifie qu’Ollama est lancé, puis actualise le jeu sur http://127.0.0.1:8001/.";
    }
  });
  $("#helpbot-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = $("#helpbot-input"), question = input.value.trim();
    const send = $("#helpbot-form button");
    if (!question || send.disabled) return;
    input.value = "";
    helpbotHistory.push({ role: "user", content: question });
    helpLog.textContent += `\n\nToi : ${question}\nAide G-mix : réfléchit…`;
    helpLog.scrollTop = helpLog.scrollHeight;
    send.disabled = true;
    fetch("/api/help-chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history: helpbotHistory.slice(0, -1) }),
    }).then(async (response) => {
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || `HTTP ${response.status}`);
      helpbotHistory.push({ role: "assistant", content: result.answer });
      helpLog.textContent = helpLog.textContent.replace("Aide G-mix : réfléchit…", `Aide G-mix : ${result.answer}`);
    }).catch((error) => {
      helpbotHistory.pop();
      helpLog.textContent = helpLog.textContent.replace("Aide G-mix : réfléchit…", `Aide G-mix : Je n’ai pas pu répondre (${error.message}). Clique sur « Vérifier la connexion IA » et réessaie.`);
    }).finally(() => { send.disabled = false; helpLog.scrollTop = helpLog.scrollHeight; });
  });
  $("#npc-modal").addEventListener("pointerdown", (event) => { if (event.target.id === "npc-modal") event.currentTarget.hidden = true; });
  $("#order-modal").addEventListener("pointerdown", (event) => { if (event.target.id === "order-modal") event.currentTarget.hidden = true; });
  $("#production-modal").addEventListener("pointerdown", (event) => { if (event.target.id === "production-modal") event.currentTarget.hidden = true; });
  $("#order-form").addEventListener("submit", placeOrder);
  $("#production-form").addEventListener("submit", placeProductionOrder);
  $("#setup-form").addEventListener("submit", createNewGame);
  $("#resume-game").addEventListener("click", resumeGame);
  $("#product-list").addEventListener("input", refreshMaterialChoices);
  $("#product-list").addEventListener("click", (event) => { if (event.target.matches(".remove-supplier")) setTimeout(refreshMaterialChoices, 0); });
  ["#custom-supplier-list", "#material-list"].forEach((selector) => $(selector).addEventListener("click", (event) => { if (event.target.matches(".remove-supplier")) event.target.closest(".supplier-entry, .setup-material-row")?.remove(); }));
  refreshMaterialChoices();
  const departmentDetails = {
    "Fournisseur": "Acteur externe. Prépare les palettes après réception d’une commande MP, puis livre selon le délai et la fiabilité indiqués.",
    "Réception": "Le réceptionnaire décharge le camion, contrôle les palettes et place les non-conformes en quarantaine avant d’alerter le pilotage.",
    "Stock MP": "Le magasinier range les matières, suit le stock de sécurité et prépare un kit pour chaque ordre de fabrication.",
    "Production": "Le chef de ligne lance les OF. Les machines travaillent en série : la plus lente fixe la cadence. Les lignes en parallèle additionnent leurs débits.",
    "Contrôle qualité": "Chaque lot est contrôlé. Les pièces conformes passent à l’emballage, les pièces à retoucher retournent en production et les rebuts sont écartés.",
    "Emballage": "Les produits conformes sont mis en colis, étiquetés puis regroupés par six sur une palette avant rangement en stock PF.",
    "Entrepôt PF": "Le magasinier PF range les palettes, prépare les commandes client et signale les niveaux sous le stock minimum.",
    "Client": "Le client commande et reçoit les produits finis. L’OTIF mesure les livraisons complètes et à l’heure.",
    "Pilotage": "Le responsable transmet les commandes MP et les OF, suit OTIF, TRS, qualité et stocks, puis traite les alertes des départements.",
    "Maintenance et PDR": `Le technicien traite une panne à la fois. ${state?.spare_parts || 0} pièce(s) de rechange disponible(s). L’entretien préventif limite les arrêts non planifiés.`,
  };
  document.querySelectorAll(".flow-step").forEach((button) => button.addEventListener("click", () => {
    document.querySelectorAll(".flow-step").forEach((step) => step.classList.toggle("active", step === button));
    selectInteraction({ type: "department", title: button.dataset.department, subtitle: departmentDetails[button.dataset.department] });
    const x = Number(button.dataset.x), z = Number(button.dataset.z);
    if (Number.isFinite(x) && Number.isFinite(z)) setDestination({ x, z });
  }));
  $("#tutorial-next").addEventListener("click", () => advanceTutorial("", true));
  $("#tutorial-skip").addEventListener("click", () => { $("#tutorial").hidden = true; });
  window.addEventListener("keydown", (event) => {
    if (event.key === "1") openOrder();
    if (event.key === "2") $("#inspector").classList.remove("closed");
    if (event.key === "3") { cameraDistance = 23; cameraYaw = 0.48; }
    if (event.key === "4") openProduction();
  });
  cameraPosition();
  animate();
  setTimeout(() => loading.classList.add("hidden"), 700);
}

startGame().catch((error) => {
  console.error(error);
  loading.innerHTML = `<div class="loading-mark">!</div><b>Le monde 3D n’a pas pu démarrer.</b><span>${escapeHTML(error.message)}</span>`;
  showToast(error.message, true);
});
