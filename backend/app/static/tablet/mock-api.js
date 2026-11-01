(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = { createMockApi: factory };
  } else {
    root.GMixTabletAPI = api;
  }
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const RIGHT_MESSAGES = {
    verrouille: "Modification interdite : le formateur a fixé ce réglage pour toute la partie.",
    initial: "Modification interdite : ce réglage ne pouvait être choisi qu’avant le début de la partie.",
    limite: "Modification interdite : nombre de changements autorisés atteint pour cette période."
  };

  const tools = [
    { id: "tableur", name: "Tableur", description: "Calculs et comparaisons avec les données de la page." },
    { id: "carte", name: "Carte du monde", description: "Usine, partenaires, trajets et crises." },
    { id: "graphiques", name: "Graphiques", description: "Courbes de KPIs et Pareto des causes." },
    { id: "planning", name: "Planning", description: "OF, camions, expéditions et préventifs." },
    { id: "journal", name: "Journal", description: "Événements filtrables par page, type et cause." }
  ].map((tool) => ({ ...tool, available: true }));

  const departments = [
    {
      id: "fournisseurs", name: "Fournisseurs", shortName: "Fournisseurs", status: "orange",
      description: "Offres, commandes et trajets d’approvisionnement.",
      kpis: [
        { label: "OTIF fournisseur", value: "91,8", unit: "%", trend: "+1,2 pt", direction: "up" },
        { label: "Coût d’achat livré", value: "8,42", unit: "€ / PF", trend: "Stable", direction: "flat" },
        { label: "Commandes en transit", value: "6", unit: "commandes", trend: "2 arrivées aujourd’hui", direction: "flat" }
      ],
      configurations: [
        { id: "offre-principale", label: "Offre principale par article", value: "Offre active de la configuration", right: "libre" },
        { id: "mode-commande", label: "Mode de commande", value: "Automatique au point de commande", right: "initial" }
      ],
      worldParameters: [{ label: "Délai effectif moyen", value: "Fourni par le moteur" }],
      actions: ["Passer une commande manuelle", "Changer d’offre"]
    },
    {
      id: "quai-dechargement", name: "Quai de déchargement", shortName: "Déchargement", status: "vert",
      description: "Créneaux, files de camions et déchargement.",
      kpis: [
        { label: "Camions en attente", value: "1", unit: "camion", trend: "Attente 12 min", direction: "flat" },
        { label: "Respect des créneaux", value: "94", unit: "%", trend: "+2 pts", direction: "up" }
      ],
      configurations: [
        { id: "creneau-reception", label: "Créneau de réception", value: "8 h – 10 h", right: "initial" },
        { id: "ordre-passage", label: "Ordre de passage des camions", value: "Premier arrivé, premier servi", right: "libre" }
      ],
      worldParameters: [{ label: "Camions à quai en même temps", value: "1" }, { label: "Capacité de la zone de dépose", value: "6 palettes" }],
      actions: ["Faire passer un camion en priorité"]
    },
    {
      id: "reception", name: "Bureau de réception", shortName: "Réception", status: "vert",
      description: "Contrôle des livraisons et mise en stock.",
      kpis: [
        { label: "Palettes contrôlées", value: "18", unit: "palettes", trend: "Aujourd’hui", direction: "flat" },
        { label: "Non-conformités", value: "1,4", unit: "%", trend: "−0,3 pt", direction: "up" }
      ],
      configurations: [
        { id: "niveau-controle", label: "Niveau de contrôle", value: "100 % des palettes", right: "libre" },
        { id: "decision-non-conforme", label: "Décision sur non-conforme", value: "Quarantaine puis renvoi", right: "libre" }
      ],
      worldParameters: [{ label: "Temps de contrôle", value: "5 min / palette" }, { label: "Capacité de la zone de quarantaine", value: "2 palettes" }],
      actions: ["Contrôler une palette", "Libérer la quarantaine"]
    },
    {
      id: "stock", name: "Stock", shortName: "Stock", status: "rouge",
      description: "Matières premières, semi-finis et produits finis.",
      kpis: [
        { label: "Couverture", value: "3,2", unit: "jours", trend: "−0,4 jour", direction: "down" },
        { label: "Ruptures", value: "2", unit: "articles", trend: "1 rupture de kit", direction: "down" },
        { label: "Taux de remplissage", value: "71", unit: "%", trend: "Stable", direction: "flat" }
      ],
      configurations: [
        { id: "point-commande", label: "Point de commande", value: "Valeur de la configuration", right: "libre" },
        { id: "methode-reapprovisionnement", label: "Méthode de réapprovisionnement", value: "Point de commande", right: "initial" },
        { id: "methode-sortie", label: "Méthode de sortie", value: "FIFO", right: "verrouille" }
      ],
      worldParameters: [{ label: "Emplacements MP", value: "24" }, { label: "Emplacements PF", value: "20 palettes" }],
      actions: ["Lancer un inventaire", "Demander un kit en urgence"]
    },
    {
      id: "production", name: "Chaîne de production", shortName: "Production", status: "orange",
      description: "Lignes, ordres de fabrication et goulot.",
      kpis: [
        { label: "Production", value: "1 240", unit: "produits", trend: "96 % des OF", direction: "up" },
        { label: "TRS", value: "78,6", unit: "%", trend: "+2,1 pts", direction: "up" },
        { label: "Goulot", value: "M3", unit: "", trend: "Débit réel le plus faible", direction: "flat" }
      ],
      configurations: [
        { id: "taille-lot", label: "Taille de lot (OF)", value: "20 produits", right: "libre" },
        { id: "regle-lancement", label: "Règle de lancement des OF", value: "À la commande client", right: "initial" },
        { id: "nomenclature-gamme", label: "Nomenclature et gamme", value: "Valeurs de la configuration", right: "verrouille" }
      ],
      worldParameters: [{ label: "Nombre de lignes", value: "3, identiques" }],
      actions: ["Lancer un OF", "Prioriser un OF", "Appeler la maintenance"]
    },
    {
      id: "qualite", name: "Contrôle qualité", shortName: "Qualité", status: "vert",
      description: "Contrôles, rebuts, retouches et lots bloqués.",
      kpis: [
        { label: "Taux de qualité", value: "97,2", unit: "%", trend: "+0,4 pt", direction: "up" },
        { label: "Lots bloqués", value: "0", unit: "lot", trend: "Aucun blocage", direction: "flat" }
      ],
      configurations: [
        { id: "frequence-controle", label: "Fréquence de contrôle", value: "100 %", right: "libre" },
        { id: "seuil-blocage", label: "Seuil de blocage d’un lot", value: "15 % de rebut", right: "libre" }
      ],
      worldParameters: [{ label: "Temps de contrôle", value: "1 min / produit" }, { label: "Part des défauts récupérables", value: "65 %" }],
      actions: ["Débloquer un lot", "Lancer une retouche"]
    },
    {
      id: "emballage", name: "Emballage", shortName: "Emballage", status: "vert",
      description: "Colis, palettes et produits finis emballés.",
      kpis: [
        { label: "Produits emballés", value: "1 206", unit: "produits", trend: "Aujourd’hui", direction: "flat" },
        { label: "Palettes terminées", value: "201", unit: "palettes", trend: "+12", direction: "up" }
      ],
      configurations: [
        { id: "produits-colis", label: "Produits par colis", value: "1", right: "verrouille" },
        { id: "colis-palette", label: "Colis par palette", value: "6", right: "initial" },
        { id: "ordre-emballage", label: "Ordre d’emballage", value: "Premier arrivé, premier emballé", right: "libre" }
      ],
      worldParameters: [{ label: "Temps d’emballage", value: "2 min / colis" }, { label: "Temps de filmage", value: "5 min / palette" }],
      actions: ["Prioriser une commande"]
    },
    {
      id: "maintenance", name: "Maintenance", shortName: "Maintenance", status: "orange",
      description: "Interventions, préventif et pièces de rechange.",
      kpis: [
        { label: "Disponibilité", value: "92,4", unit: "%", trend: "−1,1 pt", direction: "down" },
        { label: "Interventions en file", value: "2", unit: "interventions", trend: "File d’attente", direction: "down" }
      ],
      configurations: [
        { id: "strategie", label: "Stratégie de maintenance", value: "Corrective seulement", right: "libre" },
        { id: "ordre-interventions", label: "Ordre des interventions", value: "Première panne d’abord", right: "libre" }
      ],
      worldParameters: [{ label: "Techniciens", value: "1" }, { label: "Temps de déplacement jusqu’à une machine", value: "3 min" }],
      actions: ["Envoyer le technicien", "Programmer un préventif", "Commander des PDR"]
    },
    {
      id: "logistique", name: "Logistique & Transport", shortName: "Logistique", status: "rouge",
      description: "Préparation, expédition et livraison des commandes.",
      kpis: [
        { label: "OTIF client", value: "93,5", unit: "%", trend: "−1,5 pt", direction: "down" },
        { label: "Remplissage des camions", value: "82", unit: "%", trend: "+4 pts", direction: "up" },
        { label: "Commandes prêtes non parties", value: "3", unit: "commandes", trend: "1 en retard", direction: "down" }
      ],
      configurations: [
        { id: "depart-camion", label: "Départ d’un camion", value: "Quand il est plein", right: "libre" },
        { id: "delai-maximum", label: "Délai maximal avant départ", value: "4 h", right: "libre" }
      ],
      worldParameters: [{ label: "Temps de chargement", value: "2 min / palette" }, { label: "Camions à quai en même temps", value: "1" }],
      actions: ["Expédier une commande en priorité", "Faire partir un camion incomplet"]
    },
    {
      id: "clients", name: "Clients", shortName: "Clients", status: "rouge",
      description: "Demandes, commandes acceptées et délais promis.",
      kpis: [
        { label: "Taux de service", value: "93,5", unit: "%", trend: "−1,5 pt", direction: "down" },
        { label: "Carnet de commandes", value: "18", unit: "commandes", trend: "4,1 jours de production", direction: "flat" }
      ],
      configurations: [
        { id: "regle-acceptation", label: "Règle d’acceptation", value: "Décision du joueur", right: "libre" },
        { id: "delai-promis", label: "Délai promis", value: "5 jours", right: "libre" }
      ],
      worldParameters: [{ label: "Demande moyenne", value: "100 produits / jour" }, { label: "Délai attendu", value: "5 jours" }],
      actions: ["Accepter une commande", "Refuser une commande"]
    }
  ];

  function initialState() {
    return {
      mode: "mock",
      started: false,
      clock: { day: 1, time: "08:00", speed: 1, paused: true, nextDecision: { day: 1, time: "14:30" } },
      tools: copy(tools),
      departments: copy(departments),
      globalKpis: [
        { label: "Taux de service client", value: "93,5", unit: "%", departmentId: "clients" },
        { label: "TRS de la chaîne", value: "78,6", unit: "%", departmentId: "production" },
        { label: "Production du jour", value: "1 240", unit: "produits", departmentId: "production" },
        { label: "Ruptures de stock", value: "2", unit: "articles", departmentId: "stock" },
        { label: "Couverture de stock", value: "3,2", unit: "jours", departmentId: "stock" },
        { label: "Coût d’achat livré", value: "8,42", unit: "€ / PF", departmentId: "fournisseurs" }
      ],
      alerts: [
        { id: "ALT-001", departmentId: "stock", severity: "grave", title: "Rupture de matière première", detail: "Un OF est bloqué faute de matière." },
        { id: "ALT-002", departmentId: "logistique", severity: "grave", title: "Commande client en retard", detail: "Une commande dépasse sa date promise." },
        { id: "ALT-003", departmentId: "maintenance", severity: "mineure", title: "File d’interventions longue", detail: "Deux interventions attendent le technicien." },
        { id: "ALT-004", departmentId: "fournisseurs", severity: "mineure", title: "Capacité de l’offre presque atteinte", detail: "L’offre principale approche de sa capacité." }
      ],
      objectives: [
        { id: "service", label: "Taux de service client", progress: 72, current: "93,5 %" },
        { id: "trs", label: "TRS de la chaîne", progress: 58, current: "78,6 %" },
        { id: "stock", label: "Continuité des approvisionnements", progress: 41, current: "2 ruptures" }
      ]
    };
  }

  function copy(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function createMockApi() {
    let state = initialState();

    function response() {
      return Promise.resolve(copy(state));
    }

    function findConfiguration(departmentId, configurationId) {
      const department = state.departments.find((item) => item.id === departmentId);
      const configuration = department && department.configurations.find((item) => item.id === configurationId);
      if (!configuration) {
        throw new Error("Configuration inconnue.");
      }
      return configuration;
    }

    return {
      getState: response,

      updateConfiguration(departmentId, configurationId, value) {
        const configuration = findConfiguration(departmentId, configurationId);
        let message = "";
        if (configuration.right === "verrouille") message = RIGHT_MESSAGES.verrouille;
        if (configuration.right === "initial" && state.started) message = RIGHT_MESSAGES.initial;
        if (configuration.right === "libre" && configuration.remainingChanges === 0) message = RIGHT_MESSAGES.limite;
        if (message) return Promise.resolve({ ok: false, message });
        configuration.value = String(value);
        if (typeof configuration.remainingChanges === "number") configuration.remainingChanges -= 1;
        return Promise.resolve({ ok: true, state: copy(state) });
      },

      startGame(values) {
        Object.entries(values).forEach(([key, value]) => {
          const separator = key.indexOf(".");
          const departmentId = key.slice(0, separator);
          const configurationId = key.slice(separator + 1);
          const configuration = findConfiguration(departmentId, configurationId);
          if (configuration.right !== "verrouille") configuration.value = String(value);
        });
        state.started = true;
        state.clock.paused = false;
        return response();
      },

      setSpeed(speed) {
        const parsed = Number(speed);
        if (!Number.isInteger(parsed) || parsed < 1 || parsed > 60) {
          return Promise.resolve({ ok: false, message: "La vitesse doit être comprise entre ×1 et ×60." });
        }
        state.clock.speed = parsed;
        return response();
      },

      togglePause() {
        state.clock.paused = !state.clock.paused;
        return response();
      },

      advanceToDecision() {
        state.clock.day = state.clock.nextDecision.day;
        state.clock.time = state.clock.nextDecision.time;
        state.clock.paused = true;
        return response();
      },

      performAction() {
        return Promise.resolve({ ok: true, message: "Action transmise au moteur de démonstration." });
      }
    };
  }

  return createMockApi();
}));
