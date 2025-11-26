const mediaTypeEl = document.getElementById('media-type');
const eventTypeEl = document.getElementById('event-type');
const statusEl = document.getElementById('status');
const qualityProfileEl = document.getElementById('quality-profile');
const tagEl = document.getElementById('tag');
const actionEl = document.getElementById('action');
const actionValueGroupEl = document.getElementById('action-value-group');
const actionValueEl = document.getElementById('action-value');
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
    actionValue: actionValueEl.value,
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
    actionValue: actionValueEl.value,
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

actionEl.addEventListener('change', () => {
  const action = actionEl.value;
  if (action === 'add_tag' || action === 'remove_tag' || action === 'change_quality_profile') {
    actionValueGroupEl.style.display = 'block';
    if (action === 'change_quality_profile') {
      populateActionValueDropdown('quality_profiles');
    } else {
      populateActionValueDropdown('tags');
    }
  } else {
    actionValueGroupEl.style.display = 'none';
  }
});

async function populateActionValueDropdown(dataType) {
  const mediaType = mediaTypeEl.value === 'episode' ? 'sonarr' : 'radarr';
  const response = await fetch(`/api/${mediaType}/data`);
  const data = await response.json();
  actionValueEl.innerHTML = '';
  if (data[dataType]) {
    for (const item of data[dataType]) {
      const option = document.createElement('option');
      option.value = item.name || item.label;
      option.textContent = item.name || item.label;
      actionValueEl.appendChild(option);
    }
  }
}

// Initial setup
updateStatusOptions();
fetchData('sonarr');
fetchRules();
fetchSonarrLibrary();
fetchRadarrLibrary();
fetchSonarrWanted();
fetchRadarrWanted();

async function fetchAndRender(url, listElId, noItemsMessage, itemRenderer) {
    const response = await fetch(url);
    const data = await response.json();
    const listEl = document.getElementById(listElId);
    listEl.innerHTML = '';
    const items = data.records || data;
    if (items.length === 0) {
        listEl.innerHTML = `<li class="list-group-item">${noItemsMessage}</li>`;
        return;
    }
    for (const item of items) {
        listEl.appendChild(itemRenderer(item));
    }
}

function renderLibraryItem(item) {
    const li = document.createElement('li');
    li.className = 'list-group-item';
    li.textContent = item.title;
    return li;
}

function renderWantedItem(item, searchFn, idKey) {
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between align-items-center';
    li.textContent = item.title;
    const searchButton = document.createElement('button');
    searchButton.className = 'btn btn-primary btn-sm';
    searchButton.textContent = 'Search';
    searchButton.onclick = () => searchFn(item[idKey]);
    li.appendChild(searchButton);
    return li;
}

async function fetchSonarrLibrary() {
    fetchAndRender('/api/sonarr/library', 'sonarr-library', 'No items in library.', renderLibraryItem);
}

async function fetchRadarrLibrary() {
    fetchAndRender('/api/radarr/library', 'radarr-library', 'No items in library.', renderLibraryItem);
}

async function fetchSonarrWanted() {
    fetchAndRender('/api/sonarr/wanted', 'sonarr-wanted', 'No wanted items.', (item) => renderWantedItem(item, searchSonarr, 'seriesId'));
}

async function fetchRadarrWanted() {
    fetchAndRender('/api/radarr/wanted', 'radarr-wanted', 'No wanted items.', (item) => renderWantedItem(item, searchRadarr, 'movieId'));
}

async function searchSonarr(seriesId) {
  await fetch('/api/sonarr/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ seriesId }),
  });
}

async function searchRadarr(movieId) {
  await fetch('/api/radarr/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ movieId }),
  });
}
