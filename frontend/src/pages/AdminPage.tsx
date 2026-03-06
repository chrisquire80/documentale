import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Shield, Users, Activity, UserPlus, Power, CheckCircle, XCircle, Download, BarChart3 } from 'lucide-react';
import { useAuth } from '../store/AuthContext';
import Pagination from '../components/Pagination';
import UserCreationModal from '../components/UserCreationModal';
import AdminStatsTab from '../components/AdminStatsTab';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface AdminUser {
    id: string;
    email: string;
    role: string;
    department?: string;
    is_active: boolean;
    created_at: string;
}

interface AuditLogEntry {
    id: string;
    timestamp: string;
    action: string;
    user_id?: string;
    details?: string;
}

const AdminPage: React.FC = () => {
    const { currentUser } = useAuth();
    const queryClient = useQueryClient();
    const [activeTab, setActiveTab] = useState<'users' | 'audit' | 'stats'>('users');
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

    // Paginazione Users
    const [userPage, setUserPage] = useState(1);
    const usersPerPage = 10;

    // Paginazione Audit
    const [auditPage, setAuditPage] = useState(1);
    const auditPerPage = 15;

    // Esporta Audit Log State
    const [isExporting, setIsExporting] = useState(false);

    // Fetch Utenti
    const { data: usersData, isLoading: isLoadingUsers } = useQuery({
        queryKey: ['admin-users', userPage],
        queryFn: async () => {
            const token = localStorage.getItem('token');
            const offset = (userPage - 1) * usersPerPage;
            const res = await axios.get(`${BASE_URL}/admin/users?skip=${offset}&limit=${usersPerPage}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return res.data;
        },
        enabled: activeTab === 'users'
    });

    // Fetch Audit Log
    const { data: auditData, isLoading: isLoadingAudit } = useQuery({
        queryKey: ['admin-audit', auditPage],
        queryFn: async () => {
            const token = localStorage.getItem('token');
            const offset = (auditPage - 1) * auditPerPage;
            const res = await axios.get(`${BASE_URL}/admin/audit?skip=${offset}&limit=${auditPerPage}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return res.data;
        },
        enabled: activeTab === 'audit'
    });

    // Mutazione modifica utente (Status)
    const toggleUserStatusMutation = useMutation({
        mutationFn: async ({ userId, isActive }: { userId: string, isActive: boolean }) => {
            const token = localStorage.getItem('token');
            return axios.patch(`${BASE_URL}/admin/users/${userId}`, { is_active: isActive }, {
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] })
    });

    const handleExportAuditCSV = async () => {
        setIsExporting(true);
        try {
            const token = localStorage.getItem('token');
            const response = await axios.get(`${BASE_URL}/admin/audit/export`, {
                headers: { Authorization: `Bearer ${token}` },
                responseType: 'blob', // Impostiamo responseType per gestire il raw data (CSV Stream)
            });

            // Crea pseudo URL e forza il download programmativo
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'audit_logs.csv');
            document.body.appendChild(link);
            link.click();
            link.remove();
        } catch (error) {
            console.error("Errore esportazione CSV", error);
            alert("Errore durante l'esportazione CSV.");
        } finally {
            setIsExporting(false);
        }
    };

    // @ts-expect-error - Ignore type error if typing is strict on UserRole
    if (currentUser?.role !== 'ADMIN') {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <Shield size={64} style={{ color: 'var(--error)', margin: '0 auto 1rem' }} />
                <h2>Accesso Negato</h2>
                <p style={{ color: 'var(--text-muted)' }}>Non hai i permessi per visualizzare questa pagina.</p>
            </div>
        );
    }

    return (
        <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
            <nav className="nav">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Shield className="primary" />
                    <h1 style={{ fontSize: '1.25rem', fontWeight: 700 }}>Pannello Amministratore</h1>
                </div>
                <button
                    className="btn"
                    style={{ width: 'auto', background: 'transparent', border: '1px solid var(--glass)' }}
                    onClick={() => window.location.href = '/'}
                >
                    Torna alla Dashboard
                </button>
            </nav>

            <main style={{ flex: 1, padding: '2rem', maxWidth: '1200px', margin: '0 auto', width: '100%' }}>
                {/* Tabs Navegation */}
                <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '1px solid var(--glass)' }}>
                    <button
                        onClick={() => setActiveTab('users')}
                        style={{
                            background: 'none', border: 'none', padding: '1rem', cursor: 'pointer',
                            color: activeTab === 'users' ? 'var(--accent)' : 'var(--text-muted)',
                            borderBottom: activeTab === 'users' ? '2px solid var(--accent)' : '2px solid transparent',
                            display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem'
                        }}
                    >
                        <Users size={18} /> Utenti
                    </button>
                    <button
                        onClick={() => setActiveTab('audit')}
                        style={{
                            background: 'none', border: 'none', padding: '1rem', cursor: 'pointer',
                            color: activeTab === 'audit' ? 'var(--accent)' : 'var(--text-muted)',
                            borderBottom: activeTab === 'audit' ? '2px solid var(--accent)' : '2px solid transparent',
                            display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem'
                        }}
                    >
                        <Activity size={18} /> Audit Log
                    </button>
                    <button
                        onClick={() => setActiveTab('stats')}
                        style={{
                            background: 'none', border: 'none', padding: '1rem', cursor: 'pointer',
                            color: activeTab === 'stats' ? 'var(--accent)' : 'var(--text-muted)',
                            borderBottom: activeTab === 'stats' ? '2px solid var(--accent)' : '2px solid transparent',
                            display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem'
                        }}
                    >
                        <BarChart3 size={18} /> Statistiche
                    </button>
                </div>

                {/* Content: Utenti */}
                {activeTab === 'users' && (
                    <div className="auth-card" style={{ maxWidth: '100%', margin: 0 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Users size={20} /> Gestione Utenti
                            </h2>
                            <button
                                className="btn"
                                style={{ width: 'auto', padding: '0.5rem 1rem' }}
                                onClick={() => setIsCreateModalOpen(true)}
                            >
                                <UserPlus size={16} style={{ marginRight: '0.5rem' }} /> Nuovo Utente
                            </button>
                        </div>

                        {isLoadingUsers ? (
                            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>Caricamento utenti in corso...</div>
                        ) : (
                            <>
                                <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                        <thead>
                                            <tr style={{ borderBottom: '1px solid var(--glass)' }}>
                                                <th style={{ padding: '1rem 0', color: 'var(--text-muted)', fontWeight: 500 }}>Email</th>
                                                <th style={{ padding: '1rem 0', color: 'var(--text-muted)', fontWeight: 500 }}>Ruolo</th>
                                                <th style={{ padding: '1rem 0', color: 'var(--text-muted)', fontWeight: 500 }}>Dipartimento</th>
                                                <th style={{ padding: '1rem 0', color: 'var(--text-muted)', fontWeight: 500 }}>Stato</th>
                                                <th style={{ padding: '1rem 0', color: 'var(--text-muted)', fontWeight: 500, textAlign: 'right' }}>Azioni</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {usersData?.items?.map((user: AdminUser) => (
                                                <tr key={user.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                    <td style={{ padding: '1rem 0' }}>{user.email}</td>
                                                    <td style={{ padding: '1rem 0' }}>
                                                        <span style={{
                                                            padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.75rem',
                                                            background: user.role === 'ADMIN' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(56, 189, 248, 0.2)',
                                                            color: user.role === 'ADMIN' ? '#fca5a5' : '#7dd3fc'
                                                        }}>
                                                            {user.role}
                                                        </span>
                                                    </td>
                                                    <td style={{ padding: '1rem 0', color: 'var(--text-muted)' }}>{user.department || '-'}</td>
                                                    <td style={{ padding: '1rem 0' }}>
                                                        {user.is_active ?
                                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#4ade80', fontSize: '0.875rem' }}><CheckCircle size={14} /> Attivo</span> :
                                                            <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem', color: '#f87171', fontSize: '0.875rem' }}><XCircle size={14} /> Disabilitato</span>
                                                        }
                                                    </td>
                                                    <td style={{ padding: '1rem 0', textAlign: 'right' }}>
                                                        <button
                                                            onClick={() => toggleUserStatusMutation.mutate({ userId: user.id, isActive: !user.is_active })}
                                                            style={{
                                                                background: 'none', border: '1px solid var(--glass)', padding: '0.4rem', borderRadius: '6px',
                                                                color: user.is_active ? 'var(--error)' : '#4ade80', cursor: 'pointer'
                                                            }}
                                                            title={user.is_active ? "Disabilita Profilo" : "Attiva Profilo"}
                                                            disabled={user.id === currentUser.id} // Previeni auto-lock
                                                        >
                                                            <Power size={16} />
                                                        </button>
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                                {usersData?.total > usersPerPage && (
                                    <Pagination
                                        currentPage={userPage}
                                        totalPages={Math.ceil(usersData.total / usersPerPage)}
                                        total={usersData.total}
                                        onPageChange={setUserPage}
                                    />
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* Content: Audit Log */}
                {activeTab === 'audit' && (
                    <div className="auth-card" style={{ maxWidth: '100%', margin: 0 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                            <h2 style={{ fontSize: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <Activity size={20} /> Registri di Sistema
                            </h2>
                            <button
                                className="btn primary"
                                style={{ width: 'auto', padding: '0.5rem 1rem' }}
                                onClick={handleExportAuditCSV}
                                disabled={isExporting}
                            >
                                <Download size={16} style={{ marginRight: '0.5rem' }} />
                                {isExporting ? 'Esportazione...' : 'Esporta CSV'}
                            </button>
                        </div>

                        {isLoadingAudit ? (
                            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>Caricamento audit log...</div>
                        ) : (
                            <>
                                <div style={{ overflowX: 'auto' }}>
                                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
                                        <thead>
                                            <tr style={{ borderBottom: '1px solid var(--glass)' }}>
                                                <th style={{ padding: '0.75rem 0', color: 'var(--text-muted)', fontWeight: 500 }}>Data / Ora</th>
                                                <th style={{ padding: '0.75rem 0', color: 'var(--text-muted)', fontWeight: 500 }}>Azione</th>
                                                <th style={{ padding: '0.75rem 0', color: 'var(--text-muted)', fontWeight: 500 }}>Utente ID</th>
                                                <th style={{ padding: '0.75rem 0', color: 'var(--text-muted)', fontWeight: 500 }}>Dettagli</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {auditData?.items?.map((log: AuditLogEntry) => (
                                                <tr key={log.id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                                                    <td style={{ padding: '0.75rem 0', color: 'var(--text-muted)' }}>
                                                        {new Date(log.timestamp).toLocaleString('it-IT')}
                                                    </td>
                                                    <td style={{ padding: '0.75rem 0', fontWeight: 600 }}>{log.action}</td>
                                                    <td style={{ padding: '0.75rem 0', fontFamily: 'monospace', color: 'var(--text-light)' }}>
                                                        {log.user_id ? log.user_id.substring(0, 8) + '...' : 'Sistema'}
                                                    </td>
                                                    <td style={{ padding: '0.75rem 0', color: 'var(--text-muted)' }}>{log.details || '-'}</td>
                                                </tr>
                                            ))}
                                            {auditData?.items?.length === 0 && (
                                                <tr>
                                                    <td colSpan={4} style={{ padding: '2rem 0', textAlign: 'center', color: 'var(--text-muted)' }}>Nessun log trovato.</td>
                                                </tr>
                                            )}
                                        </tbody>
                                    </table>
                                </div>
                                {auditData?.total > auditPerPage && (
                                    <Pagination
                                        currentPage={auditPage}
                                        totalPages={Math.ceil(auditData.total / auditPerPage)}
                                        total={auditData.total}
                                        onPageChange={setAuditPage}
                                    />
                                )}
                            </>
                        )}
                    </div>
                )}

                {/* Content: Statistiche */}
                {activeTab === 'stats' && (
                    <AdminStatsTab />
                )}
            </main>

            {isCreateModalOpen && (
                <UserCreationModal
                    onClose={() => setIsCreateModalOpen(false)}
                    onSuccess={() => {
                        setIsCreateModalOpen(false);
                        queryClient.invalidateQueries({ queryKey: ['admin-users'] });
                    }}
                />
            )}
        </div>
    );
};

export default AdminPage;
