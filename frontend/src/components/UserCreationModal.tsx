import React, { useState } from 'react';
import { X, UserPlus, Mail, Lock, Shield, Building } from 'lucide-react';
import axios from 'axios';
import './UserCreationModal.css';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface Props {
    onClose: () => void;
    onSuccess: () => void;
}

const UserCreationModal: React.FC<Props> = ({ onClose, onSuccess }) => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('READER');
    const [department, setDepartment] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError(null);

        try {
            const token = localStorage.getItem('token');
            await axios.post(`${BASE_URL}/api/admin/users`, {
                email,
                password,
                role,
                department: department || null
            }, {
                headers: { Authorization: `Bearer ${token}` }
            });

            onSuccess();
        } catch (err: unknown) {
            let detail = 'Errore nella creazione dell\'utente.';
            if (axios.isAxiosError(err)) {
                detail = err.response?.data?.detail || detail;
            }
            setError(detail);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="auth-card modal-content" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h2 className="modal-title">
                        <UserPlus size={20} className="primary" /> Nuovo Utente
                    </h2>
                    <button onClick={onClose} className="icon-btn" title="Chiudi modale"><X size={20} /></button>
                </div>

                <form onSubmit={handleSubmit} className="modal-form">
                    {error && <div className="error-message">{error}</div>}

                    <div className="input-group">
                        <label><Mail size={16} /> Email</label>
                        <input
                            type="email"
                            className="input"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            required
                            placeholder="utente@esempio.it"
                        />
                    </div>

                    <div className="input-group">
                        <label><Lock size={16} /> Password</label>
                        <input
                            type="password"
                            className="input"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                            placeholder="••••••••"
                        />
                    </div>

                    <div className="input-group">
                        <label><Shield size={16} /> Ruolo</label>
                        <select
                            className="input"
                            value={role}
                            onChange={e => setRole(e.target.value)}
                            title="Seleziona ruolo utente"
                        >
                            <option value="READER">Lettore (READER)</option>
                            <option value="POWER_USER">Power User (POWER_USER)</option>
                            <option value="ADMIN">Amministratore (ADMIN)</option>
                        </select>
                    </div>

                    <div className="input-group">
                        <label><Building size={16} /> Dipartimento (Opzionale)</label>
                        <input
                            type="text"
                            className="input"
                            value={department}
                            onChange={e => setDepartment(e.target.value)}
                            placeholder="es. Amministrazione, IT..."
                        />
                    </div>

                    <button type="submit" className="btn primary modal-submit" disabled={loading}>
                        {loading ? 'Creazione...' : 'Crea Utente'}
                    </button>
                </form>
            </div>
        </div>
    );
};

export default UserCreationModal;
