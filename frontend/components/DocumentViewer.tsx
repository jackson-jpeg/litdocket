'use client';

import { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Download } from 'lucide-react';

// ============================================================================
// PDF.js Worker Configuration
// CRITICAL FIX: Use CDN with version matching react-pdf's pdfjs-dist dependency
// React-pdf uses pdfjs-dist@4.4.168, so worker must match exactly
// Using unpkg.com CDN ensures version compatibility and no CORS issues
// ============================================================================
pdfjs.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@4.4.168/build/pdf.worker.min.mjs`;

interface DocumentViewerProps {
  isOpen: boolean;
  onClose: () => void;
  documentUrl: string;
  documentName: string;
}

export default function DocumentViewer({
  isOpen,
  onClose,
  documentUrl,
  documentName
}: DocumentViewerProps) {
  const [numPages, setNumPages] = useState<number | null>(null);
  const [pageNumber, setPageNumber] = useState(1);
  const [scale, setScale] = useState(1.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    console.log('[DocumentViewer] PDF loaded successfully:', { numPages, documentUrl });
    setNumPages(numPages);
    setLoading(false);
    setError(null);
  };

  const onDocumentLoadError = (error: Error) => {
    console.error('[DocumentViewer] Error loading PDF:', {
      error,
      message: error.message,
      documentUrl,
      workerSrc: pdfjs.GlobalWorkerOptions.workerSrc
    });
    setLoading(false);
    setError(error.message || 'Failed to load PDF document');
  };

  const changePage = (offset: number) => {
    setPageNumber(prevPageNumber => prevPageNumber + offset);
  };

  const previousPage = () => changePage(-1);
  const nextPage = () => changePage(1);

  const zoomIn = () => setScale(prev => Math.min(prev + 0.2, 3.0));
  const zoomOut = () => setScale(prev => Math.max(prev - 0.2, 0.5));

  const handleDownload = () => {
    window.open(documentUrl, '_blank');
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-6xl h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-200">
          <div className="flex-1">
            <h2 className="text-lg font-semibold text-slate-800 truncate">{documentName}</h2>
            {numPages && (
              <p className="text-sm text-slate-600">
                Page {pageNumber} of {numPages}
              </p>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center gap-2">
            {/* Zoom Controls */}
            <button
              onClick={zoomOut}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title="Zoom Out"
            >
              <ZoomOut className="w-5 h-5 text-slate-600" />
            </button>
            <span className="text-sm text-slate-600 min-w-[4rem] text-center">
              {Math.round(scale * 100)}%
            </span>
            <button
              onClick={zoomIn}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title="Zoom In"
            >
              <ZoomIn className="w-5 h-5 text-slate-600" />
            </button>

            <div className="w-px h-6 bg-slate-300 mx-2" />

            {/* Download */}
            <button
              onClick={handleDownload}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title="Download"
            >
              <Download className="w-5 h-5 text-slate-600" />
            </button>

            {/* Close */}
            <button
              onClick={onClose}
              className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              title="Close"
            >
              <X className="w-5 h-5 text-slate-600" />
            </button>
          </div>
        </div>

        {/* PDF Viewer */}
        <div className="flex-1 overflow-auto bg-slate-100 flex items-center justify-center p-4">
          {loading && !error && (
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
              <p className="text-slate-600">Loading PDF...</p>
            </div>
          )}

          {error && (
            <div className="text-center max-w-md">
              <div className="bg-red-50 border border-red-200 rounded-lg p-6">
                <div className="text-red-600 mb-2">
                  <svg className="w-12 h-12 mx-auto mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-red-800 mb-2">Failed to Load PDF</h3>
                <p className="text-sm text-red-700 mb-4">{error}</p>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}

          {!error && (
            <Document
              file={documentUrl}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading=""
              className="flex justify-center"
            >
              <Page
                pageNumber={pageNumber}
                scale={scale}
                className="shadow-lg"
                renderTextLayer={true}
                renderAnnotationLayer={true}
              />
            </Document>
          )}
        </div>

        {/* Navigation Footer */}
        {numPages && numPages > 1 && (
          <div className="flex items-center justify-center gap-4 p-4 border-t border-slate-200">
            <button
              onClick={previousPage}
              disabled={pageNumber <= 1}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
              Previous
            </button>

            <div className="flex items-center gap-2">
              <input
                type="number"
                min={1}
                max={numPages}
                value={pageNumber}
                onChange={(e) => {
                  const page = parseInt(e.target.value);
                  if (page >= 1 && page <= numPages) {
                    setPageNumber(page);
                  }
                }}
                className="w-16 px-2 py-1 text-center border border-slate-300 rounded"
              />
              <span className="text-sm text-slate-600">of {numPages}</span>
            </div>

            <button
              onClick={nextPage}
              disabled={pageNumber >= numPages}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
