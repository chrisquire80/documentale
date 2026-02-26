import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

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
    login: (token: string) => void;
    logout: () => void;
    isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);

    const fetchMe = async () => {
        try {
            const res = await api.get<CurrentUser>('/auth/me');
            setCurrentUser(res.data);
        } catch {
            setCurrentUser(null);
        }
    };

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            setIsAuthenticated(true);
            fetchMe().finally(() => setIsLoading(false));
        } else {
            setIsLoading(false);
        }
    }, []);

    const login = (token: string) => {
        localStorage.setItem('token', token);
        setIsAuthenticated(true);
        fetchMe();
    };

    const logout = () => {
        // Invalida il token server-side nella blacklist Redis — fire-and-forget
        api.post('/auth/logout').catch(() => {});
        localStorage.removeItem('token');
        setIsAuthenticated(false);
        setCurrentUser(null);
    };

    return (
        <AuthContext.Provider value={{ isAuthenticated, currentUser, login, logout, isLoading }}>
            {children}
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
