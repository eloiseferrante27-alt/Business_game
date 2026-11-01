// Registre des assets 3D du monde v3.
// Chaque entrée correspond à une ligne de la checklist « Les assets à créer » du document v3.
// Les modèles sont procéduraux pour l'instant ; pour passer à un vrai modèle (.glb),
// il suffit de remplacer la fonction `build` d'une entrée : le reste du monde ne change pas.

export function createAssets(kit) {
  const { THREE, box, cylinder, floorMark, labelSprite, textPanel } = kit;
  const group = () => new THREE.Group();

  // --------------------------------------------------------------- palettes
  function palletEuro(g) {
    for (const z of [-0.5, 0, 0.5]) box(g, 1.2, 0.1, 0.12, 0xb98d55, 0, 0.05, z, { roughness: 0.95 });
    for (const x of [-0.5, 0, 0.5]) box(g, 0.14, 0.04, 1.1, 0xc9a06a, x, 0.12, 0, { roughness: 0.95 });
    for (let i = 0; i < 5; i++) box(g, 1.2, 0.025, 0.16, 0xd2ab73, 0, 0.155, -0.46 + i * 0.23, { roughness: 0.95 });
  }
  function palletLoad(g, color, wrapped) {
    palletEuro(g);
    for (let layer = 0; layer < 2; layer++) {
      for (const [x, z] of [[-0.3, -0.27], [0.3, -0.27], [-0.3, 0.27], [0.3, 0.27]]) {
        box(g, 0.56, 0.42, 0.5, color, x, 0.39 + layer * 0.43, z, { texture: "cardboard", roughness: 0.95 });
      }
    }
    if (wrapped) {
      box(g, 1.22, 0.9, 1.06, 0xdfeff0, 0, 0.62, 0, { opacity: 0.32, roughness: 0.15, castShadow: false });
      box(g, 0.5, 0.3, 0.01, 0xffffff, 0, 0.75, 0.535, { castShadow: false });
    } else {
      box(g, 1.18, 0.03, 0.04, 0x2c3a37, 0, 1.25, 0, { castShadow: false });
      box(g, 0.04, 0.9, 1.04, 0x2c3a37, 0, 0.82, 0, { castShadow: false });
    }
  }

  // ------------------------------------------------------------------ quais
  function dockDoor(g) {
    // Porte vue de face : ouverture en x, plan de la porte en z = 0.
    box(g, 0.25, 3, 0.3, 0x3f5a52, -1.45, 1.5, 0, { metalness: 0.3 });
    box(g, 0.25, 3, 0.3, 0x3f5a52, 1.45, 1.5, 0, { metalness: 0.3 });
    box(g, 3.15, 0.45, 0.4, 0x3f5a52, 0, 3.05, 0, { metalness: 0.3 });
    const door = box(g, 2.7, 1.1, 0.08, 0xd8d9cf, 0, 2.3, 0, { texture: "ribbed", metalness: 0.2 });
    door.name = "sectional-door";
    for (let i = 0; i < 5; i++) box(g, 0.32, 0.06, 0.04, i % 2 ? 0x2b2f2d : 0xe2b64a, -0.64 + i * 0.32, 1.78, 0.05, { castShadow: false });
    box(g, 2.9, 0.3, 0.25, 0x2b2f2d, 0, 0.18, 0.2, { roughness: 0.9 }); // butoirs
  }
  function dockLeveler(g) {
    box(g, 2.3, 0.08, 1.8, 0x8d9692, 0, 0.06, 0, { metalness: 0.1 });
    for (let i = 0; i < 8; i++) box(g, 0.28, 0.02, 0.1, i % 2 ? 0x2b2f2d : 0xe2b64a, -0.98 + i * 0.28, 0.1, 0.86, { castShadow: false });
    box(g, 2.3, 0.04, 0.35, 0x9aa39f, 0, 0.07, 1.05, { metalness: 0.1 });
  }
  function truck(g, opts) {
    const colors = { fournisseur: 0x5b6f8a, livraison: 0x456b61, client: 0x8a5d7a };
    const body = colors[opts.kind] || 0x456b61;
    box(g, 4.4, 1.7, 2.25, body, -0.6, 1.25, 0, { roughness: 0.6 });
    box(g, 4.42, 0.12, 2.27, 0xe9e7da, -0.6, 2.1, 0);
    box(g, 1.45, 1.65, 2.15, 0xe8e6d8, 2.4, 1.0, 0);
    box(g, 0.06, 0.6, 1.8, 0xa6c5bd, 3.13, 1.35, 0, { metalness: 0.2, roughness: 0.2 });
    box(g, 5.6, 0.18, 1.9, 0x2e3634, 0.1, 0.4, 0);
    for (const wx of [-2.1, -1.3, 2.4]) for (const wz of [-0.95, 0.95]) {
      cylinder(g, 0.42, 0.42, 0.26, 0x252f31, wx, 0.42, wz, 18).rotation.x = Math.PI / 2;
    }
    const sign = labelSprite(opts.label || "CAMION", "#fff9dc", opts.kind === "client" ? "#5d3a52" : opts.kind === "fournisseur" ? "#34465d" : "#28594d");
    sign.scale.set(2.6, 0.6, 1);
    sign.position.set(-0.6, 2.75, 0);
    g.add(sign);
    g.userData.sign = sign;
    if (opts.cargo) {
      const cargo = group();
      cargo.position.set(-1.5, 0.48, 0);
      palletLoad(cargo, opts.kind === "fournisseur" ? 0xb88a55 : 0xa9a37c, opts.kind !== "fournisseur");
      cargo.scale.setScalar(0.85);
      g.add(cargo);
    }
  }
  function palletJack(g) {
    box(g, 0.16, 0.08, 1.2, 0xd23b2f, -0.25, 0.06, 0.1, { metalness: 0.3 });
    box(g, 0.16, 0.08, 1.2, 0xd23b2f, 0.25, 0.06, 0.1, { metalness: 0.3 });
    box(g, 0.7, 0.35, 0.3, 0xd23b2f, 0, 0.22, -0.55, { metalness: 0.3 });
    const handle = box(g, 0.06, 1.0, 0.06, 0x2c3331, 0, 0.75, -0.75, { metalness: 0.3 });
    handle.rotation.x = -0.35;
    box(g, 0.4, 0.06, 0.06, 0x2c3331, 0, 1.2, -0.92);
  }
  function dropZone(g, opts) {
    floorMark(g, opts.w || 3.2, opts.d || 2.4, 0xe8c54a, 0, 0, true, 0.12);
    const word = textPanel(opts.text || "ZONE DE DÉPOSE", 1.8, 0.35, "#e8c54a", "#2b2f2d");
    word.rotation.x = -Math.PI / 2;
    if (opts.flipText) word.rotation.z = Math.PI;
    word.position.set(0, 0.05, (opts.d || 2.4) / 2 - 0.3);
    g.add(word);
  }

  // ------------------------------------------------------- bureaux et postes
  function deskChair(g) {
    box(g, 1.6, 0.06, 0.8, 0xc9b38c, 0, 0.75, 0, { roughness: 0.6 });
    for (const [x, z] of [[-0.74, -0.34], [0.74, -0.34], [-0.74, 0.34], [0.74, 0.34]]) box(g, 0.05, 0.75, 0.05, 0x46514d, x, 0.37, z, { metalness: 0.3 });
    box(g, 0.45, 0.6, 0.6, 0x5f6e68, 0.5, 0.42, 0, { metalness: 0.2 });
    const chair = group();
    chair.position.set(-0.2, 0, 0.75);
    box(chair, 0.5, 0.08, 0.5, 0x2f3d39, 0, 0.5, 0);
    box(chair, 0.5, 0.55, 0.07, 0x2f3d39, 0, 0.8, 0.24);
    cylinder(chair, 0.04, 0.04, 0.45, 0x46514d, 0, 0.25, 0);
    cylinder(chair, 0.28, 0.28, 0.04, 0x46514d, 0, 0.03, 0, 10);
    g.add(chair);
  }
  function computer(g) {
    box(g, 0.62, 0.4, 0.04, 0x1f2b29, 0, 1.08, -0.22);
    box(g, 0.56, 0.33, 0.01, 0x7cc4b8, 0, 1.08, -0.195, { emissive: 0x2c6b61, emissiveIntensity: 0.6, castShadow: false });
    box(g, 0.06, 0.16, 0.06, 0x1f2b29, 0, 0.84, -0.22);
    box(g, 0.45, 0.02, 0.16, 0x2f3836, 0, 0.79, 0.05);
  }
  function barcodeScanner(g) {
    box(g, 0.08, 0.06, 0.18, 0x2a2f2e, 0, 0.82, 0);
    box(g, 0.06, 0.14, 0.06, 0x2a2f2e, 0, 0.73, 0.06);
    box(g, 0.05, 0.02, 0.01, 0xff3b30, 0, 0.82, -0.095, { emissive: 0xff3b30, castShadow: false });
  }
  function labelPrinter(g) {
    box(g, 0.3, 0.22, 0.32, 0xe1e0d6, 0, 0.89, 0);
    box(g, 0.2, 0.01, 0.12, 0xffffff, 0, 0.92, 0.2, { castShadow: false });
  }
  function floorScale(g) {
    box(g, 1.3, 0.08, 1.3, 0x9aa39f, 0, 0.05, 0, { metalness: 0.1 });
    box(g, 0.12, 1.1, 0.08, 0x46514d, 0.75, 0.55, -0.55, { metalness: 0.3 });
    box(g, 0.35, 0.25, 0.12, 0x2f3d39, 0.75, 1.15, -0.55);
    box(g, 0.25, 0.1, 0.01, 0x9bd38a, 0.75, 1.18, -0.49, { emissive: 0x4d8c3a, castShadow: false });
  }
  function hatchedZone(g, opts, color, text) {
    floorMark(g, opts.w || 2.4, opts.d || 2, color, 0, 0, true, 0.14);
    for (let i = -3; i <= 3; i++) {
      const stripe = box(g, 0.08, 0.018, (opts.d || 2) * 1.05, color, i * 0.32, 0.034, 0, { castShadow: false });
      stripe.rotation.y = 0.6;
      stripe.scale.z = 0.55;
    }
    const word = textPanel(text, 1.7, 0.32, `#${color.toString(16).padStart(6, "0")}`, "#ffffff");
    word.rotation.x = -Math.PI / 2;
    if (opts.flipText) word.rotation.z = Math.PI;
    word.position.set(0, 0.05, (opts.d || 2) / 2 + 0.25);
    g.add(word);
  }
  function deliveryNote(g) {
    const sheet = box(g, 0.21, 0.005, 0.3, 0xfdfdf6, 0, 0.785, 0, { castShadow: false });
    sheet.rotation.y = 0.2;
    for (let i = 0; i < 5; i++) box(g, 0.14, 0.002, 0.012, 0x6d7470, 0.01 * i, 0.79, -0.08 + i * 0.04, { castShadow: false });
  }

  // ---------------------------------------------------------------- stock
  function palletRack(g, opts) {
    const bays = opts.bays || 3;
    const width = bays * 1.4;
    for (const x of [-width / 2, width / 2, ...Array.from({ length: bays - 1 }, (_, i) => -width / 2 + (i + 1) * 1.4)]) {
      for (const z of [-0.5, 0.5]) box(g, 0.09, 3.3, 0.09, 0x2f6aa8, x, 1.65, z, { metalness: 0.35 });
    }
    const slots = [];
    for (const level of [0.12, 1.2, 2.28]) {
      for (const z of [-0.5, 0.5]) box(g, width, 0.1, 0.06, 0xe28a2b, 0, level + 0.05, z, { metalness: 0.3 });
      for (let bay = 0; bay < bays; bay++) {
        const pallet = group();
        pallet.position.set(-width / 2 + 0.7 + bay * 1.4, level + 0.1, 0);
        palletLoad(pallet, opts.color || 0xb88a55, opts.wrapped);
        pallet.scale.set(0.95, 0.95, 0.85);
        g.add(pallet);
        slots.push(pallet);
      }
    }
    g.userData.slots = slots;
  }
  function binShelf(g, opts) {
    for (const x of [-0.9, 0.9]) for (const z of [-0.25, 0.25]) box(g, 0.05, 2, 0.05, 0x55615c, x, 1, z, { metalness: 0.3 });
    const bins = [];
    for (const y of [0.3, 0.8, 1.3, 1.8]) {
      box(g, 1.85, 0.04, 0.55, 0x7b8782, 0, y, 0, { metalness: 0.3 });
      for (let i = 0; i < 4; i++) {
        const bin = group();
        bin.position.set(-0.66 + i * 0.44, y + 0.02, 0);
        plasticBin(bin, { color: opts.color });
        g.add(bin);
        bins.push(bin);
      }
    }
    g.userData.slots = bins;
  }
  function plasticBin(g, opts = {}) {
    box(g, 0.38, 0.22, 0.45, opts.color || 0x2f7fc1, 0, 0.11, 0, { roughness: 0.5 });
    box(g, 0.3, 0.02, 0.38, 0x1e2a28, 0, 0.215, 0, { castShadow: false });
  }
  function forklift(g) {
    box(g, 1.4, 0.65, 1.0, 0xd8ad4f, 0, 0.62, 0);
    box(g, 0.85, 0.1, 0.8, 0x354947, -0.1, 1.0, 0);
    box(g, 0.1, 1.85, 0.12, 0x44534c, 0.62, 1.02, -0.43);
    box(g, 0.1, 1.85, 0.12, 0x44534c, 0.62, 1.02, 0.43);
    box(g, 0.72, 0.09, 0.9, 0xc6aa72, 1.05, 0.22, 0);
    box(g, 0.5, 0.1, 0.38, 0x253b39, -0.18, 0.96, 0);
    box(g, 0.12, 0.52, 0.38, 0x253b39, -0.38, 1.18, 0);
    for (const x of [-0.42, 0.42]) for (const z of [-0.51, 0.51]) cylinder(g, 0.23, 0.23, 0.17, 0x293536, x, 0.23, z, 14).rotation.x = Math.PI / 2;
    const beacon = new THREE.Mesh(new THREE.SphereGeometry(0.11, 12, 8), new THREE.MeshStandardMaterial({ color: 0xffb339, emissive: 0xff8a18, emissiveIntensity: 1.4 }));
    beacon.position.set(-0.25, 1.42, -0.28);
    g.add(beacon);
  }
  function chargingStation(g) {
    box(g, 0.6, 1.3, 0.4, 0x2f6a5c, 0, 0.65, 0, { metalness: 0.2 });
    box(g, 0.4, 0.25, 0.02, 0x9bd38a, 0, 1.0, 0.21, { emissive: 0x3d8a2f, castShadow: false });
    const bolt = textPanel("⚡", 0.25, 0.25, "#2f6a5c", "#f1d36b");
    bolt.position.set(0, 0.6, 0.21);
    g.add(bolt);
    const cable = cylinder(g, 0.03, 0.03, 0.9, 0x1d2321, 0.35, 0.5, 0.15, 6);
    cable.rotation.z = 0.6;
    floorMark(g, 1.6, 1.4, 0x2f7d5d, 0, 1, true, 0.08);
  }
  function zoneSign(g, opts) {
    for (const x of [-0.9, 0.9]) cylinder(g, 0.025, 0.025, 1.2, 0x55615c, x, 3.9, 0, 6);
    const panel = textPanel(opts.lines || ["ZONE"], 2.2, 0.75, opts.bg || "#2f5d50", "#fdfbe9");
    panel.position.set(0, 3.2, 0);
    const back = panel.clone();
    back.rotation.y = Math.PI;
    g.add(panel, back);
  }
  function sfCart(g) {
    box(g, 1.1, 0.06, 0.7, 0x55615c, 0, 0.35, 0, { metalness: 0.3 });
    box(g, 1.1, 0.06, 0.7, 0x55615c, 0, 0.85, 0, { metalness: 0.3 });
    for (const x of [-0.52, 0.52]) for (const z of [-0.32, 0.32]) box(g, 0.04, 1.0, 0.04, 0x55615c, x, 0.55, z, { metalness: 0.3 });
    for (const x of [-0.45, 0.45]) for (const z of [-0.28, 0.28]) cylinder(g, 0.07, 0.07, 0.05, 0x1d2321, x, 0.07, z, 10).rotation.x = Math.PI / 2;
    for (const y of [0.38, 0.88]) for (const x of [-0.3, 0.3]) {
      const tray = group();
      tray.position.set(x, y, 0);
      plasticBin(tray, { color: 0xd9a441 });
      g.add(tray);
      for (let i = 0; i < 3; i++) cylinder(g, 0.06, 0.06, 0.08, 0x9fb3ad, x - 0.1 + i * 0.1, y + 0.26, 0, 10, { metalness: 0.3 });
    }
  }

  // ------------------------------------------------------ chaîne de production
  function stackLight(g) {
    cylinder(g, 0.03, 0.03, 0.3, 0x46514d, 0, 0.15, 0, 6);
    const lights = {};
    [["vert", 0x46c26b], ["orange", 0xf1b43a], ["rouge", 0xe0483c]].forEach(([name, color], index) => {
      const mesh = new THREE.Mesh(new THREE.CylinderGeometry(0.075, 0.075, 0.14, 12), new THREE.MeshStandardMaterial({ color, emissive: color, emissiveIntensity: 0.15, roughness: 0.3 }));
      mesh.position.y = 0.66 - index * 0.15;
      g.add(mesh);
      lights[name] = mesh;
    });
    cylinder(g, 0.08, 0.08, 0.04, 0x2a302e, 0, 0.75, 0, 12);
    g.userData.lights = lights;
  }
  function machine(g, opts) {
    const accent = opts.accent || 0x70c1bb;
    const op = opts.rank || 1;
    box(g, 1.5, 0.12, 1.1, 0x2c3a37, 0, 0.06, 0, { metalness: 0.3 });
    if (op === 1) { // Préparation : presse
      box(g, 1.3, 0.8, 0.9, 0x455d58, 0, 0.52, 0, { metalness: 0.2 });
      for (const x of [-0.5, 0.5]) box(g, 0.14, 1.3, 0.14, 0x5b6f69, x, 1.55, 0, { metalness: 0.3 });
      box(g, 1.3, 0.3, 0.8, accent, 0, 2.25, 0);
      cylinder(g, 0.12, 0.12, 0.6, 0xbfc4b2, 0, 1.75, 0, 12, { metalness: 0.3 });
    } else if (op === 2) { // Assemblage : îlot robotisé
      box(g, 1.3, 0.75, 0.9, 0x5b6f69, 0, 0.5, 0, { metalness: 0.2 });
      cylinder(g, 0.18, 0.22, 0.3, accent, 0.3, 1.02, 0, 14);
      const arm = box(g, 0.14, 0.75, 0.14, 0xe0b44a, 0.3, 1.5, 0, { metalness: 0.2 });
      arm.rotation.z = 0.5;
      const fore = box(g, 0.12, 0.6, 0.12, 0xe0b44a, -0.05, 1.85, 0, { metalness: 0.2 });
      fore.rotation.z = 1.4;
      box(g, 0.2, 0.12, 0.2, 0x2c3a37, -0.35, 1.8, 0);
    } else if (op === 3) { // Finition : centre d'usinage fermé (goulot)
      box(g, 1.45, 1.7, 1.05, 0x748a7d, 0, 0.97, 0, { metalness: 0.15 });
      box(g, 0.7, 0.6, 0.02, 0x9fd0d6, -0.15, 1.15, 0.53, { opacity: 0.55, roughness: 0.1 });
      box(g, 1.47, 0.16, 1.07, accent, 0, 1.86, 0);
      box(g, 0.28, 0.4, 0.04, 0x223c3c, 0.48, 1.25, 0.53);
    } else { // Vérification : tunnel de contrôle
      box(g, 1.4, 0.55, 0.8, 0x455d58, 0, 0.4, 0, { metalness: 0.2 });
      for (const x of [-0.55, 0.55]) box(g, 0.1, 1.2, 0.85, 0x5b6f69, x, 1.25, 0, { metalness: 0.3 });
      box(g, 1.3, 0.12, 0.9, accent, 0, 1.9, 0);
      cylinder(g, 0.08, 0.06, 0.18, 0x1d2321, 0, 1.75, 0, 12);
    }
    const light = group();
    light.position.set(0.62, opts.rank === 3 ? 1.94 : 1.2, -0.42);
    stackLight(light);
    g.add(light);
    g.userData.lights = light.userData.lights;
    const tag = labelSprite(opts.tag || `M${op}`, "#f3f1df", "#245149");
    tag.scale.set(1.2, 0.3, 1);
    tag.position.set(0, 2.65, 0);
    g.add(tag);
  }
  function bufferTable(g) {
    box(g, 0.8, 0.05, 0.6, 0x9aa49f, 0, 0.75, 0, { metalness: 0.3 });
    for (const x of [-0.35, 0.35]) for (const z of [-0.25, 0.25]) box(g, 0.04, 0.75, 0.04, 0x55615c, x, 0.37, z, { metalness: 0.3 });
    for (let i = 0; i < 3; i++) cylinder(g, 0.08, 0.08, 0.1, 0xc7cdbf, -0.2 + i * 0.2, 0.83, 0, 10, { metalness: 0.3 });
  }
  function conveyor(g, opts) {
    const length = opts.length || 2;
    box(g, length, 0.12, 0.6, 0x425b54, 0, 0.62, 0);
    for (const x of [-length / 2 + 0.1, length / 2 - 0.1]) for (const z of [-0.25, 0.25]) box(g, 0.06, 0.6, 0.06, 0x55615c, x, 0.3, z);
    for (let i = 0; i < Math.floor(length / 0.25); i++) cylinder(g, 0.05, 0.05, 0.56, 0xbfc4b2, -length / 2 + 0.12 + i * 0.25, 0.7, 0, 8).rotation.x = Math.PI / 2;
  }
  function workbench(g) {
    box(g, 1.6, 0.08, 0.75, 0xa77d4a, 0, 0.88, 0, { roughness: 0.9 });
    box(g, 1.5, 0.06, 0.65, 0x55615c, 0, 0.25, 0);
    for (const x of [-0.74, 0.74]) for (const z of [-0.32, 0.32]) box(g, 0.06, 0.88, 0.06, 0x46514d, x, 0.44, z, { metalness: 0.3 });
    box(g, 1.6, 0.6, 0.04, 0x7b8782, 0, 1.25, -0.36, { metalness: 0.2 });
    for (let i = 0; i < 5; i++) box(g, 0.05, 0.2, 0.02, 0x2c3331, -0.6 + i * 0.3, 1.3, -0.33);
  }
  function wipPart(g) {
    cylinder(g, 0.12, 0.12, 0.16, 0xc7cdbf, 0, 0.08, 0, 14, { metalness: 0.3 });
    cylinder(g, 0.05, 0.05, 0.18, 0x6f7a74, 0, 0.09, 0, 10, { metalness: 0.3 });
  }
  function lineBoard(g) {
    for (const x of [-0.85, 0.85]) box(g, 0.06, 2, 0.06, 0x46514d, x, 1, 0);
    const panel = textPanel(["TABLEAU DE LIGNE", "OF · cadence · arrêts"], 1.7, 1, "#f2f1e8", "#20403b");
    panel.position.set(0, 1.5, 0.04);
    g.add(panel);
    g.userData.panelHolder = { parent: g, y: 1.5 };
  }
  function wasteBin(g, opts = {}) {
    cylinder(g, 0.3, 0.26, 0.7, opts.color || 0x3f4a47, 0, 0.35, 0, 14);
    cylinder(g, 0.31, 0.31, 0.05, 0x2a302e, 0, 0.71, 0, 14);
  }

  // ---------------------------------------------------------- contrôle qualité
  function inspectionTable(g) {
    box(g, 1.8, 0.06, 0.9, 0x1f3b37, 0, 0.88, 0, { roughness: 0.4 });
    for (const x of [-0.85, 0.85]) for (const z of [-0.4, 0.4]) box(g, 0.06, 0.88, 0.06, 0x55615c, x, 0.44, z);
    cylinder(g, 0.25, 0.25, 0.04, 0xe9e8df, 0.5, 0.93, 0, 20); // lampe loupe
    const arm = box(g, 0.04, 0.6, 0.04, 0x55615c, 0.7, 1.2, -0.3);
    arm.rotation.z = -0.3;
  }
  function measuringTools(g) {
    box(g, 0.25, 0.015, 0.05, 0xc9cfc8, 0, 0.92, 0, { metalness: 0.3 }); // pied à coulisse
    box(g, 0.02, 0.015, 0.09, 0xc9cfc8, -0.1, 0.92, 0.04, { metalness: 0.3 });
    cylinder(g, 0.06, 0.06, 0.04, 0xf1d36b, 0.25, 0.93, 0.05, 14); // mètre ruban
  }
  function testBench(g) {
    box(g, 1.5, 0.9, 0.8, 0x455d58, 0, 0.45, 0, { metalness: 0.2 });
    box(g, 1.5, 0.08, 0.8, 0x2c3a37, 0, 0.94, 0);
    box(g, 0.6, 0.45, 0.35, 0x223c3c, -0.35, 1.2, -0.15);
    box(g, 0.45, 0.25, 0.01, 0x9bd38a, -0.35, 1.25, 0.03, { emissive: 0x3d8a2f, castShadow: false });
    cylinder(g, 0.08, 0.08, 0.35, 0xbfc4b2, 0.4, 1.15, 0, 12, { metalness: 0.3 });
  }

  // ------------------------------------------------------------------ emballage
  function packingTable(g) {
    box(g, 2, 0.06, 1, 0xc9b38c, 0, 0.88, 0, { roughness: 0.6 });
    for (const x of [-0.95, 0.95]) for (const z of [-0.45, 0.45]) box(g, 0.06, 0.88, 0.06, 0x55615c, x, 0.44, z);
    cylinder(g, 0.05, 0.05, 1.2, 0x8a7a5a, 0, 1.35, -0.45, 10).rotation.z = Math.PI / 2; // rouleau de papier
  }
  function cartons(g) {
    box(g, 0.42, 0.32, 0.36, 0xb98d55, -0.3, 1.07, 0, { texture: "cardboard" }); // fermé
    box(g, 0.44, 0.02, 0.06, 0xd9c08a, -0.3, 1.24, 0, { castShadow: false }); // ruban
    const open = group();
    open.position.set(0.3, 0.91, 0);
    box(open, 0.42, 0.3, 0.02, 0xb98d55, 0, 0.15, -0.18, { texture: "cardboard" });
    box(open, 0.42, 0.3, 0.02, 0xb98d55, 0, 0.15, 0.18, { texture: "cardboard" });
    box(open, 0.02, 0.3, 0.36, 0xb98d55, -0.2, 0.15, 0, { texture: "cardboard" });
    box(open, 0.02, 0.3, 0.36, 0xb98d55, 0.2, 0.15, 0, { texture: "cardboard" });
    const flap = box(open, 0.42, 0.02, 0.2, 0xb98d55, 0, 0.36, 0.27, { texture: "cardboard" });
    flap.rotation.x = 0.8;
    g.add(open);
    const tape = cylinder(g, 0.07, 0.07, 0.05, 0xd9c08a, 0.7, 0.94, 0.1, 14);
    tape.rotation.x = Math.PI / 2;
  }
  function tableScale(g) {
    box(g, 0.4, 0.05, 0.4, 0x6c7873, 0, 0.94, 0, { metalness: 0.3 });
    box(g, 0.18, 0.08, 0.04, 0x2f3d39, 0, 0.95, 0.24);
  }
  function palletWrapper(g) {
    cylinder(g, 0.9, 0.9, 0.1, 0x7d8984, 0, 0.06, 0, 28, { metalness: 0.15 });
    box(g, 0.25, 2.4, 0.25, 0x2f6a5c, 1.15, 1.2, 0, { metalness: 0.3 });
    box(g, 0.3, 0.35, 0.3, 0xe0b44a, 0.92, 1.1, 0);
    cylinder(g, 0.08, 0.08, 0.32, 0xdfeff0, 0.8, 1.1, 0, 12, { opacity: 0.7 });
    const pallet = group();
    pallet.position.set(0, 0.1, 0);
    palletLoad(pallet, 0xa9a37c, true);
    g.add(pallet);
  }

  // -------------------------------------------------- bureau d'étude, maintenance
  function planningBoard(g) {
    for (const x of [-1.1, 1.1]) box(g, 0.06, 2.1, 0.06, 0x46514d, x, 1.05, 0);
    const panel = textPanel(["PLANNING", "OF · gammes · temps"], 2.2, 1.2, "#f2f1e8", "#20403b");
    panel.position.set(0, 1.45, 0.04);
    g.add(panel);
    const colors = [0x70c1bb, 0xd4a45c, 0x9cad8d, 0xc6a9e7];
    for (let row = 0; row < 4; row++) box(g, 0.3 + row * 0.25, 0.1, 0.01, colors[row], -0.6 + row * 0.15, 1.2 - row * 0.15 + 0.2, 0.06, { castShadow: false });
  }
  function fileCabinet(g) {
    box(g, 0.9, 1.9, 0.5, 0x7b8782, 0, 0.95, 0, { metalness: 0.3 });
    for (let i = 0; i < 4; i++) {
      box(g, 0.82, 0.38, 0.01, 0x8d9994, 0, 0.3 + i * 0.45, 0.255, { metalness: 0.3 });
      box(g, 0.2, 0.04, 0.03, 0x2c3331, 0, 0.42 + i * 0.45, 0.27);
    }
  }
  function viseBench(g) {
    workbench(g);
    box(g, 0.2, 0.18, 0.25, 0x2f6aa8, 0.5, 1.01, 0.1, { metalness: 0.3 });
    box(g, 0.24, 0.06, 0.05, 0x55615c, 0.5, 1.05, 0.26, { metalness: 0.3 });
  }
  function toolCart(g) {
    box(g, 0.8, 0.95, 0.5, 0xc0392b, 0, 0.55, 0, { metalness: 0.3 });
    for (let i = 0; i < 5; i++) box(g, 0.72, 0.012, 0.01, 0x2c3331, 0, 0.2 + i * 0.17, 0.255, { castShadow: false });
    for (const x of [-0.32, 0.32]) for (const z of [-0.2, 0.2]) cylinder(g, 0.05, 0.05, 0.04, 0x1d2321, x, 0.05, z, 10).rotation.x = Math.PI / 2;
  }
  function spareCabinet(g) {
    box(g, 1.4, 2, 0.55, 0x2f5d50, 0, 1, 0, { metalness: 0.3 });
    box(g, 0.02, 1.9, 0.01, 0x1d2321, 0, 1, 0.28, { castShadow: false });
    box(g, 0.04, 0.25, 0.03, 0xd8d6c9, 0.08, 1.05, 0.29);
  }
  function sparePart(g) {
    cylinder(g, 0.16, 0.16, 0.08, 0x8d9994, 0, 0.04, 0, 16, { metalness: 0.3 });
    for (let i = 0; i < 8; i++) {
      const tooth = box(g, 0.06, 0.08, 0.06, 0x8d9994, Math.cos(i * Math.PI / 4) * 0.18, 0.04, Math.sin(i * Math.PI / 4) * 0.18, { metalness: 0.3 });
      tooth.rotation.y = -i * Math.PI / 4;
    }
  }
  function lockoutKit(g) {
    box(g, 0.6, 0.8, 0.08, 0xe0483c, 0, 1.5, 0);
    for (let i = 0; i < 3; i++) {
      box(g, 0.1, 0.12, 0.05, 0xe0b44a, -0.18 + i * 0.18, 1.45, 0.06, { metalness: 0.3 });
      const shackle = new THREE.Mesh(new THREE.TorusGeometry(0.035, 0.01, 6, 12, Math.PI), kit.material(0xc9cfc8, 0.3, 0.7));
      shackle.position.set(-0.18 + i * 0.18, 1.52, 0.06);
      g.add(shackle);
    }
    const head = textPanel("CONSIGNATION", 0.55, 0.12, "#e0483c", "#ffffff");
    head.position.set(0, 1.78, 0.045);
    g.add(head);
  }
  function interventionBoard(g) {
    for (const x of [-0.85, 0.85]) box(g, 0.06, 2, 0.06, 0x46514d, x, 1, 0);
    const panel = textPanel(["INTERVENTIONS", "pannes · préventif"], 1.7, 1, "#f2f1e8", "#7a3b26");
    panel.position.set(0, 1.5, 0.04);
    g.add(panel);
  }

  // ---------------------------------------------------------------- commun
  function fireExtinguisher(g) {
    cylinder(g, 0.11, 0.11, 0.55, 0xd23b2f, 0, 0.6, 0, 14);
    cylinder(g, 0.04, 0.04, 0.1, 0x2c3331, 0, 0.92, 0, 8);
    box(g, 0.3, 0.3, 0.02, 0xd23b2f, 0, 1.4, -0.12, { castShadow: false });
  }
  function pedestrianDoor(g) {
    box(g, 0.12, 2.3, 0.2, 0x3f5a52, -0.6, 1.15, 0);
    box(g, 0.12, 2.3, 0.2, 0x3f5a52, 0.6, 1.15, 0);
    box(g, 1.32, 0.15, 0.2, 0x3f5a52, 0, 2.35, 0);
    const leaf = box(g, 1.05, 2.15, 0.05, 0x9bc8c2, 0.35, 1.08, 0.4, { opacity: 0.5, roughness: 0.1 });
    leaf.rotation.y = -1.2;
    const sign = textPanel("ACCÈS PIÉTONS", 1.2, 0.25, "#2f7d5d", "#ffffff");
    sign.position.set(0, 2.6, 0.11);
    g.add(sign);
  }
  function blockSign(g, opts) {
    const sign = labelSprite(opts.text.toUpperCase(), "#f3f1df", "#245149");
    sign.scale.set(Math.min(opts.width || 4, 4.2), 0.62, 1);
    sign.position.set(0, opts.y || 4.3, 0);
    g.add(sign);
    if (opts.agents) {
      const agents = labelSprite(opts.agents, "#dfe9df", "#36564f");
      agents.scale.set(Math.min(opts.width || 4, 4.2) * 0.85, 0.42, 1);
      agents.position.set(0, (opts.y || 4.3) - 0.55, 0);
      g.add(agents);
    }
  }
  function tabletDevice(g) {
    box(g, 0.34, 0.24, 0.025, 0x1d2321, 0, 0, 0, { roughness: 0.3 });
    box(g, 0.3, 0.2, 0.005, 0x7cc4b8, 0, 0, 0.014, { emissive: 0x3d9a8a, emissiveIntensity: 0.9, castShadow: false });
  }

  // La checklist : identifiant → libellé de la v3, bloc, constructeur.
  const REGISTRY = {
    quai_porte_sectionnelle: { label: "Quai avec porte sectionnelle", block: "Quai de déchargement", build: dockDoor },
    niveleur_quai: { label: "Niveleur de quai (rampe)", block: "Quai de déchargement", build: dockLeveler },
    camion_fournisseur: { label: "Camion fournisseur", block: "Quai de déchargement", build: (g, o) => truck(g, { ...o, kind: "fournisseur" }) },
    palette_mp: { label: "Palette Europe avec sa charge de MP", block: "Quai de déchargement", build: (g) => palletLoad(g, 0xb88a55, false) },
    transpalette: { label: "Transpalette manuel", block: "Quai de déchargement", build: palletJack },
    zone_depose: { label: "Zone de dépose (marquage au sol)", block: "Quai de déchargement", build: dropZone },

    bureau_chaise: { label: "Bureau et chaise", block: "Bureau de réception", build: deskChair },
    ordinateur: { label: "Ordinateur", block: "Bureau de réception", build: computer },
    lecteur_code_barres: { label: "Lecteur code-barres", block: "Bureau de réception", build: barcodeScanner },
    imprimante_etiquettes: { label: "Imprimante d’étiquettes", block: "Bureau de réception", build: labelPrinter },
    balance_sol: { label: "Balance au sol", block: "Bureau de réception", build: floorScale },
    zone_quarantaine: { label: "Zone de quarantaine (marquage rouge)", block: "Bureau de réception", build: (g, o) => hatchedZone(g, o, 0xd23b2f, "QUARANTAINE") },
    bon_livraison: { label: "Bon de livraison (document)", block: "Bureau de réception", build: deliveryNote },

    rack_palettes: { label: "Rack à palettes (un module, répété)", block: "Stock", build: palletRack },
    etagere_bacs: { label: "Étagère à bacs", block: "Stock", build: binShelf },
    bac_plastique: { label: "Bac plastique", block: "Stock", build: plasticBin },
    chariot_elevateur: { label: "Chariot élévateur", block: "Stock", build: forklift },
    borne_recharge: { label: "Borne de recharge", block: "Stock", build: chargingStation },
    panneau_zone: { label: "Panneau de zone (MP, semi-finis, PF)", block: "Stock", build: zoneSign },
    chariot_semi_finis: { label: "Bac ou chariot de pièces semi-finies", block: "Stock de semi-finis", build: sfCart },
    palette_pf_filmee: { label: "Palette de produits finis filmée", block: "Stock de produits finis", build: (g) => palletLoad(g, 0xa9a37c, true) },

    machine: { label: "Machine : un modèle par opération (M1 à M4)", block: "Chaîne de production", build: machine },
    voyant_etat: { label: "Voyant d’état (colonne lumineuse)", block: "Chaîne de production", build: stackLight },
    table_attente: { label: "Table d’attente entre deux machines", block: "Chaîne de production", build: bufferTable },
    convoyeur: { label: "Convoyeur ou chariot de transfert", block: "Chaîne de production", build: conveyor },
    etabli: { label: "Établi pour les postes manuels", block: "Chaîne de production", build: workbench },
    piece_en_cours: { label: "Pièce en cours de fabrication", block: "Chaîne de production", build: wipPart },
    tableau_ligne: { label: "Tableau de ligne (OF, cadence, arrêts)", block: "Chaîne de production", build: lineBoard },
    bac_dechets: { label: "Bac à déchets", block: "Chaîne de production", build: wasteBin },

    table_controle: { label: "Table de contrôle", block: "Contrôle qualité", build: inspectionTable },
    instruments_mesure: { label: "Instruments de mesure (pied à coulisse, mètre)", block: "Contrôle qualité", build: measuringTools },
    banc_essai: { label: "Banc d’essai", block: "Contrôle qualité", build: testBench },
    zone_conforme: { label: "Zone « conforme » (marquage vert)", block: "Contrôle qualité", build: (g, o) => hatchedZone(g, o, 0x2f9d5d, "CONFORME") },
    zone_retouche: { label: "Zone « à retoucher » (marquage orange)", block: "Contrôle qualité", build: (g, o) => hatchedZone(g, o, 0xe08a2b, "À RETOUCHER") },
    bac_rebut: { label: "Bac à rebut", block: "Contrôle qualité", build: (g) => wasteBin(g, { color: 0xd23b2f }) },

    table_emballage: { label: "Table d’emballage", block: "Emballage", build: packingTable },
    carton_ruban: { label: "Carton (fermé et ouvert) et ruban adhésif", block: "Emballage", build: cartons },
    balance_table: { label: "Balance de table", block: "Emballage", build: tableScale },
    filmeuse: { label: "Filmeuse de palettes", block: "Emballage", build: palletWrapper },

    tableau_planning: { label: "Tableau de planning", block: "Bureau d’étude", build: planningBoard },
    armoire_dossiers: { label: "Armoire à dossiers (gammes, nomenclatures)", block: "Bureau d’étude", build: fileCabinet },

    etabli_etau: { label: "Établi avec étau", block: "Maintenance et stock PDR", build: viseBench },
    servante_outils: { label: "Servante d’outils (chariot à tiroirs)", block: "Maintenance et stock PDR", build: toolCart },
    armoire_pdr: { label: "Armoire à pièces de rechange", block: "Maintenance et stock PDR", build: spareCabinet },
    piece_rechange: { label: "Pièce de rechange (modèle générique)", block: "Maintenance et stock PDR", build: sparePart },
    kit_consignation: { label: "Kit de consignation (cadenas)", block: "Maintenance et stock PDR", build: lockoutKit },
    tableau_interventions: { label: "Tableau des interventions", block: "Maintenance et stock PDR", build: interventionBoard },

    camion_livraison: { label: "Camion de livraison client", block: "Logistique & Transport", build: (g, o) => truck(g, { ...o, kind: "livraison" }) },
    zone_preparation: { label: "Zone de préparation des expéditions (marquage au sol)", block: "Logistique & Transport", build: (g, o) => dropZone(g, { ...o, text: "PRÉPARATION EXPÉDITIONS" }) },
    camion_client: { label: "Camion d’un client venu charger", block: "Logistique & Transport", build: (g, o) => truck(g, { ...o, kind: "client" }) },

    porte_pietons: { label: "Porte d’accès piétons", block: "Commun", build: pedestrianDoor },
    panneau_bloc: { label: "Panneau de signalisation du bloc", block: "Commun", build: blockSign },
    extincteur: { label: "Extincteur", block: "Commun", build: fireExtinguisher },
    tablette: { label: "Tablette du joueur", block: "Joueur", build: tabletDevice },
  };

  function make(id, opts = {}) {
    const entry = REGISTRY[id];
    if (!entry) throw new Error(`Asset inconnu : ${id}`);
    const g = group();
    g.name = id;
    entry.build(g, opts);
    g.userData.asset = { id, label: entry.label, block: entry.block };
    return g;
  }

  return { REGISTRY, make };
}
