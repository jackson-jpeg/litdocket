'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, AlertCircle, Loader2, Scale } from 'lucide-react';
import apiClient from '@/lib/api-client';

export default function HomePage() {
  const router = useRouter();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    const file = acceptedFiles[0];

    if (file.type !== 'application/pdf') {
      setError('Please upload a PDF file');
      return;
    }

    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Simulate progress
      const progressInterval = setInterval(() => {
        setProgress((prev) => Math.min(prev + 10, 90));
      }, 200);

      const response = await apiClient.post('/api/v1/documents/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      clearInterval(progressInterval);
      setProgress(100);

      const { case_id, case_created, redirect_url } = response.data;

      // Show success briefly
      setTimeout(() => {
        router.push(redirect_url);
      }, 500);

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed. Please try again.');
      setUploading(false);
      setProgress(0);
    }
  }, [router]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Scale className="w-8 h-8 text-blue-600" />
              <h1 className="text-2xl font-bold text-slate-800">
                Florida Legal Docketing Assistant
              </h1>
            </div>
            <button
              onClick={() => router.push('/dashboard')}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              View Dashboard
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 pt-16 pb-24">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-slate-800 mb-4">
            Intelligent Case Management
          </h2>
          <p className="text-lg text-slate-600 max-w-2xl mx-auto">
            Upload a legal document to automatically extract case information, calculate deadlines,
            and access AI-powered insights based on Florida court rules.
          </p>
        </div>

        {/* Upload Zone */}
        <div
          {...getRootProps()}
          className={`
            relative border-4 border-dashed rounded-2xl p-16 text-center cursor-pointer
            transition-all duration-300 ease-in-out
            ${isDragActive
              ? 'border-blue-500 bg-blue-50/50 scale-[1.02]'
              : 'border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50/30'
            }
            ${uploading ? 'opacity-50 cursor-not-allowed' : ''}
            shadow-lg hover:shadow-xl
          `}
        >
          <input {...getInputProps()} />

          <div className="flex flex-col items-center gap-6">
            {uploading ? (
              <>
                <div className="relative">
                  <FileText className="w-20 h-20 text-blue-500" />
                  <Loader2 className="w-8 h-8 text-blue-600 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 animate-spin" />
                </div>
                <div className="w-full max-w-md">
                  <div className="bg-slate-200 rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-blue-500 h-full transition-all duration-300 ease-out"
                      style={{ width: `${progress}%` }}
                    />
                  </div>
                  <p className="text-sm text-slate-600 mt-3 font-medium">
                    Analyzing document... {progress}%
                  </p>
                </div>
              </>
            ) : (
              <>
                <div className={`
                  p-6 rounded-full transition-all duration-300
                  ${isDragActive ? 'bg-blue-100 scale-110' : 'bg-slate-100'}
                `}>
                  <Upload className={`w-12 h-12 ${isDragActive ? 'text-blue-600' : 'text-slate-400'}`} />
                </div>
                <div>
                  <p className="text-2xl font-semibold text-slate-700 mb-2">
                    {isDragActive
                      ? 'Drop your PDF here'
                      : 'Drag & drop a PDF, or click to select'
                    }
                  </p>
                  <p className="text-sm text-slate-500">
                    Supported file types: PDF (max 30MB)
                  </p>
                </div>
                <div className="flex gap-4 text-sm text-slate-600 mt-4">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span>Case detection</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span>Deadline extraction</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span>AI analysis</span>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3 animate-shake">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium text-red-700">Upload Error</p>
              <p className="text-red-600 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6 mt-16">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <FileText className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="font-semibold text-slate-800 mb-2">Smart Document Analysis</h3>
            <p className="text-sm text-slate-600">
              Automatically extract case numbers, parties, and key information from legal documents
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <Scale className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="font-semibold text-slate-800 mb-2">Florida Rules Knowledge</h3>
            <p className="text-sm text-slate-600">
              AI trained on Florida state, federal, and local court rules for accurate guidance
            </p>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mb-4">
              <Loader2 className="w-6 h-6 text-blue-600" />
            </div>
            <h3 className="font-semibold text-slate-800 mb-2">Automated Deadlines</h3>
            <p className="text-sm text-slate-600">
              Calculate response deadlines based on service method and applicable rules
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
