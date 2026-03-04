import React, { useState, useRef, useEffect, useCallback, useImperativeHandle, forwardRef } from 'react';
import { Send, X, Bot, Loader2, Minimize2, Maximize2, ExternalLink, Download, Layout } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import axios from 'axios';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const api = axios.create({
    baseURL: BASE_URL,
});

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

interface ChatAssistantProps {
    isOpen: boolean;
    onClose: () => void;
    documentId?: string;
    documentTitle?: string;
    /** Se true, la chat è ancorata come pannello laterale */
    docked?: boolean;
    onToggleDock?: () => void;
    /** Callback per aprire un documento dalla citazione, con highlight e pagina */
    onOpenDocument?: (docId: string, docTitle: string, page?: number, highlightText?: string) => void;
}

export interface ChatAssistantHandle {
    sendMessage: (text: string) => void;
}

const ChatAssistantBase: React.ForwardRefRenderFunction<ChatAssistantHandle, ChatAssistantProps> = ({
    isOpen,
    onClose,
    documentId,
    documentTitle,
    docked = false,
    onToggleDock,
    onOpenDocument,
}, ref) => {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = useCallback(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, []);

    useEffect(() => { scrollToBottom(); }, [messages, scrollToBottom]);

    // Messaggio di benvenuto
    useEffect(() => {
        if (isOpen && messages.length === 0) {
            setMessages([{
                id: 'welcome',
                role: 'assistant',
                content: documentId
                    ? `Ciao! Sono il tuo assistente AI. Chiedimi qualsiasi cosa riguardo al documento **${documentTitle || 'corrente'}**.`
                    : 'Ciao! Sono il tuo assistente aziendale RAG. Chiedimi qualsiasi cosa sui documenti archiviati e ti risponderò citando le fonti pertinenti.',
            }]);
        }
    }, [isOpen, documentId, documentTitle, messages.length]);

    // Suggerimenti contestuali
    useEffect(() => {
        if (!isOpen) return;
        const token = localStorage.getItem('token');
        api.post('/ai/suggestions', { document_id: documentId, document_title: documentTitle }, {
            headers: { Authorization: `Bearer ${token}` }
        })
            .then(r => setSuggestions(r.data.suggestions || []))
            .catch(() => setSuggestions([]));
    }, [isOpen, documentId, documentTitle]);

    const sendMessage = useCallback(async (text: string) => {
        if (!text.trim() || isLoading) return;
        const userMessage: Message = { id: Date.now().toString(), role: 'user', content: text.trim() };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setSuggestions([]);
        setIsLoading(true);

        try {
            const token = localStorage.getItem('token');
            const response = await api.post('/ai/chat', {
                query: userMessage.content,
                document_id: documentId
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.data.answer,
                sources: response.data.sources,
                reasoning_steps: response.data.reasoning_steps,
            }]);
        } catch (error: any) {
            const detail = error.response?.data?.detail || error.message || 'Errore di connessione';
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: `⚠️ ${detail}`,
            }]);
        } finally {
            setIsLoading(false);
        }
    }, [isLoading, documentId]);

    useImperativeHandle(ref, () => ({
        sendMessage: (text: string) => {
            sendMessage(text);
        }
    }), [sendMessage]);

    const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); sendMessage(input); };

    const exportChat = useCallback(() => {
        const lines: string[] = [
            `# Conversazione Assistente Gemini RAG`,
            documentTitle ? `**Documento:** ${documentTitle}` : '',
            `**Data:** ${new Date().toLocaleString('it-IT')}`,
            '',
            '---',
            '',
        ];
        messages.forEach(msg => {
            if (msg.id === 'welcome') return;
            const speaker = msg.role === 'user' ? '👤 **Utente**' : '🤖 **Gemini**';
            lines.push(`### ${speaker}`);
            lines.push('');
            lines.push(msg.content);
            if (msg.sources?.length) {
                lines.push('');
                lines.push('> **Fonti:**');
                msg.sources.forEach(s => {
                    const pageInfo = s.page_number ? ` (pag. ${s.page_number})` : '';
                    lines.push(`> - ${s.title}${pageInfo}`);
                });
            }
            lines.push('');
            lines.push('---');
            lines.push('');
        });
        const blob = new Blob([lines.join('\n')], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `conversazione-gemini-${Date.now()}.md`;
        a.click();
        URL.revokeObjectURL(url);
    }, [messages, documentTitle]);

    if (!isOpen) return null;

    const windowClass = docked
        ? 'chat-panel-docked'
        : `chat-window${isExpanded ? ' expanded' : ''}`;

    return (
        <div className={windowClass}>
            <div className="chat-header">
                <div className="chat-header-left">
                    <Bot size={18} />
                    <div>
                        <h3 className="chat-header-title">Assistente Gemini RAG</h3>
                        {documentTitle && <p className="chat-header-subtitle">{documentTitle}</p>}
                    </div>
                </div>
                <div className="chat-header-actions">
                    <button onClick={exportChat} title="Esporta chat" className="chat-icon-btn">
                        <Download size={16} />
                    </button>
                    {!docked && (
                        <button onClick={() => setIsExpanded(!isExpanded)} title={isExpanded ? "Riduci" : "Espandi"} className="chat-icon-btn">
                            {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                        </button>
                    )}
                    {onToggleDock && (
                        <button onClick={onToggleDock} title={docked ? "Sgancia" : "Ancora"} className="chat-icon-btn">
                            <Layout size={16} />
                        </button>
                    )}
                    <button onClick={onClose} title="Chiudi" className="chat-icon-btn">
                        <X size={16} />
                    </button>
                </div>
            </div>

            <div className="chat-messages">
                {messages.map(msg => (
                    <div key={msg.id} className={`chat-msg-row ${msg.role}`}>
                        <div className={`chat-bubble ${msg.role}`}>
                                    {msg.reasoning_steps && msg.reasoning_steps.length > 0 && (
                                        <details className="chat-reasoning">
                                            <summary className="chat-reasoning-summary">\ud83d\udd0d Come ho trovato questa risposta</summary>
                                            <ol className="chat-reasoning-steps">
                                                {msg.reasoning_steps.map((step, i) => (<li key={i}>{step}</li>))}
                                            </ol>
                                        </details>
                                    )}
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                            {msg.sources && msg.sources.length > 0 && (
                                <div className="chat-sources">
                                    <p className="chat-sources-label">Fonti:</p>
                                    <div className="chat-sources-list">
                                        {msg.sources.map((src, idx) => (
                                            <div key={idx} className="chat-source-item">
                                                <span className="chat-source-title">{src.title}</span>
                                                {onOpenDocument && (
                                                    <button
                                                        onClick={() => onOpenDocument(
                                                            src.document_id,
                                                            src.title,
                                                            src.page_number,
                                                            src.snippet
                                                        )}
                                                        className="chat-source-link"
                                                        title={src.page_number ? `Apri pag. ${src.page_number}` : 'Apri documento'}
                                                    >
                                                        <ExternalLink size={10} />
                                                        {src.page_number && <span style={{ fontSize: '0.68rem', marginLeft: '2px' }}>pag.{src.page_number}</span>}
                                                    </button>
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
                        <span>Ricerca in corso...</span>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-footer">
                {suggestions.length > 0 && messages.length < 3 && (
                    <div className="chat-suggestions">
                        {suggestions.map((s, i) => (
                            <button key={i} className="chat-suggestion-chip" onClick={() => sendMessage(s)}>
                                {s}
                            </button>
                        ))}
                    </div>
                )}
                <form onSubmit={handleSubmit} className="chat-input-container">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Chiedi all'AI..."
                        disabled={isLoading}
                    />
                    <button type="submit" disabled={!input.trim() || isLoading} className="chat-send-btn">
                        <Send size={16} />
                    </button>
                </form>
            </div>
        </div>
    );
};

export const ChatAssistant = forwardRef(ChatAssistantBase);
