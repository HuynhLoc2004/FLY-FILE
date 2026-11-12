import { useEffect, useRef, useState } from 'react';
import { Archive, ArrowUp, ChevronDown, Combine, FileCheck2, FileType2, FolderKanban, Images, Languages, Menu, Minimize2, PlaneTakeoff, Repeat2, Search, Sparkles, SplitSquareHorizontal, X } from 'lucide-react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';

const navItems = [
  { id: 'home', icon: <FolderKanban size={18} />, label: 'Bàn file', desc: 'Tổng quan', path: '/' },
  { id: 'merge', icon: <Combine size={18} />, label: 'Gộp PDF', desc: 'Ghép hồ sơ', path: '/tool/merge' },
  { id: 'compress', icon: <Minimize2 size={18} />, label: 'Nén PDF', desc: 'Làm nhẹ file', path: '/tool/compress' },
  { id: 'split', icon: <SplitSquareHorizontal size={18} />, label: 'Cắt PDF', desc: 'Tách trang', path: '/tool/split' },
  { id: 'pdf-to-word', icon: <FileType2 size={18} />, label: 'PDF → Word', desc: 'Chỉnh sửa', path: '/tool/pdf-to-word' },
  { id: 'word-to-pdf', icon: <FileCheck2 size={18} />, label: 'Word → PDF', desc: 'Đóng gói', path: '/tool/word-to-pdf' },
  { id: 'pdf-to-image', icon: <Images size={18} />, label: 'PDF → Hình ảnh', desc: 'Xuất trang', path: '/tool/pdf-to-image' },
  { id: 'image-to-pdf', icon: <Archive size={18} />, label: 'Ảnh → PDF', desc: 'Gom ảnh', path: '/tool/image-to-pdf' },
  { id: 'convert-image', icon: <Repeat2 size={18} />, label: 'Đổi ảnh', desc: 'Đổi định dạng', path: '/tool/convert-image' },
  { id: 'translate', icon: <Languages size={18} />, label: 'Dịch PDF', desc: 'Việt - Anh', path: '/tool/translate' },
];

const Layout = ({ children }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const moreMenuRef = useRef(null);
  const searchValue = new URLSearchParams(location.search).get('q') || '';

  useEffect(() => {
    const frameId = window.requestAnimationFrame(() => {
      setMenuOpen(false);
      setMoreOpen(false);
    });
    return () => window.cancelAnimationFrame(frameId);
  }, [location.pathname]);

  useEffect(() => {
    if (!moreOpen) return undefined;

    const handlePointerDown = (event) => {
      if (!moreMenuRef.current?.contains(event.target)) {
        setMoreOpen(false);
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        setMoreOpen(false);
      }
    };

    document.addEventListener('pointerdown', handlePointerDown);
    document.addEventListener('keydown', handleKeyDown);

    return () => {
      document.removeEventListener('pointerdown', handlePointerDown);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [moreOpen]);

  useEffect(() => {
    const handleScroll = () => {
      const top = window.scrollY || document.documentElement.scrollTop || document.querySelector('.main-content')?.scrollTop || 0;
      setShowScrollTop(top > 240);
    };

    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });
    const mainContent = document.querySelector('.main-content');
    if (mainContent) mainContent.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      window.removeEventListener('scroll', handleScroll);
      if (mainContent) mainContent.removeEventListener('scroll', handleScroll);
    };
  }, []);

  const updateToolSearch = (value) => {
    const query = value.trim();

    navigate({
      pathname: '/',
      search: query ? `?q=${encodeURIComponent(query)}` : '',
      hash: query ? 'tools' : '',
    }, { replace: true });
  };

  return (
    <div className="app-container">
      <div className="main-content">
        <header className={`top-header ${menuOpen ? 'menu-open' : ''}`}>
          <div className="top-header-brand-block">
            <NavLink to="/" className="top-header-logo" aria-label="Fly FILE">
              <span><PlaneTakeoff size={19} /></span>
              <strong>Fly FILE</strong>
            </NavLink>
            <div className="top-header-kicker">
              <Sparkles size={14} />
              File desk
            </div>
          </div>

          <nav className="header-nav" aria-label="Menu công cụ">
            {navItems.slice(0, 5).map((item) => (
              <NavLink
                to={item.path}
                key={item.id}
                className={({ isActive }) => `header-nav-item ${isActive ? 'active' : ''}`}
              >
                {item.icon}
                <span>{item.label}</span>
              </NavLink>
            ))}
            <div className={`header-nav-more ${moreOpen ? 'open' : ''}`} ref={moreMenuRef}>
              <button
                type="button"
                className="header-nav-more-btn"
                aria-expanded={moreOpen}
                aria-controls="header-more-menu"
                onClick={() => setMoreOpen((open) => !open)}
              >
                Thêm
                <ChevronDown size={15} />
              </button>
              <div className="header-nav-panel" id="header-more-menu">
                {navItems.slice(5).map((item) => (
                  <NavLink
                    to={item.path}
                    key={item.id}
                    className={({ isActive }) => `header-panel-item ${isActive ? 'active' : ''}`}
                    onClick={() => setMoreOpen(false)}
                  >
                    <span className="header-panel-icon">{item.icon}</span>
                    <span>
                      <strong>{item.label}</strong>
                      <small>{item.desc}</small>
                    </span>
                  </NavLink>
                ))}
              </div>
            </div>
          </nav>

          <div className="top-header-actions">
            <label className="top-header-search" aria-label="Tìm công cụ">
              <Search size={15} />
              <input
                type="search"
                value={searchValue}
                placeholder="Tìm công cụ"
                onChange={(event) => updateToolSearch(event.target.value)}
              />
              {searchValue && (
                <button
                  type="button"
                  aria-label="Xóa tìm kiếm"
                  onClick={() => updateToolSearch('')}
                >
                  <X size={14} />
                </button>
              )}
            </label>
            <button
              className="mobile-menu-btn"
              type="button"
              aria-label={menuOpen ? 'Đóng menu' : 'Mở menu'}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((open) => !open)}
            >
              {menuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </header>

        <div className={`mobile-nav-sheet ${menuOpen ? 'open' : ''}`}>
          <div className="mobile-nav-head">
            <span>Menu công cụ</span>
            <small>Chọn trang xử lý file</small>
          </div>
          <label className="mobile-nav-search" aria-label="Tìm công cụ">
            <Search size={16} />
            <input
              type="search"
              value={searchValue}
              placeholder="Tìm công cụ"
              onChange={(event) => updateToolSearch(event.target.value)}
            />
            {searchValue && (
              <button
                type="button"
                aria-label="Xóa tìm kiếm"
                onClick={() => updateToolSearch('')}
              >
                <X size={14} />
              </button>
            )}
          </label>
          <div className="mobile-nav-grid">
            {navItems.map((item) => (
              <NavLink
                to={item.path}
                key={item.id}
                className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => setMenuOpen(false)}
              >
                <span className="mobile-nav-icon">{item.icon}</span>
                <span>
                  <strong>{item.label}</strong>
                  <small>{item.desc}</small>
                </span>
              </NavLink>
            ))}
          </div>
        </div>

        {children}
      </div>
      <button
        className={`scroll-to-top-btn ${showScrollTop ? 'show' : ''}`}
        type="button"
        aria-label="Lên đầu trang"
        onClick={() => {
          window.scrollTo({ top: 0, behavior: 'smooth' });
          document.querySelector('.main-content')?.scrollTo({ top: 0, behavior: 'smooth' });
        }}
      >
        <ArrowUp size={20} strokeWidth={2.4} />
      </button>
    </div>
  );
};

export default Layout;
