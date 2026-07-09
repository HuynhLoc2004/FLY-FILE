import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import Layout from './components/Layout';
import Home from './pages/Home';
import CursorFollower from './components/CursorFollower';

const ToolPage = lazy(() => import('./pages/ToolPage'));

function App() {
  return (
    <Router>
      <CursorFollower />
      <Layout>
        <Suspense fallback={<div className="loading-mini-card route-loading-card">Đang mở trang...</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/tool/:toolId" element={<ToolPage />} />
          </Routes>
        </Suspense>
      </Layout>
    </Router>
  );
}

export default App;
