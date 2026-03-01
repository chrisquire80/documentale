import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import type { AppNotification } from '../components/NotificationBell';

const BASE_WS_URL = (import.meta.env.VITE_API_URL as string)?.replace('http', 'ws') || 'ws://localhost:8000';

export type UserRole = 'admin' | 'power_user' | 'reader';

interface CurrentUser {
    id: string;
    email: string;
    role: UserRole;
    department?: string;
    is_active: boolean;
}

interface AuthContextType {
    isAuthenticated: boolean;
    currentUser: CurrentUser | null;
    login: (token: string, refreshToken: string) => void;
    logout: () => void;
    isLoading: boolean;
    notifications: AppNotification[];
    markAllRead: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [toasts, setToasts] = useState<{ id: number, message: string }[]>([]);
    const [notifications, setNotifications] = useState<AppNotification[]>([]);

    const markAllRead = useCallback(() => {
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    }, []);

    const addToast = (msg: string) => {
        const id = Date.now();
        setToasts(prev => [...prev, { id, message: msg }]);
        setTimeout(() => {
            setToasts(prev => prev.filter(t => t.id !== id));
        }, 5000);
    };

    const addNotification = useCallback((type: string, message: string) => {
        const n: AppNotification = { id: Date.now(), type, message, read: false, timestamp: new Date() };
        setNotifications(prev => [...prev.slice(-49), n]);
    }, []);

    useEffect(() => {
        let ws: WebSocket | null = null;
        const token = localStorage.getItem('token');

        if (isAuthenticated && token) {
            ws = new WebSocket(`${BASE_WS_URL}/ws/${token}`);

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const supportedTypes = ['NEW_COMMENT', 'NOTIFICATION', 'UPLOAD_COMPLETE', 'DOC_MODIFIED'];

                    if (supportedTypes.includes(data.type)) {
                        addToast(data.message);
                        addNotification(data.type, data.message);
                    }
                } catch (e) {
                    console.error("WS Parse error", e);
                }
            };

            ws.onerror = (e) => console.error("WS Error", e);
        }

        return () => {
            if (ws) ws.close();
        };
    }, [isAuthenticated, addNotification]);

    const fetchMe = async () => {
        try {
            const res = await api.get<CurrentUser>('/auth/me');
            setCurrentUser(res.data);
            setIsAuthenticated(true);
        } catch {
            setCurrentUser(null);
            setIsAuthenticated(false);
            localStorage.removeItem('token');
            localStorage.removeItem('refreshToken');
        }
    };

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            fetchMe().finally(() => setIsLoading(false));
        } else {
            setIsAuthenticated(false);
            setIsLoading(false);
        }
    }, []);

    const login = (token: string, refreshToken: string) => {
        localStorage.setItem('token', token);
        localStorage.setItem('refreshToken', refreshToken);
        setIsAuthenticated(true);
        fetchMe();
    };

    const logout = () => {
        // Invalida il token server-side nella blacklist Redis — fire-and-forget
        api.post('/auth/logout').catch(() => { });
        localStorage.removeItem('token');
        localStorage.removeItem('refreshToken');
        setIsAuthenticated(false);
        setCurrentUser(null);
        setNotifications([]);
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, currentUser, login, logout, isLoading, notifications, markAllRead }}>
            {children}

            {/* Toast Container */}
            <div style={{
                position: 'fixed', bottom: '20px', right: '20px', zIndex: 9999,
                display: 'flex', flexDirection: 'column', gap: '10px'
            }}>
                {toasts.map(t => (
                    <div key={t.id} style={{
                        background: 'var(--accent)', color: 'var(--bg-dark)', padding: '12px 20px',
                        borderRadius: '0.5rem', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.5)',
                        borderLeft: '4px solid white', fontWeight: 600, fontSize: '0.9rem',
                        transition: 'all 0.3s ease-out'
                    }}>
                        {t.message}
                    </div>
                ))}
            </div>
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
