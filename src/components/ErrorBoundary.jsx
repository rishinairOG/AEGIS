import React from 'react';

/**
 * Error Boundary to catch React render errors and show a fallback UI
 * instead of a blank screen. Wraps the root App in main.jsx.
 */
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[AEGIS] ErrorBoundary caught:', error, errorInfo?.componentStack);
  }

  render() {
    if (this.state.hasError) {
      const fallback = this.props.fallback;
      if (typeof fallback === 'function') {
        return fallback(this.state.error);
      }
      return (
        <div
          className="fixed inset-0 flex flex-col items-center justify-center bg-[#0a0a0f] text-cyan-400 p-8 font-mono"
          role="alert"
        >
          <h1 className="text-xl font-bold mb-2">Something went wrong</h1>
          <p className="text-sm text-gray-400 mb-4 max-w-lg text-center">
            {this.state.error?.message || 'An unexpected error occurred.'}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 rounded border border-cyan-500/50 hover:bg-cyan-500/10 transition-colors"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;
