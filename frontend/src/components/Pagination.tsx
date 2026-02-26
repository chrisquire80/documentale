import React from 'react';

type PageItem = number | 'ellipsis';

/**
 * Generates the sequence of page numbers to display.
 * Always shows: first page, current ±1, last page, with ellipsis in gaps.
 *
 * Examples (current=5, total=10):
 *   [1, 'ellipsis', 4, 5, 6, 'ellipsis', 10]
 */
function getPageItems(current: number, total: number): PageItem[] {
    if (total <= 1) return [1];
    if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);

    const items: PageItem[] = [1];

    if (current > 3) items.push('ellipsis');

    const start = Math.max(2, current - 1);
    const end = Math.min(total - 1, current + 1);
    for (let p = start; p <= end; p++) items.push(p);

    if (current < total - 2) items.push('ellipsis');

    items.push(total);
    return items;
}

interface Props {
    currentPage: number;
    totalPages: number;
    total: number;
    onPageChange: (page: number) => void;
}

const Pagination: React.FC<Props> = ({ currentPage, totalPages, total, onPageChange }) => {
    if (total === 0) return null;

    const pages = getPageItems(currentPage, totalPages);

    return (
        <nav className="pagination" aria-label="Navigazione pagine">
            <button
                className="pagination-btn"
                onClick={() => onPageChange(currentPage - 1)}
                disabled={currentPage === 1}
                aria-label="Pagina precedente"
            >
                ←
            </button>

            {pages.map((p, i) =>
                p === 'ellipsis' ? (
                    <span key={`ell-${i}`} className="pagination-ellipsis">…</span>
                ) : (
                    <button
                        key={p}
                        className={`pagination-btn${p === currentPage ? ' pagination-btn--active' : ''}`}
                        onClick={() => onPageChange(p)}
                        aria-current={p === currentPage ? 'page' : undefined}
                    >
                        {p}
                    </button>
                )
            )}

            <button
                className="pagination-btn"
                onClick={() => onPageChange(currentPage + 1)}
                disabled={currentPage >= totalPages}
                aria-label="Pagina successiva"
            >
                →
            </button>

            <span className="pagination-info">
                {total} document{total !== 1 ? 'i' : 'o'}
            </span>
        </nav>
    );
};

export default Pagination;
