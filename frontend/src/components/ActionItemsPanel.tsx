import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { CheckSquare, Square, AlertCircle, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react';

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000';

interface Decision {
  text: string;
  date?: string | null;
}

interface ActionItem {
  action: string;
  owner?: string | null;
  deadline?: string | null;
  status: 'pending' | 'done';
}

interface OpenQuestion {
  text: string;
}

interface Props {
  docId: string;
  metadata: Record<string, any>;
}

const ActionItemsPanel: React.FC<Props> = ({ docId, metadata }) => {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);

  const decisions: Decision[] = metadata?.decisions ?? [];
  const actionItems: ActionItem[] = metadata?.action_items ?? [];
  const openQuestions: OpenQuestion[] = metadata?.open_questions ?? [];

  const hasAny = decisions.length > 0 || actionItems.length > 0 || openQuestions.length > 0;

  const toggleMutation = useMutation({
    mutationFn: (updated: ActionItem[]) => {
      const token = localStorage.getItem('token');
      return axios.patch(
        `${BASE_URL}/api/documents/${docId}/action-items`,
        { action_items: updated },
        { headers: { Authorization: `Bearer ${token}` } }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    },
  });

  const toggleItem = (idx: number) => {
    const updated = actionItems.map((item, i) =>
      i === idx ? { ...item, status: item.status === 'done' ? 'pending' : 'done' } : item
    ) as ActionItem[];
    toggleMutation.mutate(updated);
    // Optimistic update — refetch on success handles the canonical state
  };

  if (!hasAny) return null;

  const pendingCount = actionItems.filter(i => i.status !== 'done').length;

  return (
    <div style={{ borderTop: '1px solid rgba(255,255,255,0.08)', marginTop: 8 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          padding: '6px 0',
          background: 'none',
          border: 'none',
          cursor: 'pointer',
          color: '#94a3b8',
          fontSize: 12,
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
        }}
      >
        <CheckSquare size={13} />
        <span>Action Items</span>
        {pendingCount > 0 && (
          <span style={{
            background: '#f59e0b',
            color: '#fff',
            borderRadius: 8,
            padding: '0 5px',
            fontSize: 10,
            fontWeight: 700,
            marginLeft: 2,
          }}>
            {pendingCount}
          </span>
        )}
        <span style={{ marginLeft: 'auto' }}>
          {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        </span>
      </button>

      {open && (
        <div style={{ paddingBottom: 8 }}>
          {/* Decisions */}
          {decisions.length > 0 && (
            <Section icon={<AlertCircle size={12} color="#22c55e" />} title="Decisioni">
              {decisions.map((d, i) => (
                <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'flex-start', marginBottom: 4 }}>
                  <span style={{ color: '#22c55e', flexShrink: 0, marginTop: 1 }}>•</span>
                  <span style={{ fontSize: 12, color: '#cbd5e1' }}>
                    {d.text}
                    {d.date && <span style={{ color: '#64748b', marginLeft: 6 }}>({d.date})</span>}
                  </span>
                </div>
              ))}
            </Section>
          )}

          {/* Action Items */}
          {actionItems.length > 0 && (
            <Section icon={<CheckSquare size={12} color="#f59e0b" />} title="Compiti">
              {actionItems.map((item, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    gap: 6,
                    alignItems: 'flex-start',
                    marginBottom: 5,
                    cursor: 'pointer',
                    opacity: item.status === 'done' ? 0.5 : 1,
                  }}
                  onClick={() => toggleItem(i)}
                >
                  {item.status === 'done'
                    ? <CheckSquare size={13} color="#22c55e" style={{ flexShrink: 0, marginTop: 1 }} />
                    : <Square size={13} color="#94a3b8" style={{ flexShrink: 0, marginTop: 1 }} />
                  }
                  <div>
                    <span style={{
                      fontSize: 12,
                      color: '#cbd5e1',
                      textDecoration: item.status === 'done' ? 'line-through' : 'none',
                    }}>
                      {item.action}
                    </span>
                    <div style={{ display: 'flex', gap: 6, marginTop: 2, flexWrap: 'wrap' }}>
                      {item.owner && <Badge color="#6366f1">{item.owner}</Badge>}
                      {item.deadline && <Badge color="#f59e0b">{item.deadline}</Badge>}
                    </div>
                  </div>
                </div>
              ))}
            </Section>
          )}

          {/* Open Questions */}
          {openQuestions.length > 0 && (
            <Section icon={<HelpCircle size={12} color="#94a3b8" />} title="Questioni aperte">
              {openQuestions.map((q, i) => (
                <div key={i} style={{ display: 'flex', gap: 6, alignItems: 'flex-start', marginBottom: 4 }}>
                  <span style={{ color: '#64748b', flexShrink: 0, marginTop: 1 }}>?</span>
                  <span style={{ fontSize: 12, color: '#94a3b8' }}>{q.text}</span>
                </div>
              ))}
            </Section>
          )}
        </div>
      )}
    </div>
  );
};

const Section: React.FC<{ icon: React.ReactNode; title: string; children: React.ReactNode }> = ({
  icon, title, children,
}) => (
  <div style={{ marginBottom: 8 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
      {icon}
      <span style={{ fontSize: 11, fontWeight: 600, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {title}
      </span>
    </div>
    {children}
  </div>
);

const Badge: React.FC<{ color: string; children: React.ReactNode }> = ({ color, children }) => (
  <span style={{
    background: `${color}22`,
    color,
    borderRadius: 4,
    padding: '1px 5px',
    fontSize: 10,
    fontWeight: 600,
  }}>
    {children}
  </span>
);

export default ActionItemsPanel;
