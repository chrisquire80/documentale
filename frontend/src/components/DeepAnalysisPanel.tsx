import React from 'react';
import { Sparkles, Check, X, ChevronRight, FileText, Layout, Glasses, Calendar, User, Tag, Info } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import './DeepAnalysisPanel.css';

interface TagData {
    id: string;
    name: string;
}

interface VersionTag {
    is_ai_generated: boolean;
    status: 'suggested' | 'validated';
    page_number?: number;
    tag: TagData;
}

interface DocumentVersion {
    id: string;
    version_num: number;
    ai_status: string;
    ai_summary?: string;
    ai_entities?: any;
    ai_reasoning?: string;
    tags: VersionTag[];
}

interface DeepAnalysisPanelProps {
    doc: {
        id: string;
        title: string;
        category?: string;
        department?: string;
        versions: DocumentVersion[];
    };
    onApproveTag: (versionId: string, tagId: string) => void;
    onRejectTag: (versionId: string, tagId: string) => void;
    onJumpToPage?: (page: number) => void;
}

const DeepAnalysisPanel: React.FC<DeepAnalysisPanelProps> = ({ doc, onApproveTag, onRejectTag, onJumpToPage }) => {
    const currentVersion = doc.versions?.[0]; // Assumiamo la versione più recente sia la prima
    const entities = currentVersion?.ai_entities || {};

    if (!currentVersion) return <div className="deep-analysis-empty">Nessuna analisi disponibile.</div>;

    return (
        <div className="deep-analysis-container">
            {/* Header: Category & Type */}
            <div className="deep-analysis-header">
                <div className="category-badge">
                    <Layout size={16} />
                    <span>{doc.category || 'Generale'}</span>
                </div>
                <div className="ai-status-badge">
                    <Sparkles size={14} />
                    <span>Deep Analysis Ready</span>
                </div>
            </div>

            {/* Executive Summary */}
            <section className="analysis-section">
                <h3>
                    <FileText size={18} />
                    Riassunto Esecutivo
                </h3>
                <p className="summary-text">{currentVersion.ai_summary || "Analisi del contenuto in corso..."}</p>
            </section>

            {/* Glass-Box Reasoning */}
            {currentVersion.ai_reasoning && (
                <section className="analysis-section reasoning-box">
                    <h3>
                        <Glasses size={18} />
                        Reasoning "Glass-Box"
                    </h3>
                    <div className="reasoning-content">
                        <ReactMarkdown>{currentVersion.ai_reasoning}</ReactMarkdown>
                    </div>
                    <div className="compliance-note">
                        <Info size={12} />
                        <span>Trasparenza algoritmica ai sensi del regolamento AI Act.</span>
                    </div>
                </section>
            )}

            {/* Extracted Entities */}
            <section className="analysis-section">
                <h3>
                    <ChevronRight size={18} />
                    Entità Estratte
                </h3>
                <div className="entities-grid">
                    {entities.dates?.length > 0 && (
                        <div className="entity-group">
                            <label><Calendar size={14} /> Date</label>
                            <div className="entity-pills">
                                {entities.dates.map((d: string, i: number) => <span key={i} className="entity-pill">{d}</span>)}
                            </div>
                        </div>
                    )}
                    {entities.signatories?.length > 0 && (
                        <div className="entity-group">
                            <label><User size={14} /> Firmatari</label>
                            <div className="entity-pills">
                                {entities.signatories.map((s: string, i: number) => <span key={i} className="entity-pill">{s}</span>)}
                            </div>
                        </div>
                    )}
                    {entities.amounts?.length > 0 && (
                        <div className="entity-group">
                            <label><Tag size={14} /> Importi</label>
                            <div className="entity-pills">
                                {entities.amounts.map((a: string, i: number) => <span key={i} className="entity-pill amount">{a}</span>)}
                            </div>
                        </div>
                    )}
                </div>

                {entities.clauses?.length > 0 && (
                    <div className="clauses-list">
                        <label>Clausole Critiche</label>
                        <ul>
                            {entities.clauses.map((c: string, i: number) => <li key={i}>{c}</li>)}
                        </ul>
                    </div>
                )}
            </section>

            {/* Tags with Validation */}
            <section className="analysis-section">
                <h3>
                    <Tag size={18} />
                    Auto-Tagging & Validazione
                </h3>
                <div className="validation-tags-list">
                    {currentVersion.tags.map((vt) => (
                        <div key={vt.tag.id} className={`validation-tag ${vt.status}`}>
                            <div className="tag-info" onClick={() => vt.page_number && onJumpToPage?.(vt.page_number)}>
                                <span className="tag-name">{vt.tag.name}</span>
                                {vt.page_number && (
                                    <span className="page-citation" title="Vai alla pagina">
                                        p. {vt.page_number}
                                    </span>
                                )}
                            </div>

                            {vt.status === 'suggested' && (
                                <div className="tag-actions">
                                    <button
                                        className="approve-btn"
                                        onClick={() => onApproveTag(currentVersion.id, vt.tag.id)}
                                        title="Approva"
                                    >
                                        <Check size={14} />
                                    </button>
                                    <button
                                        className="reject-btn"
                                        onClick={() => onRejectTag(currentVersion.id, vt.tag.id)}
                                        title="Rifiuta"
                                    >
                                        <X size={14} />
                                    </button>
                                </div>
                            )}
                            {vt.status === 'validated' && (
                                <div className="validated-check">
                                    <Check size={12} />
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </section>
        </div>
    );
};

export default DeepAnalysisPanel;
