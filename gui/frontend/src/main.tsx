import React from 'react';
import ReactDOM from 'react-dom/client';
import { HashRouter } from 'react-router-dom';
import App from './App';
import { ThemeProvider } from './lib/state/ThemeContext';
import { DataProvider } from './lib/state/DataContext';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <DataProvider>
        <HashRouter>
          <App />
        </HashRouter>
      </DataProvider>
    </ThemeProvider>
  </React.StrictMode>,
);
