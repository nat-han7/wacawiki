class WacaBook extends HTMLElement {
    constructor() {
        super();
        this.attachShadow({ mode: 'open' });
    }

    static get observedAttributes() {
        return ['thumbnail', 'title', 'author', 'href', 'skeleton'];
    }

    connectedCallback() {
        this.render();
    }

    attributeChangedCallback() {
        this.render();
    }

    render() {
        const isSkeleton = this.hasAttribute('skeleton');

        const thumbnail = this.getAttribute('thumbnail') || 'https://via.placeholder.com/150x220?text=Kein+Cover';
        const title = this.getAttribute('title') || 'Unbekannter Titel';
        const author = this.getAttribute('author') || 'Unbekannt';
        const href = this.getAttribute('href') || '#';

        this.shadowRoot.innerHTML = `
            <style>
                :host {
                    display: block;
                    width: 100%;
                    margin: 0;
                }

                *, *::before, *::after {
                    box-sizing: border-box;
                }

                .book-card {
                    display: flex;
                    flex-direction: column;
                    width: 100%;
                    height: 100%;
                    background: #18221e;
                    border: 1px solid rgba(229, 169, 60, 0.2);
                    border-radius: 12px;
                    padding: 10px;
                    text-decoration: none;
                    color: #e2e8e5;
                    transition: all 0.25s ease;
                    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.4);
                    position: relative;
                    overflow: hidden;
                }

                .book-card:not(.skeleton):hover, 
                .book-card:not(.skeleton):active {
                    transform: translateY(-4px);
                    border-color: rgba(229, 169, 60, 0.6);
                    box-shadow: 0 0 20px rgba(229, 169, 60, 0.25), 0 8px 25px rgba(0, 0, 0, 0.6);
                }

                .cover-wrapper {
                    position: relative;
                    width: 100%;
                    aspect-ratio: 2 / 3;
                    border-radius: 8px;
                    overflow: hidden;
                    margin-bottom: 8px;
                    background: #0f1412;
                }

                .cover-img {
                    width: 100%;
                    height: 100%;
                    object-fit: cover;
                    display: block;
                }

                .cover-wrapper::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 6px;
                    height: 100%;
                    background: linear-gradient(to right, rgba(0,0,0,0.5), transparent);
                    z-index: 1;
                }

                .book-info {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                    flex-grow: 1;
                }

                .book-title {
                    font-family: 'Cinzel', serif, sans-serif;
                    font-size: clamp(0.85rem, 2vw, 0.95rem);
                    font-weight: 700;
                    color: #ffffff;
                    margin: 0;
                    line-height: 1.25;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                .book-author {
                    font-family: 'Plus Jakarta Sans', sans-serif;
                    font-size: 0.75rem;
                    color: #9ab0a6;
                    margin-top: auto;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }

                /* --- SKELETON STYLES & ANIMATION --- */
                .skeleton-box {
                    background-color: #22302a;
                    position: relative;
                    overflow: hidden;
                    border-radius: 4px;
                }

                .skeleton-box::after {
                    position: absolute;
                    top: 0;
                    right: 0;
                    bottom: 0;
                    left: 0;
                    transform: translateX(-100%);
                    background-image: linear-gradient(
                        90deg,
                        rgba(255, 255, 255, 0) 0,
                        rgba(255, 255, 255, 0.05) 20%,
                        rgba(255, 255, 255, 0.1) 60%,
                        rgba(255, 255, 255, 0)
                    );
                    animation: shimmer 1.6s infinite;
                    content: '';
                }

                @keyframes shimmer {
                    100% {
                        transform: translateX(100%);
                    }
                }

                .skeleton-title {
                    height: 14px;
                    width: 85%;
                    margin-top: 4px;
                }

                .skeleton-author {
                    height: 10px;
                    width: 60%;
                    margin-top: 4px;
                }
            </style>

            ${isSkeleton ? `
                <div class="book-card skeleton">
                    <div class="cover-wrapper skeleton-box"></div>
                    <div class="book-info">
                        <div class="skeleton-box skeleton-title"></div>
                        <div class="skeleton-box skeleton-author"></div>
                    </div>
                </div>
            ` : `
                <a href="${href}" class="book-card">
                    <div class="cover-wrapper">
                        <img class="cover-img" src="${thumbnail}" alt="${title}" loading="lazy">
                    </div>
                    <div class="book-info">
                        <h4 class="book-title">${title}</h4>
                        <span class="book-author">von ${author}</span>
                    </div>
                </a>
            `}
        `;
    }
}

customElements.define('waca-book', WacaBook);
