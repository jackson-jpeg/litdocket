'use client';

/**
 * Document Analyzer - AI-Powered Legal Document Analysis
 *
 * Gold Standard Design System (matching Dashboard):
 * - Light slate background
 * - White cards with shadows
 * - Rounded corners
 * - Uppercase tracking headers
 */

import { useState, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Upload,
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  Calendar,
  Scale,
  User,
  Building,
  ChevronRight,
  Loader2,
  Sparkles,
  ArrowLeft,
} from 'lucide-react';
import apiClient from '@/lib/api-client';

interface AnalysisResult {
  document_id: string;
  case_id: string;
  case_number: string;
  is_new_case: boolean;
  ai_summary: string;
  deadlines_extracted: number;
  analysis: {
    document_type?: string;
    filing_date?: string;
    court?: string;
    case_type?: string;
    jurisdiction?: string;
    parties?: Array<{ name: string; role: string }>;
    key_dates?: Array<{ date: string; description: string }>;
    deadlines_mentioned?: Array<{ description: string; deadline_date?: string; priority?: string }>;
  };
}

type AnalysisStage = 'idle' | 'uploading' | 'parsing' | 'analyzing' | 'extracting' | 'complete' | 'error';

const STAGE_MESSAGES: Record<AnalysisStage, string> = {
  idle: 'Ready for document upload',
  uploading: 'Uploading document...',
  parsing: 'Parsing PDF content...',
  analyzing: 'AI analyzing legal content...',
  extracting: 'Extracting deadlines & dates...',
  complete: 'Analysis complete',
  error: 'Analysis failed',
};

export default function DocumentAnalyzerPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [stage, setStage] = useState<AnalysisStage>('idle');
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf') {
        setFile(droppedFile);
        setError(null);
      } else {
        setError('Only PDF files are accepted');
      }
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === 'application/pdf') {
        setFile(selectedFile);
        setError(null);
      } else {
        setError('Only PDF files are accepted');
      }
    }
  }, []);

  const analyzeDocument = async () => {
    if (!file) return;

    setStage('uploading');
    setProgress(10);
    setError(null);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Simulate stage progression for UX
      setStage('parsing');
      setProgress(30);

      setTimeout(() => {
        setStage('analyzing');
        setProgress(60);
      }, 500);

      const response = await apiClient.post('/api/v1/documents/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      setStage('extracting');
      setProgress(90);

      // Brief pause to show extracting stage
      await new Promise(resolve => setTimeout(resolve, 300));

      setResult(response.data);
      setStage('complete');
      setProgress(100);
    } catch (err: unknown) {
      console.error('Analysis failed:', err);
      const axiosError = err as { response?: { data?: { detail?: string } } };
      setError(axiosError.response?.data?.detail || 'Document analysis failed');
      setStage('error');
    }
  };

  const reset = () => {
    setFile(null);
    setStage('idle');
    setProgress(0);
    setResult(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const navigateToCase = () => {
    if (result?.case_id) {
      router.push(`/cases/${result.case_id}`);
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority?.toLowerCase()) {
      case 'fatal': return 'text-red-600 bg-red-50';
      case 'critical': return 'text-orange-600 bg-orange-50';
      case 'important': return 'text-amber-600 bg-amber-50';
      case 'standard': return 'text-blue-600 bg-blue-50';
      default: return 'text-slate-600 bg-slate-50';
    }
  };

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => router.push('/tools')}
              className="text-slate-400 hover:text-slate-700 transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <FileText className="w-5 h-5 text-blue-600" />
              </div>
              <h1 className="text-2xl font-bold text-slate-900">Document Analyzer</h1>
              <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-mono rounded-full border border-amber-200">
                BETA
              </span>
            </div>
          </div>
          <p className="text-slate-500 text-sm">
            AI-powered analysis of legal documents with automatic deadline extraction
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Upload Panel */}
          <div className="space-y-4">
            {/* Upload Zone */}
            <div
              onDragEnter={handleDrag}
              onDragLeave={handleDrag}
              onDragOver={handleDrag}
              onDrop={handleDrop}
              className={`
                border-2 border-dashed p-8 text-center transition-all cursor-pointer rounded-xl
                ${dragActive
                  ? 'border-blue-400 bg-blue-50'
                  : file
                    ? 'border-green-400 bg-green-50'
                    : 'border-slate-300 bg-white hover:border-slate-400'
                }
              `}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                onChange={handleFileSelect}
                className="hidden"
              />

              {file ? (
                <div className="space-y-3">
                  <div className="w-12 h-12 mx-auto bg-green-100 rounded-full flex items-center justify-center">
                    <FileText className="w-6 h-6 text-green-600" />
                  </div>
                  <p className="font-medium text-slate-900">{file.name}</p>
                  <p className="text-sm text-slate-500">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      reset();
                    }}
                    className="text-red-600 hover:text-red-700 text-sm font-medium"
                  >
                    Remove file
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className={`w-12 h-12 mx-auto rounded-full flex items-center justify-center ${dragActive ? 'bg-blue-100' : 'bg-slate-100'}`}>
                    <Upload className={`w-6 h-6 ${dragActive ? 'text-blue-600' : 'text-slate-500'}`} />
                  </div>
                  <p className="font-medium text-slate-700">
                    Drop PDF here or click to select
                  </p>
                  <p className="text-xs text-slate-500">
                    Supported: Legal filings, orders, motions, complaints
                  </p>
                </div>
              )}
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 p-4 flex items-start gap-3 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-700 text-sm">Error</p>
                  <p className="text-sm text-red-600">{error}</p>
                </div>
              </div>
            )}

            {/* Analyze Button */}
            <button
              onClick={analyzeDocument}
              disabled={!file || stage !== 'idle'}
              className={`
                w-full py-4 font-semibold text-lg transition-all flex items-center justify-center gap-3 rounded-lg
                ${file && stage === 'idle'
                  ? 'bg-slate-900 hover:bg-slate-800 text-white'
                  : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                }
              `}
            >
              {stage !== 'idle' && stage !== 'complete' && stage !== 'error' ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>{STAGE_MESSAGES[stage]}</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-5 h-5" />
                  <span>Analyze Document</span>
                </>
              )}
            </button>

            {/* Progress Bar */}
            {stage !== 'idle' && stage !== 'complete' && stage !== 'error' && (
              <div className="space-y-2">
                <div className="h-2 bg-slate-200 overflow-hidden rounded-full">
                  <div
                    className="h-full bg-blue-600 transition-all duration-300 rounded-full"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-slate-500">
                  <span>{STAGE_MESSAGES[stage]}</span>
                  <span>{progress}%</span>
                </div>
              </div>
            )}

            {/* Analysis Progress Log */}
            {stage !== 'idle' && (
              <div className="bg-white border border-slate-200 p-4 rounded-lg">
                <div className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-3">Analysis Progress</div>
                <div className="space-y-2">
                  <div className={`flex items-center gap-2 text-sm ${progress >= 10 ? 'text-green-600' : 'text-slate-400'}`}>
                    {progress >= 10 ? <CheckCircle className="w-4 h-4" /> : <div className="w-4 h-4 border-2 border-slate-300 rounded-full" />}
                    <span>Upload received</span>
                  </div>
                  <div className={`flex items-center gap-2 text-sm ${progress >= 30 ? 'text-green-600' : 'text-slate-400'}`}>
                    {progress >= 30 ? <CheckCircle className="w-4 h-4" /> : <div className="w-4 h-4 border-2 border-slate-300 rounded-full" />}
                    <span>PDF parsed successfully</span>
                  </div>
                  <div className={`flex items-center gap-2 text-sm ${progress >= 60 ? 'text-green-600' : 'text-slate-400'}`}>
                    {progress >= 60 ? <CheckCircle className="w-4 h-4" /> : <div className="w-4 h-4 border-2 border-slate-300 rounded-full" />}
                    <span>AI analysis complete</span>
                  </div>
                  <div className={`flex items-center gap-2 text-sm ${progress >= 90 ? 'text-green-600' : 'text-slate-400'}`}>
                    {progress >= 90 ? <CheckCircle className="w-4 h-4" /> : <div className="w-4 h-4 border-2 border-slate-300 rounded-full" />}
                    <span>Deadlines extracted</span>
                  </div>
                  <div className={`flex items-center gap-2 text-sm ${stage === 'complete' ? 'text-green-600' : 'text-slate-400'}`}>
                    {stage === 'complete' ? <CheckCircle className="w-4 h-4" /> : <div className="w-4 h-4 border-2 border-slate-300 rounded-full" />}
                    <span>Ready</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right: Results Panel */}
          <div className="space-y-4">
            {result ? (
              <>
                {/* Success Header */}
                <div className="bg-green-50 border border-green-200 p-4 flex items-start gap-3 rounded-lg">
                  <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-medium text-green-700 text-sm">Analysis Complete</p>
                    <p className="text-sm text-green-600">
                      {result.is_new_case ? 'New case created' : 'Attached to existing case'}
                    </p>
                  </div>
                </div>

                {/* Case Info */}
                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="bg-slate-100 border-b border-slate-200 px-4 py-2">
                    <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">Case Information</span>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="flex items-center gap-3">
                      <Scale className="w-4 h-4 text-slate-400" />
                      <span className="text-slate-500 text-sm">Case Number:</span>
                      <span className="font-medium text-blue-600">{result.case_number || 'Not detected'}</span>
                    </div>
                    {result.analysis.court && (
                      <div className="flex items-center gap-3">
                        <Building className="w-4 h-4 text-slate-400" />
                        <span className="text-slate-500 text-sm">Court:</span>
                        <span className="font-medium text-slate-900">{result.analysis.court}</span>
                      </div>
                    )}
                    {result.analysis.document_type && (
                      <div className="flex items-center gap-3">
                        <FileText className="w-4 h-4 text-slate-400" />
                        <span className="text-slate-500 text-sm">Document Type:</span>
                        <span className="font-medium text-slate-900">{result.analysis.document_type}</span>
                      </div>
                    )}
                    {result.analysis.filing_date && (
                      <div className="flex items-center gap-3">
                        <Calendar className="w-4 h-4 text-slate-400" />
                        <span className="text-slate-500 text-sm">Filing Date:</span>
                        <span className="font-medium text-slate-900">{result.analysis.filing_date}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Parties */}
                {result.analysis.parties && result.analysis.parties.length > 0 && (
                  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <div className="bg-slate-100 border-b border-slate-200 px-4 py-2">
                      <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                        Parties ({result.analysis.parties.length})
                      </span>
                    </div>
                    <div className="p-4">
                      <div className="space-y-2">
                        {result.analysis.parties.map((party, idx) => (
                          <div key={idx} className="flex items-center gap-3">
                            <User className="w-4 h-4 text-slate-400" />
                            <span className="font-medium text-slate-900">{party.name}</span>
                            <span className="text-xs text-slate-500 bg-slate-100 px-2 py-0.5 rounded-full uppercase">
                              {party.role}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Extracted Deadlines */}
                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="bg-slate-100 border-b border-slate-200 px-4 py-2 flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                      Deadlines Extracted ({result.deadlines_extracted})
                    </span>
                    <Clock className="w-4 h-4 text-blue-600" />
                  </div>
                  <div className="p-4">
                    {result.analysis.deadlines_mentioned && result.analysis.deadlines_mentioned.length > 0 ? (
                      <div className="space-y-3">
                        {result.analysis.deadlines_mentioned.slice(0, 5).map((deadline, idx) => (
                          <div key={idx} className="border-l-2 border-blue-300 pl-3 py-1">
                            <p className="text-sm text-slate-700">{deadline.description}</p>
                            <div className="flex items-center gap-3 mt-1">
                              {deadline.deadline_date && (
                                <span className="font-mono text-xs text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                                  {deadline.deadline_date}
                                </span>
                              )}
                              {deadline.priority && (
                                <span className={`text-xs uppercase px-2 py-0.5 rounded font-medium ${getPriorityColor(deadline.priority)}`}>
                                  {deadline.priority}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                        {result.analysis.deadlines_mentioned.length > 5 && (
                          <p className="text-xs text-slate-500">
                            +{result.analysis.deadlines_mentioned.length - 5} more deadlines
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="text-slate-500 text-sm">No explicit deadlines detected in document</p>
                    )}
                  </div>
                </div>

                {/* AI Summary */}
                {result.ai_summary && (
                  <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                    <div className="bg-slate-100 border-b border-slate-200 px-4 py-2 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-amber-500" />
                      <span className="text-xs font-bold text-slate-600 uppercase tracking-wider">AI Summary</span>
                    </div>
                    <div className="p-4">
                      <p className="text-sm text-slate-700 leading-relaxed">{result.ai_summary}</p>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={navigateToCase}
                    className="flex-1 bg-slate-900 hover:bg-slate-800 text-white py-3 font-semibold flex items-center justify-center gap-2 transition-colors rounded-lg"
                  >
                    <span>Go to Case</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                  <button
                    onClick={reset}
                    className="px-6 bg-white border border-slate-300 hover:bg-slate-50 py-3 font-medium text-slate-700 transition-colors rounded-lg"
                  >
                    Analyze Another
                  </button>
                </div>
              </>
            ) : (
              /* Empty State */
              <div className="bg-white border border-slate-200 p-12 text-center rounded-xl">
                <div className="w-16 h-16 mx-auto bg-slate-100 rounded-full flex items-center justify-center mb-4">
                  <FileText className="w-8 h-8 text-slate-400" />
                </div>
                <p className="text-slate-600 font-medium">
                  Upload a document to begin analysis
                </p>
                <p className="text-slate-400 text-sm mt-2">
                  Results will appear here
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Features */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-blue-50 rounded-lg flex items-center justify-center mb-3">
              <Scale className="w-5 h-5 text-blue-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Case Detection</h3>
            <p className="text-xs text-slate-500">
              Automatically extracts case number, court, jurisdiction, and parties
            </p>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-amber-50 rounded-lg flex items-center justify-center mb-3">
              <Clock className="w-5 h-5 text-amber-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Deadline Extraction</h3>
            <p className="text-xs text-slate-500">
              AI identifies response deadlines, hearing dates, and filing requirements
            </p>
          </div>
          <div className="bg-white border border-slate-200 p-4 rounded-lg">
            <div className="w-10 h-10 bg-red-50 rounded-lg flex items-center justify-center mb-3">
              <AlertTriangle className="w-5 h-5 text-red-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">Priority Classification</h3>
            <p className="text-xs text-slate-500">
              Deadlines categorized as Fatal, Critical, Important, or Standard
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
