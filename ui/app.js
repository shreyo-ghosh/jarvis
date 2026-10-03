const API_BASE = window.JARVIS_API_BASE || "";

const statusCounts = {
  draft: "stat-draft",
  pending_approval: "stat-pending",
  approved: "stat-approved",
  scheduled: "stat-scheduled",
};

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }
  if (response.status === 204) return {};
  return response.json();
}

function badge(status) {
  return `<span class="badge ${status}">${status.replace("_", " ")}</span>`;
}

function actionButtons(item) {
  const actions = [];
  if (item.status === "draft") {
    actions.push(`<button data-action="submit" data-id="${item.content_id}">Submit</button>`);
  }
  if (item.status === "pending_approval") {
    actions.push(`<button data-action="approve" data-id="${item.content_id}">Approve</button>`);
  }
  if (item.status === "approved") {
    actions.push(`<button data-action="schedule" data-id="${item.content_id}">Schedule tomorrow</button>`);
  }
  return actions.join("");
}

function renderContent(items) {
  const list = document.getElementById("content-list");
  Object.values(statusCounts).forEach((id) => {
    document.getElementById(id).textContent = "0";
  });

  items.forEach((item) => {
    const counter = statusCounts[item.status];
    if (counter) {
      const node = document.getElementById(counter);
      node.textContent = Number(node.textContent) + 1;
    }
  });

  if (!items.length) {
    list.innerHTML = "<p>No content yet. Create your first LaunchLayer draft.</p>";
    return;
  }

  list.innerHTML = items
    .map(
      (item) => `
      <article class="content-item">
        <div class="section-header">
          <h3>${item.title}</h3>
          ${badge(item.status)}
        </div>
        <p><strong>${item.channel}</strong> · ${item.content_type} · Campaign ${item.campaign_id}</p>
        <p>${item.body.slice(0, 220)}${item.body.length > 220 ? "…” : ""}</p>
        <div class="item-actions">${actionButtons(item)}</div>
      </article>`
    )
    .join("");
}

async function loadContent() {
  const statusNode = document.getElementById("api-status");
  try {
    const data = await api("/growth/content");
    renderContent(data.items || []);
    statusNode.textContent = "API connected";
  } catch (error) {
    statusNode.textContent = "API unavailable";
    document.getElementById("content-list").innerHTML =
      `<p>Unable to load content: ${error.message}</p>`;
  }
}

document.getElementById("content-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(event.target);
  const payload = Object.fromEntries(formData.entries());

  try {
    await api("/growth/content", { method: "POST", body: JSON.stringify(payload) });
    event.target.reset();
    await loadContent();
  } catch (error) {
    alert(`Could not create content: ${error.message}`);
  }
});

document.getElementById("content-list").addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) return;

  const { action, id } = button.dataset;
  const endpoint = {
    submit: `/growth/content/${id}/submit`,
    approve: `/growth/content/${id}/approve`,
    schedule: `/growth/content/${id}/schedule`,
  }[action];

  const payload =
    action === "approve"
      ? { actor: prompt("Approver name:") }
      : action === "schedule"
        ? { scheduled_for: new Date(Date.now() + 86400000).toISOString(), actor: "shreyo" }
        : { actor: "shreyo" };

  try {
    await api(endpoint, { method: "POST", body: JSON.stringify(payload) });
    await loadContent();
  } catch (error) {
    alert(`Action failed: ${error.message}`);
  }
});

document.getElementById("refresh").addEventListener("click", loadContent);
loadContent();
