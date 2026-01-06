/**
 * Complete Profile Page
 *
 * Collects additional user information after signup (firm, role, jurisdictions).
 */

'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Building2, Briefcase, MapPin, Loader2 } from 'lucide-react';
import { useAuth } from '@/lib/auth/auth-context';

const US_STATES = [
  'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
  'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
  'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
  'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
  'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
];

const ROLES = [
  { value: 'attorney', label: 'Attorney' },
  { value: 'paralegal', label: 'Paralegal' },
  { value: 'legal_assistant', label: 'Legal Assistant' },
  { value: 'law_clerk', label: 'Law Clerk' }
];

export default function CompleteProfilePage() {
  const router = useRouter();
  const { user, completeSignup } = useAuth();

  const [firmName, setFirmName] = useState('');
  const [role, setRole] = useState('attorney');
  const [selectedJurisdictions, setSelectedJurisdictions] = useState<string[]>(['FL']);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const toggleJurisdiction = (state: string) => {
    setSelectedJurisdictions(prev =>
      prev.includes(state)
        ? prev.filter(s => s !== state)
        : [...prev, state]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    if (selectedJurisdictions.length === 0) {
      setError('Please select at least one jurisdiction');
      setLoading(false);
      return;
    }

    try {
      await completeSignup({
        firm_name: firmName || undefined,
        role,
        jurisdictions: selectedJurisdictions
      });

      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to complete profile');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-slate-900">Complete your profile</h2>
        <p className="text-sm text-slate-600 mt-1">
          Help us customize your experience
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Firm Name */}
        <div>
          <label htmlFor="firm" className="block text-sm font-medium text-slate-700 mb-2">
            Law Firm / Organization <span className="text-slate-400">(Optional)</span>
          </label>
          <div className="relative">
            <Building2 className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              id="firm"
              type="text"
              value={firmName}
              onChange={(e) => setFirmName(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Smith & Associates"
            />
          </div>
        </div>

        {/* Role */}
        <div>
          <label htmlFor="role" className="block text-sm font-medium text-slate-700 mb-2">
            Your Role
          </label>
          <div className="relative">
            <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <select
              id="role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none"
            >
              {ROLES.map(r => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Jurisdictions */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-3">
            <MapPin className="inline w-4 h-4 mr-1" />
            Jurisdictions (Select all that apply)
          </label>
          <div className="grid grid-cols-5 gap-2 max-h-48 overflow-y-auto p-2 border border-slate-200 rounded-lg">
            {US_STATES.map(state => (
              <button
                key={state}
                type="button"
                onClick={() => toggleJurisdiction(state)}
                className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                  selectedJurisdictions.includes(state)
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
                }`}
              >
                {state}
              </button>
            ))}
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {selectedJurisdictions.length} jurisdiction{selectedJurisdictions.length !== 1 ? 's' : ''} selected
          </p>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 text-white py-3 rounded-lg font-medium hover:from-blue-700 hover:to-indigo-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Completing profile...
            </>
          ) : (
            'Continue to Dashboard'
          )}
        </button>
      </form>
    </div>
  );
}
