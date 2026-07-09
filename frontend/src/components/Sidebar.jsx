import { Archive, Combine, FileCheck2, FileType2, FolderKanban, Images, Languages, Minimize2, Plane, Repeat2, SplitSquareHorizontal } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

const Sidebar = () => {
  const location = useLocation();
  const menuItems = [
    { id: 'home',           icon: <FolderKanban size={19} />, label: 'Bàn file',            desc: 'Tổng quan', path: '/' },
    { id: 'merge',          icon: <Combine size={19} />,      label: 'Gộp PDF',             desc: 'Ghép hồ sơ', path: '/tool/merge' },
    { id: 'compress',       icon: <Minimize2 size={19} />,    label: 'Nén PDF',             desc: 'Làm nhẹ file', path: '/tool/compress' },
    { id: 'split',          icon: <SplitSquareHorizontal size={19} />, label: 'Cắt PDF',    desc: 'Tách trang', path: '/tool/split' },
    { id: 'pdf-to-word',    icon: <FileType2 size={19} />,    label: 'PDF → Word',          desc: 'Chỉnh sửa', path: '/tool/pdf-to-word' },
    { id: 'word-to-pdf',    icon: <FileCheck2 size={19} />,   label: 'Word → PDF',          desc: 'Đóng gói', path: '/tool/word-to-pdf' },
    { id: 'pdf-to-image',   icon: <Images size={19} />,       label: 'PDF → Hình ảnh',      desc: 'Xuất trang', path: '/tool/pdf-to-image' },
    { id: 'image-to-pdf',   icon: <Archive size={19} />,      label: 'Hình ảnh → PDF',      desc: 'Gom ảnh', path: '/tool/image-to-pdf' },
    { id: 'convert-image',  icon: <Repeat2 size={19} />,      label: 'Chuyển đổi ảnh',      desc: 'Đổi định dạng', path: '/tool/convert-image' },
    { id: 'translate',      icon: <Languages size={19} />,    label: 'Dịch PDF',            desc: 'Việt - Anh', path: '/tool/translate' },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-mark"><Plane size={21} /></div>
        <div>
          <div className="sidebar-logo-title">Fly FILE</div>
          <div className="sidebar-logo-sub">File cockpit</div>
        </div>
      </div>
      <div className="sidebar-menu">
        <div className="sidebar-menu-head">
          <span>Menu</span>
          <small>Chọn trang xử lý</small>
        </div>
        {menuItems.map(item => (
          <Link to={item.path} key={item.id} className={`sidebar-item ${location.pathname === item.path ? 'active' : ''}`}>
            <div className="icon">{item.icon}</div>
            <div className="sidebar-item-copy">
              <div className="label">{item.label}</div>
              <span>{item.desc}</span>
            </div>
          </Link>
        ))}
      </div>
      <div className="sidebar-footer">
        <div className="sidebar-footer-glow" />
        <span>Sẵn sàng xử lý</span>
        <strong>PDF, Word, Image</strong>
      </div>
    </div>
  );
};

export default Sidebar;
