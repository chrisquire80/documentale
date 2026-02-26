export interface DocumentMetadata {
    tags?: string[];
    [key: string]: any;
}

export interface Document {
    id: string;
    title: string;
    is_restricted: boolean;
    doc_metadata: DocumentMetadata;
    current_version: number;
    owner_id: string;
    created_at: string;
}

export interface PaginatedDocuments {
    items: Document[];
    total: number;
    limit: number;
    offset: number;
}
