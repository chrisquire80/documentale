import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, Database, Zap, HardDrive, Activity } from 'lucide-react';
import api from '../services/api';

interface Stats {
    redis_available: boolean;
    message?: string;
    keyspace_hits?: number;
    keyspace_misses?: number;
    hit_rate_percent?: number;
    total_operations?: number;
    cached_doc_queries?: number;
    used_memory_human?: string;
}

interface Props {
    onClose: () => void;
}

function HitRateBar({ rate }: { rate: number }) {
    const color = rate >= 70 ? '#22c55e' : rate >= 40 ? '#f59e0b' : '#ef4444';
    return (
        <div style={{ marginTop: '0.4rem' }}>
            <div style={{ height: '6px', background: 'var(--glass)', borderRadius: '999px', overflow: 'hidden' }}>
                <div style={{ width: `${rate}%`, height: '100%', background: color, borderRadius: '999px', transition: 'width 0.4s ease' }} />
            </div>
        </div>
    );
}

const StatRow: React.FC<{ label: React.ReactNode; value: React.ReactNode }> = ({ label, value }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.6rem 0', borderBottom: '1px solid var(--glass)' }}>
        <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>{label}</span>
        <strong>{value}</strong>
    </div>
);

const CacheStatsModal: React.FC<Props> = ({ onClose }) => {
    const { data, isLoading, error, dataUpdatedAt } = useQuery<Stats>({
        queryKey: ['admin-stats'],
        queryFn: async () => {
            const res = await api.get('/admin/stats');
            return res.data;
        },
        refetchInterval: 5000,
        retry: false,
    });

    const lastUpdate = dataUpdatedAt
        ? new Date(dataUpdatedAt).toLocaleTimeString('it-IT')
        : '—';

    return (
        <div
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 200 }}
            onClick={onClose}
        >
            <div
                className="auth-card"
                style={{ margin: 0, position: 'relative', width: '100%', maxWidth: '460px' }}
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem' }}>
                        <Database size={18} style={{ color: 'var(--accent)' }} />
                        Analytics Cache Redis
                    </h2>
                    <button
                        onClick={onClose}
                        style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex' }}
                        aria-label="Chiudi"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Loading */}
                {isLoading && (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem' }}>
                        Caricamento statistiche…
                    </div>
                )}

                {/* Error / Access denied */}
                {error && (
                    <div style={{ color: 'var(--error)', textAlign: 'center', padding: '1.5rem', background: 'rgba(239,68,68,0.08)', borderRadius: '0.5rem' }}>
                        Accesso riservato agli amministratori.
                    </div>
                )}

                {/* Redis unavailable */}
                {data && !data.redis_available && (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '1.5rem' }}>
                        {data.message ?? 'Redis non disponibile. La cache è disabilitata.'}
                    </div>
                )}

                {/* Stats */}
                {data?.redis_available && (
                    <>
                        {/* Hit Rate with bar */}
                        <div style={{ background: 'rgba(56,189,248,0.06)', borderRadius: '0.5rem', padding: '0.8rem 1rem', marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                                    <Zap size={14} style={{ color: 'var(--accent)' }} />
                                    Cache Hit Rate
                                </span>
                                <strong style={{ fontSize: '1.5rem', color: data.hit_rate_percent! >= 70 ? '#22c55e' : data.hit_rate_percent! >= 40 ? '#f59e0b' : '#ef4444' }}>
                                    {data.hit_rate_percent}%
                                </strong>
                            </div>
                            <HitRateBar rate={data.hit_rate_percent!} />
                        </div>

                        <StatRow
                            label={<span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><Activity size={14} />Hit</span>}
                            value={<span style={{ color: '#22c55e' }}>{data.keyspace_hits?.toLocaleString('it-IT')}</span>}
                        />
                        <StatRow
                            label="Miss"
                            value={<span style={{ color: '#ef4444' }}>{data.keyspace_misses?.toLocaleString('it-IT')}</span>}
                        />
                        <StatRow
                            label="Operazioni totali"
                            value={data.total_operations?.toLocaleString('it-IT')}
                        />
                        <StatRow
                            label="Query documenti in cache"
                            value={data.cached_doc_queries}
                        />
                        <StatRow
                            label={<span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}><HardDrive size={14} />Memoria usata</span>}
                            value={data.used_memory_human}
                        />

                        <div style={{ marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.75rem', textAlign: 'right' }}>
                            Aggiornamento automatico ogni 5s — ultimo: {lastUpdate}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default CacheStatsModal;
