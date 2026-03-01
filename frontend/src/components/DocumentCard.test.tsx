import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DocumentCard from './DocumentCard';

// Stub all child modals to avoid heavy rendering
vi.mock('./DocumentPreviewModal', () => ({
  default: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div data-testid="preview-modal" /> : null,
}));
vi.mock('./EditMetadataModal', () => ({
  default: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div data-testid="edit-modal" /> : null,
}));
vi.mock('./ShareModal', () => ({
  default: () => <div data-testid="share-modal" />,
}));
vi.mock('./CommentsPanel', () => ({
  default: () => <div data-testid="comments-panel" />,
}));
vi.mock('./DocumentVersionModal', () => ({
  default: ({ isOpen }: { isOpen: boolean }) =>
    isOpen ? <div data-testid="version-modal" /> : null,
}));
vi.mock('./UploadModal', () => ({
  default: () => <div data-testid="upload-modal" />,
}));
vi.mock('./RelatedDocumentsModal', () => ({
  default: () => <div data-testid="related-modal" />,
}));

const mockUseAuth = vi.fn();
vi.mock('../store/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock('@tanstack/react-query', () => ({
  useMutation: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
  useQueryClient: vi.fn(() => ({ invalidateQueries: vi.fn() })),
}));

vi.mock('axios', () => ({
  default: { delete: vi.fn().mockResolvedValue({}) },
}));

const mockDoc = {
  id: 'doc-1',
  title: 'Test Document',
  owner_id: 'user-1',
  created_at: '2024-01-15T10:00:00Z',
  doc_metadata: { tags: ['finance', 'Q1'] },
};

describe('DocumentCard', () => {
  beforeEach(() => {
    mockUseAuth.mockReturnValue({ currentUser: { id: 'user-1', role: 'reader' } });
  });

  it('renders document title', () => {
    render(<DocumentCard doc={mockDoc} />);
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });

  it('renders document tags', () => {
    render(<DocumentCard doc={mockDoc} />);
    expect(screen.getByText('finance')).toBeInTheDocument();
    expect(screen.getByText('Q1')).toBeInTheDocument();
  });

  it('renders standard action buttons', () => {
    render(<DocumentCard doc={mockDoc} />);
    expect(screen.getByTitle('Anteprima')).toBeInTheDocument();
    expect(screen.getByTitle('Scarica')).toBeInTheDocument();
    expect(screen.getByTitle('Commenti')).toBeInTheDocument();
    expect(screen.getByTitle('Condividi')).toBeInTheDocument();
    expect(screen.getByTitle('Versioni')).toBeInTheDocument();
  });

  it('shows edit and delete buttons for document owner', () => {
    render(<DocumentCard doc={mockDoc} />);
    expect(screen.getByTitle('Modifica')).toBeInTheDocument();
    expect(screen.getByTitle('Cestino')).toBeInTheDocument();
  });

  it('shows edit and delete buttons for ADMIN', () => {
    mockUseAuth.mockReturnValue({ currentUser: { id: 'other', role: 'ADMIN' } });
    render(<DocumentCard doc={mockDoc} />);
    expect(screen.getByTitle('Modifica')).toBeInTheDocument();
    expect(screen.getByTitle('Cestino')).toBeInTheDocument();
  });

  it('hides edit and delete buttons for non-owner reader', () => {
    mockUseAuth.mockReturnValue({ currentUser: { id: 'other-user', role: 'reader' } });
    render(<DocumentCard doc={mockDoc} />);
    expect(screen.queryByTitle('Modifica')).not.toBeInTheDocument();
    expect(screen.queryByTitle('Cestino')).not.toBeInTheDocument();
  });

  it('opens preview modal when Anteprima is clicked', () => {
    render(<DocumentCard doc={mockDoc} />);
    fireEvent.click(screen.getByTitle('Anteprima'));
    expect(screen.getByTestId('preview-modal')).toBeInTheDocument();
  });

  it('opens comments panel when Commenti is clicked', () => {
    render(<DocumentCard doc={mockDoc} />);
    fireEvent.click(screen.getByTitle('Commenti'));
    expect(screen.getByTestId('comments-panel')).toBeInTheDocument();
  });

  it('opens share modal when Condividi is clicked', () => {
    render(<DocumentCard doc={mockDoc} />);
    fireEvent.click(screen.getByTitle('Condividi'));
    expect(screen.getByTestId('share-modal')).toBeInTheDocument();
  });

  it('opens version modal when Versioni is clicked', () => {
    render(<DocumentCard doc={mockDoc} />);
    fireEvent.click(screen.getByTitle('Versioni'));
    expect(screen.getByTestId('version-modal')).toBeInTheDocument();
  });

  it('opens edit modal when Modifica is clicked', () => {
    render(<DocumentCard doc={mockDoc} />);
    fireEvent.click(screen.getByTitle('Modifica'));
    expect(screen.getByTestId('edit-modal')).toBeInTheDocument();
  });

  it('shows highlight snippet when present', () => {
    const doc = { ...mockDoc, highlight_snippet: 'found <em>keyword</em> here' };
    render(<DocumentCard doc={doc} />);
    expect(screen.getByText(/found/)).toBeInTheDocument();
  });

  it('renders without tags when doc_metadata is absent', () => {
    const doc = { ...mockDoc, doc_metadata: null };
    render(<DocumentCard doc={doc} />);
    expect(screen.getByText('Test Document')).toBeInTheDocument();
  });

  it('renders checkbox when onToggleSelect is provided', () => {
    render(<DocumentCard doc={mockDoc} onToggleSelect={vi.fn()} />);
    expect(document.querySelector('.doc-checkbox-inline')).toBeInTheDocument();
  });

  it('calls onToggleSelect with doc id when checkbox clicked', () => {
    const mockToggle = vi.fn();
    render(<DocumentCard doc={mockDoc} onToggleSelect={mockToggle} />);
    fireEvent.click(document.querySelector('.doc-checkbox-inline')!);
    expect(mockToggle).toHaveBeenCalledWith('doc-1');
  });

  it('checkbox has selected class when isSelected is true', () => {
    render(<DocumentCard doc={mockDoc} onToggleSelect={vi.fn()} isSelected={true} />);
    expect(document.querySelector('.doc-checkbox-inline')).toHaveClass('selected');
  });

  it('does not render checkbox when onToggleSelect is not provided', () => {
    render(<DocumentCard doc={mockDoc} />);
    expect(document.querySelector('.doc-checkbox-inline')).not.toBeInTheDocument();
  });

  it('renders related documents button', () => {
    render(<DocumentCard doc={mockDoc} />);
    expect(screen.getByTitle('Correlati')).toBeInTheDocument();
  });
});
