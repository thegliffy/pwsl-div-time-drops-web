(() => {
  const form = document.getElementById("generate-form");
  const fileInput = document.getElementById("file");
  const fileName = document.getElementById("file-name");
  const submitBtn = document.getElementById("submit-btn");
  const statusSection = document.getElementById("status");
  const statusLog = document.getElementById("status-log");

  function showStatus(message, kind) {
    statusSection.hidden = false;
    statusLog.textContent = message;
    statusLog.classList.remove("is-error", "is-ok");
    if (kind === "error") statusLog.classList.add("is-error");
    if (kind === "ok") statusLog.classList.add("is-ok");
  }

  function appendStatus(line) {
    statusLog.textContent = statusLog.textContent
      ? `${statusLog.textContent}\n${line}`
      : line;
  }

  fileInput.addEventListener("change", () => {
    const file = fileInput.files && fileInput.files[0];
    fileName.textContent = file ? file.name : "No file selected";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      showStatus("Please choose a valid Time Improvement labels PDF first.", "error");
      return;
    }

    const minDropRaw = document.getElementById("min_drop").value;
    const minDrop = Number(minDropRaw);
    if (Number.isNaN(minDrop) || minDrop < 0) {
      showStatus("Minimum time drop must be a number, e.g. 1.0", "error");
      return;
    }

    const filename = document.getElementById("filename").value.trim() || "time_drop_labels";

    const body = new FormData();
    body.append("file", file);
    body.append("min_drop", String(minDrop));
    body.append("filename", filename);

    submitBtn.disabled = true;
    submitBtn.textContent = "Working…";
    showStatus(`Reading: ${file.name}\nParsing for drops of ${minDrop}s or more…`, null);

    try {
      const response = await fetch("/api/generate", {
        method: "POST",
        body,
      });

      const contentType = response.headers.get("content-type") || "";

      if (!response.ok) {
        let detail = `Request failed (${response.status}).`;
        if (contentType.includes("application/json")) {
          const payload = await response.json();
          detail = payload.detail || detail;
        } else {
          detail = (await response.text()) || detail;
        }
        showStatus(detail, "error");
        return;
      }

      const countHeader = response.headers.get("X-Qualifying-Count");
      const blob = await response.blob();
      const disposition = response.headers.get("Content-Disposition") || "";
      const match = /filename="?([^";]+)"?/i.exec(disposition);
      let downloadName = match ? match[1] : `${filename}.pdf`;
      if (!downloadName.toLowerCase().endsWith(".pdf")) {
        downloadName += ".pdf";
      }

      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = downloadName;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);

      const countText = countHeader
        ? `${countHeader} qualifying swim(s)`
        : "Label sheet ready";
      showStatus(`${countText} saved as ${downloadName}.\nDownload started.`, "ok");
      appendStatus("Done.");
    } catch (err) {
      showStatus(`Something went wrong: ${err.message || err}`, "error");
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Generate Label Sheet";
    }
  });
})();
