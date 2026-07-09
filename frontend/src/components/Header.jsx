import { Crown } from 'lucide-react';

const Header = ({ title }) => {
  return (
    <div className="header">
      <div className="header-title">{title}</div>
      <div className="header-actions">
        <button className="btn btn-premium">
          <Crown size={16} /> Thử miễn phí
        </button>
        <button className="btn btn-outline">Đăng nhập</button>
      </div>
    </div>
  );
};

export default Header;
