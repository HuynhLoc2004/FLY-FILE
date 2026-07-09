import { Layers, FileArchive, Scissors, FileText, Image as ImageIcon, Languages, FileOutput, ArrowLeftRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const tools = [
  { id: 'merge', title: 'Gộp PDF', desc: 'Ghép nhiều PDF theo đúng thứ tự.', icon: <Layers size={20} />, color: '#e4a808' },
  { id: 'compress', title: 'Nén PDF', desc: 'Giảm dung lượng file để gửi nhanh hơn.', icon: <FileArchive size={20} />, color: '#ef4444' },
  { id: 'split', title: 'Cắt PDF', desc: 'Tách file theo trang hoặc khoảng trang.', icon: <Scissors size={20} />, color: '#8b5cf6' },
  { id: 'pdf-to-word', title: 'PDF sang Word', desc: 'Xuất nội dung PDF thành DOCX.', icon: <FileText size={20} />, color: '#3b82f6' },
  { id: 'word-to-pdf', title: 'Word sang PDF', desc: 'Chuyển DOCX thành PDF nhanh.', icon: <FileOutput size={20} />, color: '#0f766e' },
  { id: 'pdf-to-image', title: 'PDF sang Hình ảnh', desc: 'Xuất từng trang thành PNG hoặc JPG.', icon: <ImageIcon size={20} />, color: '#f59e0b' },
  { id: 'image-to-pdf', title: 'Hình ảnh sang PDF', desc: 'Ghép nhiều ảnh thành một file PDF.', icon: <FileText size={20} />, color: '#10b981' },
  { id: 'convert-image', title: 'Chuyển đổi ảnh', desc: 'Đổi JPG, PNG, WEBP.', icon: <ArrowLeftRight size={20} />, color: '#ec4899' },
  { id: 'translate', title: 'Dịch PDF', desc: 'Dịch PDF tiếng Việt sang tiếng Anh.', icon: <Languages size={20} />, color: '#2563eb' },
];

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="page-container">
      <section className="home-hero">
        <div>
          <div className="hero-eyebrow">Fly FILE</div>
          <h1>Trạm xử lý PDF cho hồ sơ, tài liệu và bản dịch.</h1>
          <p>
            Các công cụ từ Smart-PDF đã được đưa vào workspace mới với giao diện theo phong cách Fly_PTE.
          </p>
        </div>
        <div className="hero-status">
          <span>Backend</span>
          <strong>Smart-PDF API</strong>
          <small>Giữ nguyên endpoints để deploy lại dễ hơn.</small>
        </div>
      </section>

      <div className="section-title">Công cụ PDF</div>
      <div className="tool-grid">
        {tools.map(tool => (
          <div 
            key={tool.id} 
            className="tool-card"
            onClick={() => navigate(`/tool/${tool.id}`)}
          >
            <div className="tool-icon" style={{ backgroundColor: tool.color }}>
              {tool.icon}
            </div>
            <div>
              <div className="tool-title">{tool.title}</div>
              <div className="tool-desc">{tool.desc}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Home;
