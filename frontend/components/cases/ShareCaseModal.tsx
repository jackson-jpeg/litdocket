'use client';

import { useState, useEffect } from 'react';
import apiClient from '@/lib/api-client';
import {
  X,
  Users,
  Mail,
  Check,
  AlertTriangle,
  RefreshCw,
  Trash2,
  Shield,
  Edit,
  Eye,
  Crown,
} from 'lucide-react';
import type {
  CaseAccess,
  CaseAccessListResponse,
  CaseAccessRole,
  ShareCaseResponse,
} from '@/types';

interface ShareCaseModalProps {
  caseId: string;
  caseTitle: string;
  isOpen: boolean;
  onClose: () => void;
}

const roleConfig: Record<CaseAccessRole, { label: string; icon: React.ReactNode; description: string }> = {
  owner: {
    label: 'Owner',
    icon: <Crown className="w-4 h-4 text-wax" />,
    description: 'Full control including sharing',
  },
  editor: {
    label: 'Editor',
    icon: <Edit className="w-4 h-4 text-steel" />,
    description: 'Can edit case data and deadlines',
  },
  viewer: {
    label: 'Viewer',
    icon: <Eye className="w-4 h-4 text-ink-muted" />,
    description: 'Read-only access',
  },
};

function AccessListItem({
  access,
  isOwner,
  onRevoke,
  onChangeRole,
  isProcessing,
}: {
  access: CaseAccess;
  isOwner: boolean;
  onRevoke: () => void;
  onChangeRole: (role: CaseAccessRole) => void;
  isProcessing: boolean;
}) {
  const role = roleConfig[access.role];
  const isPending = !access.invitation_accepted_at && access.invited_email;

  return (
    <div className="flex items-center justify-between p-3 border border-ink/20 bg-paper">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-surface border border-ink/20 flex items-center justify-center">
          {role.icon}
        </div>
        <div>
          <p className="font-medium text-ink">
            {access.user?.name || access.user?.email || access.invited_email}
          </p>
          <p className="text-xs text-ink-secondary">
            {isPending ? (
              <span className="text-important font-mono">PENDING</span>
            ) : (
              <span className="font-mono">{access.user?.email}</span>
            )}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {!isOwner && !isProcessing && (
          <>
            <select
              value={access.role}
              onChange={(e) => onChangeRole(e.target.value as CaseAccessRole)}
              className="text-sm border border-ink/20 px-2 py-1 bg-paper font-mono"
            >
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
              <option value="owner">Owner</option>
            </select>
            <button
              onClick={onRevoke}
              className="p-1.5 text-ink-muted hover:text-fatal hover:bg-fatal/10 transition-transform hover:translate-x-0.5"
              title="Revoke access"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          </>
        )}
        {isOwner && (
          <span className="px-2 py-1 bg-wax/10 text-wax border border-wax text-xs font-mono font-medium uppercase">
            Owner
          </span>
        )}
        {isProcessing && <RefreshCw className="w-4 h-4 text-ink-muted animate-spin" />}
      </div>
    </div>
  );
}

export default function ShareCaseModal({ caseId, caseTitle, isOpen, onClose }: ShareCaseModalProps) {
  const [accessList, setAccessList] = useState<CaseAccess[]>([]);
  const [ownerId, setOwnerId] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingIds, setProcessingIds] = useState<Set<string>>(new Set());

  // Share form state
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<CaseAccessRole>('viewer');
  const [sharing, setSharing] = useState(false);
  const [shareError, setShareError] = useState<string | null>(null);
  const [shareSuccess, setShareSuccess] = useState<string | null>(null);

  const fetchAccessList = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get<CaseAccessListResponse>(
        `/api/v1/case-access/cases/${caseId}/access`
      );
      setAccessList(response.data.access_grants);
      setOwnerId(response.data.owner_id);
    } catch (err) {
      console.error('Failed to fetch access list:', err);
      setError('Failed to load sharing settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchAccessList();
    }
  }, [isOpen, caseId]);

  const handleShare = async (e: React.FormEvent) => {
    e.preventDefault();
    setShareError(null);
    setShareSuccess(null);

    if (!email.trim()) {
      setShareError('Please enter an email address');
      return;
    }

    setSharing(true);
    try {
      const response = await apiClient.post<ShareCaseResponse>(
        `/api/v1/case-access/cases/${caseId}/access`,
        { email: email.trim(), role }
      );

      setShareSuccess(response.data.message);
      setEmail('');
      setRole('viewer');

      // Refresh access list
      await fetchAccessList();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setShareError(detail || 'Failed to share case');
    } finally {
      setSharing(false);
    }
  };

  const handleRevoke = async (accessId: string) => {
    setProcessingIds((prev) => new Set(prev).add(accessId));
    try {
      await apiClient.delete(`/api/v1/case-access/cases/${caseId}/access/${accessId}`);
      setAccessList((prev) => prev.filter((a) => a.id !== accessId));
    } catch (err) {
      console.error('Failed to revoke access:', err);
    } finally {
      setProcessingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(accessId);
        return newSet;
      });
    }
  };

  const handleChangeRole = async (accessId: string, newRole: CaseAccessRole) => {
    setProcessingIds((prev) => new Set(prev).add(accessId));
    try {
      await apiClient.patch(`/api/v1/case-access/cases/${caseId}/access/${accessId}`, {
        role: newRole,
      });
      setAccessList((prev) =>
        prev.map((a) => (a.id === accessId ? { ...a, role: newRole } : a))
      );
    } catch (err) {
      console.error('Failed to update role:', err);
    } finally {
      setProcessingIds((prev) => {
        const newSet = new Set(prev);
        newSet.delete(accessId);
        return newSet;
      });
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-ink/50 flex items-center justify-center z-50 p-4">
      <div className="bg-paper border-2 border-ink shadow-modal max-w-lg w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-ink bg-surface">
          <div className="flex items-center gap-2">
            <Users className="w-5 h-5 text-steel" />
            <h2 className="text-lg font-heading font-semibold text-ink">Share Case</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-ink-muted hover:text-ink transition-transform hover:translate-x-0.5"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 overflow-y-auto max-h-[calc(90vh-8rem)]">
          <p className="text-sm text-ink-secondary mb-4">
            Sharing: <span className="font-medium font-mono text-ink">{caseTitle}</span>
          </p>

          {/* Share Form */}
          <form onSubmit={handleShare} className="mb-6">
            <div className="flex gap-2 mb-2">
              <div className="flex-1">
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Enter email address"
                    className="w-full pl-10 pr-4 py-2 border border-ink/20 bg-paper focus:outline-none focus:border-ink font-mono"
                    disabled={sharing}
                  />
                </div>
              </div>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as CaseAccessRole)}
                className="border border-ink/20 px-3 py-2 bg-paper font-mono"
                disabled={sharing}
              >
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
                <option value="owner">Owner</option>
              </select>
              <button
                type="submit"
                disabled={sharing}
                className="btn-primary disabled:opacity-50"
              >
                {sharing ? <RefreshCw className="w-4 h-4 animate-spin" /> : 'Share'}
              </button>
            </div>

            {shareError && (
              <p className="text-sm text-fatal flex items-center gap-1 font-mono">
                <AlertTriangle className="w-4 h-4" /> {shareError}
              </p>
            )}
            {shareSuccess && (
              <p className="text-sm text-status-success flex items-center gap-1 font-mono">
                <Check className="w-4 h-4" /> {shareSuccess}
              </p>
            )}
          </form>

          {/* Role descriptions */}
          <div className="bg-surface border border-ink/20 p-3 mb-4">
            <p className="text-xs font-mono font-medium text-ink-secondary uppercase tracking-wide mb-2">Access Levels:</p>
            <div className="space-y-1">
              {Object.entries(roleConfig).map(([key, config]) => (
                <div key={key} className="flex items-center gap-2 text-xs text-ink-secondary">
                  {config.icon}
                  <span className="font-medium text-ink">{config.label}:</span>
                  <span>{config.description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Access List */}
          <div>
            <h3 className="text-sm font-mono font-medium text-ink uppercase tracking-wide mb-2">People with access</h3>

            {loading ? (
              <div className="flex items-center justify-center py-8">
                <span className="font-mono text-ink-secondary">LOADING<span className="animate-pulse">_</span></span>
              </div>
            ) : error ? (
              <div className="flex items-center gap-2 text-fatal py-4 font-mono">
                <AlertTriangle className="w-5 h-5" />
                <span>{error}</span>
              </div>
            ) : accessList.length === 0 ? (
              <p className="text-sm text-ink-muted py-4 text-center">
                No one else has access to this case yet.
              </p>
            ) : (
              <div className="space-y-2">
                {accessList.map((access) => (
                  <AccessListItem
                    key={access.id}
                    access={access}
                    isOwner={access.user_id === ownerId && access.id === 'owner'}
                    onRevoke={() => handleRevoke(access.id)}
                    onChangeRole={(newRole) => handleChangeRole(access.id, newRole)}
                    isProcessing={processingIds.has(access.id)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-ink bg-surface">
          <button
            onClick={onClose}
            className="btn-secondary"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
