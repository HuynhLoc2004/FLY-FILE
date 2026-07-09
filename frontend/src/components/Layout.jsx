import { Menu, Sparkles } from 'lucide-react';
import Sidebar from './Sidebar';

const Layout = ({ children }) => {
  return (
    <div className="app-container">
      <Sidebar />
      <div className="main-content">
        <header className="top-header">
          <div className="top-header-left">
            <button className="mobile-menu-btn" aria-label="Mở menu">
              <Menu size={20} />
            </button>
            <div className="top-header-kicker">
              <Sparkles size={14} />
              Bộ công cụ PDF thông minh
            </div>
          </div>
          <div className="top-header-brand">Fly FILE</div>
        </header>
        {children}
      </div>
    </div>
  );
};

export default Layout;
