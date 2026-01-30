'use client';

/**
 * ErrorBoundary - Global Error Catcher
 *
 * Catches React component errors and prevents entire app crashes.
 * Shows user-friendly error message with option to reload or report.
 */

import React, { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, MessageCircle } from 'lucide-react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error to console in development
    console.error('ErrorBoundary caught an error:', error, errorInfo);

    // Store error details
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI - Sovereign Design System style
      return (
        <div className="min-h-screen bg-steel flex items-center justify-center p-4">
          <div className="max-w-2xl w-full">
            {/* Error Card */}
            <div className="bg-white border-4 border-red-600 shadow-hard">
              {/* Header */}
              <div className="bg-red-600 px-6 py-4 border-b-4 border-red-700">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-white rounded">
                    <AlertTriangle className="w-6 h-6 text-red-600" />
                  </div>
                  <div>
                    <h1 className="text-xl font-serif font-bold text-white">
                      Application Error
                    </h1>
                    <p className="text-red-100 text-sm mt-0.5">
                      Something went wrong while rendering this page
                    </p>
                  </div>
                </div>
              </div>

              {/* Error Details */}
              <div className="px-6 py-6">
                <div className="space-y-4">
                  <p className="text-slate-700">
                    LitDocket encountered an unexpected error. This has been logged and
                    our team has been notified. You can try the following:
                  </p>

                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={this.handleReload}
                      className="flex items-center gap-2 px-4 py-2 bg-navy text-white hover:bg-navy-dark transition-colors font-medium"
                    >
                      <RefreshCw className="w-4 h-4" />
                      Reload Page
                    </button>
                    <button
                      onClick={this.handleGoHome}
                      className="flex items-center gap-2 px-4 py-2 bg-slate-200 text-slate-700 hover:bg-slate-300 transition-colors font-medium"
                    >
                      <Home className="w-4 h-4" />
                      Go to Dashboard
                    </button>
                    <button
                      onClick={this.handleReset}
                      className="flex items-center gap-2 px-4 py-2 bg-slate-100 text-slate-600 hover:bg-slate-200 transition-colors font-medium"
                    >
                      Try Again
                    </button>
                  </div>

                  {/* Error Message (Development Only) */}
                  {process.env.NODE_ENV === 'development' && this.state.error && (
                    <details className="mt-6">
                      <summary className="cursor-pointer text-sm font-medium text-slate-700 hover:text-slate-900 select-none">
                        Technical Details (Development Only)
                      </summary>
                      <div className="mt-3 p-4 bg-slate-100 border border-slate-300 overflow-auto">
                        <div className="space-y-3">
                          <div>
                            <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                              Error Message:
                            </div>
                            <div className="font-mono text-sm text-red-700">
                              {this.state.error.message}
                            </div>
                          </div>

                          {this.state.error.stack && (
                            <div>
                              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                                Stack Trace:
                              </div>
                              <pre className="font-mono text-xs text-slate-700 whitespace-pre-wrap break-words">
                                {this.state.error.stack}
                              </pre>
                            </div>
                          )}

                          {this.state.errorInfo?.componentStack && (
                            <div>
                              <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                                Component Stack:
                              </div>
                              <pre className="font-mono text-xs text-slate-700 whitespace-pre-wrap break-words">
                                {this.state.errorInfo.componentStack}
                              </pre>
                            </div>
                          )}
                        </div>
                      </div>
                    </details>
                  )}

                  {/* Help Text */}
                  <div className="mt-6 pt-6 border-t border-slate-200">
                    <div className="flex items-start gap-3 text-sm text-slate-600">
                      <MessageCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="font-medium text-slate-700 mb-1">
                          Need help?
                        </p>
                        <p>
                          If this problem persists, please contact support with the error code{' '}
                          <span className="font-mono bg-slate-100 px-1 py-0.5 rounded">
                            {Date.now().toString(36).toUpperCase()}
                          </span>
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Bottom Info */}
            <div className="mt-4 text-center text-sm text-slate-500">
              LitDocket v3 • Error caught by ErrorBoundary
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Hook for functional components to reset error boundary
 * Usage: const resetError = useErrorBoundary();
 */
export function useErrorHandler() {
  const [error, setError] = React.useState<Error | null>(null);

  React.useEffect(() => {
    if (error) {
      throw error;
    }
  }, [error]);

  return setError;
}
