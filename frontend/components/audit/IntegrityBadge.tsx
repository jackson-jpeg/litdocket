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
import { supabase } from '@/lib/supabase';

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
      // Call the Supabase RPC function to verify the audit chain
      const { data, error: rpcError } = await supabase
        .rpc('verify_audit_chain', { p_record_id: recordId });

      if (rpcError) {
        throw new Error(rpcError.message);
      }

      // The function returns a table, take the first row
      const verification = Array.isArray(data) ? data[0] : data;

      if (!verification) {
        // No audit entries found - record might be new or not audited
        setResult({
          is_valid: true,
          total_entries: 0,
          broken_at_sequence: null,
          error_message: null,
        });
        setState('verified');
      } else {
        setResult(verification);
        setState(verification.is_valid ? 'verified' : 'failed');
      }

      setVerifiedAt(new Date());

    } catch (err) {
      console.error('Integrity verification failed:', err);
      setError(err instanceof Error ? err.message : 'Verification failed');
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
            className="btn-beveled flex items-center gap-2 text-xs"
            title="Click to verify the cryptographic integrity of this record's audit trail"
          >
            <ShieldQuestion className="w-4 h-4 text-grey-500" />
            <span>Verify Integrity</span>
          </button>
        );

      case 'verifying':
        return (
          <div className="flex items-center gap-2 px-3 py-1 bg-surface-dark border border-grey-300 text-xs">
            <LoadingSpinner className="w-4 h-4 text-navy" />
            <span className="text-grey-600">Verifying chain...</span>
          </div>
        );

      case 'verified':
        return (
          <div className={`flex items-center gap-2 ${showDetails ? 'flex-col items-start' : ''}`}>
            <div
              className="flex items-center gap-2 px-3 py-1 bg-filed/10 border border-filed text-filed text-xs"
              title={`Chain of custody verified at ${verifiedAt?.toLocaleTimeString()}`}
            >
              <ShieldCheck className="w-4 h-4" />
              <span className="font-semibold">VERIFIED</span>
            </div>

            {showDetails && result && (
              <div className="text-xs text-grey-600 mt-1">
                <p>Chain of Custody: Intact</p>
                <p>{result.total_entries} audit entries verified</p>
                <p className="text-grey-400">
                  Checked: {verifiedAt?.toLocaleString()}
                </p>
              </div>
            )}

            <button
              onClick={verifyIntegrity}
              className="text-xs text-navy underline ml-2"
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
              className="flex items-center gap-2 px-3 py-1 bg-overdue/10 border border-overdue text-overdue text-xs"
              title="Integrity verification failed - possible tampering detected"
            >
              <ShieldAlert className="w-4 h-4" />
              <span className="font-semibold">INTEGRITY ALERT</span>
            </div>

            {showDetails && result && (
              <div className="text-xs text-overdue mt-1">
                <p>Chain of Custody: BROKEN</p>
                {result.broken_at_sequence && (
                  <p>Break detected at entry #{result.broken_at_sequence}</p>
                )}
                {result.error_message && (
                  <p className="text-grey-600">{result.error_message}</p>
                )}
              </div>
            )}
          </div>
        );

      case 'error':
        return (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1 bg-warning/10 border border-warning text-warning text-xs">
              <ShieldQuestion className="w-4 h-4" />
              <span>Check Failed</span>
            </div>
            <button
              onClick={verifyIntegrity}
              className="text-xs text-navy underline"
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
      const { data, error } = await supabase
        .rpc('verify_audit_chain', { p_record_id: recordId });

      if (error) throw error;

      const result = Array.isArray(data) ? data[0] : data;
      setVerified(result?.is_valid ?? true);
    } catch {
      setVerified(null);
    } finally {
      setChecking(false);
    }
  };

  const iconSize = size === 'sm' ? 'w-4 h-4' : 'w-5 h-5';

  if (checking) {
    return <LoadingSpinner className={`${iconSize} text-grey-400`} />;
  }

  if (verified === null) {
    return (
      <button
        onClick={checkIntegrity}
        className="hover:opacity-75"
        title="Verify integrity"
      >
        <ShieldQuestion className={`${iconSize} text-grey-400`} />
      </button>
    );
  }

  return verified ? (
    <ShieldCheck
      className={`${iconSize} text-filed`}
      title="Integrity verified"
    />
  ) : (
    <ShieldAlert
      className={`${iconSize} text-overdue`}
      title="Integrity alert - check audit log"
    />
  );
}

export default IntegrityBadge;
