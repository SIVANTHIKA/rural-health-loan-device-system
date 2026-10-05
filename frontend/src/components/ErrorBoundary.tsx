import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertOctagon, RefreshCw, Home } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

/**
 * Clinical Operational Error Boundary
 *
 * Catches unhandled JavaScript runtime exceptions anywhere in the child component tree,
 * logs the diagnostic context safely, and displays an accessible, non-technical fallback UI.
 * Prevents full-screen application crashes during clinical field workflows.
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      error,
      errorInfo: null,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // Capture diagnostic information for local debugging
    this.setState({ errorInfo });
    // In production, diagnostic telemetry can be routed to audit logging service
    console.error('ErrorBoundary captured runtime UI failure:', error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  handleReload = (): void => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div className="min-h-[400px] flex items-center justify-center p-6">
          <div className="max-w-lg w-full bg-slate-900 border border-rose-500/40 rounded-2xl p-6 sm:p-8 shadow-2xl text-center space-y-6">
            <div className="w-14 h-14 mx-auto rounded-full bg-rose-500/10 border border-rose-500/30 flex items-center justify-center text-rose-400">
              <AlertOctagon className="w-8 h-8 animate-pulse" />
            </div>

            <div className="space-y-2">
              <h2 className="text-lg font-bold text-white tracking-wide">
                {this.props.fallbackTitle || 'Interface Rendering Notice'}
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                An unexpected display error occurred while rendering this view. Your return check-in data in the backend database remains safe and intact.
              </p>
            </div>

            {/* Sanitized Error Detail for Field Staff */}
            <div className="bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-left">
              <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                Diagnostic Identifier
              </span>
              <p className="text-xs font-mono text-rose-300 break-words">
                {this.state.error?.name || 'RuntimeError'}: {this.state.error?.message || 'Component failed to render.'}
              </p>
            </div>

            {/* Actionable Recovery Controls */}
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
              <button
                onClick={this.handleReset}
                className="w-full sm:w-auto px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl flex items-center justify-center gap-2 transition-all border border-slate-700"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Retry View</span>
              </button>

              <button
                onClick={this.handleReload}
                className="w-full sm:w-auto px-5 py-2.5 bg-teal-500 hover:bg-teal-400 text-slate-950 text-xs font-bold rounded-xl flex items-center justify-center gap-2 transition-all shadow-lg shadow-teal-500/20"
              >
                <Home className="w-4 h-4" />
                <span>Reload Application</span>
              </button>
            </div>

            <p className="text-[10px] text-slate-500">
              Rural Health Loan-Device System • Client Resilience Error Boundary
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
