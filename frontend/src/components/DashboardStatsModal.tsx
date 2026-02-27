import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, PieChart, Users, Tag, FileText } from 'lucide-react';
import api from '../services/api';
import './DashboardStatsModal.css';

interface DocumentStats {
    total_documents: number;
    by_tags: Record<string, number>;
    by_users: Record<string, number>;
}

interface Props {
    onClose: () => void;
}

const StatBox: React.FC<{ icon: React.ReactNode; label: string; value: string | number; color: string }> = ({ icon, label, value, color }) => (
    <div className="stat-box">
        <div className="stat-box-icon" style={{ background: `${color}15`, color: color }}>
            {icon}
        </div>
        <div>
            <div className="stat-box-label">{label}</div>
            <div className="stat-box-value">{value}</div>
        </div>
    </div>
);

const DashboardStatsModal: React.FC<Props> = ({ onClose }) => {
    const { data, isLoading, error } = useQuery<DocumentStats>({
        queryKey: ['doc-stats'],
        queryFn: async () => {
            const res = await api.get('/documents/stats');
            return res.data;
        }
    });

    return (
        <div className="dashboard-stats-overlay" onClick={onClose}>
            <div
                className="auth-card dashboard-stats-modal"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="stats-header">
                    <h2 className="stats-title">
                        <PieChart size={20} style={{ color: 'var(--accent)' }} />
                        Statistiche Documenti
                    </h2>
                    <button
                        onClick={onClose}
                        className="stats-close-btn"
                        aria-label="Chiudi"
                    >
                        <X size={20} />
                    </button>
                </div>

                {isLoading && (
                    <div className="stats-loading">
                        Caricamento statistiche...
                    </div>
                )}

                {error && (
                    <div className="stats-error">
                        Errore nel caricamento delle statistiche.
                    </div>
                )}

                {data && (
                    <div className="stats-content-list">
                        {/* KPI Principali */}
                        <div className="stats-grid-kpi">
                            <StatBox
                                icon={<FileText size={24} />}
                                label="Totale Documenti Attivi"
                                value={data.total_documents}
                                color="#64DEC2"
                            />
                            <StatBox
                                icon={<Users size={24} />}
                                label="Utenti Attivi (Proprietari)"
                                value={Object.keys(data.by_users).length}
                                color="#A5B4FC"
                            />
                        </div>

                        {/* Distribuzione Tag */}
                        <div>
                            <h3 className="stats-tags-title">
                                <Tag size={16} /> Principali Tag Utilizzati
                            </h3>
                            {Object.keys(data.by_tags).length === 0 ? (
                                <p className="stats-tags-none">Nessun tag assegnato ai documenti.</p>
                            ) : (
                                <div className="stats-tags-container">
                                    {Object.entries(data.by_tags).map(([tag, count]) => (
                                        <div key={tag} className="stats-tag-badge">
                                            <span className="stats-tag-label">{tag}</span>
                                            <span className="stats-tag-count">{count}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DashboardStatsModal;
