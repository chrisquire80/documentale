import React, { useCallback, useImperativeHandle, forwardRef, useState } from 'react';
import { Viewer, Worker } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import { pageNavigationPlugin } from '@react-pdf-viewer/page-navigation';
import { searchPlugin } from '@react-pdf-viewer/search';

import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';
import '@react-pdf-viewer/search/lib/styles/index.css';
import { Bot } from 'lucide-react';

interface PdfViewerProps {
    url: string;
    zoom: number; // Ignorato qui o si può gestire con il zoomPlugin
    onTextSelect?: (text: string) => void;
    /** Testo da evidenziare dopo il rendering della pagina (es. snippet da citazione chat) */
    highlightText?: string;
    /** Pagina iniziale da mostrare quando il PDF carica (es. da citazione chat) */
    initialPage?: number;
}

export interface PdfViewerHandle {
    scrollToPage: (page: number) => void;
}

const PdfViewer = forwardRef<PdfViewerHandle, PdfViewerProps>(({ url, zoom, onTextSelect, highlightText, initialPage }, ref) => {
    // Inizializza i plugin
    const defaultLayoutPluginInstance = defaultLayoutPlugin();
    const pageNavigationPluginInstance = pageNavigationPlugin();
    const searchPluginInstance = searchPlugin();

    const { jumpToPage } = pageNavigationPluginInstance;
    const { highlight } = searchPluginInstance;

    // Gestione Highlight-to-chat
    const [selection, setSelection] = useState<{ text: string; x: number; y: number } | null>(null);

    const handleMouseUp = useCallback((e: React.MouseEvent) => {
        const sel = window.getSelection();
        if (sel && sel.toString().trim().length > 0) {
            // Un workaround semplice per posizionare il pulsante vicino al puntatore del mouse
            setSelection({
                text: sel.toString().trim(),
                x: e.clientX,
                y: e.clientY - 40
            });
        } else {
            setSelection(null);
        }
    }, []);

    // Esponi scrollToPage al componente genitore
    useImperativeHandle(ref, () => ({
        scrollToPage: (page: number) => {
            // @react-pdf-viewer usa indici 0-based
            jumpToPage(page - 1);
            if (highlightText) {
                // Aspetta che la navigazione sia completata prima di evidenziare
                setTimeout(() => {
                    highlight({
                        keyword: highlightText,
                        matchCase: false,
                    });
                }, 500);
            }
        },
    }), [jumpToPage, highlight, highlightText]);

    const handleDocumentLoad = () => {
        if (initialPage && initialPage > 0) {
            jumpToPage(initialPage - 1);
        }
        if (highlightText) {
            setTimeout(() => {
                highlight({
                    keyword: highlightText,
                    matchCase: false,
                });
            }, 500);
        }
    };

    return (
        <div style={{ position: 'relative', height: '100%', width: '100%' }} onMouseUp={handleMouseUp}>
            <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
                <Viewer
                    fileUrl={url}
                    plugins={[defaultLayoutPluginInstance, pageNavigationPluginInstance, searchPluginInstance]}
                    onDocumentLoad={handleDocumentLoad}
                    defaultScale={zoom ? zoom / 100 : 1}
                />
            </Worker>

            {selection && (
                <button
                    className="floating-ai-btn"
                    style={{
                        position: 'fixed',
                        left: `${selection.x}px`,
                        top: `${selection.y}px`,
                        transform: 'translateX(-50%)',
                        zIndex: 9999
                    }}
                    onClick={() => {
                        if (onTextSelect) onTextSelect(selection.text);
                        setSelection(null);
                    }}
                >
                    <Bot size={16} />
                    Chiedi a Gemini
                </button>
            )}
        </div>
    );
});

PdfViewer.displayName = 'PdfViewer';

export default PdfViewer;
