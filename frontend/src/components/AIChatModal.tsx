import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { X, Send, Bot, User, Loader2, FileText } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface ChatSource {
    document_id: string;
    title: string;
    snippet: string;
}

interface ChatMessage {
    role: 'user' | 'assistant';
    text: string;
    sources?: ChatSource[];
}

interface Props {
    docId?: string;
    docTitle?: string;
    onClose: () => void;
}

const AIChatModal: React.FC<Props> = ({ docId, docTitle, onClose }) => {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const send = async () => {
        const query = input.trim();
        if (!query || loading) return;

        setMessages(prev => [...prev, { role: 'user', text: query }]);
        setInput('');
        setLoading(true);

        try {
            const token = localStorage.getItem('token');
            const res = await axios.post(
                `${BASE_URL}/ai/chat`,
                { query, document_id: docId ?? null },
                { headers: { Authorization: `Bearer ${token}` } }
            );
            setMessages(prev => [
                ...prev,
                { role: 'assistant', text: res.data.answer, sources: res.data.sources ?? [] },
            ]);
        } catch (err: any) {
            const detail = err.response?.data?.detail ?? 'Errore di comunicazione con il server.';
            setMessages(prev => [
                ...prev,
                { role: 'assistant', text: `⚠️ ${detail}` },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const handleKey = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    };

    return (
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1000, padding: '1rem',
        }}>
            <div style={{
                background: 'var(--bg-card)', borderRadius: '1rem',
                width: '100%', maxWidth: '700px', height: '80vh',
                display: 'flex', flexDirection: 'column',
                border: '1px solid var(--border)', boxShadow: '0 25px 50px -12px rgba(0,0,0,0.6)',
            }}>
                {/* Header */}
                <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '1rem 1.5rem', borderBottom: '1px solid var(--border)',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <Bot size={22} style={{ color: 'var(--accent)' }} />
                        <div>
                            <div style={{ fontWeight: 700, fontSize: '1rem' }}>
                                AI Chat
                            </div>
                            {docTitle && (
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                    contesto: {docTitle}
                                </div>
                            )}
                            {!docTitle && (
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                    su tutti i tuoi documenti
                                </div>
                            )}
                        </div>
                    </div>
                    <button onClick={onClose} style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--text-muted)', padding: '4px',
                    }}>
                        <X size={20} />
                    </button>
                </div>

                {/* Messages */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '1rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {messages.length === 0 && (
                        <div style={{
                            textAlign: 'center', color: 'var(--text-muted)',
                            marginTop: '3rem', fontSize: '0.9rem',
                        }}>
                            <Bot size={40} style={{ margin: '0 auto 1rem', opacity: 0.4 }} />
                            <p>Fai una domanda sui tuoi documenti.</p>
                            {docTitle && <p style={{ marginTop: '0.25rem' }}>Cercherò in <strong>{docTitle}</strong>.</p>}
                        </div>
                    )}

                    {messages.map((msg, i) => (
                        <div key={i} style={{
                            display: 'flex', gap: '0.75rem',
                            flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                        }}>
                            <div style={{
                                width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                                background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-hover)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                                {msg.role === 'user'
                                    ? <User size={16} style={{ color: 'var(--bg-dark)' }} />
                                    : <Bot size={16} style={{ color: 'var(--accent)' }} />
                                }
                            </div>
                            <div style={{ maxWidth: '75%' }}>
                                <div style={{
                                    background: msg.role === 'user' ? 'var(--accent)' : 'var(--bg-hover)',
                                    color: msg.role === 'user' ? 'var(--bg-dark)' : 'var(--text-primary)',
                                    padding: '0.65rem 1rem', borderRadius: '0.75rem',
                                    fontSize: '0.9rem', lineHeight: 1.55, whiteSpace: 'pre-wrap',
                                }}>
                                    {msg.text}
                                </div>
                                {msg.sources && msg.sources.length > 0 && (
                                    <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                        {msg.sources.map(src => (
                                            <span key={src.document_id} style={{
                                                fontSize: '0.72rem', padding: '2px 8px',
                                                background: 'var(--bg-hover)', borderRadius: '1rem',
                                                color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px',
                                                border: '1px solid var(--border)',
                                            }}>
                                                <FileText size={10} />
                                                {src.title}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}

                    {loading && (
                        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
                            <div style={{
                                width: 32, height: 32, borderRadius: '50%',
                                background: 'var(--bg-hover)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                            }}>
                                <Bot size={16} style={{ color: 'var(--accent)' }} />
                            </div>
                            <Loader2 size={18} style={{ color: 'var(--text-muted)', animation: 'spin 1s linear infinite' }} />
                        </div>
                    )}
                    <div ref={bottomRef} />
                </div>

                {/* Input */}
                <div style={{
                    padding: '1rem 1.5rem', borderTop: '1px solid var(--border)',
                    display: 'flex', gap: '0.75rem', alignItems: 'flex-end',
                }}>
                    <textarea
                        value={input}
                        onChange={e => setInput(e.target.value)}
                        onKeyDown={handleKey}
                        placeholder="Scrivi una domanda… (Invio per inviare)"
                        rows={2}
                        style={{
                            flex: 1, resize: 'none',
                            background: 'var(--bg-hover)', border: '1px solid var(--border)',
                            borderRadius: '0.5rem', padding: '0.65rem 0.9rem',
                            color: 'var(--text-primary)', fontSize: '0.9rem',
                            outline: 'none', fontFamily: 'inherit',
                        }}
                    />
                    <button
                        onClick={send}
                        disabled={!input.trim() || loading}
                        style={{
                            background: input.trim() && !loading ? 'var(--accent)' : 'var(--bg-hover)',
                            border: 'none', borderRadius: '0.5rem', cursor: input.trim() && !loading ? 'pointer' : 'default',
                            padding: '0.65rem 1rem', color: input.trim() && !loading ? 'var(--bg-dark)' : 'var(--text-muted)',
                            display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600, fontSize: '0.85rem',
                            transition: 'all 0.2s',
                        }}
                    >
                        <Send size={16} />
                        Invia
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AIChatModal;
