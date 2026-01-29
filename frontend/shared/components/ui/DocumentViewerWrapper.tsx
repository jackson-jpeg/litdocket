'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';

interface DocumentViewerWrapperProps {
  isOpen: boolean;
  onClose: () => void;
  documentUrl: string;
  documentName: string;
}

// Completely prevent SSR for react-pdf
const DocumentViewer = dynamic(
  () => import('./DocumentViewer'),
  {
    ssr: false,
    loading: () => (
      <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
        <div className="text-white text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading PDF viewer...</p>
        </div>
      </div>
    ),
  }
);

export default function DocumentViewerWrapper(props: DocumentViewerWrapperProps) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Don't render anything until client-side is mounted
  if (!isMounted || !props.isOpen) {
    return null;
  }

  return <DocumentViewer {...props} />;
}
