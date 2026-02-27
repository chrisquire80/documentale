import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { X, BarChart2, FileText, Trash2, Files } from 'lucide-react';
import api from '../services/api';

interface DocStats {
    total_documents: number;
    active_documents: number;
    deleted_documents: number;
    by_file_type: { file_type: string; count: number }[];
    uploads_by_day: { day: string; count: number }[];
    top_uploaders: { owner_id: string; count: number }[];
}

interface Props {
    onClose: () => void;
}

const TYPE_LABELS: Record<string, string> = {
    'application/pdf': 'PDF',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
    'application/msword': 'DOC',
    'text/plain': 'TXT',
    'image/jpeg': 'JPEG',
    'image/png': 'PNG',
    'image/gif': 'GIF',
    'image/webp': 'WebP',
};

const StatsWidget: React.FC<Props> = ({ onClose }) => {
    const { data, isLoading, error } = useQuery<DocStats>({
        queryKey: ['document-stats'],
        queryFn: async () => {
            const res = await api.get('/admin/document-stats');
            return res.data;
        },
    });

    const maxByDay = data ? Math.max(...data.uploads_by_day.map((d) => d.count), 1) : 1;
    const maxByType = data ? Math.max(...data.by_file_type.map((t) => t.count), 1) : 1;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: '660px', maxHeight: '85vh', overflowY: 'auto' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <BarChart2 size={18} /> Statistiche Documenti
                    </h2>
                    <button className="icon-btn" onClick={onClose}><X size={20} /></button>
                </div>

                {isLoading && <p style={{ color: 'var(--text-muted)' }}>Caricamento…</p>}
                {error && <p style={{ color: 'var(--error)' }}>Errore: solo gli amministratori possono visualizzare le statistiche.</p>}

                {data && (
                    <>
                        {/* Riepilogo */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: '1rem', marginBottom: '2rem' }}>
                            {[
                                { icon: <Files size={20} />, label: 'Totale', value: data.total_documents, color: 'var(--accent)' },
                                { icon: <FileText size={20} />, label: 'Attivi', value: data.active_documents, color: '#22c55e' },
                                { icon: <Trash2 size={20} />, label: 'Nel cestino', value: data.deleted_documents, color: 'var(--error)' },
                            ].map((s) => (
                                <div key={s.label} style={{ background: 'var(--glass)', borderRadius: '0.6rem', padding: '1rem', textAlign: 'center' }}>
                                    <div style={{ color: s.color, marginBottom: '0.3rem' }}>{s.icon}</div>
                                    <div style={{ fontSize: '1.8rem', fontWeight: 700, color: s.color }}>{s.value}</div>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{s.label}</div>
                                </div>
                            ))}
                        </div>

                        {/* Per tipo file */}
                        {data.by_file_type.length > 0 && (
                            <>
                                <p style={{ fontWeight: 600, marginBottom: '0.75rem' }}>Per tipo file</p>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1.75rem' }}>
                                    {data.by_file_type.map((t) => (
                                        <div key={t.file_type}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.2rem' }}>
                                                <span>{TYPE_LABELS[t.file_type] ?? t.file_type}</span>
                                                <span style={{ color: 'var(--text-muted)' }}>{t.count}</span>
                                            </div>
                                            <div style={{ height: '6px', background: 'var(--glass)', borderRadius: '999px', overflow: 'hidden' }}>
                                                <div style={{
                                                    height: '100%',
                                                    width: `${(t.count / maxByType) * 100}%`,
                                                    background: 'var(--accent)',
                                                    borderRadius: '999px',
                                                    transition: 'width 0.4s ease',
                                                }} />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </>
                        )}

                        {/* Upload ultimi 30 giorni */}
                        {data.uploads_by_day.length > 0 && (
                            <>
                                <p style={{ fontWeight: 600, marginBottom: '0.75rem' }}>Upload ultimi 30 giorni</p>
                                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '3px', height: '80px', marginBottom: '0.4rem' }}>
                                    {data.uploads_by_day.map((d) => (
                                        <div
                                            key={d.day}
                                            title={`${d.day}: ${d.count} upload`}
                                            style={{
                                                flex: 1,
                                                background: 'var(--accent)',
                                                borderRadius: '2px 2px 0 0',
                                                height: `${Math.max(4, (d.count / maxByDay) * 100)}%`,
                                                opacity: 0.8,
                                                cursor: 'default',
                                                transition: 'opacity 0.15s',
                                            }}
                                            onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.opacity = '1'; }}
                                            onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.opacity = '0.8'; }}
                                        />
                                    ))}
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                    <span>{data.uploads_by_day[0]?.day}</span>
                                    <span>{data.uploads_by_day[data.uploads_by_day.length - 1]?.day}</span>
                                </div>
                            </>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

export default StatsWidget;
