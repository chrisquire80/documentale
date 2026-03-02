import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { Link2, Trash2, PlusCircle, ChevronDown, ChevronUp, ArrowRight, ArrowLeft } from 'lucide-react';
import AddLinkModal from './AddLinkModal';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

const RELATION_LABELS: Record<string, { label: string; color: string }> = {
  segue_da:    { label: 'Segue da',      color: '#6366f1' },
  riferisce_a: { label: 'Si riferisce a', color: '#0ea5e9' },
  supera:      { label: 'Sostituisce',   color: '#f59e0b' },
  collegato_a: { label: 'Collegato',     color: '#94a3b8' },
};

interface LinkItem {
  id: string;
  from_doc_id: string;
  to_doc_id: string;
  relation_type: string;
  notes: string | null;
  created_at: string;
  from_doc_title: string | null;
  to_doc_title: string | null;
}

interface Props {
  docId: string;
  docTitle: string;
  canEdit: boolean;
}

const DocumentLinksPanel: React.FC<Props> = ({ docId, docTitle, canEdit }) => {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);

  const { data: links = [], isLoading } = useQuery<LinkItem[]>({
    queryKey: ['doc-links', docId],
    queryFn: async () => {
      const token = localStorage.getItem('token');
      const res = await axios.get(`${BASE_URL}/api/documents/${docId}/links`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      return res.data;
    },
    enabled: open,
  });

  const deleteMutation = useMutation({
    mutationFn: (linkId: string) => {
      const token = localStorage.getItem('token');
      return axios.delete(`${BASE_URL}/api/documents/links/${linkId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['doc-links', docId] });
    },
  });

  const outgoing = links.filter(l => l.from_doc_id === docId);
  const incoming = links.filter(l => l.to_doc_id === docId);

  return (
    <>
      <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', marginTop: 8 }}>
        <button
          onClick={() => setOpen(o => !o)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 6,
            padding: '6px 0', background: 'none', border: 'none', cursor: 'pointer',
            color: '#94a3b8', fontSize: 12, fontWeight: 600,
            textTransform: 'uppercase', letterSpacing: '0.05em',
          }}
        >
          <Link2 size={13} />
          <span>Documenti Collegati</span>
          {links.length > 0 && (
            <span style={{
              background: '#6366f122', color: '#6366f1',
              borderRadius: 8, padding: '0 5px', fontSize: 10, fontWeight: 700, marginLeft: 2,
            }}>
              {links.length}
            </span>
          )}
          <span style={{ marginLeft: 'auto' }}>
            {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
          </span>
        </button>

        {open && (
          <div style={{ paddingBottom: 8 }}>
            {isLoading && <p style={{ fontSize: 12, color: '#64748b' }}>Caricamento...</p>}

            {/* Outgoing links */}
            {outgoing.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                  <ArrowRight size={11} color="#64748b" />
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Collegato a
                  </span>
                </div>
                {outgoing.map(link => (
                  <LinkRow
                    key={link.id}
                    link={link}
                    targetTitle={link.to_doc_title}
                    canDelete={canEdit}
                    onDelete={() => deleteMutation.mutate(link.id)}
                  />
                ))}
              </div>
            )}

            {/* Incoming links */}
            {incoming.length > 0 && (
              <div style={{ marginBottom: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
                  <ArrowLeft size={11} color="#64748b" />
                  <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Referenziato da
                  </span>
                </div>
                {incoming.map(link => (
                  <LinkRow
                    key={link.id}
                    link={link}
                    targetTitle={link.from_doc_title}
                    canDelete={false}
                    onDelete={() => {}}
                  />
                ))}
              </div>
            )}

            {!isLoading && links.length === 0 && (
              <p style={{ fontSize: 12, color: '#64748b', margin: '4px 0' }}>Nessun collegamento.</p>
            )}

            {canEdit && (
              <button
                onClick={() => setAddOpen(true)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  background: 'none', border: '1px dashed rgba(99,102,241,0.4)',
                  borderRadius: 6, padding: '4px 10px', cursor: 'pointer',
                  color: '#6366f1', fontSize: 12, marginTop: 4,
                }}
              >
                <PlusCircle size={12} />
                Aggiungi collegamento
              </button>
            )}
          </div>
        )}
      </div>

      {addOpen && (
        <AddLinkModal
          docId={docId}
          docTitle={docTitle}
          onClose={() => setAddOpen(false)}
        />
      )}
    </>
  );
};

const LinkRow: React.FC<{
  link: LinkItem;
  targetTitle: string | null;
  canDelete: boolean;
  onDelete: () => void;
}> = ({ link, targetTitle, canDelete, onDelete }) => {
  const rel = RELATION_LABELS[link.relation_type] ?? { label: link.relation_type, color: '#94a3b8' };

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '4px 0', marginBottom: 2,
    }}>
      <span style={{
        background: `${rel.color}22`, color: rel.color,
        borderRadius: 4, padding: '1px 5px', fontSize: 10, fontWeight: 600, flexShrink: 0,
      }}>
        {rel.label}
      </span>
      <span style={{ fontSize: 12, color: '#cbd5e1', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {targetTitle ?? 'Documento sconosciuto'}
      </span>
      {link.notes && (
        <span style={{ fontSize: 11, color: '#64748b', fontStyle: 'italic' }} title={link.notes}>
          {link.notes.slice(0, 20)}{link.notes.length > 20 ? '…' : ''}
        </span>
      )}
      {canDelete && (
        <button
          onClick={onDelete}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#64748b', padding: 2 }}
          title="Rimuovi collegamento"
        >
          <Trash2 size={12} />
        </button>
      )}
    </div>
  );
};

export default DocumentLinksPanel;
