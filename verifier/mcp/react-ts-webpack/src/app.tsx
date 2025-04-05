import React, { ReactElement } from 'react';
import { createRoot } from 'react-dom/client';

import './app.css';
import { BrowserRouter as Router, Route, Routes } from 'react-router-dom';

import { VerifyTee } from './components/verify-tee';
import { VerifyMCP } from './components/verify-mcp';

const container = document.getElementById('root');
const root = createRoot(container!);

root.render(<App />);

function App(): ReactElement {
  return (
    <Router>
      <div>
        <Routes>
          <Route path="/" element={<VerifyMCP />} />
          <Route path="/verify-tee" element={<VerifyTee />} />
          <Route path="/verify-mcp" element={<VerifyMCP />} />
        </Routes>
      </div>
    </Router>
  );
}
