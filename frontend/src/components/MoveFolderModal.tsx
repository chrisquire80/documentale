import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { X, FolderInput } from 'lucide-react';
import type { FolderNode } from './FolderTree';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface Props {
    docId: string;
    docTitle: string;
    currentFolderId: string | null;
    onClose: () => void;
    onSuccess: () => void;
}

function flattenFolders(nodes: FolderNode[], depth = 0): { id: string; label: string }[] {
    const result: { id: string; label: string }[] = [];
    for (const n of nodes) {
        result.push({ id: n.id, label: '  '.repeat(depth) + n.name });
        if (n.children.length) result.push(...flattenFolders(n.children, depth + 1));
    }
    return result;
}

const MoveFolderModal: React.FC<Props> = ({ docId, docTitle, currentFolderId, onClose, onSuccess }) => {
    const [selectedId, setSelectedId] = useState<string>(currentFolderId ?? '__root__');
    const queryClient = useQueryClient();

    const { data: folders = [] } = useQuery<FolderNode[]>({
        queryKey: ['folders'],
        queryFn: async () => {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${BASE_URL}/folders/`, { headers: { Authorization: `Bearer ${token}` } });
            return res.data;
        }
    });

    const moveMutation = useMutation({
        mutationFn: async () => {
            const token = localStorage.getItem('token');
            if (selectedId === '__root__') {
                // Remove from current folder (if any)
                if (currentFolderId) {
                    return axios.delete(`${BASE_URL}/folders/${currentFolderId}/documents/${docId}`, {
                        headers: { Authorization: `Bearer ${token}` }
                    });
                }
            } else {
                return axios.patch(`${BASE_URL}/folders/${selectedId}/documents/${docId}`, {}, {
                    headers: { Authorization: `Bearer ${token}` }
                });
            }
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            onSuccess();
            onClose();
        }
    });

    const options = flattenFolders(folders);

    return (
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            zIndex: 1100, padding: '1rem',
        }}>
            <div style={{
                background: 'var(--bg-card)', borderRadius: '0.75rem',
                width: '100%', maxWidth: '380px', padding: '1.5rem',
                border: '1px solid var(--border)', boxShadow: '0 20px 40px -8px rgba(0,0,0,0.5)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', fontWeight: 700 }}>
                        <FolderInput size={18} style={{ color: 'var(--accent)' }} />
                        Sposta in cartella
                    </div>
                    <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
                        <X size={18} />
                    </button>
                </div>

                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '1rem' }}>
                    Documento: <strong style={{ color: 'var(--text-primary)' }}>{docTitle}</strong>
                </div>

                <select
                    value={selectedId}
                    onChange={e => setSelectedId(e.target.value)}
                    style={{
                        width: '100%', background: 'var(--bg-hover)', border: '1px solid var(--border)',
                        borderRadius: '0.5rem', padding: '0.6rem 0.8rem',
                        color: 'var(--text-primary)', fontSize: '0.88rem',
                        outline: 'none', marginBottom: '1.25rem', fontFamily: 'inherit',
                    }}
                >
                    <option value="__root__">— Nessuna cartella (root) —</option>
                    {options.map(o => (
                        <option key={o.id} value={o.id}>{o.label}</option>
                    ))}
                </select>

                <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
                    <button onClick={onClose} style={{
                        background: 'var(--bg-hover)', border: '1px solid var(--border)',
                        borderRadius: '0.5rem', padding: '0.5rem 1rem',
                        cursor: 'pointer', color: 'var(--text-muted)', fontSize: '0.85rem',
                    }}>
                        Annulla
                    </button>
                    <button
                        onClick={() => moveMutation.mutate()}
                        disabled={moveMutation.isPending || selectedId === (currentFolderId ?? '__root__')}
                        style={{
                            background: 'var(--accent)', border: 'none', borderRadius: '0.5rem',
                            padding: '0.5rem 1.2rem', cursor: 'pointer',
                            color: 'var(--bg-dark)', fontWeight: 700, fontSize: '0.85rem',
                        }}
                    >
                        {moveMutation.isPending ? 'Spostamento…' : 'Sposta'}
                    </button>
                </div>
            </div>
        </div>
    );
};

export default MoveFolderModal;
