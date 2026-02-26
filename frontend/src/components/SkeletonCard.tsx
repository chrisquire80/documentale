import React from 'react';

const SkeletonCard: React.FC = () => (
    <div className="doc-card skeleton-card" aria-hidden="true">
        <div className="skeleton-line skeleton-title" />
        <div className="skeleton-line skeleton-meta" />
        <div className="skeleton-line skeleton-meta-short" />
        <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem' }}>
            <div className="skeleton-line skeleton-badge" />
            <div className="skeleton-line skeleton-badge" />
        </div>
    </div>
);

export default SkeletonCard;
