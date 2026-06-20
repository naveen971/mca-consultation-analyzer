/**
 * Word cloud display logic — renders base64 images and keyword bar charts.
 * Supports tab switching between overall and per-sentiment clouds.
 */

const WordCloudManager = {
    currentTab: 'overall',
    data: null,
    sentimentData: null,

    /**
     * Initialize with word cloud data.
     */
    init(wordcloudData, sentimentWordcloudData) {
        this.data = wordcloudData;
        this.sentimentData = sentimentWordcloudData;
        this.setupTabs();
        this.render('overall');
    },

    /**
     * Set up tab click handlers.
     */
    setupTabs() {
        const tabs = document.querySelectorAll('#wordcloud-tabs .tab');
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                this.currentTab = tab.dataset.tab;
                this.render(this.currentTab);
            });
        });
    },

    /**
     * Render the word cloud for a given tab.
     */
    render(tab) {
        const imgEl = document.getElementById('wordcloud-image');
        const keywordsEl = document.getElementById('keywords-list');

        let cloudData = null;

        if (tab === 'overall') {
            cloudData = this.data;
        } else if (this.sentimentData) {
            const key = tab.toLowerCase();
            cloudData = this.sentimentData[key];
        }

        if (cloudData && cloudData.image_base64) {
            imgEl.src = `data:image/png;base64,${cloudData.image_base64}`;
            imgEl.alt = `${tab.charAt(0).toUpperCase() + tab.slice(1)} Word Cloud`;
            this.renderKeywords(cloudData.top_keywords || [], keywordsEl);
        } else {
            imgEl.src = '';
            imgEl.alt = 'No data available for this category';
            keywordsEl.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    <p>No keywords available for ${tab} comments</p>
                </div>
            `;
        }
    },

    /**
     * Render the keyword bar chart list.
     */
    renderKeywords(keywords, container) {
        if (!keywords.length) {
            container.innerHTML = '<p style="color: var(--text-muted);">No keywords found</p>';
            return;
        }

        container.innerHTML = keywords.slice(0, 15).map((kw, i) => `
            <div class="keyword-item" style="animation: slideInLeft 0.3s ease-out ${i * 0.05}s both;">
                <span class="keyword-name">${escapeHtml(kw.keyword)}</span>
                <div class="keyword-bar-wrapper">
                    <div class="keyword-bar" style="width: ${kw.score * 100}%;"></div>
                </div>
                <span class="keyword-score">${(kw.score * 100).toFixed(0)}%</span>
            </div>
        `).join('');
    }
};

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
