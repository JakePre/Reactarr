const mediaTypeEl = document.getElementById('media-type');
const eventTypeEl = document.getElementById('event-type');
const statusEl = document.getElementById('status');
const qualityProfileEl = document.getElementById('quality-profile');
const tagEl = document.getElementById('tag');
const videoCodecEl = document.getElementById('video-codec');
const audioCodecEl = document.getElementById('audio-codec');
const resolutionEl = document.getElementById('resolution');
const minSizeEl = document.getElementById('min-size');
const maxSizeEl = document.getElementById('max-size');
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
    videoCodec: videoCodecEl.value,
    audioCodec: audioCodecEl.value,
    resolution: resolutionEl.value,
    minSize: minSizeEl.value,
    maxSize: maxSizeEl.value,
    action: actionEl.value,
    actionValue: actionValueEl.value,
  };

  await createRule(rule);

  fetchRules();
}

async function previewRule() {
  const rule = {
    mediaType: mediaTypeEl.value,
    eventType: eventTypeEl.value,
    status: statusEl.value,
    qualityProfile: qualityProfileEl.value,
    tag: tagEl.value,
    videoCodec: videoCodecEl.value,
    audioCodec: audioCodecEl.value,
    resolution: resolutionEl.value,
    minSize: minSizeEl.value,
    maxSize: maxSizeEl.value,
    action: actionEl.value,
    actionValue: actionValueEl.value,
  };

  const affectedItems = await previewRuleApi(rule);

  previewResultsEl.innerHTML = '';
  if (affectedItems.length === 0) {
    previewResultsEl.innerHTML = '<li class="list-group-item">No items would be affected by this rule.</li>';
  } else {
    for (const item of affectedItems) {
      const li = document.createElement('li');
      li.className = 'list-group-item';
      li.textContent = item.title;
      previewResultsEl.appendChild(li);
    }
  }
  previewCardEl.style.display = 'block';
}

async function fetchRules() {
  const rules = await getRules();

  rulesListEl.innerHTML = '';
  if (rules.length === 0) {
    rulesListEl.innerHTML = '<li class="list-group-item">No rules yet.</li>';
    return;
  }

  for (const rule of rules) {
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
    if (rule.videoCodec) {
      ruleText += ` and video codec is ${rule.videoCodec}`;
    }
    if (rule.audioCodec) {
      ruleText += ` and audio codec is ${rule.audioCodec}`;
    }
    if (rule.resolution) {
      ruleText += ` and resolution is ${rule.resolution}`;
    }
    if (rule.minSize) {
      ruleText += ` and min size is ${rule.minSize}MB`;
    }
    if (rule.maxSize) {
      ruleText += ` and max size is ${rule.maxSize}MB`;
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
  await deleteRuleApi(ruleId);
  fetchRules();
}

async function fetchData(mediaType) {
  let data;
  if (mediaType === 'sonarr') {
    data = await getSonarrData();
  } else {
    data = await getRadarrData();
  }

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
  let data;
  if (mediaType === 'sonarr') {
    data = await getSonarrData();
  } else {
    data = await getRadarrData();
  }
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

fetchSonarrWanted();
fetchRadarrWanted();

async function fetchAndRender(fetchFn, listElId, noItemsMessage, itemRenderer) {
  const data = await fetchFn();
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



async function fetchSonarrWanted() {
  fetchAndRender(getSonarrWanted, 'sonarr-wanted', 'No wanted items.', (item) => renderWantedItem(item, searchSonarr, 'seriesId'));
}

async function fetchRadarrWanted() {
  fetchAndRender(getRadarrWanted, 'radarr-wanted', 'No wanted items.', (item) => renderWantedItem(item, searchRadarr, 'movieId'));
}

async function searchSonarr(seriesId) {
  await searchSonarrApi(seriesId);
}

async function searchRadarr(movieId) {
  await searchRadarrApi(movieId);
}
