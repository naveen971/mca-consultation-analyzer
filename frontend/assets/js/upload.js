/**
 * Upload page logic — handles file drag-drop, upload, preview,
 * and orchestrates the analysis pipeline (sentiment → summary → wordcloud).
 */

const API_BASE = window.location.origin;

// ── DOM Elements ──────────────────────────────────────────────────────────
const uploadZone = document.getElementById('upload-zone');
const fileInput = document.getElementById('file-input');
const fileInfo = document.getElementById('file-info');
const fileName = document.getElementById('file-name');
const fileMeta = document.getElementById('file-meta');
const columnsInfo = document.getElementById('columns-info');
const previewSection = document.getElementById('preview-section');
const previewThead = document.getElementById('preview-thead');
const previewTbody = document.getElementById('preview-tbody');
const analyzeSection = document.getElementById('analyze-section');
const btnAnalyze = document.getElementById('btn-analyze');
const commentCountInfo = document.getElementById('comment-count-info');
const progressSection = document.getElementById('progress-section');
const progressBar = document.getElementById('progress-bar');
const progressPct = document.getElementById('progress-pct');
const progressTitle = document.getElementById('progress-title');
const manualInput = document.getElementById('manual-input');
const btnAnalyzeText = document.getElementById('btn-analyze-text');
const btnChangeFile = document.getElementById('btn-change-file');
const btnRemoveFile = document.getElementById('btn-remove-file');

// State
let uploadedComments = [];
let uploadedFileName = '';

// ── Drag & Drop ───────────────────────────────────────────────────────────
uploadZone.addEventListener('click', () => fileInput.click());

uploadZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
});

uploadZone.addEventListener('dragleave', () => {
    uploadZone.classList.remove('drag-over');
});

uploadZone.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    const files = e.dataTransfer.files;
    if (files.length > 0) handleFile(files[0]);
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) handleFile(e.target.files[0]);
});

btnChangeFile.addEventListener('click', () => fileInput.click());

btnRemoveFile.addEventListener('click', () => {
    resetUpload();
});

// ── Manual Text Input ────────────────────────────────────────────────────
manualInput.addEventListener('input', () => {
    const text = manualInput.value.trim();
    btnAnalyzeText.disabled = text.length === 0;
});

btnAnalyzeText.addEventListener('click', () => {
    const text = manualInput.value.trim();
    if (!text) return;

    const lines = text.split('\n').filter(line => line.trim().length > 0);
    uploadedComments = lines.map(line => ({
        text: line.trim(),
        stakeholder_name: null,
        section: null,
    }));
    uploadedFileName = 'manual-input';

    runAnalysisPipeline();
});

// ── File Handling ────────────────────────────────────────────────────────
async function handleFile(file) {
    // Validate
    const validTypes = ['.csv', '.xlsx', '.xls'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validTypes.includes(ext)) {
        showToast('Please upload a CSV or Excel file.', 'error');
        return;
    }
    if (file.size > 10 * 1024 * 1024) {
        showToast('File is too large. Maximum size is 10 MB.', 'error');
        return;
    }

    // Show file info
    uploadZone.classList.add('hidden');
    fileInfo.classList.remove('hidden');
    fileName.textContent = file.name;
    fileMeta.textContent = `${(file.size / 1024).toFixed(1)} KB • ${ext.toUpperCase().slice(1)}`;

    // Upload to backend
    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData,
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || err.error || 'Upload failed');
        }

        const data = await res.json();
        uploadedFileName = data.filename;
        uploadedComments = data.comments;

        // Show detected columns
        columnsInfo.classList.remove('hidden');
        document.getElementById('col-comment').textContent = data.detected_columns.comment_column;
        document.getElementById('col-stakeholder').textContent =
            data.detected_columns.stakeholder_column || '—';
        document.getElementById('col-section').textContent =
            data.detected_columns.section_column || '—';

        // Show preview table
        if (data.preview && data.preview.length > 0) {
            renderPreview(data.preview);
            previewSection.classList.remove('hidden');
        }

        // Show analyze button
        analyzeSection.classList.remove('hidden');
        commentCountInfo.textContent =
            `${data.comments.length} comments detected from ${data.total_rows} rows`;

    } catch (err) {
        showToast(err.message, 'error');
        resetUpload();
    }
}

function renderPreview(rows) {
    if (!rows.length) return;
    const headers = Object.keys(rows[0]);

    previewThead.innerHTML = `<tr>${headers.map(h =>
        `<th>${escapeHtml(h)}</th>`
    ).join('')}</tr>`;

    previewTbody.innerHTML = rows.map(row =>
        `<tr>${headers.map(h =>
            `<td title="${escapeHtml(String(row[h] || ''))}">${escapeHtml(String(row[h] || ''))}</td>`
        ).join('')}</tr>`
    ).join('');
}

function resetUpload() {
    uploadZone.classList.remove('hidden');
    fileInfo.classList.add('hidden');
    columnsInfo.classList.add('hidden');
    previewSection.classList.add('hidden');
    analyzeSection.classList.add('hidden');
    progressSection.classList.add('hidden');
    fileInput.value = '';
    uploadedComments = [];
}

// ── Analysis Pipeline ────────────────────────────────────────────────────
btnAnalyze.addEventListener('click', () => runAnalysisPipeline());

async function runAnalysisPipeline() {
    if (uploadedComments.length === 0) {
        showToast('No comments to analyze.', 'error');
        return;
    }

    // Show progress, hide analyze button
    analyzeSection.classList.add('hidden');
    progressSection.classList.remove('hidden');
    btnAnalyze.disabled = true;
    btnAnalyzeText.disabled = true;

    const results = {
        filename: uploadedFileName,
        timestamp: new Date().toISOString(),
        comments: uploadedComments,
        sentiment: null,
        summary: null,
        wordcloud: null,
        wordcloudBySentiment: null,
    };

    try {
        // Step 1: Sentiment Analysis
        updateProgress('sentiment', 25, 'Analyzing sentiment...');
        const sentimentPayload = { comments: uploadedComments };
        const sentimentRes = await fetch(`${API_BASE}/api/sentiment/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sentimentPayload),
        });
        if (!sentimentRes.ok) throw new Error('Sentiment analysis failed');
        results.sentiment = await sentimentRes.json();
        updateProgress('sentiment', 40, 'Sentiment analysis complete!', true);

        // Step 2: Summary Generation
        updateProgress('summary', 55, 'Generating summaries...');
        const summaryRes = await fetch(`${API_BASE}/api/summary/batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sentimentPayload),
        });
        if (!summaryRes.ok) throw new Error('Summary generation failed');
        results.summary = await summaryRes.json();
        updateProgress('summary', 70, 'Summaries generated!', true);

        // Step 3: Word Cloud
        updateProgress('wordcloud', 80, 'Creating word cloud...');
        const texts = uploadedComments.map(c => c.text);
        const wcRes = await fetch(`${API_BASE}/api/wordcloud/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ comments: texts }),
        });
        if (!wcRes.ok) throw new Error('Word cloud generation failed');
        results.wordcloud = await wcRes.json();

        // Step 3b: Per-sentiment word clouds
        if (results.sentiment && results.sentiment.results) {
            const sentimentLabels = results.sentiment.results.map(r => r.sentiment);
            const wcSentRes = await fetch(`${API_BASE}/api/wordcloud/by-sentiment`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ comments: texts, sentiments: sentimentLabels }),
            });
            if (wcSentRes.ok) {
                results.wordcloudBySentiment = await wcSentRes.json();
            }
        }
        updateProgress('wordcloud', 100, 'Analysis complete!', true);

        // Store results and redirect
        sessionStorage.setItem('analysisResults', JSON.stringify(results));

        setTimeout(() => {
            window.location.href = 'results.html';
        }, 800);

    } catch (err) {
        showToast(`Analysis failed: ${err.message}`, 'error');
        progressSection.classList.add('hidden');
        analyzeSection.classList.remove('hidden');
        btnAnalyze.disabled = false;
        btnAnalyzeText.disabled = false;
    }
}

// ── Progress Updates ─────────────────────────────────────────────────────
function updateProgress(step, pct, title, done = false) {
    progressBar.style.width = pct + '%';
    progressPct.textContent = pct + '%';
    progressTitle.textContent = title;

    // Update step indicators
    const stepEl = document.getElementById(`step-${step}`);
    if (stepEl) {
        if (done) {
            stepEl.classList.remove('active');
            stepEl.classList.add('done');
        } else {
            stepEl.classList.add('active');
        }
    }
}

// ── Utilities ────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span>${type === 'error' ? '❌' : '✅'}</span> ${escapeHtml(message)}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}
