import React, { useState } from 'react';
import { Bell, X, CheckCheck } from 'lucide-react';

export interface AppNotification {
    id: number;
    type: string;
    message: string;
    read: boolean;
    timestamp: Date;
}

interface Props {
    notifications: AppNotification[];
    onMarkAllRead: () => void;
}

const NotificationBell: React.FC<Props> = ({ notifications, onMarkAllRead }) => {
    const [open, setOpen] = useState(false);
    const unread = notifications.filter(n => !n.read).length;

    const typeIcon: Record<string, string> = {
        UPLOAD_COMPLETE: '✅',
        DOC_MODIFIED: '📝',
        NEW_COMMENT: '💬',
        NOTIFICATION: '🔔',
    };

    return (
        <div style={{ position: 'relative' }}>
            <button
                onClick={() => setOpen(v => !v)}
                style={{
                    background: 'none', border: 'none', cursor: 'pointer',
                    color: 'var(--text-muted)', padding: '6px',
                    borderRadius: '0.5rem', position: 'relative',
                    display: 'flex', alignItems: 'center',
                }}
                title="Notifiche"
            >
                <Bell size={20} />
                {unread > 0 && (
                    <span style={{
                        position: 'absolute', top: 0, right: 0,
                        background: '#ef4444', color: 'white',
                        borderRadius: '9999px', fontSize: '0.65rem',
                        fontWeight: 700, minWidth: '16px', height: '16px',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        padding: '0 3px',
                    }}>
                        {unread > 9 ? '9+' : unread}
                    </span>
                )}
            </button>

            {open && (
                <>
                    {/* Backdrop */}
                    <div
                        style={{ position: 'fixed', inset: 0, zIndex: 998 }}
                        onClick={() => setOpen(false)}
                    />
                    {/* Dropdown */}
                    <div style={{
                        position: 'absolute', top: '110%', right: 0, zIndex: 999,
                        background: 'var(--bg-card)', border: '1px solid var(--border)',
                        borderRadius: '0.75rem', width: '340px', maxHeight: '420px',
                        boxShadow: '0 20px 40px -8px rgba(0,0,0,0.5)',
                        display: 'flex', flexDirection: 'column', overflow: 'hidden',
                    }}>
                        {/* Header */}
                        <div style={{
                            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                            padding: '0.85rem 1rem', borderBottom: '1px solid var(--border)',
                        }}>
                            <span style={{ fontWeight: 700, fontSize: '0.9rem' }}>
                                Notifiche {unread > 0 && <span style={{ color: '#ef4444' }}>({unread})</span>}
                            </span>
                            <div style={{ display: 'flex', gap: '6px' }}>
                                {unread > 0 && (
                                    <button
                                        onClick={() => { onMarkAllRead(); }}
                                        style={{
                                            background: 'none', border: 'none', cursor: 'pointer',
                                            color: 'var(--accent)', fontSize: '0.75rem',
                                            display: 'flex', alignItems: 'center', gap: '4px',
                                        }}
                                        title="Segna tutte come lette"
                                    >
                                        <CheckCheck size={14} /> Lette
                                    </button>
                                )}
                                <button onClick={() => setOpen(false)} style={{
                                    background: 'none', border: 'none', cursor: 'pointer',
                                    color: 'var(--text-muted)', padding: '2px',
                                }}>
                                    <X size={14} />
                                </button>
                            </div>
                        </div>

                        {/* List */}
                        <div style={{ overflowY: 'auto', flex: 1 }}>
                            {notifications.length === 0 ? (
                                <div style={{
                                    padding: '2rem', textAlign: 'center',
                                    color: 'var(--text-muted)', fontSize: '0.85rem',
                                }}>
                                    <Bell size={28} style={{ margin: '0 auto 0.5rem', opacity: 0.3 }} />
                                    Nessuna notifica
                                </div>
                            ) : (
                                [...notifications].reverse().map(n => (
                                    <div key={n.id} style={{
                                        padding: '0.75rem 1rem',
                                        borderBottom: '1px solid var(--border)',
                                        background: n.read ? 'transparent' : 'rgba(var(--accent-rgb, 99,102,241), 0.06)',
                                        display: 'flex', gap: '0.6rem', alignItems: 'flex-start',
                                    }}>
                                        <span style={{ fontSize: '1rem', lineHeight: 1, marginTop: '2px' }}>
                                            {typeIcon[n.type] ?? '🔔'}
                                        </span>
                                        <div style={{ flex: 1 }}>
                                            <div style={{ fontSize: '0.82rem', lineHeight: 1.4 }}>{n.message}</div>
                                            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                                                {n.timestamp.toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' })}
                                            </div>
                                        </div>
                                        {!n.read && (
                                            <div style={{
                                                width: 8, height: 8, borderRadius: '50%',
                                                background: 'var(--accent)', flexShrink: 0, marginTop: 4,
                                            }} />
                                        )}
                                    </div>
                                ))
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    );
};

export default NotificationBell;
