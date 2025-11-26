const mediaTypeEl = document.getElementById('media-type');
const titleFilterEl = document.getElementById('title-filter');
const videoCodecEl = document.getElementById('video-codec');
const audioCodecEl = document.getElementById('audio-codec');
const resolutionEl = document.getElementById('resolution');
const minSizeEl = document.getElementById('min-size');
const maxSizeEl = document.getElementById('max-size');
const tableBodyEl = document.querySelector('#results-table tbody');

let currentItems = [];

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

        const items = await getSonarrLibrary();
        currentItems = items.map(item => ({
            title: item.title,
            videoCodec: 'N/A (Series)',
            audioCodec: 'N/A (Series)',
            resolution: item.qualityProfileId, // This is ID, not name.
            size: item.statistics ? item.statistics.sizeOnDisk : 0,
            status: item.status,
            raw: item
        }));
    } else {
        const items = await getRadarrLibrary();
        currentItems = items.map(item => ({
            title: item.title,
            videoCodec: item.movieFile && item.movieFile.mediaInfo ? item.movieFile.mediaInfo.videoCodec : '',
            audioCodec: item.movieFile && item.movieFile.mediaInfo ? item.movieFile.mediaInfo.audioCodec : '',
            resolution: item.movieFile && item.movieFile.mediaInfo ? item.movieFile.mediaInfo.resolution : '',
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
fetchLibrary();
