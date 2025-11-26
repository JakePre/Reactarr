const mediaTypeEl = document.getElementById('media-type');
const titleFilterEl = document.getElementById('title-filter');
const videoCodecEl = document.getElementById('video-codec');
const audioCodecEl = document.getElementById('audio-codec');
const resolutionEl = document.getElementById('resolution');
const minSizeEl = document.getElementById('min-size');
const maxSizeEl = document.getElementById('max-size');
const tableBodyEl = document.querySelector('#results-table tbody');

let currentItems = [];
let sonarrMetadata = { qualityProfiles: {}, tags: {} };
let radarrMetadata = { qualityProfiles: {}, tags: {} };

async function fetchMetadata() {
    try {
        const [sonarrRes, radarrRes] = await Promise.all([
            fetch('/api/sonarr/data'),
            fetch('/api/radarr/data')
        ]);

        const sonarrData = await sonarrRes.json();
        const radarrData = await radarrRes.json();

        console.log("Sonarr Data:", sonarrData);
        console.log("Radarr Data:", radarrData);

        if (sonarrData.quality_profiles) {
            sonarrData.quality_profiles.forEach(p => sonarrMetadata.qualityProfiles[p.id] = p.name);
        }
        if (sonarrData.tags) {
            sonarrData.tags.forEach(t => sonarrMetadata.tags[t.id] = t.label);
        }

        if (radarrData.quality_profiles) {
            radarrData.quality_profiles.forEach(p => radarrMetadata.qualityProfiles[p.id] = p.name);
        }
        if (radarrData.tags) {
            radarrData.tags.forEach(t => radarrMetadata.tags[t.id] = t.label);
        }
    } catch (e) {
        console.error("Error fetching metadata:", e);
    }
}

async function fetchLibrary() {
    const mediaType = mediaTypeEl.value;
    if (mediaType === 'sonarr') {
        // For Sonarr, we might want episodes, but library returns Series.
        // Series don't have codecs usually, episodes do.
        // Fetching all episodes for all series is heavy.
        // Maybe we just list Series for now, or fetch episodes for a selected series?
        // The user asked for "identifying all of these attributes", which implies file level info.
        // Let's stick to Series level info if available, or maybe just fetch Series and show basic info?
        // Wait, Series objects in Sonarr don't have mediaInfo. Episodes do.
        // Radarr Movies DO have mediaInfo.

        // If the user wants to filter by codec in Sonarr, we need episodes.
        // Fetching all episodes is too much.
        // Let's start with Radarr support as it's cleaner (1 Movie = 1 File).
        // For Sonarr, maybe we just show Series status?
        // Or we can try to fetch episodes for the first 50 series?

        // Let's implement Radarr first fully.
        // For Sonarr, let's just show Series and maybe note that file info is not available at series level.

        const items = await getSonarrLibrary() || [];
        currentItems = items.map(item => ({
            title: item.title,
            videoCodec: 'N/A (Series)',
            audioCodec: 'N/A (Series)',
            resolution: sonarrMetadata.qualityProfiles[item.qualityProfileId] || item.qualityProfileId,
            quality: sonarrMetadata.qualityProfiles[item.qualityProfileId] || 'Unknown',
            tags: item.tags.map(id => sonarrMetadata.tags[id] || id).join(', '),
            size: item.statistics ? item.statistics.sizeOnDisk : 0,
            status: item.status,
            raw: item
        }));
    } else if (mediaType === 'sonarr_episodes') {
        const items = await getSonarrEpisodes() || [];
        currentItems = items.map(item => {
            const file = item.episodeFile;
            const mediaInfo = file && file.mediaInfo;
            const quality = file && file.quality && file.quality.quality ? file.quality.quality.name : '';
            return {
                title: `${item.seriesTitle} - S${item.seasonNumber}E${item.episodeNumber} - ${item.title}`,
                videoCodec: mediaInfo ? mediaInfo.videoCodec : '',
                audioCodec: mediaInfo ? mediaInfo.audioCodec : '',
                resolution: mediaInfo ? mediaInfo.resolution : '',
                quality: quality,
                tags: item.tags ? item.tags.map(id => sonarrMetadata.tags[id] || id).join(', ') : '',
                size: file ? file.size : 0,
                status: item.hasFile ? 'Downloaded' : (item.monitored ? 'Missing' : 'Unmonitored'), // Simplified status logic
                raw: item
            };
        });
    } else {
        const items = await getRadarrLibrary() || [];
        currentItems = items.map(item => ({
            title: item.title,
            videoCodec: item.movieFile && item.movieFile.mediaInfo ? item.movieFile.mediaInfo.videoCodec : '',
            audioCodec: item.movieFile && item.movieFile.mediaInfo ? item.movieFile.mediaInfo.audioCodec : '',
            resolution: item.movieFile && item.movieFile.mediaInfo ? item.movieFile.mediaInfo.resolution : '',
            quality: item.movieFile && item.movieFile.quality && item.movieFile.quality.quality ? item.movieFile.quality.quality.name : (radarrMetadata.qualityProfiles[item.qualityProfileId] || ''),
            tags: item.tags.map(id => radarrMetadata.tags[id] || id).join(', '),
            size: item.sizeOnDisk,
            status: item.status,
            raw: item
        }));
    }
    renderTable(currentItems);
}

function renderTable(items) {
    tableBodyEl.innerHTML = '';
    if (items.length === 0) {
        tableBodyEl.innerHTML = '<tr><td colspan="6">No items found.</td></tr>';
        return;
    }

    for (const item of items) {
        const tr = document.createElement('tr');
        const sizeMB = item.size ? (item.size / (1024 * 1024)).toFixed(2) : '0';

        tr.innerHTML = `
            <td>${item.title}</td>
            <td>${item.videoCodec || '-'}</td>
            <td>${item.audioCodec || '-'}</td>
            <td>${item.resolution || '-'}</td>
            <td>${item.quality || '-'}</td>
            <td>${item.tags || '-'}</td>
            <td>${sizeMB}</td>
            <td>${item.status}</td>
        `;
        tableBodyEl.appendChild(tr);
    }
}

function applyFilters() {
    const title = titleFilterEl.value.toLowerCase();
    const videoCodec = videoCodecEl.value.toLowerCase();
    const audioCodec = audioCodecEl.value.toLowerCase();
    const resolution = resolutionEl.value.toLowerCase();
    const minSize = minSizeEl.value ? parseFloat(minSizeEl.value) : null;
    const maxSize = maxSizeEl.value ? parseFloat(maxSizeEl.value) : null;

    const filteredItems = currentItems.filter(item => {
        if (title && !item.title.toLowerCase().includes(title)) return false;
        if (videoCodec && !String(item.videoCodec).toLowerCase().includes(videoCodec)) return false;
        if (audioCodec && !String(item.audioCodec).toLowerCase().includes(audioCodec)) return false;
        if (resolution && !String(item.resolution).toLowerCase().includes(resolution)) return false;

        const sizeMB = item.size ? item.size / (1024 * 1024) : 0;
        if (minSize !== null && sizeMB < minSize) return false;
        if (maxSize !== null && sizeMB > maxSize) return false;

        return true;
    });

    renderTable(filteredItems);
}

mediaTypeEl.addEventListener('change', fetchLibrary);

// Initial load
fetchMetadata().then(fetchLibrary);
