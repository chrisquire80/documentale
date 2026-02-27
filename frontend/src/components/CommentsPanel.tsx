import React, { useState, useEffect, useRef } from 'react';
import { X, Send, User, MessageSquare } from 'lucide-react';
import api from '../services/api';

interface Comment {
    id: string;
    content: string;
    created_at: string;
    user: {
        id: string;
        email: string;
    };
}

interface CommentsPanelProps {
    docId: string;
    docTitle: string;
    onClose: () => void;
}

const CommentsPanel: React.FC<CommentsPanelProps> = ({ docId, docTitle, onClose }) => {
    const [comments, setComments] = useState<Comment[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [newComment, setNewComment] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    const fetchComments = async () => {
        try {
            setLoading(true);
            const response = await api.get(`/documents/${docId}/comments`);
            setComments(response.data);
            setError(null);
        } catch (err: any) {
            console.error('Failed to load comments:', err);
            setError(err.response?.data?.detail || 'Impossibile caricare i commenti.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchComments();
    }, [docId]);

    useEffect(() => {
        scrollToBottom();
    }, [comments]);

    const handlePostComment = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!newComment.trim()) return;

        setSubmitting(true);
        try {
            const response = await api.post(`/documents/${docId}/comments`, {
                content: newComment.trim()
            });
            // Add the new comment to the list
            setComments(prev => [...prev, response.data]);
            setNewComment('');
        } catch (err: any) {
            console.error('Failed to post comment:', err);
            alert(err.response?.data?.detail || 'Impossibile inviare il commento.');
        } finally {
            setSubmitting(false);
        }
    };

    // Format relative time (very basic Italian)
    const formatTime = (isoString: string) => {
        const date = new Date(isoString);
        return date.toLocaleDateString('it-IT', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
    };

    return (
        <div style={{
            position: 'fixed', top: 0, right: 0, bottom: 0, width: '400px', maxWidth: '100%',
            backgroundColor: 'var(--bg-card)', borderLeft: '1px solid var(--border)',
            boxShadow: '-4px 0 15px rgba(0,0,0,0.5)', zIndex: 1000,
            display: 'flex', flexDirection: 'column'
        }}>
            {/* Header */}
            <div style={{
                padding: '1.25rem', borderBottom: '1px solid var(--border)',
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                backgroundColor: 'var(--bg-dark)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <MessageSquare size={20} color="var(--accent)" />
                    <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-light)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '280px' }}>
                        {docTitle}
                    </h3>
                </div>
                <button
                    onClick={onClose}
                    style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                >
                    <X size={24} />
                </button>
            </div>

            {/* Comments List */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '1rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {loading ? (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '2rem' }}>Caricamento...</div>
                ) : error ? (
                    <div style={{ color: 'var(--error)', textAlign: 'center' }}>{error}</div>
                ) : comments.length === 0 ? (
                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', marginTop: '3rem' }}>
                        <MessageSquare size={48} style={{ opacity: 0.2, margin: '0 auto 1rem auto' }} />
                        Non ci sono ancora commenti.<br />Scrivi il primo!
                    </div>
                ) : (
                    comments.map(comment => (
                        <div key={comment.id} style={{
                            backgroundColor: 'var(--bg-dark)', padding: '0.875rem',
                            borderRadius: '0.5rem', border: '1px solid var(--border)'
                        }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--accent)', fontWeight: 600 }}>
                                    <User size={14} />
                                    {comment.user.email}
                                </div>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                    {formatTime(comment.created_at)}
                                </span>
                            </div>
                            <div style={{ color: 'var(--text-light)', fontSize: '0.95rem', lineHeight: 1.4, whiteSpace: 'pre-wrap' }}>
                                {comment.content}
                            </div>
                        </div>
                    ))
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input Form */}
            <div style={{ padding: '1rem', borderTop: '1px solid var(--border)', backgroundColor: 'var(--bg-dark)' }}>
                <form onSubmit={handlePostComment} style={{ display: 'flex', gap: '0.5rem' }}>
                    <textarea
                        value={newComment}
                        onChange={e => setNewComment(e.target.value)}
                        placeholder="Scrivi un commento..."
                        disabled={loading || submitting}
                        style={{
                            flex: 1, resize: 'none', height: '60px', padding: '0.75rem',
                            borderRadius: '0.5rem', border: '1px solid var(--border)',
                            backgroundColor: 'white', color: 'black', fontFamily: 'inherit'
                        }}
                        onKeyDown={e => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handlePostComment(e);
                            }
                        }}
                    />
                    <button
                        type="submit"
                        disabled={!newComment.trim() || submitting}
                        style={{
                            backgroundColor: newComment.trim() && !submitting ? 'var(--accent)' : 'var(--bg-card)',
                            color: newComment.trim() && !submitting ? 'var(--bg-dark)' : 'var(--text-muted)',
                            border: 'none', borderRadius: '0.5rem', padding: '0 1rem',
                            cursor: newComment.trim() && !submitting ? 'pointer' : 'not-allowed',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s'
                        }}
                    >
                        <Send size={20} />
                    </button>
                </form>
            </div>
        </div>
    );
};

export default CommentsPanel;
