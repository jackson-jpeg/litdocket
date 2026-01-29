'use client';

/**
 * IntegrityBadge - Cryptographic Chain of Custody Verification
 *
 * The enterprise feature that screams reliability.
 * Shows a green shield when the audit chain is verified.
 *
 * "Chain of Custody: Verified. No tampering detected since creation."
 */

import React, { useState, useCallback } from 'react';
import apiClient from '@/lib/api-client';

interface AuditVerificationResult {
  is_valid: boolean;
  total_entries: number;
  broken_at_sequence: number | null;
  error_message: string | null;
}

interface IntegrityBadgeProps {
  recordId: string;
  tableName?: string;
  showDetails?: boolean;
  className?: string;
}

// Shield icons as simple SVGs
interface IconProps {
  className?: string;
  title?: string;
}

const ShieldCheck = ({ className, title }: IconProps) => (
  <svg className={className} width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
    <path d="M10 1L2 4V9C2 14 5.5 17.5 10 19C14.5 17.5 18 14 18 9V4L10 1ZM8 14L5 11L6.5 9.5L8 11L13.5 5.5L15 7L8 14Z" />
  </svg>
);

const ShieldAlert = ({ className, title }: IconProps) => (
  <svg className={className} width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
    <path d="M10 1L2 4V9C2 14 5.5 17.5 10 19C14.5 17.5 18 14 18 9V4L10 1ZM9 6H11V11H9V6ZM9 13H11V15H9V13Z" />
  </svg>
);

const ShieldQuestion = ({ className, title }: IconProps) => (
  <svg className={className} width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
    <path d="M10 1L2 4V9C2 14 5.5 17.5 10 19C14.5 17.5 18 14 18 9V4L10 1ZM10 7C11.1 7 12 7.9 12 9C12 9.7 11.6 10.3 11 10.7V12H9V10C9 9.4 9.4 9 10 9C10.6 9 11 8.6 11 8S10.6 7 10 7 9 7.4 9 8H7C7 6.9 7.9 6 10 6V7ZM9 14H11V16H9V14Z" />
  </svg>
);

const LoadingSpinner = ({ className }: IconProps) => (
  <svg className={`animate-spin ${className}`} width="20" height="20" viewBox="0 0 20 20" fill="none">
    <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="2" strokeOpacity="0.3" />
    <path d="M10 2C5.58 2 2 5.58 2 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
  </svg>
);

type VerificationState = 'idle' | 'verifying' | 'verified' | 'failed' | 'error';

export function IntegrityBadge({
  recordId,
  tableName,
  showDetails = false,
  className = '',
}: IntegrityBadgeProps) {
  const [state, setState] = useState<VerificationState>('idle');
  const [result, setResult] = useState<AuditVerificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [verifiedAt, setVerifiedAt] = useState<Date | null>(null);

  const verifyIntegrity = useCallback(async () => {
    setState('verifying');
    setError(null);

    try {
      const response = await apiClient.get(`/api/v1/audit/verify/${recordId}`);
      const verification = response.data as AuditVerificationResult;

      setResult(verification);
      setState(verification.is_valid ? 'verified' : 'failed');
      setVerifiedAt(new Date());

    } catch (err: unknown) {
      const axiosError = err as { response?: { status?: number; data?: { detail?: string } } };
      if (axiosError.response?.status === 501) {
        setError('Audit verification not available');
      } else {
        setError(axiosError.response?.data?.detail || 'Verification failed');
      }
      setState('error');
    }
  }, [recordId]);

  // Badge content based on state
  const renderBadge = () => {
    switch (state) {
      case 'idle':
        return (
          <button
            onClick={verifyIntegrity}
            className="flex items-center gap-2 px-3 py-1.5 text-xs bg-slate-100 border border-slate-300 rounded hover:bg-slate-200 transition-colors"
            title="Click to verify the cryptographic integrity of this record's audit trail"
          >
            <ShieldQuestion className="w-4 h-4 text-slate-500" />
            <span>Verify Integrity</span>
          </button>
        );

      case 'verifying':
        return (
          <div className="flex items-center gap-2 px-3 py-1 bg-slate-100 border border-slate-300 text-xs rounded">
            <LoadingSpinner className="w-4 h-4 text-blue-600" />
            <span className="text-slate-600">Verifying chain...</span>
          </div>
        );

      case 'verified':
        return (
          <div className={`flex items-center gap-2 ${showDetails ? 'flex-col items-start' : ''}`}>
            <div
              className="flex items-center gap-2 px-3 py-1 bg-green-50 border border-green-500 text-green-700 text-xs rounded"
              title={`Chain of custody verified at ${verifiedAt?.toLocaleTimeString()}`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span className="font-semibold">VERIFIED</span>
            </div>

            {showDetails && result && (
              <div className="text-xs text-slate-600 mt-1">
                <p>Chain of Custody: Intact</p>
                <p>{result.total_entries} audit entries verified</p>
                <p className="text-slate-400">
                  Checked: {verifiedAt?.toLocaleString()}
                </p>
              </div>
            )}

            <button
              onClick={verifyIntegrity}
              className="text-xs text-blue-600 underline ml-2 hover:text-blue-700"
              title="Re-verify integrity"
            >
              Re-check
            </button>
          </div>
        );

      case 'failed':
        return (
          <div className={`flex items-center gap-2 ${showDetails ? 'flex-col items-start' : ''}`}>
            <div
              className="flex items-center gap-2 px-3 py-1 bg-red-50 border border-red-500 text-red-700 text-xs rounded"
              title="Integrity verification failed - possible tampering detected"
            >
              <ShieldAlert className="w-4 h-4" />
              <span className="font-semibold">INTEGRITY ALERT</span>
            </div>

            {showDetails && result && (
              <div className="text-xs text-red-600 mt-1">
                <p>Chain of Custody: BROKEN</p>
                {result.broken_at_sequence && (
                  <p>Break detected at entry #{result.broken_at_sequence}</p>
                )}
                {result.error_message && (
                  <p className="text-slate-600">{result.error_message}</p>
                )}
              </div>
            )}
          </div>
        );

      case 'error':
        return (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1 bg-amber-50 border border-amber-500 text-amber-700 text-xs rounded">
              <ShieldQuestion className="w-4 h-4" />
              <span>Check Failed</span>
            </div>
            <button
              onClick={verifyIntegrity}
              className="text-xs text-blue-600 underline hover:text-blue-700"
            >
              Retry
            </button>
          </div>
        );
    }
  };

  return (
    <div className={`inline-flex ${className}`}>
      {renderBadge()}
    </div>
  );
}

/**
 * Compact version for table rows
 */
export function IntegrityIndicator({
  recordId,
  size = 'sm',
}: {
  recordId: string;
  size?: 'sm' | 'md';
}) {
  const [verified, setVerified] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(false);

  const checkIntegrity = async () => {
    setChecking(true);
    try {
      const response = await apiClient.get(`/api/v1/audit/verify/${recordId}`);
      setVerified(response.data?.is_valid ?? true);
    } catch {
      setVerified(null);
    } finally {
      setChecking(false);
    }
  };

  const iconSize = size === 'sm' ? 'w-4 h-4' : 'w-5 h-5';

  if (checking) {
    return <LoadingSpinner className={`${iconSize} text-slate-400`} />;
  }

  if (verified === null) {
    return (
      <button
        onClick={checkIntegrity}
        className="hover:opacity-75"
        title="Verify integrity"
      >
        <ShieldQuestion className={`${iconSize} text-slate-400`} />
      </button>
    );
  }

  return verified ? (
    <ShieldCheck
      className={`${iconSize} text-green-600`}
      title="Integrity verified"
    />
  ) : (
    <ShieldAlert
      className={`${iconSize} text-red-600`}
      title="Integrity alert - check audit log"
    />
  );
}

export default IntegrityBadge;
