const sampleBatch = {
  batch_id: "demo-batch-001",
  dry_run: true,
  max_steps: 3,
  features: [
    {
      feature_id: "feat-001",
      objective: "Add an onboarding tooltip to the dashboard."
    },
    {
      feature_id: "feat-002",
      objective: "Expose a status endpoint for release bundles."
    },
    {
      feature_id: "feat-003",
      objective: "Add a CLI command to list recent batches."
    }
  ]
};

const batchInput = document.getElementById("batch-input");
const submitButton = document.getElementById("submit-batch");
const submitStatus = document.getElementById("submit-status");
const refreshButton = document.getElementById("refresh");
const loadSampleButton = document.getElementById("load-sample");
const batchList = document.getElementById("batch-list");

function setStatus(text) {
  submitStatus.textContent = text;
}

function renderBatches(batches) {
  if (!batches.length) {
    batchList.innerHTML = "<p class=\"muted\">No batches yet.</p>";
    return;
  }
  batchList.innerHTML = batches
    .map((batch) => {
      const features = batch.features || [];
      const featureItems = features
        .map((feature) => `<li>${feature.feature_id}: ${feature.status}</li>`)
        .join("");
      return `
        <div class="batch-card">
          <h3>${batch.batch_id}</h3>
          <span class="tag">${batch.status}</span>
          <ul class="feature-list">${featureItems}</ul>
        </div>
      `;
    })
    .join("");
}

async function fetchBatches() {
  const res = await fetch("/batches");
  const data = await res.json();
  renderBatches(data.batches || []);
}

submitButton.addEventListener("click", async () => {
  setStatus("Submitting...");
  try {
    const payload = JSON.parse(batchInput.value || "{}");
    const res = await fetch("/batches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      setStatus(`Error: ${data.error || res.statusText}`);
      return;
    }
    setStatus(`Submitted ${data.batch_id}`);
    await fetchBatches();
  } catch (err) {
    setStatus(`Error: ${err.message}`);
  }
});

refreshButton.addEventListener("click", fetchBatches);
loadSampleButton.addEventListener("click", () => {
  batchInput.value = JSON.stringify(sampleBatch, null, 2);
});

batchInput.value = JSON.stringify(sampleBatch, null, 2);
fetchBatches();
