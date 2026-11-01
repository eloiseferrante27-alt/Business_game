(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) {
    module.exports = { createLiveApi: api, ApiError: api.ApiError };
  } else {
    root.GMixLiveAPI = { createLiveApi: api, ApiError: api.ApiError };
  }
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  class ApiError extends Error {
    constructor(message, status, payload) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.payload = payload;
    }
  }

  function detailMessage(payload, fallback) {
    if (!payload) return fallback;
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) {
      return payload.detail.map((item) => item.msg || String(item)).join(" ");
    }
    if (typeof payload.message === "string") return payload.message;
    return fallback;
  }

  function createLiveApi(options) {
    const settings = options || {};
    const fetchImpl = settings.fetchImpl || (typeof fetch !== "undefined" ? fetch.bind(globalThis) : null);
    if (!fetchImpl) throw new Error("L’adaptateur live nécessite fetch.");

    async function request(path, init) {
      const requestInit = Object.assign({ credentials: "same-origin" }, init || {});
      requestInit.headers = Object.assign({ Accept: "application/json" }, requestInit.headers || {});
      let response;
      try {
        response = await fetchImpl(path, requestInit);
      } catch (error) {
        throw new ApiError("Le serveur est injoignable. Vérifiez la connexion puis réessayez.", 0, error);
      }
      const text = await response.text();
      let payload = null;
      if (text) {
        try {
          payload = JSON.parse(text);
        } catch (error) {
          throw new ApiError("Le serveur a renvoyé une réponse illisible.", response.status, text);
        }
      }
      if (!response.ok) {
        throw new ApiError(detailMessage(payload, `La requête a échoué (HTTP ${response.status}).`), response.status, payload);
      }
      return payload;
    }

    function post(path, body) {
      return request(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    }

    return {
      getState() {
        return request("/api/v2/tablet");
      },

      newGame(setup) {
        return post("/api/v2/tablet/new-game", {
          company_name: setup.company_name,
          difficulty: setup.difficulty,
          scenario_id: "default",
          rules_confirmed: setup.rules_confirmed === true
        });
      },

      nextTurn() {
        return post("/api/v2/tablet/next-turn", {});
      },

      performAction(action) {
        return post("/api/v2/tablet/actions", action);
      },

      compare(sku, quantity) {
        const query = new URLSearchParams({ sku: String(sku), quantity: String(quantity) });
        return request(`/api/tablet/compare?${query.toString()}`);
      },

      updateConfiguration(departmentId, configurationId, value) {
        return post("/api/v2/tablet/configuration", {
          department_id: departmentId,
          configuration_id: configurationId,
          value
        });
      }
    };
  }

  createLiveApi.ApiError = ApiError;
  return createLiveApi;
}));
