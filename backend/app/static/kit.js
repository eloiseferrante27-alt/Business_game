// Primitives partagées par le monde 3D : matériaux, boîtes, cylindres, étiquettes.
import * as THREE from "./three.module.js";

export function createKit(renderer) {
  function grainTexture(base, kind, size = 128) {
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = size;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = `#${base.toString(16).padStart(6, "0")}`;
    ctx.fillRect(0, 0, size, size);
    for (let i = 0; i < size * size * 0.12; i++) {
      const v = Math.floor(105 + Math.random() * 100);
      ctx.fillStyle = `rgba(${v},${v},${v},${Math.random() * 0.1})`;
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
    } else if (kind === "ribbed") {
      ctx.fillStyle = "rgba(20,30,28,.18)";
      for (let y = 0; y < size; y += 12) ctx.fillRect(0, y, size, 2);
    }
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
    tex.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
    return tex;
  }

  const textures = {
    concrete: grainTexture(0xb5b8ae, "concrete"),
    cardboard: grainTexture(0xb58958, "cardboard"),
    steel: grainTexture(0x63736e, "steel"),
    ribbed: grainTexture(0xd8d9cf, "ribbed"),
  };
  const materialCache = new Map();

  function material(color, roughness = 0.8, metalness = 0, texture = null, options = {}) {
    const key = `${color}|${roughness}|${metalness}|${texture}|${options.emissive ?? ""}|${options.opacity ?? ""}`;
    if (!options.unique && materialCache.has(key)) return materialCache.get(key);
    const map = texture ? textures[texture].clone() : null;
    if (map) {
      map.needsUpdate = true;
      const repeat = { concrete: [7, 5], ribbed: [1, 2] }[texture] || [1.2, 1.2];
      map.repeat.set(...repeat);
    }
    const mat = new THREE.MeshStandardMaterial({ color, map, roughness, metalness });
    if (options.emissive !== undefined) { mat.emissive.setHex(options.emissive); mat.emissiveIntensity = options.emissiveIntensity ?? 0.6; }
    if (options.opacity !== undefined) { mat.transparent = true; mat.opacity = options.opacity; mat.depthWrite = false; }
    if (!options.unique) materialCache.set(key, mat);
    return mat;
  }

  function box(parent, width, height, depth, color, x, y, z, options = {}) {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(width, height, depth),
      material(color, options.roughness ?? 0.82, options.metalness ?? 0, options.texture ?? null, options),
    );
    mesh.position.set(x, y, z);
    mesh.castShadow = options.castShadow !== false;
    mesh.receiveShadow = true;
    parent.add(mesh);
    return mesh;
  }

  function cylinder(parent, radiusTop, radiusBottom, height, color, x, y, z, segments = 12, options = {}) {
    const mesh = new THREE.Mesh(
      new THREE.CylinderGeometry(radiusTop, radiusBottom, height, segments),
      material(color, options.roughness ?? 0.8, options.metalness ?? 0, null, options),
    );
    mesh.position.set(x, y, z);
    mesh.castShadow = options.castShadow !== false;
    mesh.receiveShadow = true;
    parent.add(mesh);
    return mesh;
  }

  // Marquage au sol : un rectangle plat (plein ou en bordure).
  function floorMark(parent, width, depth, color, x, z, outline = false, thickness = 0.1) {
    if (!outline) return box(parent, width, 0.02, depth, color, x, 0.035, z, { castShadow: false, roughness: 0.6 });
    const group = new THREE.Group();
    box(group, width, 0.02, thickness, color, 0, 0.036, -depth / 2, { castShadow: false });
    box(group, width, 0.02, thickness, color, 0, 0.036, depth / 2, { castShadow: false });
    box(group, thickness, 0.02, depth, color, -width / 2, 0.036, 0, { castShadow: false });
    box(group, thickness, 0.02, depth, color, width / 2, 0.036, 0, { castShadow: false });
    group.position.set(x, 0, z);
    parent.add(group);
    return group;
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

  // Panneau plat (texte peint sur une plaque), pour la signalisation et les tableaux.
  function textPanel(lines, width = 1.6, height = 0.9, bg = "#20403b", fg = "#eef3e3") {
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = Math.round(512 * height / width);
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = bg;
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = fg;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    const list = Array.isArray(lines) ? lines : [lines];
    const size = Math.min(64, canvas.height / (list.length + 0.6));
    list.forEach((line, i) => {
      ctx.font = `${i === 0 ? 700 : 500} ${i === 0 ? size : size * 0.72}px Arial`;
      ctx.fillText(line, canvas.width / 2, (canvas.height / (list.length + 1)) * (i + 1), canvas.width - 30);
    });
    const texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(width, height), new THREE.MeshStandardMaterial({ map: texture, roughness: 0.7 }));
    return mesh;
  }

  return { THREE, textures, material, box, cylinder, floorMark, labelSprite, textPanel };
}
