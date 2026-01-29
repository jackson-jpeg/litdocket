'use client';

/**
 * useRecentItems - Track recently accessed items (cases, tools, etc.)
 *
 * Persists recent items to localStorage with automatic deduplication
 * and maximum item limits.
 */

import { useState, useEffect, useCallback } from 'react';

export interface RecentCase {
  id: string;
  case_number: string;
  title: string;
  accessedAt: number;
}

export interface RecentTool {
  id: string;
  name: string;
  path: string;
  accessedAt: number;
}

const STORAGE_KEY_CASES = 'litdocket:recent-cases';
const STORAGE_KEY_TOOLS = 'litdocket:recent-tools';
const MAX_RECENT_CASES = 5;
const MAX_RECENT_TOOLS = 4;

function getStoredItems<T>(key: string): T[] {
  if (typeof window === 'undefined') return [];
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function setStoredItems<T>(key: string, items: T[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(key, JSON.stringify(items));
  } catch (err) {
    console.error('Failed to save to localStorage:', err);
  }
}

export function useRecentCases() {
  const [recentCases, setRecentCases] = useState<RecentCase[]>([]);

  // Load from localStorage on mount
  useEffect(() => {
    setRecentCases(getStoredItems<RecentCase>(STORAGE_KEY_CASES));
  }, []);

  // Add a case to recent list
  const addRecentCase = useCallback((caseItem: Omit<RecentCase, 'accessedAt'>) => {
    setRecentCases(prev => {
      // Remove existing entry if present
      const filtered = prev.filter(c => c.id !== caseItem.id);

      // Add to front with new timestamp
      const newItem: RecentCase = {
        ...caseItem,
        accessedAt: Date.now(),
      };

      const updated = [newItem, ...filtered].slice(0, MAX_RECENT_CASES);
      setStoredItems(STORAGE_KEY_CASES, updated);
      return updated;
    });
  }, []);

  // Remove a case from recent list
  const removeRecentCase = useCallback((caseId: string) => {
    setRecentCases(prev => {
      const updated = prev.filter(c => c.id !== caseId);
      setStoredItems(STORAGE_KEY_CASES, updated);
      return updated;
    });
  }, []);

  // Clear all recent cases
  const clearRecentCases = useCallback(() => {
    setRecentCases([]);
    setStoredItems(STORAGE_KEY_CASES, []);
  }, []);

  return {
    recentCases,
    addRecentCase,
    removeRecentCase,
    clearRecentCases,
  };
}

export function useRecentTools() {
  const [recentTools, setRecentTools] = useState<RecentTool[]>([]);

  // Load from localStorage on mount
  useEffect(() => {
    setRecentTools(getStoredItems<RecentTool>(STORAGE_KEY_TOOLS));
  }, []);

  // Add a tool to recent list
  const addRecentTool = useCallback((tool: Omit<RecentTool, 'accessedAt'>) => {
    setRecentTools(prev => {
      // Remove existing entry if present
      const filtered = prev.filter(t => t.id !== tool.id);

      // Add to front with new timestamp
      const newItem: RecentTool = {
        ...tool,
        accessedAt: Date.now(),
      };

      const updated = [newItem, ...filtered].slice(0, MAX_RECENT_TOOLS);
      setStoredItems(STORAGE_KEY_TOOLS, updated);
      return updated;
    });
  }, []);

  return {
    recentTools,
    addRecentTool,
  };
}

/**
 * Hook to track when a case is viewed
 * Call this on case detail page to automatically update recent cases
 */
export function useTrackCaseView(caseData: { id: string; case_number: string; title: string } | null) {
  const { addRecentCase } = useRecentCases();

  useEffect(() => {
    if (caseData?.id) {
      addRecentCase({
        id: caseData.id,
        case_number: caseData.case_number,
        title: caseData.title,
      });
    }
  }, [caseData?.id, caseData?.case_number, caseData?.title, addRecentCase]);
}

/**
 * Hook to track when a tool is used
 * Call this on tool pages to automatically update recent tools
 */
export function useTrackToolView(toolId: string, toolName: string, toolPath: string) {
  const { addRecentTool } = useRecentTools();

  useEffect(() => {
    if (toolId) {
      addRecentTool({
        id: toolId,
        name: toolName,
        path: toolPath,
      });
    }
  }, [toolId, toolName, toolPath, addRecentTool]);
}
