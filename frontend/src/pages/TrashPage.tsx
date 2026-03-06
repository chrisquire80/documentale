import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { useAuth } from '../store/AuthContext';
import { Trash2, RotateCcw, FileText, AlertTriangle, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

interface TrashedDocument {
    id: string;
    title: string;
    deleted_at: string;
    owner_id: string;
}

const fetchTrash = async (token: string, page: number = 0) => {
    const res = await axios.get(`${import.meta.env.VITE_API_URL}/documents/trash?offset=${page * 20}`, {
        headers: { Authorization: `Bearer ${token}` }
    });
    return res.data;
};

const TrashPage: React.FC = () => {
    const { currentUser } = useAuth();
    const token = localStorage.getItem('token');
    const queryClient = useQueryClient();
    const [page, setPage] = useState(0);

    const { data: trashData, isLoading } = useQuery({
        queryKey: ['trash', page],
        queryFn: () => fetchTrash(token!, page),
        enabled: !!token,
    });

    const restoreMutation = useMutation({
        mutationFn: (docId: string) => axios.post(`${import.meta.env.VITE_API_URL}/documents/${docId}/restore`, {}, {
            headers: { Authorization: `Bearer ${token}` }
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['trash'] });
            queryClient.invalidateQueries({ queryKey: ['documents'] }); // refresh home
        }
    });

    const hardDeleteMutation = useMutation({
        mutationFn: (docId: string) => axios.delete(`${import.meta.env.VITE_API_URL}/documents/${docId}/hard`, {
            headers: { Authorization: `Bearer ${token}` }
        }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['trash'] });
        }
    });

    if (!token) {
        return <div className="p-8 text-center text-red-500">Accesso Negato</div>;
    }

    return (
        <div className="min-h-screen bg-[var(--bg-dark)]">
            <header className="p-4 border-b border-[var(--border)] bg-[var(--bg-card)] flex items-center">
                <Link to="/" className="flex items-center gap-2 text-[var(--accent)] hover:opacity-80 transition-opacity">
                    <ArrowLeft size={20} />
                    <span className="font-semibold">Torna alla Dashboard</span>
                </Link>
            </header>

            <main className="container mx-auto p-4 lg:p-8">
                <div className="flex items-center gap-3 mb-8">
                    <Trash2 className="w-8 h-8 text-[var(--error)]" />
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-red-400 to-red-600">
                        Cestino
                    </h1>
                </div>

                <div className="bg-[var(--bg-card)] rounded-xl border border-[var(--glass)] overflow-hidden">
                    <div className="p-4 bg-[rgba(255,255,255,0.02)] border-b border-[var(--glass)] flex items-center gap-2 text-[var(--text-muted)] text-sm">
                        <AlertTriangle className="w-4 h-4 text-orange-400" />
                        <span>I documenti in questa sezione verranno eliminati definitivamente dopo 30 giorni.</span>
                    </div>

                    {isLoading ? (
                        <div className="p-12 text-center text-[var(--text-muted)] animate-pulse">Caricamento cestino...</div>
                    ) : trashData?.items.length === 0 ? (
                        <div className="p-16 text-center flex flex-col items-center">
                            <div className="w-16 h-16 rounded-full bg-[rgba(255,255,255,0.02)] flex items-center justify-center mb-4 border border-[var(--glass)]">
                                <Trash2 className="w-8 h-8 text-[var(--text-muted)] opacity-50" />
                            </div>
                            <h3 className="text-xl font-medium text-[var(--text-main)] mb-1">Cestino vuoto</h3>
                            <p className="text-[var(--text-muted)]">Non ci sono documenti eliminati di recente.</p>
                        </div>
                    ) : (
                        <div className="divide-y divide-[var(--glass)]">
                            {trashData?.items.map((doc: TrashedDocument) => (
                                <div key={doc.id} className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-[rgba(255,255,255,0.01)] transition-colors">
                                    <div className="flex items-start gap-4">
                                        <div className="p-3 rounded-lg bg-[rgba(255,255,255,0.03)] text-[var(--text-muted)] mt-1 md:mt-0">
                                            <FileText className="w-5 h-5" />
                                        </div>
                                        <div>
                                            <h4 className="font-medium text-[var(--text-main)] text-lg mb-1">{doc.title}</h4>
                                            <div className="text-sm text-[var(--text-muted)] flex items-center gap-2">
                                                <span>Eliminato il: {new Date(doc.deleted_at).toLocaleDateString()} alle {new Date(doc.deleted_at).toLocaleTimeString()}</span>
                                                {((currentUser?.role as string) === 'ADMIN' && currentUser?.id !== doc.owner_id) && (
                                                    <span className="px-2 py-0.5 rounded text-xs bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                                        Altro Utente
                                                    </span>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-3 self-end md:self-auto">
                                        <button
                                            onClick={() => restoreMutation.mutate(doc.id)}
                                            disabled={restoreMutation.isPending}
                                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[var(--accent)] bg-opacity-10 text-[var(--accent)] hover:bg-opacity-20 transition-all border border-[var(--accent)] border-opacity-30 flex-1 md:flex-none justify-center"
                                        >
                                            <RotateCcw className="w-4 h-4" />
                                            <span>Ripristina</span>
                                        </button>

                                        <button
                                            onClick={() => {
                                                if (confirm('Questa azione è irreversibile. Eliminare definitivamente il documento?')) {
                                                    hardDeleteMutation.mutate(doc.id);
                                                }
                                            }}
                                            disabled={hardDeleteMutation.isPending}
                                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all border border-red-500/30 flex-1 md:flex-none justify-center"
                                        >
                                            <Trash2 className="w-4 h-4" />
                                            <span>Elimina</span>
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}

                    {/* Pagination */}
                    {trashData && trashData.total > 20 && (
                        <div className="p-4 border-t border-[var(--glass)] flex justify-between items-center">
                            <button
                                onClick={() => setPage(p => Math.max(0, p - 1))}
                                disabled={page === 0}
                                className="px-4 py-2 rounded-lg bg-[rgba(255,255,255,0.05)] text-[var(--text-main)] hover:bg-[rgba(255,255,255,0.1)] disabled:opacity-50 transition-colors"
                            >
                                Precedente
                            </button>
                            <span className="text-[var(--text-muted)] text-sm">
                                Pagina {page + 1}
                            </span>
                            <button
                                onClick={() => setPage(p => p + 1)}
                                disabled={(page + 1) * 20 >= trashData.total}
                                className="px-4 py-2 rounded-lg bg-[rgba(255,255,255,0.05)] text-[var(--text-main)] hover:bg-[rgba(255,255,255,0.1)] disabled:opacity-50 transition-colors"
                            >
                                Successiva
                            </button>
                        </div>
                    )}
                </div>
            </main>
        </div>
    );
};

export default TrashPage;
