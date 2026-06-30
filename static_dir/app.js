const BACKEND_BASE =
  window.location.protocol === "file:" ||
  !window.location.port ||
  window.location.port !== "8001"
    ? "http://127.0.0.1:8001"
    : "";

const URL_API_BUSCA = `${BACKEND_BASE}/search_assets`;
const URL_API_DOWNLOAD = `${BACKEND_BASE}/download_csv`;

// Example coordinates for testing (Curitiba BR-116 segment)
const EXAMPLE_START = "-25.5557, -49.2075";
const EXAMPLE_END = "-25.5600, -49.2000";

const searchForm = document.getElementById("search-form");
const startInput = document.getElementById("start-coords");
const endInput = document.getElementById("end-coords");
const btnSubmit = document.getElementById("btn-submit");
const btnExample = document.getElementById("btn-example");

const resultsSummary = document.getElementById("results-summary");
const summaryTotal = document.getElementById("summary-total");
const summaryWarning = document.getElementById("summary-warning");
const summaryRegulatory = document.getElementById("summary-regulatory");
const summaryRadar = document.getElementById("summary-radar");

const downloadArea = document.getElementById("download-area");
const btnDownload = document.getElementById("btn-download");
const generalError = document.getElementById("general-error");

// Input Form Groups for styling errors
const startGroup = startInput.closest(".form-group");
const endGroup = endInput.closest(".form-group");

// Error Text Elements
const startErrorText = document.getElementById("start-coords-error");
const endErrorText = document.getElementById("end-coords-error");

searchForm.addEventListener("submit", handleFormSubmit);
btnExample.addEventListener("click", prefillExampleCoordinates);

// Clear errors when the user types
startInput.addEventListener("input", () =>
  clearInputError(startGroup, startErrorText),
);
endInput.addEventListener("input", () =>
  clearInputError(endGroup, endErrorText),
);

function prefillExampleCoordinates() {
  startInput.value = EXAMPLE_START;
  endInput.value = EXAMPLE_END;

  clearInputError(startGroup, startErrorText);
  clearInputError(endGroup, endErrorText);
  hideElement(generalError);
  hideElement(resultsSummary);
  hideElement(downloadArea);
}

function showInputError(group, textElement, message) {
  group.classList.add("has-error");
  textElement.textContent = message;
}

function clearInputError(group, textElement) {
  group.classList.remove("has-error");
}

function hideElement(element) {
  element.classList.add("hidden");
  element.setAttribute("aria-hidden", "true");
}

function showElement(element) {
  element.classList.remove("hidden");
  element.removeAttribute("aria-hidden");
}

function parseCoordinate(value) {
  if (!value || typeof value !== "string") return null;

  const cleaned = value.trim();

  // Try splitting by semicolon first (e.g. "-25.5557; -49.2075" or Portuguese decimals "-25,5557; -49,2075")
  let parts = cleaned.split(";");
  if (parts.length !== 2) {
    // If not, try splitting by comma, but only if there is exactly 1 comma (e.g. "-25.5557, -49.2075")
    const commaCount = (cleaned.match(/,/g) || []).length;
    if (commaCount === 1) {
      parts = cleaned.split(",");
    } else {
      // If there are no commas or more than one comma, split by spaces (e.g. "-25.5557 -49.2075")
      parts = cleaned.split(/\s+/);
    }
  }

  if (parts.length !== 2) return null;

  // Replace decimal commas with dots if necessary
  const latStr = parts[0].trim().replace(",", ".");
  const lonStr = parts[1].trim().replace(",", ".");

  const lat = parseFloat(latStr);
  const lon = parseFloat(lonStr);

  if (isNaN(lat) || isNaN(lon)) return null;
  if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;

  return { lat, lon };
}

function updateSummaryMetrics(data) {
  const signs = data.signs || [];

  const total = data.count !== undefined ? data.count : signs.length;
  let warningCount = 0;
  let regulatoryCount = 0;
  let radarCount = 0;

  signs.forEach((sign) => {
    const type = sign.sign_type;
    if (type === "warning-sign") {
      warningCount++;
    } else if (type === "regulatory-sign") {
      regulatoryCount++;
    } else if (type === "speed-camera") {
      radarCount++;
    }
  });

  summaryTotal.textContent = total;
  summaryWarning.textContent = warningCount;
  summaryRegulatory.textContent = regulatoryCount;
  summaryRadar.textContent = radarCount;
}

async function handleFormSubmit(event) {
  event.preventDefault();

  hideElement(generalError);
  hideElement(resultsSummary);
  hideElement(downloadArea);

  let hasValidationError = false;
  const startVal = startInput.value.trim();
  const endVal = endInput.value.trim();

  if (!startVal) {
    showInputError(
      startGroup,
      startErrorText,
      "Por favor, insira a coordenada de início.",
    );
    hasValidationError = true;
  } else if (!parseCoordinate(startVal)) {
    showInputError(
      startGroup,
      startErrorText,
      "Formato inválido. Use: Latitude, Longitude (ex: -25.5557, -49.2075)",
    );
    hasValidationError = true;
  }

  if (!endVal) {
    showInputError(
      endGroup,
      endErrorText,
      "Por favor, insira a coordenada de fim.",
    );
    hasValidationError = true;
  } else if (!parseCoordinate(endVal)) {
    showInputError(
      endGroup,
      endErrorText,
      "Formato inválido. Use: Latitude, Longitude (ex: -25.5600, -49.2000)",
    );
    hasValidationError = true;
  }

  if (hasValidationError) return;

  const startCoords = parseCoordinate(startVal);
  const endCoords = parseCoordinate(endVal);

  btnSubmit.disabled = true;
  btnSubmit.classList.add("loading");

  try {
    const queryParams = new URLSearchParams({
      start_lat: startCoords.lat,
      start_lon: startCoords.lon,
      end_lat: endCoords.lat,
      end_lon: endCoords.lon,
    });

    const requestUrl = `${URL_API_BUSCA}?${queryParams.toString()}`;

    const response = await fetch(requestUrl, {
      method: "POST",
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `Erro do servidor: ${response.status}`,
      );
    }

    const data = await response.json();
    updateSummaryMetrics(data);
    setupDownloadLink();

    showElement(resultsSummary);
    showElement(downloadArea);
  } catch (error) {
    console.error("Erro na busca:", error);
    if (error.name === "TypeError" && error.message.includes("fetch")) {
      generalError.textContent = `Erro de conexão: Não foi possível se conectar ao servidor na porta 8001. Certifique-se de que o backend está rodando e com o CORS habilitado.`;
    } else {
      generalError.textContent = `Erro ao buscar trecho: ${error.message}`;
    }
    showElement(generalError);
  } finally {
    btnSubmit.disabled = false;
    btnSubmit.classList.remove("loading");
  }
}

function setupDownloadLink() {
  btnDownload.href = URL_API_DOWNLOAD;
}
