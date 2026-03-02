import React, { useState, useRef, useEffect } from 'react';
import { Send, X, Bot, User, Loader2, Minimize2, Maximize2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';

interface ChatSource {
    document_id: string;
    title: string;
    snippet: string;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: ChatSource[];
}

interface ChatAssistantProps {
    isOpen: boolean;
    onClose: () => void;
    documentId?: string; // Se fornito, contestualizza la chat a questo documento
    documentTitle?: string;
}

export function ChatAssistant({ isOpen, onClose, documentId, documentTitle }: ChatAssistantProps) {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    // Auto-scroll all'ultimo messaggio
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };
    useEffect(() => { scrollToBottom(); }, [messages]);

    // Messaggio di benvenuto contestualizzato
    useEffect(() => {
        if (isOpen && messages.length === 0) {
            setMessages([
                {
                    id: 'welcome',
                    role: 'assistant',
                    content: documentId
                        ? `Ciao! Sono il tuo assistente AI. Chiedimi qualsiasi cosa riguardo al documento **${documentTitle || 'corrente'}**.`
                        : 'Ciao! Sono il tuo assistente aziendale RAG. Chiedimi qualsiasi cosa sui documenti archiviati e ti risponderò citando le fonti pertinenti.'
                }
            ]);
        }
    }, [isOpen, documentId, documentTitle, messages.length]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: Message = { id: Date.now().toString(), role: 'user', content: input.trim() };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        try {
            const response = await fetch('http://localhost:8000/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                },
                body: JSON.stringify({
                    query: userMessage.content,
                    document_id: documentId
                })
            });

            if (!response.ok) throw new Error('Errore durante la comunicazione con l\'intelligenza artificiale');

            const data = await response.json();

            const aiMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: data.answer,
                sources: data.sources
            };

            setMessages(prev => [...prev, aiMessage]);
        } catch (error) {
            setMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: 'Mi dispiace, si è verificato un errore di connessione con i server AI.'
            }]);
        } finally {
            setIsLoading(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className={`fixed bottom-0 right-0 z-50 bg-white shadow-2xl border-l border-t border-gray-200 transition-all duration-300 ease-in-out flex flex-col
      ${isExpanded ? 'w-full md:w-[600px] h-full md:h-[80vh]' : 'w-full md:w-[400px] h-[550px]'}
      md:rounded-tl-2xl md:right-6 md:bottom-6
    `}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-gray-100 bg-gradient-to-r from-blue-600 to-indigo-700 text-white md:rounded-tl-2xl">
                <div className="flex items-center gap-2">
                    <Bot className="w-5 h-5 text-blue-200" />
                    <div>
                        <h3 className="font-semibold text-sm">Assistente Gemini RAG</h3>
                        {documentTitle && <p className="text-xs text-blue-200 truncate max-w-[200px]">{documentTitle}</p>}
                    </div>
                </div>
                <div className="flex items-center gap-1">
                    <button onClick={() => setIsExpanded(!isExpanded)} className="p-1.5 hover:bg-white/20 rounded-md transition-colors hidden md:block" title={isExpanded ? "Riduci" : "Espandi"}>
                        {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                    </button>
                    <button onClick={onClose} className="p-1.5 hover:bg-white/20 rounded-md transition-colors" title="Chiudi">
                        <X className="w-5 h-5" />
                    </button>
                </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
                {messages.map((msg) => (
                    <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} gap-2`}>
                            {/* Avatar */}
                            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${msg.role === 'user' ? 'bg-indigo-100' : 'bg-blue-100'}`}>
                                {msg.role === 'user' ? <User className="w-4 h-4 text-indigo-600" /> : <Bot className="w-4 h-4 text-blue-600" />}
                            </div>

                            {/* Bubble */}
                            <div className={`px-4 py-3 rounded-2xl ${msg.role === 'user' ? 'bg-indigo-600 text-white rounded-tr-none' : 'bg-white text-gray-800 border border-gray-100 rounded-tl-none shadow-sm'}`}>
                                <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-a:text-blue-600">
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                </div>

                                {/* Sources */}
                                {msg.sources && msg.sources.length > 0 && (
                                    <div className="mt-3 pt-3 border-t border-gray-100">
                                        <p className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wider">Fonti citate:</p>
                                        <div className="flex flex-col gap-2">
                                            {msg.sources.map((src, idx) => (
                                                <div key={idx} className="bg-gray-50 p-2 rounded border border-gray-100 flex items-start gap-2 group cursor-help relative">
                                                    <span className="bg-blue-100 text-blue-700 text-[10px] uppercase px-1.5 py-0.5 rounded font-bold mt-0.5">REF</span>
                                                    <span className="text-xs text-gray-600 truncate">{src.title}</span>

                                                    {/* Tooltip for snippet on hover */}
                                                    <div className="opacity-0 invisible group-hover:opacity-100 group-hover:visible absolute z-10 bottom-full left-0 mb-2 w-64 p-2 bg-gray-900 text-white text-xs rounded shadow-lg transition-all duration-200 pointer-events-none">
                                                        <p className="line-clamp-4">{src.snippet}</p>
                                                        <div className="absolute top-full left-4 -mt-1 w-2 h-2 bg-gray-900 rotate-45"></div>
                                                    </div>
                                                </div>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                ))}
                {isLoading && (
                    <div className="flex items-center gap-2 text-gray-500 text-sm mt-4 pl-10">
                        <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
                        Gemini sta analizzando i documenti...
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 bg-white border-t border-gray-100">
                <form onSubmit={handleSubmit} className="flex items-center gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Chiedi qualcosa sui documenti..."
                        className="flex-1 bg-gray-50 border border-gray-200 rounded-full px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        disabled={!input.trim() || isLoading}
                        className="p-2.5 bg-blue-600 text-white rounded-full hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        <Send className="w-5 h-5 ml-0.5" />
                    </button>
                </form>
            </div>
        </div>
    );
}
