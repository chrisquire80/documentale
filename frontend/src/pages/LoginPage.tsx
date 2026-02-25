import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../store/AuthContext';

const LoginPage: React.FC = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const { login } = useAuth();
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const response = await api.post('/auth/login', { email, password });
            login(response.data.access_token);
            navigate('/');
        } catch (err) {
            setError('Credenziali non valide');
        }
    };

    return (
        <div className="container">
            <div className="auth-card">
                <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>DMS Local-First</h2>
                <form onSubmit={handleSubmit}>
                    <input
                        className="input"
                        type="email"
                        placeholder="Email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                    />
                    <input
                        className="input"
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        required
                    />
                    {error && <p style={{ color: 'var(--error)', fontSize: '0.875rem' }}>{error}</p>}
                    <button className="btn" type="submit">Accedi</button>
                </form>
            </div>
        </div>
    );
};

export default LoginPage;
