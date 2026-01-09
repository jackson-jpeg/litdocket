'use client';

/**
 * Document Analyzer - AI-Powered Legal Document Analysis
 *
 * Sovereign Design System:
 * - Terminal aesthetic with dark theme
 * - Dense data display
 * - Zero radius
 * - Real-time analysis feedback
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
  X,
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
      case 'fatal': return 'text-red-500';
      case 'critical': return 'text-rose-500';
      case 'important': return 'text-amber-500';
      default: return 'text-slate-400';
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      {/* Header */}
      <header className="bg-slate-900 border-b border-slate-800">
        <div className="max-w-5xl mx-auto px-6 py-6">
          <div className="flex items-center gap-4 mb-4">
            <button
              onClick={() => router.push('/tools')}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <FileText className="w-6 h-6 text-cyan-400" />
              <h1 className="text-2xl font-mono font-bold">DOCUMENT ANALYZER</h1>
              <span className="px-2 py-0.5 bg-amber-900 text-amber-400 text-xs font-mono">BETA</span>
            </div>
          </div>
          <p className="text-slate-400 text-sm font-mono">
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
                border-2 border-dashed p-8 text-center transition-all cursor-pointer
                ${dragActive
                  ? 'border-cyan-500 bg-cyan-900/20'
                  : file
                    ? 'border-emerald-600 bg-emerald-900/10'
                    : 'border-slate-700 bg-slate-900 hover:border-slate-500'
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
                  <FileText className="w-12 h-12 text-emerald-400 mx-auto" />
                  <p className="font-mono text-white">{file.name}</p>
                  <p className="text-sm text-slate-400 font-mono">
                    {(file.size / 1024 / 1024).toFixed(2)} MB
                  </p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      reset();
                    }}
                    className="text-slate-400 hover:text-red-400 text-sm font-mono"
                  >
                    REMOVE
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <Upload className={`w-12 h-12 mx-auto ${dragActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                  <p className="font-mono text-slate-300">
                    Drop PDF here or click to select
                  </p>
                  <p className="text-xs text-slate-500 font-mono">
                    Supported: Legal filings, orders, motions, complaints
                  </p>
                </div>
              )}
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-900/30 border border-red-800 p-4 flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-mono text-red-400 text-sm">ERROR</p>
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              </div>
            )}

            {/* Analyze Button */}
            <button
              onClick={analyzeDocument}
              disabled={!file || stage !== 'idle'}
              className={`
                w-full py-4 font-mono font-bold text-lg transition-all flex items-center justify-center gap-3
                ${file && stage === 'idle'
                  ? 'bg-cyan-600 hover:bg-cyan-500 text-white'
                  : 'bg-slate-800 text-slate-500 cursor-not-allowed'
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
                  <span>ANALYZE DOCUMENT</span>
                </>
              )}
            </button>

            {/* Progress Bar */}
            {stage !== 'idle' && stage !== 'complete' && stage !== 'error' && (
              <div className="space-y-2">
                <div className="h-2 bg-slate-800 overflow-hidden">
                  <div
                    className="h-full bg-cyan-500 transition-all duration-300"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs font-mono text-slate-500">
                  <span>{STAGE_MESSAGES[stage]}</span>
                  <span>{progress}%</span>
                </div>
              </div>
            )}

            {/* Analysis Terminal Log */}
            {stage !== 'idle' && (
              <div className="bg-slate-900 border border-slate-700 p-4 font-mono text-xs">
                <div className="text-slate-500 mb-2">[ANALYSIS LOG]</div>
                <div className="space-y-1">
                  <div className={progress >= 10 ? 'text-emerald-400' : 'text-slate-600'}>
                    {progress >= 10 ? '>' : ' '} Upload received
                  </div>
                  <div className={progress >= 30 ? 'text-emerald-400' : 'text-slate-600'}>
                    {progress >= 30 ? '>' : ' '} PDF parsed successfully
                  </div>
                  <div className={progress >= 60 ? 'text-emerald-400' : 'text-slate-600'}>
                    {progress >= 60 ? '>' : ' '} AI analysis complete
                  </div>
                  <div className={progress >= 90 ? 'text-emerald-400' : 'text-slate-600'}>
                    {progress >= 90 ? '>' : ' '} Deadlines extracted
                  </div>
                  <div className={stage === 'complete' ? 'text-emerald-400' : 'text-slate-600'}>
                    {stage === 'complete' ? '>' : ' '} Ready
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
                <div className="bg-emerald-900/30 border border-emerald-800 p-4 flex items-start gap-3">
                  <CheckCircle className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-mono text-emerald-400 text-sm">ANALYSIS COMPLETE</p>
                    <p className="text-sm text-emerald-300">
                      {result.is_new_case ? 'New case created' : 'Attached to existing case'}
                    </p>
                  </div>
                </div>

                {/* Case Info */}
                <div className="bg-slate-900 border border-slate-700">
                  <div className="bg-slate-800 border-b border-slate-700 px-4 py-2">
                    <span className="font-mono text-sm text-slate-300">CASE INFORMATION</span>
                  </div>
                  <div className="p-4 space-y-3">
                    <div className="flex items-center gap-3">
                      <Scale className="w-4 h-4 text-slate-500" />
                      <span className="text-slate-400 text-sm">Case Number:</span>
                      <span className="font-mono text-cyan-400">{result.case_number || 'Not detected'}</span>
                    </div>
                    {result.analysis.court && (
                      <div className="flex items-center gap-3">
                        <Building className="w-4 h-4 text-slate-500" />
                        <span className="text-slate-400 text-sm">Court:</span>
                        <span className="font-mono text-white">{result.analysis.court}</span>
                      </div>
                    )}
                    {result.analysis.document_type && (
                      <div className="flex items-center gap-3">
                        <FileText className="w-4 h-4 text-slate-500" />
                        <span className="text-slate-400 text-sm">Document Type:</span>
                        <span className="font-mono text-white">{result.analysis.document_type}</span>
                      </div>
                    )}
                    {result.analysis.filing_date && (
                      <div className="flex items-center gap-3">
                        <Calendar className="w-4 h-4 text-slate-500" />
                        <span className="text-slate-400 text-sm">Filing Date:</span>
                        <span className="font-mono text-white">{result.analysis.filing_date}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Parties */}
                {result.analysis.parties && result.analysis.parties.length > 0 && (
                  <div className="bg-slate-900 border border-slate-700">
                    <div className="bg-slate-800 border-b border-slate-700 px-4 py-2">
                      <span className="font-mono text-sm text-slate-300">PARTIES ({result.analysis.parties.length})</span>
                    </div>
                    <div className="p-4">
                      <div className="space-y-2">
                        {result.analysis.parties.map((party, idx) => (
                          <div key={idx} className="flex items-center gap-3">
                            <User className="w-4 h-4 text-slate-500" />
                            <span className="font-mono text-white">{party.name}</span>
                            <span className="text-xs text-slate-500 uppercase">{party.role}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

                {/* Extracted Deadlines */}
                <div className="bg-slate-900 border border-slate-700">
                  <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 flex items-center justify-between">
                    <span className="font-mono text-sm text-slate-300">
                      DEADLINES EXTRACTED ({result.deadlines_extracted})
                    </span>
                    <Clock className="w-4 h-4 text-cyan-400" />
                  </div>
                  <div className="p-4">
                    {result.analysis.deadlines_mentioned && result.analysis.deadlines_mentioned.length > 0 ? (
                      <div className="space-y-3">
                        {result.analysis.deadlines_mentioned.slice(0, 5).map((deadline, idx) => (
                          <div key={idx} className="border-l-2 border-slate-700 pl-3 py-1">
                            <p className="text-sm text-white">{deadline.description}</p>
                            <div className="flex items-center gap-3 mt-1">
                              {deadline.deadline_date && (
                                <span className="font-mono text-xs text-cyan-400">
                                  {deadline.deadline_date}
                                </span>
                              )}
                              {deadline.priority && (
                                <span className={`font-mono text-xs uppercase ${getPriorityColor(deadline.priority)}`}>
                                  {deadline.priority}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                        {result.analysis.deadlines_mentioned.length > 5 && (
                          <p className="text-xs text-slate-500 font-mono">
                            +{result.analysis.deadlines_mentioned.length - 5} more
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
                  <div className="bg-slate-900 border border-slate-700">
                    <div className="bg-slate-800 border-b border-slate-700 px-4 py-2 flex items-center gap-2">
                      <Sparkles className="w-4 h-4 text-amber-400" />
                      <span className="font-mono text-sm text-slate-300">AI SUMMARY</span>
                    </div>
                    <div className="p-4">
                      <p className="text-sm text-slate-300 leading-relaxed">{result.ai_summary}</p>
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-3">
                  <button
                    onClick={navigateToCase}
                    className="flex-1 bg-cyan-600 hover:bg-cyan-500 py-3 font-mono font-bold flex items-center justify-center gap-2 transition-colors"
                  >
                    <span>GO TO CASE</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                  <button
                    onClick={reset}
                    className="px-6 bg-slate-700 hover:bg-slate-600 py-3 font-mono transition-colors"
                  >
                    ANALYZE ANOTHER
                  </button>
                </div>
              </>
            ) : (
              /* Empty State */
              <div className="bg-slate-900 border border-slate-700 p-12 text-center">
                <FileText className="w-16 h-16 text-slate-700 mx-auto mb-4" />
                <p className="text-slate-500 font-mono text-sm">
                  Upload a document to begin analysis
                </p>
                <p className="text-slate-600 font-mono text-xs mt-2">
                  Results will appear here
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Features */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 p-4">
            <Scale className="w-5 h-5 text-cyan-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Case Detection</h3>
            <p className="text-xs text-slate-400">
              Automatically extracts case number, court, jurisdiction, and parties
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4">
            <Clock className="w-5 h-5 text-amber-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Deadline Extraction</h3>
            <p className="text-xs text-slate-400">
              AI identifies response deadlines, hearing dates, and filing requirements
            </p>
          </div>
          <div className="bg-slate-900 border border-slate-800 p-4">
            <AlertTriangle className="w-5 h-5 text-rose-400 mb-2" />
            <h3 className="font-mono text-sm font-bold text-white mb-1">Priority Classification</h3>
            <p className="text-xs text-slate-400">
              Deadlines categorized as Fatal, Critical, Important, or Standard
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
