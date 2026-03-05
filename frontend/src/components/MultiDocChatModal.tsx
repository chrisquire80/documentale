import React, { useRef } from 'react';
import { X, Bot } from 'lucide-react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, Download } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const api = axios.create({ baseURL: BASE_URL });

interface MultiDocChatModalProps {
    isOpen: boolean;
    onClose: () => void;
    documentIds: string[];
    documentTitles?: string[];
}

interface ChatSource {
    document_id: string;
    title: string;
    snippet: string;
    page_number?: number;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: ChatSource[];
    reasoning_steps?: string[];
}

const MultiDocChatModal: React.FC<MultiDocChatModalProps> = ({
    isOpen,
    onClose,
    documentIds,
    documentTitles = [],
}) => {
    const [messages, setMessages] = React.useState<Message[]>([]);
    const [input, setInput] = React.useState('');
    const [isLoading, setIsLoading] = React.useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    React.useEffect(() => {
        if (isOpen && messages.length === 0) {
            const docList = documentTitles.length
                ? documentTitles.map(t => `**${t}**`).join(', ')
                : `${documentIds.length} documenti selezionati`;
            setMessages([{
                id: 'welcome',
                role: 'assistant',
                content: `Ciao! Sono in modalità **Chat di Gruppo**.\n\nSto analizzando ${docList}.\n\nChiedimi qualsiasi cosa e confronterò le informazioni tra tutti i documenti selezionati.`,
            }]);
        }
        if (!isOpen) {
            setMessages([]);
        }
    }, [isOpen]);

    React.useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async (text: string) => {
        if (!text.trim() || isLoading) return;
        const userMsg: Message = { id: Date.now().toString(), role: 'user', content: text.trim() };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setIsLoading(true);

        try {
            const token = localStorage.getItem('token');
            const res = await api.post('/ai/chat', {
                query: userMsg.content,
                document_ids: documentIds,
            }, { headers: { Authorization: `Bearer ${token}` } });

            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: res.data.answer,
                sources: res.data.sources,
                reasoning_steps: res.data.reasoning_steps,
            }]);
        } catch (err: unknown) {
            let detail = 'Errore di connessione';
            if (axios.isAxiosError(err)) {
                detail = err.response?.data?.detail || detail;
            }
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `⚠️ ${detail}`,
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    const exportChat = () => {
        const lines = [
            '# Chat di Gruppo — Gemini RAG',
            `**Documenti:** ${documentTitles.join(', ') || documentIds.join(', ')}`,
            `**Data:** ${new Date().toLocaleString('it-IT')}`,
            '',
            '---',
            '',
        ];
        messages.forEach(msg => {
            if (msg.id === 'welcome') return;
            const who = msg.role === 'user' ? '👤 **Utente**' : '🤖 **Gemini**';
            lines.push(`### ${who}`, '', msg.content, '', '---', '');
        });
        const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-di-gruppo-${Date.now()}.md`;
        a.click();
        URL.revokeObjectURL(url);
    };

    if (!isOpen) return null;

    return (
        <div className="modal-overlay chat-modal-overlay" onClick={onClose}>
            <div
                className="modal-content multi-doc-chat-modal"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="multi-doc-chat-header">
                    <div className="multi-doc-chat-header-left">
                        <Bot size={18} />
                        <div>
                            <h3 className="multi-doc-chat-title">Chat di Gruppo</h3>
                            <p className="multi-doc-chat-subtitle">
                                {documentIds.length} documenti selezionati
                                {documentTitles.length > 0 && ` · ${documentTitles.slice(0, 2).join(', ')}${documentTitles.length > 2 ? ` +${documentTitles.length - 2}` : ''}`}
                            </p>
                        </div>
                    </div>
                    <div className="multi-doc-chat-header-actions">
                        <button onClick={exportChat} className="chat-icon-btn" title="Esporta chat">
                            <Download size={16} />
                        </button>
                        <button onClick={onClose} className="chat-icon-btn" title="Chiudi">
                            <X size={16} />
                        </button>
                    </div>
                </div>

                {/* Document pills */}
                {documentTitles.length > 0 && (
                    <div className="multi-doc-chat-pills">
                        {documentTitles.map((title, i) => (
                            <span key={i} className="multi-doc-chat-pill">{title}</span>
                        ))}
                    </div>
                )}

                {/* Messages */}
                <div className="multi-doc-chat-messages">
                    {messages.map((msg: Message) => (
                        <div key={msg.id} className={`chat-msg-row ${msg.role}`}>
                            <div className={`chat-bubble ${msg.role}`}>
                                {msg.reasoning_steps && msg.reasoning_steps.length > 0 && (
                                    <details className="chat-reasoning">
                                        <summary className="chat-reasoning-summary">🔍 Come ho trovato questa risposta</summary>
                                        <ol className="chat-reasoning-steps">
                                            {msg.reasoning_steps.map((step: string, i: number) => (
                                                <li key={i}>{step}</li>
                                            ))}
                                        </ol>
                                    </details>
                                )}
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                                {msg.sources && msg.sources.length > 0 && (
                                    <div className="chat-sources">
                                        <p className="chat-sources-label">Fonti:</p>
                                        <div className="chat-sources-list">
                                            {msg.sources.map((src: ChatSource, idx: number) => (
                                                <div key={idx} className="chat-source-item">
                                                    <span className="chat-source-title">{src.title}</span>
                                                    {src.page_number && (
                                                        <span className="chat-source-page">pag.{src.page_number}</span>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    {isLoading && (
                        <div className="chat-loading">
                            <Loader2 size={16} className="animate-spin" />
                            <span>Analisi in corso...</span>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="multi-doc-chat-footer">
                    <form
                        onSubmit={e => { e.preventDefault(); sendMessage(input); }}
                        className="chat-input-container"
                    >
                        <input
                            type="text"
                            value={input}
                            onChange={e => setInput(e.target.value)}
                            placeholder="Chiedi qualcosa a tutti i documenti selezionati..."
                            disabled={isLoading}
                        />
                        <button type="submit" disabled={!input.trim() || isLoading} className="chat-send-btn" title="Invia messaggio">
                            <Send size={16} />
                        </button>
                    </form>
                </div>
            </div>
        </div>
    );
};

export default MultiDocChatModal;
