/**
 * SESMT Photo Manager - Reusable photo/evidence management
 * Handles photo input sync, file signatures, deduplication, and UI refresh
 */
(function () {
  /**
   * Initialize photo manager for a single input
   * @param {Object} config - Configuration object
   * @param {string} config.inputId - ID of the file input element
   * @param {string} config.statusId - ID of the status display element
   * @param {string} config.listId - ID of the list container element
   * @param {string} config.emptyId - ID of the empty message element
   * @param {Function} [config.onChange] - Optional callback on file change
   */
  window.SesmtPhotoManager = {
    init: function (config) {
      if (!config || !config.inputId || !config.statusId || !config.listId || !config.emptyId) {
        return;
      }

      var input = document.getElementById(config.inputId);
      var status = document.getElementById(config.statusId);
      var listNode = document.getElementById(config.listId);
      var emptyNode = document.getElementById(config.emptyId);

      if (!input || !status || !listNode || !emptyNode) {
        return;
      }

      var files = Array.from(input.files || []);

      function createTransfer(currentFiles) {
        var transfer = new DataTransfer();
        currentFiles.forEach(function (file) {
          transfer.items.add(file);
        });
        return transfer.files;
      }

      function fileSignature(file) {
        return [file.name, file.size, file.lastModified, file.type].join("::");
      }

      function appendFiles(targetFiles, incomingFiles) {
        incomingFiles.forEach(function (file) {
          var signature = fileSignature(file);
          var exists = targetFiles.some(function (current) {
            return fileSignature(current) === signature;
          });
          if (!exists) {
            targetFiles.push(file);
          }
        });
      }

      function pluralize(total) {
        return total === 1 ? "ficheiro" : "ficheiros";
      }

      function refresh() {
        input.files = createTransfer(files);
        var statusText = files.length
          ? files.length + " " + pluralize(files.length) + " selecionado(s)"
          : "Nenhum ficheiro selecionado";
        status.textContent = statusText;

        listNode.innerHTML = "";
        emptyNode.style.display = files.length ? "none" : "";

        files.forEach(function (file, index) {
          var row = document.createElement("div");
          row.className = "small border rounded-2 px-3 py-2 d-flex align-items-center justify-content-between gap-3";

          var label = document.createElement("div");
          label.className = "text-truncate";
          label.textContent = file.name;

          var removeButton = document.createElement("button");
          removeButton.type = "button";
          removeButton.className = "btn btn-sm btn-label-danger";
          removeButton.textContent = "X";
          removeButton.addEventListener("click", function () {
            files = files.filter(function (_item, currentIndex) {
              return currentIndex !== index;
            });
            refresh();
          });

          row.appendChild(label);
          row.appendChild(removeButton);
          listNode.appendChild(row);
        });
      }

      input.addEventListener("click", function () {
        input.value = "";
      });

      input.addEventListener("change", function () {
        appendFiles(files, Array.from(input.files || []));
        refresh();
        if (typeof config.onChange === "function") {
          config.onChange();
        }
      });

      refresh();
    }
  };

  /**
   * Dual-input photo manager (camera + device)
   * @param {Object} config - Configuration object
   * @param {string} config.cameraInputId - ID of camera input
   * @param {string} config.deviceInputId - ID of device input
   * @param {string} config.cameraStatusId - ID of camera status element
   * @param {string} config.deviceStatusId - ID of device status element
   * @param {string} config.totalStatusId - ID of total status element
   * @param {string} config.listNodeId - ID of combined list container
   * @param {string} config.emptyNodeId - ID of empty message element
   */
  window.SesmtPhotoManager.dual = function (config) {
    if (
      !config ||
      !config.cameraInputId ||
      !config.deviceInputId ||
      !config.cameraStatusId ||
      !config.deviceStatusId ||
      !config.totalStatusId ||
      !config.listNodeId ||
      !config.emptyNodeId
    ) {
      return;
    }

    var cameraInput = document.getElementById(config.cameraInputId);
    var deviceInput = document.getElementById(config.deviceInputId);
    var cameraStatus = document.getElementById(config.cameraStatusId);
    var deviceStatus = document.getElementById(config.deviceStatusId);
    var totalStatus = document.getElementById(config.totalStatusId);
    var listNode = document.getElementById(config.listNodeId);
    var emptyNode = document.getElementById(config.emptyNodeId);

    if (!cameraInput || !deviceInput || !cameraStatus || !deviceStatus || !totalStatus || !listNode || !emptyNode) {
      return;
    }

    var cameraFiles = Array.from(cameraInput.files || []);
    var deviceFiles = Array.from(deviceInput.files || []);

    function createTransfer(files) {
      var transfer = new DataTransfer();
      files.forEach(function (file) {
        transfer.items.add(file);
      });
      return transfer.files;
    }

    function syncInputFiles() {
      cameraInput.files = createTransfer(cameraFiles);
      deviceInput.files = createTransfer(deviceFiles);
    }

    function fileSignature(file) {
      return [file.name, file.size, file.lastModified, file.type].join("::");
    }

    function appendFiles(targetFiles, incomingFiles) {
      incomingFiles.forEach(function (file) {
        var signature = fileSignature(file);
        var exists = targetFiles.some(function (current) {
          return fileSignature(current) === signature;
        });
        if (!exists) {
          targetFiles.push(file);
        }
      });
    }

    function getFiles() {
      return cameraFiles
        .map(function (file, index) {
          return { file: file, source: "camera", index: index };
        })
        .concat(
          deviceFiles.map(function (file, index) {
            return { file: file, source: "device", index: index };
          })
        );
    }

    function pluralize(total) {
      return total === 1 ? "foto capturada" : "fotos capturadas";
    }

    function refresh() {
      syncInputFiles();
      var cameraCount = cameraFiles.length;
      var deviceCount = deviceFiles.length;
      var files = getFiles();

      cameraStatus.textContent = cameraCount
        ? cameraCount + " ficheiro(s) selecionado(s)"
        : "Nenhum ficheiro selecionado";
      deviceStatus.textContent = deviceCount
        ? deviceCount + " ficheiro(s) selecionado(s)"
        : "Nenhum ficheiro selecionado";
      totalStatus.textContent = files.length
        ? files.length + " " + pluralize(files.length)
        : "Nenhuma foto capturada";

      listNode.innerHTML = "";
      emptyNode.style.display = files.length ? "none" : "";

      files.forEach(function (entry) {
        var item = document.createElement("div");
        item.className = "small border rounded-2 px-3 py-2 d-flex align-items-center justify-content-between gap-3";

        var label = document.createElement("div");
        label.className = "text-truncate";
        label.textContent = entry.file.name;

        var removeButton = document.createElement("button");
        removeButton.type = "button";
        removeButton.className = "btn btn-sm btn-label-danger";
        removeButton.textContent = "X";
        removeButton.addEventListener("click", function () {
          if (entry.source === "camera") {
            cameraFiles.splice(entry.index, 1);
          } else {
            deviceFiles.splice(entry.index, 1);
          }
          refresh();
        });

        item.appendChild(label);
        item.appendChild(removeButton);
        listNode.appendChild(item);
      });
    }

    cameraInput.addEventListener("click", function () {
      cameraInput.value = "";
    });

    deviceInput.addEventListener("click", function () {
      deviceInput.value = "";
    });

    cameraInput.addEventListener("change", function () {
      appendFiles(cameraFiles, Array.from(cameraInput.files || []));
      refresh();
    });

    deviceInput.addEventListener("change", function () {
      appendFiles(deviceFiles, Array.from(deviceInput.files || []));
      refresh();
    });

    refresh();
  };
})();
