'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import {
  FileEdit,
  Sparkles,
  Send,
  Copy,
  Download,
  ChevronDown,
  ChevronUp,
  Scale,
  FileText,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  BookOpen,
  Gavel,
} from 'lucide-react';

interface BriefSection {
  title: string;
  content: string;
  citations: Array<{
    text: string;
    source: string;
    page?: string;
  }>;
}

interface BriefDraft {
  id: string;
  document_type: string;
  title: string;
  sections: BriefSection[];
  content: string | null;
  citations: Array<{
    text: string;
    source: string;
    citation: string;
  }>;
  status: string;
  created_at: string;
}

interface BriefDraftingAssistantProps {
  caseId: string;
  caseTitle?: string;
  jurisdiction?: string;
  className?: string;
}

const DOCUMENT_TYPES = [
  { value: 'motion_to_dismiss', label: 'Motion to Dismiss', icon: Gavel },
  { value: 'motion_for_summary_judgment', label: 'Motion for Summary Judgment', icon: Scale },
  { value: 'opposition_brief', label: 'Opposition Brief', icon: FileText },
  { value: 'reply_brief', label: 'Reply Brief', icon: FileText },
  { value: 'memorandum_of_law', label: 'Memorandum of Law', icon: BookOpen },
  { value: 'trial_brief', label: 'Trial Brief', icon: Scale },
  { value: 'appellate_brief', label: 'Appellate Brief', icon: Gavel },
  { value: 'discovery_motion', label: 'Discovery Motion', icon: FileText },
];

export default function BriefDraftingAssistant({
  caseId,
  caseTitle,
  jurisdiction,
  className = '',
}: BriefDraftingAssistantProps) {
  const [expanded, setExpanded] = useState(false);
  const [drafts, setDrafts] = useState<BriefDraft[]>([]);
  const [loading, setLoading] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [selectedType, setSelectedType] = useState('motion_to_dismiss');
  const [arguments_, setArguments] = useState('');
  const [currentDraft, setCurrentDraft] = useState<BriefDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (expanded) {
      fetchDrafts();
    }
  }, [expanded, caseId]);

  const fetchDrafts = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/v1/case-intelligence/cases/${caseId}/briefs`);
      setDrafts(response.data || []);
    } catch (err) {
      console.error('Failed to fetch drafts:', err);
    } finally {
      setLoading(false);
    }
  };

  const generateDraft = async () => {
    if (!arguments_.trim()) {
      setError('Please provide the key arguments or issues to address');
      return;
    }

    try {
      setGenerating(true);
      setError(null);

      const response = await apiClient.post(`/api/v1/case-intelligence/cases/${caseId}/briefs/generate`, {
        document_type: selectedType,
        arguments: arguments_.split('\n').filter((a) => a.trim()),
        jurisdiction: jurisdiction || 'federal',
        include_citations: true,
      });

      setCurrentDraft(response.data);
      setArguments('');
      fetchDrafts();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail || 'Failed to generate draft. Please try again.');
    } finally {
      setGenerating(false);
    }
  };

  const copyToClipboard = async () => {
    if (!currentDraft) return;

    const content = currentDraft.sections
      .map((s) => `## ${s.title}\n\n${s.content}`)
      .join('\n\n---\n\n');

    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const downloadDraft = () => {
    if (!currentDraft) return;

    const content = currentDraft.sections
      .map((s) => `${s.title}\n${'='.repeat(s.title.length)}\n\n${s.content}`)
      .join('\n\n---\n\n');

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${currentDraft.title.replace(/\s+/g, '_')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const selectedTypeInfo = DOCUMENT_TYPES.find((t) => t.value === selectedType);

  return (
    <div className={`card overflow-hidden ${className}`}>
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg">
            <FileEdit className="w-5 h-5 text-white" />
          </div>
          <div className="text-left">
            <h3 className="font-semibold text-slate-900">Brief Drafting Assistant</h3>
            <p className="text-sm text-slate-500">AI-powered legal document drafting</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-purple-500" />
          {expanded ? (
            <ChevronUp className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-slate-400" />
          )}
        </div>
      </button>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-slate-200">
          {/* Draft Generator */}
          <div className="p-4 bg-gradient-to-br from-purple-50 to-pink-50">
            <h4 className="text-sm font-semibold text-slate-700 mb-3">Generate New Draft</h4>

            {/* Document Type Selection */}
            <div className="mb-3">
              <label className="block text-xs text-slate-500 mb-1">Document Type</label>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
              >
                {DOCUMENT_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Arguments Input */}
            <div className="mb-3">
              <label className="block text-xs text-slate-500 mb-1">
                Key Arguments (one per line)
              </label>
              <textarea
                value={arguments_}
                onChange={(e) => setArguments(e.target.value)}
                placeholder="Enter the main arguments or issues to address..."
                rows={4}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 text-sm focus:ring-2 focus:ring-purple-500 focus:border-purple-500 resize-none"
              />
            </div>

            {error && (
              <div className="mb-3 p-2 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
                <AlertCircle className="w-4 h-4" />
                {error}
              </div>
            )}

            <button
              onClick={generateDraft}
              disabled={generating || !arguments_.trim()}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg font-medium hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {generating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Generating Draft...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Generate Draft
                </>
              )}
            </button>
          </div>

          {/* Current Draft Preview */}
          {currentDraft && (
            <div className="border-t border-slate-200">
              <div className="p-4">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-sm font-semibold text-slate-700">{currentDraft.title}</h4>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={copyToClipboard}
                      className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
                      title="Copy to clipboard"
                    >
                      {copied ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                    <button
                      onClick={downloadDraft}
                      className="p-1.5 rounded hover:bg-slate-100 text-slate-500 hover:text-slate-700 transition-colors"
                      title="Download"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                <div className="max-h-80 overflow-y-auto space-y-4">
                  {currentDraft.sections.map((section, idx) => (
                    <div key={idx} className="p-3 bg-white rounded-lg border border-slate-200">
                      <h5 className="font-medium text-slate-900 mb-2">{section.title}</h5>
                      <p className="text-sm text-slate-700 whitespace-pre-wrap">{section.content}</p>
                      {section.citations && section.citations.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-slate-100">
                          <p className="text-xs text-slate-500 mb-1">Citations:</p>
                          <ul className="text-xs text-slate-600 space-y-0.5">
                            {section.citations.map((cite, cIdx) => (
                              <li key={cIdx} className="italic">
                                {cite.source}
                                {cite.page && `, at ${cite.page}`}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Legal Disclaimer */}
                <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs text-amber-800">
                    <strong>Important:</strong> This AI-generated draft is for reference only.
                    Always verify citations, review for accuracy, and ensure compliance with
                    local court rules before filing. Attorney review and modification required.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Previous Drafts */}
          {drafts.length > 0 && (
            <div className="border-t border-slate-200 p-4">
              <h4 className="text-sm font-semibold text-slate-700 mb-3">Previous Drafts</h4>
              <div className="space-y-2">
                {drafts.slice(0, 5).map((draft) => (
                  <button
                    key={draft.id}
                    onClick={() => setCurrentDraft(draft)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      currentDraft?.id === draft.id
                        ? 'border-purple-300 bg-purple-50'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-900 truncate">
                        {draft.title}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full ${
                          draft.status === 'draft'
                            ? 'bg-yellow-100 text-yellow-700'
                            : draft.status === 'reviewed'
                            ? 'bg-blue-100 text-blue-700'
                            : 'bg-green-100 text-green-700'
                        }`}
                      >
                        {draft.status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {new Date(draft.created_at).toLocaleDateString()}
                    </p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
