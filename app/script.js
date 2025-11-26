const mediaTypeEl = document.getElementById('media-type');
const eventTypeEl = document.getElementById('event-type');
const statusEl = document.getElementById('status');
const qualityProfileEl = document.getElementById('quality-profile');
const tagEl = document.getElementById('tag');
const actionEl = document.getElementById('action');
const rulesListEl = document.getElementById('rules');
const previewCardEl = document.getElementById('preview-card');
const previewResultsEl = document.getElementById('preview-results');

async function addRule() {
  const rule = {
    mediaType: mediaTypeEl.value,
    eventType: eventTypeEl.value,
    status: statusEl.value,
    qualityProfile: qualityProfileEl.value,
    tag: tagEl.value,
    action: actionEl.value,
  };

  await fetch('/api/rules', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rule),
  });

  fetchRules();
}

async function previewRule() {
  const rule = {
    mediaType: mediaTypeEl.value,
    eventType: eventTypeEl.value,
    status: statusEl.value,
    qualityProfile: qualityProfileEl.value,
    tag: tagEl.value,
    action: actionEl.value,
  };

  const response = await fetch('/api/rules/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rule),
  });
  const data = await response.json();

  previewResultsEl.innerHTML = '';
  if (data.affected_items.length === 0) {
    previewResultsEl.innerHTML = '<li class="list-group-item">No items would be affected by this rule.</li>';
  } else {
    for (const item of data.affected_items) {
      const li = document.createElement('li');
      li.className = 'list-group-item';
      li.textContent = item.title;
      previewResultsEl.appendChild(li);
    }
  }
  previewCardEl.style.display = 'block';
}

async function fetchRules() {
  const response = await fetch('/api/rules');
  const data = await response.json();

  rulesListEl.innerHTML = '';
  if (data.rules.length === 0) {
    rulesListEl.innerHTML = '<li class="list-group-item">No rules yet.</li>';
    return;
  }

  for (const rule of data.rules) {
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between align-items-center';
    let ruleText = `If ${rule.mediaType} is ${rule.eventType}`;
    if (rule.status) {
      ruleText += ` and status is ${rule.status}`;
    }
    if (rule.qualityProfile) {
      ruleText += ` and quality profile is ${rule.qualityProfile}`;
    }
    if (rule.tag) {
      ruleText += ` and tag is ${rule.tag}`;
    }
    ruleText += ` then ${rule.action}`;
    li.textContent = ruleText;

    const deleteButton = document.createElement('button');
    deleteButton.className = 'btn btn-danger btn-sm';
    deleteButton.textContent = 'Delete';
    deleteButton.onclick = () => deleteRule(rule.id);

    li.appendChild(deleteButton);
    rulesListEl.appendChild(li);
  }
}

async function deleteRule(ruleId) {
  await fetch(`/api/rules/${ruleId}`, { method: 'DELETE' });
  fetchRules();
}

async function fetchData(mediaType) {
    const response = await fetch(`/api/${mediaType}/data`);
    const data = await response.json();

    qualityProfileEl.innerHTML = '<option value="">Any</option>';
    tagEl.innerHTML = '<option value="">Any</option>';

    if (data.quality_profiles) {
        for (const profile of data.quality_profiles) {
            const option = document.createElement('option');
            option.value = profile.name;
            option.textContent = profile.name;
            qualityProfileEl.appendChild(option);
        }
    }

    if (data.tags) {
        for (const tag of data.tags) {
            const option = document.createElement('option');
            option.value = tag.label;
            option.textContent = tag.label;
            tagEl.appendChild(option);
        }
    }
}

function updateStatusOptions() {
    const eventType = eventTypeEl.value;
    statusEl.innerHTML = '';
    statusEl.disabled = false;

    if (eventType === 'downloaded') {
        statusEl.innerHTML = `
            <option value="waiting_for_import">Waiting for Import</option>
            <option value="completed">Completed</option>
        `;
    } else {
        statusEl.disabled = true;
    }
}

mediaTypeEl.addEventListener('change', () => {
    const mediaType = mediaTypeEl.value === 'episode' ? 'sonarr' : 'radarr';
    fetchData(mediaType);
});

eventTypeEl.addEventListener('change', updateStatusOptions);

// Initial setup
updateStatusOptions();
fetchData('sonarr');
fetchRules();
