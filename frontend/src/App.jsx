import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import Layout from './components/Layout';
import Home from './pages/Home';
import CursorFollower from './components/CursorFollower';

const ToolPage = lazy(() => import('./pages/ToolPage'));

const AppContent = () => {
  const location = useLocation();
  const showCursorFollower = location.pathname === '/';
  
  return (
    <>
      {showCursorFollower && <CursorFollower />}
      <Layout>
        <Suspense fallback={<div className="loading-mini-card route-loading-card">Đang mở trang...</div>}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/tool/:toolId" element={<ToolPage />} />
          </Routes>
        </Suspense>
      </Layout>
    </>
  );
};

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;
