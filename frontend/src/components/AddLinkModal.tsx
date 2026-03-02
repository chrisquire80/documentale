import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { X, Link2, Search } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const RELATION_LABELS: Record<string, string> = {
  segue_da: 'Segue da / fa seguito a',
  riferisce_a: 'Si riferisce a / cita',
  supera: 'Sostituisce / aggiorna',
  collegato_a: 'Genericamente collegato',
};

interface Props {
  docId: string;
  docTitle: string;
  onClose: () => void;
}

const AddLinkModal: React.FC<Props> = ({ docId, docTitle, onClose }) => {
  const queryClient = useQueryClient();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [relationType, setRelationType] = useState('collegato_a');
  const [notes, setNotes] = useState('');

  const { data: searchResults, isFetching } = useQuery({
    queryKey: ['doc-search-link', searchQuery],
    queryFn: async () => {
      if (!searchQuery.trim()) return { items: [] };
      const token = localStorage.getItem('token');
      const res = await axios.get(`${BASE_URL}/api/documents/search`, {
        params: { query: searchQuery, limit: 10 },
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.data;
    },
    enabled: searchQuery.length > 2,
  });

  const docs = (searchResults?.items ?? []).filter((d: any) => d.id !== docId);

  const createMutation = useMutation({
    mutationFn: () => {
      const token = localStorage.getItem('token');
      return axios.post(
        `${BASE_URL}/api/documents/${docId}/links`,
        { to_doc_id: selectedDocId, relation_type: relationType, notes: notes || null },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doc-links', docId] });
      onClose();
    },
  });

  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1100,
    }}>
      <div style={{
        background: '#1e293b', borderRadius: 12, padding: 24,
        width: 520, maxHeight: '80vh', display: 'flex', flexDirection: 'column',
        boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 20 }}>
          <Link2 size={18} color="#6366f1" />
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: '#f1f5f9' }}>
            Collega documento
          </h3>
          <span style={{ marginLeft: 'auto' }}>
            <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b' }}>
              <X size={18} />
            </button>
          </span>
        </div>

        <p style={{ margin: '0 0 16px', fontSize: 13, color: '#64748b' }}>
          Da: <strong style={{ color: '#94a3b8' }}>{docTitle}</strong>
        </p>

        {/* Relation type */}
        <label style={labelStyle}>Tipo di relazione</label>
        <select
          value={relationType}
          onChange={e => setRelationType(e.target.value)}
          style={selectStyle}
        >
          {Object.entries(RELATION_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>

        {/* Search */}
        <label style={{ ...labelStyle, marginTop: 14 }}>Cerca documento di destinazione</label>
        <div style={{ position: 'relative' }}>
          <Search size={14} style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: '#64748b' }} />
          <input
            type="text"
            placeholder="Digita almeno 3 caratteri..."
            value={searchQuery}
            onChange={e => { setSearchQuery(e.target.value); setSelectedDocId(null); }}
            style={{ ...inputStyle, paddingLeft: 30 }}
          />
        </div>

        {/* Results */}
        {docs.length > 0 && (
          <div style={{
            marginTop: 8, maxHeight: 180, overflowY: 'auto',
            border: '1px solid rgba(255,255,255,0.08)', borderRadius: 8,
          }}>
            {docs.map((d: any) => (
              <div
                key={d.id}
                onClick={() => setSelectedDocId(d.id)}
                style={{
                  padding: '8px 12px',
                  cursor: 'pointer',
                  background: selectedDocId === d.id ? 'rgba(99,102,241,0.2)' : 'transparent',
                  borderLeft: selectedDocId === d.id ? '3px solid #6366f1' : '3px solid transparent',
                  fontSize: 13,
                  color: '#cbd5e1',
                  transition: 'background 0.15s',
                }}
              >
                {d.title}
              </div>
            ))}
          </div>
        )}

        {isFetching && <p style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>Ricerca...</p>}
        {searchQuery.length > 2 && !isFetching && docs.length === 0 && (
          <p style={{ fontSize: 12, color: '#64748b', marginTop: 6 }}>Nessun documento trovato.</p>
        )}

        {/* Note */}
        <label style={{ ...labelStyle, marginTop: 14 }}>Nota opzionale</label>
        <input
          type="text"
          placeholder="es. Approvazione del 15 gennaio..."
          value={notes}
          onChange={e => setNotes(e.target.value)}
          style={inputStyle}
        />

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, marginTop: 20, justifyContent: 'flex-end' }}>
          <button onClick={onClose} style={cancelBtnStyle}>Annulla</button>
          <button
            onClick={() => createMutation.mutate()}
            disabled={!selectedDocId || createMutation.isPending}
            style={{
              ...primaryBtnStyle,
              opacity: !selectedDocId ? 0.5 : 1,
              cursor: !selectedDocId ? 'not-allowed' : 'pointer',
            }}
          >
            {createMutation.isPending ? 'Salvataggio...' : 'Crea collegamento'}
          </button>
        </div>
      </div>
    </div>
  );
};

const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 12, fontWeight: 600,
  color: '#64748b', marginBottom: 6,
  textTransform: 'uppercase', letterSpacing: '0.04em',
};

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', borderRadius: 8,
  border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.05)',
  color: '#f1f5f9', fontSize: 13, outline: 'none', boxSizing: 'border-box',
};

const selectStyle: React.CSSProperties = {
  ...inputStyle, cursor: 'pointer',
};

const cancelBtnStyle: React.CSSProperties = {
  padding: '8px 16px', borderRadius: 8,
  border: '1px solid rgba(255,255,255,0.1)',
  background: 'transparent', color: '#94a3b8',
  fontSize: 13, cursor: 'pointer',
};

const primaryBtnStyle: React.CSSProperties = {
  padding: '8px 16px', borderRadius: 8,
  border: 'none', background: '#6366f1',
  color: '#fff', fontSize: 13, fontWeight: 600,
};

export default AddLinkModal;
