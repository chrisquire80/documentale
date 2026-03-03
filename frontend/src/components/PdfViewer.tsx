import { useEffect, useRef, useState, useCallback, useImperativeHandle, forwardRef } from 'react';
import * as pdfjsLib from 'pdfjs-dist';
import { ChevronLeft, ChevronRight, Loader2, Bot } from 'lucide-react';

// Worker file is in public/pdf.worker.min.mjs (copied from node_modules)
pdfjsLib.GlobalWorkerOptions.workerSrc = '/pdf.worker.min.mjs';

interface PdfViewerProps {
    url: string;
    zoom: number;
    onTextSelect?: (text: string) => void;
}

export interface PdfViewerHandle {
    scrollToPage: (page: number) => void;
}

const PdfViewer = forwardRef<PdfViewerHandle, PdfViewerProps>(({ url, zoom, onTextSelect }, ref) => {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const textLayerRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [pdfDoc, setPdfDoc] = useState<pdfjsLib.PDFDocumentProxy | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [numPages, setNumPages] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const renderTaskRef = useRef<any>(null);

    // Selezione testo
    const [selection, setSelection] = useState<{ text: string; x: number; y: number } | null>(null);

    const handleMouseUp = useCallback(() => {
        const sel = window.getSelection();
        if (sel && sel.toString().trim().length > 0 && textLayerRef.current) {
            const range = sel.getRangeAt(0);
            const rect = range.getBoundingClientRect();
            const containerRect = textLayerRef.current.getBoundingClientRect();

            // Posiziona il pulsante sopra la selezione
            setSelection({
                text: sel.toString().trim(),
                x: rect.left - containerRect.left + (rect.width / 2),
                y: rect.top - containerRect.top - 40
            });
        } else {
            setSelection(null);
        }
    }, []);

    // Load PDF document — StrictMode-safe (no .destroy() on cleanup)
    useEffect(() => {
        let cancelled = false;
        setIsLoading(true);
        setError(null);

        const loadingTask = pdfjsLib.getDocument({
            url,
            withCredentials: false,
        });

        loadingTask.promise
            .then((doc) => {
                if (cancelled) {
                    doc.destroy();
                    return;
                }
                setPdfDoc(doc);
                setNumPages(doc.numPages);
                setCurrentPage(1);
                setIsLoading(false);
            })
            .catch((err) => {
                if (cancelled) return;
                console.error('PDF load error:', err);
                setError('Impossibile caricare il PDF.');
                setIsLoading(false);
            });

        return () => {
            cancelled = true;
        };
    }, [url]);

    // Render current page
    const renderPage = useCallback(async (pageNum: number) => {
        if (!pdfDoc || !canvasRef.current || !textLayerRef.current) return;

        // Cancel any ongoing render
        if (renderTaskRef.current) {
            try { renderTaskRef.current.cancel(); } catch { /* ignore */ }
        }

        try {
            const page = await pdfDoc.getPage(pageNum);
            const scale = (zoom / 100) * 1.5; // 1.5x for crisp rendering
            const viewport = page.getViewport({ scale });

            const canvas = canvasRef.current;
            const context = canvas.getContext('2d');
            if (!context) return;

            canvas.height = viewport.height;
            canvas.width = viewport.width;

            const renderContext = {
                canvasContext: context,
                viewport: viewport,
                canvas: canvas,
            };

            renderTaskRef.current = page.render(renderContext);
            await renderTaskRef.current.promise;

            // Render Text Layer
            const textContent = await page.getTextContent();
            textLayerRef.current.innerHTML = '';
            textLayerRef.current.style.height = `${viewport.height}px`;
            textLayerRef.current.style.width = `${viewport.width}px`;

            await (pdfjsLib as any).renderTextLayer({
                textContentSource: textContent,
                container: textLayerRef.current,
                viewport: viewport,
                enhanceTextSelection: true,
            }).promise;

        } catch (err: any) {
            if (err?.name !== 'RenderingCancelledException') {
                console.error('PDF render error:', err);
            }
        }
    }, [pdfDoc, zoom]);

    useEffect(() => {
        if (pdfDoc) {
            renderPage(currentPage);
            setSelection(null);
        }
    }, [pdfDoc, currentPage, renderPage]);

    // Cleanup PDF doc on unmount
    useEffect(() => {
        return () => {
            if (pdfDoc) {
                pdfDoc.destroy();
            }
        };
    }, [pdfDoc]);

    const goToPrev = () => setCurrentPage(p => Math.max(1, p - 1));
    const goToNext = () => setCurrentPage(p => Math.min(numPages, p + 1));

    // Expose scrollToPage to parent
    useImperativeHandle(ref, () => ({
        scrollToPage: (page: number) => {
            if (page >= 1 && page <= numPages) {
                setCurrentPage(page);
            }
        },
    }), [numPages]);

    if (isLoading) {
        return (
            <div className="pdf-loading-overlay">
                <Loader2 size={32} className="pdf-spinner" />
                <span>Caricamento PDF...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="pdf-error-overlay">
                <p>{error}</p>
                <a
                    href={url.replace('inline=true', 'inline=false')}
                    className="btn pdf-download-btn"
                >
                    Scarica file
                </a>
            </div>
        );
    }

    return (
        <div className="pdf-viewer-main" ref={containerRef}>
            <div className="pdf-toolbar">
                <div className="pdf-controls">
                    <button onClick={goToPrev} disabled={currentPage <= 1} className="pdf-nav-btn" title="Pagina precedente">
                        <ChevronLeft size={20} />
                    </button>
                    <span className="pdf-page-indicator">
                        Pagina {currentPage} di {numPages}
                    </span>
                    <button onClick={goToNext} disabled={currentPage >= numPages} className="pdf-nav-btn" title="Pagina successiva">
                        <ChevronRight size={20} />
                    </button>
                </div>
            </div>

            <div className="pdf-container">
                <div className="pdf-page-wrapper" onMouseUp={handleMouseUp}>
                    <canvas ref={canvasRef} />
                    <div ref={textLayerRef} className="textLayer" />

                    {selection && (
                        <button
                            className="floating-ai-btn"
                            style={{
                                left: `${selection.x}px`,
                                top: `${selection.y}px`,
                                transform: 'translateX(-50%)'
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
            </div>
        </div>
    );
});

PdfViewer.displayName = 'PdfViewer';

export default PdfViewer;
