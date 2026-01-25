import { useState, useCallback } from 'react';
import apiClient from '@/lib/api-client';

interface Source {
  source_number: number;
  document_id: string;
  document_name: string;
  document_type: string | null;
  chunk_text: string;
  similarity: number;
}

interface RAGResponse {
  question: string;
  answer: string;
  sources: Source[];
  confidence: 'low' | 'medium' | 'high';
  total_sources: number;
}

interface RAGStats {
  case_id: string;
  total_documents: number;
  documents_with_embeddings: number;
  documents_pending_embedding: number;
  total_embedding_chunks: number;
  rag_enabled: boolean;
}

interface UseRAGOptions {
  caseId: string;
  onSuccess?: (response: RAGResponse) => void;
  onError?: (error: Error) => void;
}

export function useRAG({ caseId, onSuccess, onError }: UseRAGOptions) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<RAGStats | null>(null);

  /**
   * Ask a question using RAG (Retrieval Augmented Generation)
   */
  const ask = useCallback(async (question: string, includeSources = true) => {
    if (!question.trim()) {
      setError('Question cannot be empty');
      return null;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await apiClient.post('/rag/ask', {
        question: question.trim(),
        case_id: caseId,
        include_sources: includeSources
      });

      if (response.data.success) {
        const data = response.data.data as RAGResponse;
        setResult(data);
        onSuccess?.(data);
        return data;
      } else {
        throw new Error(response.data.message || 'Failed to get answer');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to search documents';
      setError(errorMessage);
      onError?.(new Error(errorMessage));
      return null;
    } finally {
      setLoading(false);
    }
  }, [caseId, onSuccess, onError]);

  /**
   * Perform semantic search (returns chunks without AI-generated answer)
   */
  const search = useCallback(async (query: string, topK = 5) => {
    if (!query.trim()) {
      setError('Query cannot be empty');
      return null;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await apiClient.post('/rag/semantic', {
        query: query.trim(),
        case_id: caseId,
        top_k: topK
      });

      if (response.data.success) {
        return response.data.data;
      } else {
        throw new Error(response.data.message || 'Search failed');
      }
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to search';
      setError(errorMessage);
      onError?.(new Error(errorMessage));
      return null;
    } finally {
      setLoading(false);
    }
  }, [caseId, onError]);

  /**
   * Get RAG statistics for the case
   */
  const getStats = useCallback(async () => {
    try {
      const response = await apiClient.get(`/rag/stats/${caseId}`);
      if (response.data.success) {
        const statsData = response.data.data as RAGStats;
        setStats(statsData);
        return statsData;
      }
      return null;
    } catch (err: any) {
      console.error('Failed to fetch RAG stats:', err);
      return null;
    }
  }, [caseId]);

  /**
   * Generate embeddings for a specific document
   */
  const generateEmbeddings = useCallback(async (documentId: string) => {
    try {
      const response = await apiClient.post(`/rag/embed/${documentId}`);
      return response.data.success;
    } catch (err: any) {
      console.error('Failed to generate embeddings:', err);
      return false;
    }
  }, []);

  /**
   * Clear current results
   */
  const clear = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    // State
    loading,
    result,
    error,
    stats,

    // Methods
    ask,
    search,
    getStats,
    generateEmbeddings,
    clear
  };
}

/**
 * Example usage:
 *
 * const { ask, loading, result, error } = useRAG({
 *   caseId: 'abc123',
 *   onSuccess: (response) => {
 *     console.log('Answer:', response.answer);
 *   }
 * });
 *
 * // Ask a question
 * await ask("What was the service date for the complaint?");
 *
 * // Access results
 * if (result) {
 *   console.log(result.answer);
 *   console.log(result.sources);
 * }
 */
