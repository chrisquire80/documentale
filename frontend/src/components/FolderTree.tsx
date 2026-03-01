import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Folder, FolderOpen, FolderPlus, Pencil, Trash2, ChevronRight, ChevronDown, Home } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

export interface FolderNode {
    id: string;
    name: string;
    parent_id: string | null;
    created_at: string;
    children: FolderNode[];
}

interface Props {
    selectedFolderId: string | null;
    onSelectFolder: (id: string | null) => void;
}

const FolderItem: React.FC<{
    node: FolderNode;
    depth: number;
    selectedFolderId: string | null;
    onSelectFolder: (id: string | null) => void;
    onRefresh: () => void;
}> = ({ node, depth, selectedFolderId, onSelectFolder, onRefresh }) => {
    const [expanded, setExpanded] = useState(true);
    const [editing, setEditing] = useState(false);
    const [editName, setEditName] = useState(node.name);
    const queryClient = useQueryClient();

    const renameMutation = useMutation({
        mutationFn: async (name: string) => {
            const token = localStorage.getItem('token');
            return axios.patch(`${BASE_URL}/folders/${node.id}`, { name }, {
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => { onRefresh(); setEditing(false); }
    });

    const deleteMutation = useMutation({
        mutationFn: async () => {
            const token = localStorage.getItem('token');
            return axios.delete(`${BASE_URL}/folders/${node.id}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
        },
        onSuccess: () => {
            if (selectedFolderId === node.id) onSelectFolder(null);
            onRefresh();
        }
    });

    const isSelected = selectedFolderId === node.id;
    const hasChildren = node.children.length > 0;

    return (
        <div>
            <div
                style={{
                    display: 'flex', alignItems: 'center', gap: '4px',
                    padding: `5px 6px 5px ${8 + depth * 16}px`,
                    borderRadius: '0.4rem', cursor: 'pointer',
                    background: isSelected ? 'var(--accent)' : 'transparent',
                    color: isSelected ? 'var(--bg-dark)' : 'var(--text-primary)',
                    userSelect: 'none',
                }}
                onClick={() => onSelectFolder(node.id)}
            >
                {/* Expand/collapse toggle */}
                <span
                    onClick={e => { e.stopPropagation(); setExpanded(v => !v); }}
                    style={{ width: 14, flexShrink: 0, opacity: hasChildren ? 1 : 0 }}
                >
                    {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                </span>

                {isSelected
                    ? <FolderOpen size={14} style={{ flexShrink: 0 }} />
                    : <Folder size={14} style={{ flexShrink: 0, opacity: 0.7 }} />
                }

                {editing ? (
                    <input
                        autoFocus
                        value={editName}
                        onChange={e => setEditName(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === 'Enter') renameMutation.mutate(editName.trim());
                            if (e.key === 'Escape') { setEditing(false); setEditName(node.name); }
                        }}
                        onClick={e => e.stopPropagation()}
                        style={{
                            flex: 1, background: 'var(--bg-card)', border: '1px solid var(--accent)',
                            borderRadius: '3px', padding: '1px 5px', fontSize: '0.82rem',
                            color: 'var(--text-primary)', outline: 'none',
                        }}
                    />
                ) : (
                    <span style={{ flex: 1, fontSize: '0.83rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {node.name}
                    </span>
                )}

                {/* Actions — visible on hover */}
                {!editing && (
                    <div
                        className="folder-actions"
                        style={{ display: 'flex', gap: '2px', flexShrink: 0 }}
                        onClick={e => e.stopPropagation()}
                    >
                        <button
                            onClick={() => { setEditing(true); setEditName(node.name); }}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', opacity: 0.6, color: 'inherit' }}
                            title="Rinomina"
                        >
                            <Pencil size={11} />
                        </button>
                        <button
                            onClick={() => {
                                if (confirm(`Eliminare "${node.name}"? I documenti contenuti resteranno nella root.`))
                                    deleteMutation.mutate();
                            }}
                            style={{ background: 'none', border: 'none', cursor: 'pointer', padding: '2px', opacity: 0.6, color: isSelected ? 'inherit' : 'var(--error)' }}
                            title="Elimina cartella"
                        >
                            <Trash2 size={11} />
                        </button>
                    </div>
                )}
            </div>

            {expanded && hasChildren && (
                <div>
                    {node.children.map(child => (
                        <FolderItem
                            key={child.id}
                            node={child}
                            depth={depth + 1}
                            selectedFolderId={selectedFolderId}
                            onSelectFolder={onSelectFolder}
                            onRefresh={onRefresh}
                        />
                    ))}
                </div>
            )}
        </div>
    );
};


const FolderTree: React.FC<Props> = ({ selectedFolderId, onSelectFolder }) => {
    const [newFolderName, setNewFolderName] = useState('');
    const [showInput, setShowInput] = useState(false);
    const queryClient = useQueryClient();

    const { data: folders = [], refetch } = useQuery<FolderNode[]>({
        queryKey: ['folders'],
        queryFn: async () => {
            const token = localStorage.getItem('token');
            const res = await axios.get(`${BASE_URL}/folders/`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            return res.data;
        }
    });

    const createMutation = useMutation({
        mutationFn: async (name: string) => {
            const token = localStorage.getItem('token');
            return axios.post(`${BASE_URL}/folders/`, {
                name,
                parent_id: selectedFolderId ?? null
            }, { headers: { Authorization: `Bearer ${token}` } });
        },
        onSuccess: () => {
            refetch();
            setNewFolderName('');
            setShowInput(false);
        }
    });

    const handleCreate = () => {
        const name = newFolderName.trim();
        if (name) createMutation.mutate(name);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {/* Root / tutti i documenti */}
            <div
                style={{
                    display: 'flex', alignItems: 'center', gap: '6px',
                    padding: '5px 6px', borderRadius: '0.4rem', cursor: 'pointer',
                    background: selectedFolderId === null ? 'var(--accent)' : 'transparent',
                    color: selectedFolderId === null ? 'var(--bg-dark)' : 'var(--text-muted)',
                    fontSize: '0.83rem', fontWeight: 600,
                }}
                onClick={() => onSelectFolder(null)}
            >
                <Home size={14} />
                Tutti i documenti
            </div>

            {/* Folder tree */}
            {folders.map(node => (
                <FolderItem
                    key={node.id}
                    node={node}
                    depth={0}
                    selectedFolderId={selectedFolderId}
                    onSelectFolder={onSelectFolder}
                    onRefresh={() => refetch()}
                />
            ))}

            {/* New folder input */}
            {showInput ? (
                <div style={{ display: 'flex', gap: '4px', padding: '4px 6px', alignItems: 'center' }}>
                    <input
                        autoFocus
                        value={newFolderName}
                        onChange={e => setNewFolderName(e.target.value)}
                        onKeyDown={e => {
                            if (e.key === 'Enter') handleCreate();
                            if (e.key === 'Escape') { setShowInput(false); setNewFolderName(''); }
                        }}
                        placeholder="Nome cartella…"
                        style={{
                            flex: 1, background: 'var(--bg-hover)', border: '1px solid var(--accent)',
                            borderRadius: '4px', padding: '3px 8px', fontSize: '0.82rem',
                            color: 'var(--text-primary)', outline: 'none',
                        }}
                    />
                    <button
                        onClick={handleCreate}
                        disabled={!newFolderName.trim()}
                        style={{
                            background: 'var(--accent)', border: 'none', borderRadius: '4px',
                            padding: '3px 8px', cursor: 'pointer', fontSize: '0.75rem',
                            color: 'var(--bg-dark)', fontWeight: 700,
                        }}
                    >
                        OK
                    </button>
                </div>
            ) : (
                <button
                    onClick={() => setShowInput(true)}
                    style={{
                        display: 'flex', alignItems: 'center', gap: '5px',
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: 'var(--text-muted)', fontSize: '0.78rem',
                        padding: '4px 6px', borderRadius: '0.4rem',
                        marginTop: '2px',
                    }}
                    title={selectedFolderId ? 'Crea sottocartella qui' : 'Nuova cartella nella root'}
                >
                    <FolderPlus size={13} />
                    {selectedFolderId ? 'Nuova sottocartella' : 'Nuova cartella'}
                </button>
            )}
        </div>
    );
};

export default FolderTree;
