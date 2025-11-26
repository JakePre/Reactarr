// API interaction layer

async function getRules() {
    const response = await fetch('/api/rules');
    const data = await response.json();
    return data.rules;
}

async function createRule(rule) {
    await fetch('/api/rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule),
    });
}

async function deleteRuleApi(ruleId) {
    await fetch(`/api/rules/${ruleId}`, { method: 'DELETE' });
}

async function previewRuleApi(rule) {
    const response = await fetch('/api/rules/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rule),
    });
    const data = await response.json();
    return data.affected_items;
}

async function getSonarrData() {
    const response = await fetch('/api/sonarr/data');
    return await response.json();
}

async function getRadarrData() {
    const response = await fetch('/api/radarr/data');
    return await response.json();
}

async function getSonarrLibrary() {
    const response = await fetch('/api/sonarr/library');
    return await response.json();
}

async function getSonarrEpisodes() {
    const response = await fetch('/api/sonarr/episodes');
    return await response.json();
}

async function getRadarrLibrary() {
    const response = await fetch('/api/radarr/library');
    return await response.json();
}

async function getSonarrWanted() {
    const response = await fetch('/api/sonarr/wanted');
    return await response.json();
}

async function getRadarrWanted() {
    const response = await fetch('/api/radarr/wanted');
    return await response.json();
}

async function searchSonarrApi(seriesId) {
    await fetch('/api/sonarr/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ seriesId }),
    });
}

async function searchRadarrApi(movieId) {
    await fetch('/api/radarr/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ movieId }),
    });
}
