'use client';

/**
 * useCasePageModals - Centralized modal state management for case page
 *
 * Replaces 11+ useState calls with a single useReducer for type-safe
 * modal state transitions.
 */

import { useReducer, useCallback } from 'react';
import type { Deadline, Trigger } from '@/hooks/useCaseData';
import type { Document } from '@/types';

// Tab options for the unified add event modal
export type AddEventTab = 'quick' | 'rule' | 'trigger';

// All possible modal states
export type ModalState =
  | { type: 'closed' }
  | { type: 'add-event'; tab: AddEventTab }
  | { type: 'view-deadline'; deadline: Deadline }
  | { type: 'view-chain'; trigger: Trigger }
  | { type: 'edit-trigger'; trigger: Trigger }
  | { type: 'view-document'; document: Document }
  | { type: 'upload-document' };

// Actions for transitioning between states
export type ModalAction =
  | { type: 'CLOSE' }
  | { type: 'OPEN_ADD_EVENT'; tab?: AddEventTab }
  | { type: 'SET_ADD_EVENT_TAB'; tab: AddEventTab }
  | { type: 'VIEW_DEADLINE'; deadline: Deadline }
  | { type: 'VIEW_CHAIN'; trigger: Trigger }
  | { type: 'EDIT_TRIGGER'; trigger: Trigger }
  | { type: 'VIEW_DOCUMENT'; document: Document }
  | { type: 'UPLOAD_DOCUMENT' };

// Initial state
const initialState: ModalState = { type: 'closed' };

// Reducer function
function modalReducer(state: ModalState, action: ModalAction): ModalState {
  switch (action.type) {
    case 'CLOSE':
      return { type: 'closed' };

    case 'OPEN_ADD_EVENT':
      return { type: 'add-event', tab: action.tab || 'quick' };

    case 'SET_ADD_EVENT_TAB':
      if (state.type === 'add-event') {
        return { ...state, tab: action.tab };
      }
      return state;

    case 'VIEW_DEADLINE':
      return { type: 'view-deadline', deadline: action.deadline };

    case 'VIEW_CHAIN':
      return { type: 'view-chain', trigger: action.trigger };

    case 'EDIT_TRIGGER':
      return { type: 'edit-trigger', trigger: action.trigger };

    case 'VIEW_DOCUMENT':
      return { type: 'view-document', document: action.document };

    case 'UPLOAD_DOCUMENT':
      return { type: 'upload-document' };

    default:
      return state;
  }
}

// Hook interface
export interface UseCasePageModalsReturn {
  modal: ModalState;
  dispatch: React.Dispatch<ModalAction>;

  // Convenience methods
  close: () => void;
  openAddEvent: (tab?: AddEventTab) => void;
  setAddEventTab: (tab: AddEventTab) => void;
  viewDeadline: (deadline: Deadline) => void;
  viewChain: (trigger: Trigger) => void;
  editTrigger: (trigger: Trigger) => void;
  viewDocument: (document: Document) => void;
  openUploadDocument: () => void;

  // State checks
  isOpen: boolean;
  isAddEventOpen: boolean;
  isViewDeadlineOpen: boolean;
  isViewChainOpen: boolean;
  isEditTriggerOpen: boolean;
  isViewDocumentOpen: boolean;
  isUploadDocumentOpen: boolean;
}

export function useCasePageModals(): UseCasePageModalsReturn {
  const [modal, dispatch] = useReducer(modalReducer, initialState);

  // Convenience methods
  const close = useCallback(() => dispatch({ type: 'CLOSE' }), []);
  const openAddEvent = useCallback((tab?: AddEventTab) =>
    dispatch({ type: 'OPEN_ADD_EVENT', tab }), []);
  const setAddEventTab = useCallback((tab: AddEventTab) =>
    dispatch({ type: 'SET_ADD_EVENT_TAB', tab }), []);
  const viewDeadline = useCallback((deadline: Deadline) =>
    dispatch({ type: 'VIEW_DEADLINE', deadline }), []);
  const viewChain = useCallback((trigger: Trigger) =>
    dispatch({ type: 'VIEW_CHAIN', trigger }), []);
  const editTrigger = useCallback((trigger: Trigger) =>
    dispatch({ type: 'EDIT_TRIGGER', trigger }), []);
  const viewDocument = useCallback((document: Document) =>
    dispatch({ type: 'VIEW_DOCUMENT', document }), []);
  const openUploadDocument = useCallback(() =>
    dispatch({ type: 'UPLOAD_DOCUMENT' }), []);

  // State checks
  const isOpen = modal.type !== 'closed';
  const isAddEventOpen = modal.type === 'add-event';
  const isViewDeadlineOpen = modal.type === 'view-deadline';
  const isViewChainOpen = modal.type === 'view-chain';
  const isEditTriggerOpen = modal.type === 'edit-trigger';
  const isViewDocumentOpen = modal.type === 'view-document';
  const isUploadDocumentOpen = modal.type === 'upload-document';

  return {
    modal,
    dispatch,
    close,
    openAddEvent,
    setAddEventTab,
    viewDeadline,
    viewChain,
    editTrigger,
    viewDocument,
    openUploadDocument,
    isOpen,
    isAddEventOpen,
    isViewDeadlineOpen,
    isViewChainOpen,
    isEditTriggerOpen,
    isViewDocumentOpen,
    isUploadDocumentOpen,
  };
}

// Type guard helpers for extracting data from modal state
export function getViewingDeadline(state: ModalState): Deadline | null {
  return state.type === 'view-deadline' ? state.deadline : null;
}

export function getViewingChainTrigger(state: ModalState): Trigger | null {
  return state.type === 'view-chain' ? state.trigger : null;
}

export function getEditingTrigger(state: ModalState): Trigger | null {
  return state.type === 'edit-trigger' ? state.trigger : null;
}

export function getViewingDocument(state: ModalState): Document | null {
  return state.type === 'view-document' ? state.document : null;
}

export function getAddEventTab(state: ModalState): AddEventTab | null {
  return state.type === 'add-event' ? state.tab : null;
}
