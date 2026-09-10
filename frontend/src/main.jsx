import React, { Component } from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './styles.css';

class ErrorBoundary extends Component {
  state = { error: null };
  static getDerivedStateFromError(error) {
    return { error };
  }
  componentDidCatch(error) {
    console.error('Uncaught error:', error);
  }
  render() {
    if (this.state.error) {
      return (
        <div className="error-boundary">
          <h2>😵 Something went wrong</h2>
          <p className="muted">{String(this.state.error)}</p>
          <button onClick={() => window.location.reload()}>Reload the app</button>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
);
