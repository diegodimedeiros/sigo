/**
 * SESMT Geolocation Handler - Reusable geolocation rendering and capture
 * Handles geolocation display, capture, and error messaging
 */
(function () {
  /**
   * Render geolocation coordinates in the UI
   * @param {HTMLElement} container - Container to render into
   * @param {HTMLElement} emptyNode - Empty message element (hidden when coordinates present)
   * @param {string|number} latitude - Latitude value
   * @param {string|number} longitude - Longitude value
   * @param {string} [hash] - Optional hash value to display
   */
  window.SesmtGeolocation = {
    render: function (container, emptyNode, latitude, longitude, hash) {
      if (!container || !emptyNode) {
        return;
      }

      container.innerHTML = "";
      emptyNode.style.display = "none";

      var latDiv = document.createElement("div");
      latDiv.className = "small border rounded-2 px-3 py-2";
      latDiv.textContent = "Latitude: " + latitude;

      var lngDiv = document.createElement("div");
      lngDiv.className = "small border rounded-2 px-3 py-2";
      lngDiv.textContent = "Longitude: " + longitude;

      container.appendChild(latDiv);
      container.appendChild(lngDiv);

      if (hash) {
        var hashDiv = document.createElement("div");
        hashDiv.className = "small border rounded-2 px-3 py-2";
        hashDiv.textContent = "Hash: " + hash;
        container.appendChild(hashDiv);
      }
    },

    /**
     * Show an error or status message
     * @param {HTMLElement} container - Container to clear
     * @param {HTMLElement} emptyNode - Element to display message in
     * @param {string} message - Message text
     */
    showMessage: function (container, emptyNode, message) {
      if (!container || !emptyNode) {
        return;
      }

      container.innerHTML = "";
      emptyNode.style.display = "";
      emptyNode.textContent = message;
    },

    /**
     * Initialize geolocation capture for a form
     * @param {Object} config - Configuration object
     * @param {string} config.latitudeId - ID of latitude input field
     * @param {string} config.longitudeId - ID of longitude input field
     * @param {string} config.containerId - ID of result container
     * @param {string} config.emptyNodeId - ID of empty message element
     * @param {Function} [config.onChange] - Optional callback on location change
     */
    initCapture: function (config) {
      if (!config || !config.latitudeId || !config.longitudeId || !config.containerId || !config.emptyNodeId) {
        return;
      }

      var latInput = document.getElementById(config.latitudeId);
      var lonInput = document.getElementById(config.longitudeId);
      var container = document.getElementById(config.containerId);
      var emptyNode = document.getElementById(config.emptyNodeId);

      if (!latInput || !lonInput || !container || !emptyNode) {
        return;
      }

      var self = window.SesmtGeolocation;

      function renderCurrent() {
        var lat = (latInput.value || "").trim();
        var lon = (lonInput.value || "").trim();

        if (lat && lon) {
          self.render(container, emptyNode, lat, lon);
        } else {
          self.showMessage(container, emptyNode, "Nenhuma geolocalização registrada ainda.");
        }
      }

      function capture() {
        var lat = (latInput.value || "").trim();
        var lon = (lonInput.value || "").trim();

        if (lat && lon) {
          renderCurrent();
          return;
        }

        if (!navigator.geolocation) {
          self.showMessage(container, emptyNode, "Geolocalização indisponível neste dispositivo.");
          return;
        }

        self.showMessage(container, emptyNode, "Obtendo geolocalização...");

        navigator.geolocation.getCurrentPosition(
          function (position) {
            var latitude = Number(position.coords.latitude || 0).toFixed(7);
            var longitude = Number(position.coords.longitude || 0).toFixed(7);
            latInput.value = latitude;
            lonInput.value = longitude;
            renderCurrent();
            if (typeof config.onChange === "function") {
              config.onChange();
            }
          },
          function () {
            self.showMessage(container, emptyNode, "Não foi possível obter a localização.");
          },
          {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 15000
          }
        );
      }

      capture();

      return {
        capture: capture,
        renderCurrent: renderCurrent
      };
    }
  };
})();
