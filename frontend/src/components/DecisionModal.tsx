import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import axios from 'axios';
import {
    X, Scale, ChevronRight, AlertTriangle, CheckCircle2, Lightbulb,
    TrendingUp, Calendar, Circle, Loader2, MessageSquare,
} from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

// ── Types ─────────────────────────────────────────────────────────────────────

interface TimelineItem {
    doc_id: string;
    title: string;
    date: string | null;
    key_point: string;
    stance: 'favorevole' | 'contrario' | 'neutro' | 'incerto';
}

interface DecisionResult {
    topic_summary: string;
    timeline: TimelineItem[];
    evolution: string;
    contradictions: string[];
    agreements: string[];
    decision_recommendation: string;
    confidence: number;
    reasoning: string;
}

interface Props {
    /** document_ids to compare directly (bulk mode) */
    documentIds?: string[];
    /** anchor doc id for auto-discovery mode */
    anchorDocId?: string;
    anchorDocTitle?: string;
    onClose: () => void;
}

// ── Stance config ─────────────────────────────────────────────────────────────

const STANCE: Record<string, { label: string; color: string; bg: string }> = {
    favorevole: { label: 'Favorevole', color: '#22c55e', bg: 'rgba(34,197,94,0.12)' },
    contrario:  { label: 'Contrario',  color: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
    neutro:     { label: 'Neutro',     color: '#94a3b8', bg: 'rgba(148,163,184,0.12)' },
    incerto:    { label: 'Incerto',    color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
};

// ── Main component ────────────────────────────────────────────────────────────

const DecisionModal: React.FC<Props> = ({ documentIds, anchorDocId, anchorDocTitle, onClose }) => {
    const [question, setQuestion] = useState('');
    const [started, setStarted] = useState(false);

    const isBulkMode = !!(documentIds && documentIds.length >= 2);
    const isAnchorMode = !!anchorDocId;

    const compareMutation = useMutation({
        mutationFn: async (): Promise<DecisionResult> => {
            const token = localStorage.getItem('token');
            const headers = { Authorization: `Bearer ${token}` };

            if (isBulkMode) {
                const res = await axios.post(
                    `${BASE_URL}/api/ai/compare`,
                    { document_ids: documentIds, question },
                    { headers }
                );
                return res.data;
            } else {
                const res = await axios.get(
                    `${BASE_URL}/api/ai/compare-anchor/${anchorDocId}`,
                    { params: { question: question || '' }, headers }
                );
                return res.data;
            }
        },
    });

    const handleStart = () => {
        setStarted(true);
        compareMutation.mutate();
    };

    const result = compareMutation.data;

    return (
        <div style={overlay}>
            <div style={container}>
                {/* ── Header ─────────────────────────────────────── */}
                <div style={headerStyle}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                        <Scale size={20} color="#818cf8" />
                        <h2 style={{ margin: 0, fontSize: 17, fontWeight: 700, color: '#f1f5f9' }}>
                            Analisi Decisionale
                        </h2>
                        {isAnchorMode && anchorDocTitle && (
                            <span style={{ fontSize: 12, color: '#64748b', marginLeft: 4 }}>
                                — partendo da «{anchorDocTitle}»
                            </span>
                        )}
                        {isBulkMode && (
                            <span style={{ fontSize: 12, color: '#64748b', marginLeft: 4 }}>
                                — {documentIds!.length} documenti selezionati
                            </span>
                        )}
                    </div>
                    <button onClick={onClose} style={closeBtn}>
                        <X size={18} />
                    </button>
                </div>

                {/* ── Phase 1: Question input ─────────────────────── */}
                {!started && (
                    <div style={{ padding: '28px 32px 32px' }}>
                        <p style={{ margin: '0 0 20px', fontSize: 14, color: '#94a3b8', lineHeight: 1.6 }}>
                            {isAnchorMode
                                ? 'Identificherò automaticamente i documenti correlati e li analizzerò in sequenza cronologica per produrre una raccomandazione decisionale.'
                                : 'Analizzerò i documenti selezionati in sequenza cronologica per evidenziare l\'evoluzione del tema e produrre una raccomandazione decisionale.'}
                        </p>

                        <label style={labelSt}>Domanda specifica (opzionale)</label>
                        <div style={{ position: 'relative', marginBottom: 24 }}>
                            <MessageSquare size={15} style={{
                                position: 'absolute', left: 12, top: '50%',
                                transform: 'translateY(-50%)', color: '#64748b',
                            }} />
                            <input
                                type="text"
                                placeholder="es. Dobbiamo procedere con il fornitore X? Come è cambiata la valutazione?"
                                value={question}
                                onChange={e => setQuestion(e.target.value)}
                                onKeyDown={e => e.key === 'Enter' && handleStart()}
                                style={{ ...inputSt, paddingLeft: 36 }}
                                autoFocus
                            />
                        </div>

                        <button onClick={handleStart} style={primaryBtn}>
                            <Scale size={16} />
                            Avvia Analisi
                            <ChevronRight size={16} />
                        </button>
                    </div>
                )}

                {/* ── Phase 2: Loading ────────────────────────────── */}
                {started && compareMutation.isPending && (
                    <div style={{ padding: '60px 32px', textAlign: 'center' }}>
                        <Loader2 size={40} color="#818cf8" style={{ animation: 'spin 1s linear infinite' }} />
                        <p style={{ marginTop: 20, color: '#94a3b8', fontSize: 14 }}>
                            Analisi cronologica in corso...
                        </p>
                        <p style={{ margin: '4px 0 0', color: '#64748b', fontSize: 12 }}>
                            Gemini sta confrontando i documenti e costruendo la raccomandazione
                        </p>
                    </div>
                )}

                {/* ── Phase 3: Error ──────────────────────────────── */}
                {compareMutation.isError && (
                    <div style={{ padding: '32px', textAlign: 'center' }}>
                        <AlertTriangle size={36} color="#ef4444" />
                        <p style={{ marginTop: 12, color: '#ef4444', fontSize: 14 }}>
                            {(compareMutation.error as any)?.response?.data?.detail ?? 'Errore durante l\'analisi.'}
                        </p>
                        <button
                            onClick={() => { setStarted(false); compareMutation.reset(); }}
                            style={{ ...primaryBtn, marginTop: 16 }}
                        >
                            Riprova
                        </button>
                    </div>
                )}

                {/* ── Phase 4: Results ────────────────────────────── */}
                {result && (
                    <div style={{ overflowY: 'auto', maxHeight: 'calc(90vh - 80px)', padding: '0 32px 32px' }}>

                        {/* Topic summary */}
                        <div style={summaryCard}>
                            <TrendingUp size={16} color="#818cf8" />
                            <p style={{ margin: 0, fontSize: 14, color: '#cbd5e1', lineHeight: 1.6 }}>
                                {result.topic_summary}
                            </p>
                        </div>

                        {/* Timeline */}
                        <SectionTitle icon={<Calendar size={14} />} title="Cronologia documenti" />
                        <div style={{ marginBottom: 24, position: 'relative' }}>
                            {/* vertical line */}
                            <div style={{
                                position: 'absolute', left: 15, top: 8, bottom: 8,
                                width: 2, background: 'rgba(129,140,248,0.2)',
                            }} />
                            {result.timeline.map((item, i) => {
                                const s = STANCE[item.stance] ?? STANCE.neutro;
                                return (
                                    <div key={item.doc_id} style={{ display: 'flex', gap: 14, marginBottom: 16, position: 'relative' }}>
                                        {/* dot */}
                                        <div style={{
                                            width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                                            background: s.bg, border: `2px solid ${s.color}`,
                                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                                            fontSize: 11, fontWeight: 700, color: s.color, zIndex: 1,
                                        }}>
                                            {i + 1}
                                        </div>
                                        <div style={{
                                            background: 'rgba(255,255,255,0.03)',
                                            border: '1px solid rgba(255,255,255,0.07)',
                                            borderRadius: 10, padding: '10px 14px', flex: 1,
                                        }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                                                <span style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0' }}>
                                                    {item.title}
                                                </span>
                                                {item.date && (
                                                    <span style={{ fontSize: 11, color: '#64748b' }}>{item.date}</span>
                                                )}
                                                <span style={{
                                                    fontSize: 10, fontWeight: 700, padding: '1px 7px',
                                                    borderRadius: 20, background: s.bg, color: s.color,
                                                    border: `1px solid ${s.color}44`,
                                                }}>
                                                    {s.label}
                                                </span>
                                            </div>
                                            <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
                                                {item.key_point}
                                            </p>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>

                        {/* Evolution */}
                        {result.evolution && (
                            <>
                                <SectionTitle icon={<TrendingUp size={14} />} title="Evoluzione della discussione" />
                                <p style={{ ...prose, marginBottom: 24 }}>{result.evolution}</p>
                            </>
                        )}

                        {/* Contradictions + Agreements */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
                            {result.contradictions.length > 0 && (
                                <div style={pillSection}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                                        <AlertTriangle size={13} color="#ef4444" />
                                        <span style={{ fontSize: 12, fontWeight: 700, color: '#ef4444', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                                            Contraddizioni
                                        </span>
                                    </div>
                                    {result.contradictions.map((c, i) => (
                                        <Pill key={i} text={c} color="#ef4444" />
                                    ))}
                                </div>
                            )}
                            {result.agreements.length > 0 && (
                                <div style={pillSection}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                                        <CheckCircle2 size={13} color="#22c55e" />
                                        <span style={{ fontSize: 12, fontWeight: 700, color: '#22c55e', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                                            Punti di accordo
                                        </span>
                                    </div>
                                    {result.agreements.map((a, i) => (
                                        <Pill key={i} text={a} color="#22c55e" />
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Decision recommendation */}
                        <div style={decisionCard}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                <Lightbulb size={18} color="#fbbf24" />
                                <span style={{ fontSize: 14, fontWeight: 700, color: '#fbbf24', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                                    Raccomandazione
                                </span>
                                <ConfidenceBadge value={result.confidence} />
                            </div>
                            <p style={{ margin: '0 0 16px', fontSize: 15, color: '#f1f5f9', lineHeight: 1.7, fontWeight: 500 }}>
                                {result.decision_recommendation}
                            </p>
                            {result.reasoning && (
                                <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', lineHeight: 1.6, fontStyle: 'italic', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: 12 }}>
                                    {result.reasoning}
                                </p>
                            )}
                        </div>

                    </div>
                )}

                {/* CSS for spin */}
                <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
            </div>
        </div>
    );
};

// ── Sub-components ─────────────────────────────────────────────────────────────

const SectionTitle: React.FC<{ icon: React.ReactNode; title: string }> = ({ icon, title }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 12 }}>
        <span style={{ color: '#64748b' }}>{icon}</span>
        <span style={{ fontSize: 12, fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {title}
        </span>
    </div>
);

const Pill: React.FC<{ text: string; color: string }> = ({ text, color }) => (
    <div style={{
        background: `${color}10`, border: `1px solid ${color}30`,
        borderRadius: 6, padding: '5px 10px', marginBottom: 6,
        fontSize: 12, color: '#cbd5e1', lineHeight: 1.4,
    }}>
        {text}
    </div>
);

const ConfidenceBadge: React.FC<{ value: number }> = ({ value }) => {
    const pct = Math.round(value * 100);
    const color = pct >= 75 ? '#22c55e' : pct >= 45 ? '#f59e0b' : '#ef4444';
    return (
        <span style={{
            marginLeft: 'auto', fontSize: 12, fontWeight: 700,
            background: `${color}20`, color, borderRadius: 20,
            padding: '2px 10px', border: `1px solid ${color}44`,
        }}>
            Confidenza {pct}%
        </span>
    );
};

// ── Styles ─────────────────────────────────────────────────────────────────────

const overlay: React.CSSProperties = {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.75)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1200,
    backdropFilter: 'blur(4px)',
};

const container: React.CSSProperties = {
    background: '#0f172a',
    border: '1px solid rgba(129,140,248,0.25)',
    borderRadius: 16,
    width: 740,
    maxWidth: '95vw',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 25px 80px rgba(0,0,0,0.6), 0 0 0 1px rgba(129,140,248,0.1)',
    overflow: 'hidden',
};

const headerStyle: React.CSSProperties = {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '20px 28px',
    borderBottom: '1px solid rgba(255,255,255,0.06)',
    background: 'rgba(129,140,248,0.05)',
    flexShrink: 0,
};

const closeBtn: React.CSSProperties = {
    background: 'none', border: 'none', cursor: 'pointer',
    color: '#64748b', padding: 4, borderRadius: 6,
};

const labelSt: React.CSSProperties = {
    display: 'block', fontSize: 12, fontWeight: 600,
    color: '#64748b', marginBottom: 8,
    textTransform: 'uppercase', letterSpacing: '0.04em',
};

const inputSt: React.CSSProperties = {
    width: '100%', padding: '10px 14px', borderRadius: 10,
    border: '1px solid rgba(255,255,255,0.1)',
    background: 'rgba(255,255,255,0.04)',
    color: '#f1f5f9', fontSize: 14, outline: 'none',
    boxSizing: 'border-box',
};

const primaryBtn: React.CSSProperties = {
    display: 'flex', alignItems: 'center', gap: 8,
    padding: '10px 22px', borderRadius: 10,
    border: 'none', background: 'linear-gradient(135deg, #6366f1, #818cf8)',
    color: '#fff', fontSize: 14, fontWeight: 700,
    cursor: 'pointer', boxShadow: '0 4px 15px rgba(99,102,241,0.3)',
};

const summaryCard: React.CSSProperties = {
    display: 'flex', gap: 12, alignItems: 'flex-start',
    background: 'rgba(129,140,248,0.07)',
    border: '1px solid rgba(129,140,248,0.2)',
    borderRadius: 10, padding: '14px 16px',
    marginTop: 24, marginBottom: 24,
};

const pillSection: React.CSSProperties = {
    background: 'rgba(255,255,255,0.02)',
    border: '1px solid rgba(255,255,255,0.06)',
    borderRadius: 10, padding: '14px 16px',
};

const decisionCard: React.CSSProperties = {
    background: 'rgba(251,191,36,0.06)',
    border: '1px solid rgba(251,191,36,0.25)',
    borderRadius: 12, padding: '20px 22px',
    marginTop: 8,
};

const prose: React.CSSProperties = {
    fontSize: 13, color: '#94a3b8', lineHeight: 1.7, margin: 0,
};

export default DecisionModal;
