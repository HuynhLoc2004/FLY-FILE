import { useEffect, useMemo, useState } from 'react';
import { Archive, ArrowLeft, ArrowRight, CheckCircle2, ChevronDown, Combine, FileCheck2, FileType2, Images, Languages, Minimize2, Repeat2, ShieldCheck, SplitSquareHorizontal, Wand2, Zap } from 'lucide-react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const heroImages = [
  {
    src: '/pdf-logo.svg',
    title: 'PDF',
    bg: '#172338',
    panel: '#24506f',
    label: 'Gộp, cắt, nén PDF',
    desc: 'Dọn file PDF thành bộ hồ sơ sạch, nhẹ và dễ gửi.',
  },
  {
    src: '/word-logo.svg',
    title: 'WORD',
    bg: '#1d2542',
    panel: '#344b82',
    label: 'Chuyển đổi Word',
    desc: 'Đổi qua lại giữa Word và PDF để chỉnh sửa nhanh hơn.',
  },
  {
    src: '/icon-page.svg',
    title: 'FILE',
    bg: '#102f33',
    panel: '#1f6f75',
    label: 'Sắp xếp hồ sơ',
    desc: 'Gom ảnh, trang và tài liệu vào cùng một luồng xử lý.',
  },
];

const tools = [
  { id: 'merge', title: 'Gộp PDF', desc: 'Xếp nhiều file vào một bộ hồ sơ gọn gàng.', icon: <Combine size={20} />, color: '#0ea5e9' },
  { id: 'compress', title: 'Nén PDF', desc: 'Làm nhẹ file trước khi gửi hoặc upload.', icon: <Minimize2 size={20} />, color: '#14b8a6' },
  { id: 'split', title: 'Cắt PDF', desc: 'Tách trang, lấy phần cần dùng trong vài bước.', icon: <SplitSquareHorizontal size={20} />, color: '#f97316' },
  { id: 'pdf-to-word', title: 'PDF sang Word', desc: 'Đưa nội dung PDF về DOCX dễ chỉnh sửa.', icon: <FileType2 size={20} />, color: '#6366f1' },
  { id: 'word-to-pdf', title: 'Word sang PDF', desc: 'Đóng gói DOCX thành PDF ổn định.', icon: <FileCheck2 size={20} />, color: '#059669' },
  { id: 'pdf-to-image', title: 'PDF sang Hình ảnh', desc: 'Xuất từng trang thành ảnh rõ nét.', icon: <Images size={20} />, color: '#eab308' },
  { id: 'image-to-pdf', title: 'Hình ảnh sang PDF', desc: 'Gom ảnh giấy tờ thành một file PDF.', icon: <Archive size={20} />, color: '#ec4899' },
  { id: 'convert-image', title: 'Chuyển đổi ảnh', desc: 'Đổi định dạng JPG, PNG, WEBP nhanh.', icon: <Repeat2 size={20} />, color: '#8b5cf6' },
  { id: 'translate', title: 'Dịch PDF', desc: 'Dịch tài liệu Việt - Anh cho hồ sơ.', icon: <Languages size={20} />, color: '#0284c7' },
];

const highlights = [
  { icon: <Zap size={18} />, title: 'Nhanh', desc: 'Thả file, xử lý, tải về trong một luồng gọn.' },
  { icon: <ShieldCheck size={18} />, title: 'Sạch', desc: 'Giao diện ít nhiễu, tập trung vào tài liệu.' },
  { icon: <Wand2 size={18} />, title: 'Đủ dùng', desc: 'PDF, Word, ảnh và dịch tài liệu nằm cùng chỗ.' },
];

const workflowSteps = ['Chọn công cụ', 'Thả tài liệu', 'Kiểm tra kết quả', 'Tải file về'];

const normalizeText = (value) => value
  .toLowerCase()
  .normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '')
  .replace(/đ/g, 'd');

const Home = () => {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeIndex, setActiveIndex] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const toolQuery = searchParams.get('q') || '';

  useEffect(() => {
    heroImages.forEach((item) => {
      const image = new Image();
      image.src = item.src;
    });
  }, []);

  useEffect(() => {
    let frameId = 0;
    const syncViewport = () => {
      window.cancelAnimationFrame(frameId);
      frameId = window.requestAnimationFrame(() => setIsMobile(window.innerWidth < 640));
    };
    syncViewport();
    window.addEventListener('resize', syncViewport);
    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener('resize', syncViewport);
    };
  }, []);

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion) return undefined;

    const timer = window.setInterval(() => {
      if (document.hidden) return;
      setActiveIndex((current) => (current + 1) % heroImages.length);
    }, isMobile ? 6200 : 4800);

    return () => window.clearInterval(timer);
  }, [isMobile]);

  useEffect(() => {
    if (!toolQuery) return;

    window.requestAnimationFrame(() => {
      document.getElementById('tools')?.scrollIntoView({ block: 'start' });
    });
  }, [toolQuery]);

  const roles = useMemo(() => ({
    center: activeIndex,
    left: (activeIndex + heroImages.length - 1) % heroImages.length,
    right: (activeIndex + 1) % heroImages.length,
  }), [activeIndex]);

  const filteredTools = useMemo(() => {
    const query = normalizeText(toolQuery.trim());
    if (!query) return tools;

    return tools.filter((tool) => normalizeText([
      tool.id,
      tool.title,
      tool.desc,
    ].join(' ')).includes(query));
  }, [toolQuery]);

  const clearToolSearch = () => {
    setSearchParams({}, { replace: true });
  };

  const navigateHero = (direction) => {
    if (isAnimating) return;

    setIsAnimating(true);
    setActiveIndex((current) => {
      if (direction === 'next') return (current + 1) % heroImages.length;
      return (current + heroImages.length - 1) % heroImages.length;
    });

    window.setTimeout(() => setIsAnimating(false), isMobile ? 360 : 560);
  };

  const getHeroImageStyle = (index) => {
    const base = {
      transition: isMobile
        ? 'transform 360ms cubic-bezier(0.4,0,0.2,1), opacity 360ms cubic-bezier(0.4,0,0.2,1)'
        : 'transform 560ms cubic-bezier(0.4,0,0.2,1), opacity 560ms cubic-bezier(0.4,0,0.2,1), left 560ms cubic-bezier(0.4,0,0.2,1), bottom 560ms cubic-bezier(0.4,0,0.2,1), height 560ms cubic-bezier(0.4,0,0.2,1)',
      willChange: 'transform, opacity',
    };

    if (index === roles.center) {
      return {
        ...base,
        left: '50%',
        bottom: isMobile ? '24%' : '2%',
        height: isMobile ? '50%' : '74%',
        transform: `translateX(-50%) rotateY(0deg) rotateX(0deg) scale(${isMobile ? 1.14 : 1.28})`,
        opacity: 1,
        zIndex: 20,
      };
    }

    if (index === roles.left) {
      return {
        ...base,
        left: isMobile ? '22%' : '30%',
        bottom: isMobile ? '35%' : '16%',
        height: isMobile ? '19%' : '30%',
        transform: 'translateX(-50%) rotateY(42deg) rotateZ(-7deg) scale(0.92)',
        opacity: 0.82,
        zIndex: 10,
      };
    }

    return {
      ...base,
      left: isMobile ? '78%' : '70%',
      bottom: isMobile ? '35%' : '16%',
      height: isMobile ? '19%' : '30%',
      transform: 'translateX(-50%) rotateY(-42deg) rotateZ(7deg) scale(0.92)',
      opacity: 0.82,
      zIndex: 10,
    };
  };

  return (
    <div className="home-page">
      <section
        id="hero"
        className="file-hero"
        style={{ backgroundColor: heroImages[activeIndex].bg }}
      >
        <div className="file-hero-grain" />
        <div className="file-hero-brand">Fly FILE</div>
        <div className="file-hero-ghost">FILE DESK</div>
        <div className="file-hero-runner" aria-hidden="true">
          <span>PDF WORD FILE</span>
          <span>Sắp xếp hồ sơ</span>
          <span>PDF WORD FILE</span>
          <span>Gom ảnh nhanh</span>
          <span>PDF WORD FILE</span>
          <span>Dịch tài liệu</span>
        </div>
        <div className="file-hero-orbit file-hero-orbit-one" />
        <div className="file-hero-orbit file-hero-orbit-two" />
        <div
          className="file-hero-panel"
          style={{ backgroundColor: heroImages[activeIndex].panel }}
        />

        <div className="file-hero-carousel" aria-label="Banner công cụ file">
          {heroImages.map((item, index) => (
            <div
              className="file-hero-image-wrap"
              key={item.src}
              style={getHeroImageStyle(index)}
            >
              <img src={item.src} alt={item.label} draggable="false" />
              <span>{item.title}</span>
            </div>
          ))}
        </div>

        <div className="file-hero-copy">
          <div className="file-hero-copy-track" key={heroImages[activeIndex].title}>
            <p className="file-hero-kicker">{heroImages[activeIndex].label}</p>
            <h1>Xử lý tài liệu nhanh, nhìn vào là muốn làm.</h1>
            <p className="file-hero-desc">
              {heroImages[activeIndex].desc} Một bàn làm việc tiếng Việt cho PDF, Word, hình ảnh và hồ sơ dịch thuật.
            </p>
          </div>
          <div className="file-hero-nav" aria-label="Điều khiển banner">
            <button type="button" onClick={() => navigateHero('prev')} aria-label="Ảnh trước">
              <ArrowLeft size={26} strokeWidth={2.25} />
            </button>
            <button type="button" onClick={() => navigateHero('next')} aria-label="Ảnh tiếp theo">
              <ArrowRight size={26} strokeWidth={2.25} />
            </button>
          </div>
          <div className="file-hero-dots" aria-label="Trạng thái banner">
            {heroImages.map((item, index) => (
              <button
                type="button"
                key={item.title}
                className={index === activeIndex ? 'active' : ''}
                onClick={() => setActiveIndex(index)}
                aria-label={`Chọn ${item.title}`}
              />
            ))}
          </div>
        </div>

        <button className="file-hero-cta" type="button" onClick={() => document.getElementById('tools')?.scrollIntoView({ behavior: 'smooth' })}>
          Xem công cụ
          <ArrowRight size={28} strokeWidth={2.25} />
        </button>

        <div className="file-hero-scroll-cue" aria-hidden="true">
          <span>Lướt xuống</span>
          <ChevronDown size={20} />
        </div>
      </section>

      <section className="page-container home-tools-section" id="tools">
        <div className="home-section-head">
          <div>
            <p>Công cụ chính</p>
            <h2>{toolQuery ? `Kết quả cho "${toolQuery}"` : 'Chọn việc cần làm với file'}</h2>
          </div>
          <div className="home-section-actions">
            {toolQuery && (
              <button className="home-search-clear" type="button" onClick={clearToolSearch}>
                Xóa lọc
              </button>
            )}
            <button
              className="home-scroll-top"
              type="button"
              onClick={() => document.getElementById('hero')?.scrollIntoView({ behavior: 'smooth' })}
            >
              <ArrowLeft size={16} />
              Lên banner
            </button>
            <div className="home-section-chip">
              <CheckCircle2 size={16} />
              {filteredTools.length}/{tools.length} công cụ
            </div>
          </div>
        </div>
        {filteredTools.length > 0 ? (
          <div className="tool-grid">
            {filteredTools.map(tool => (
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
        ) : (
          <div className="home-empty-tools">
            <strong>Không tìm thấy công cụ phù hợp.</strong>
            <span>Thử tìm bằng PDF, Word, ảnh, nén, cắt, gộp hoặc dịch.</span>
          </div>
        )}
      </section>

      <section className="page-container home-flow-section">
        <div className="home-highlight-grid">
          {highlights.map((item) => (
            <div className="home-highlight" key={item.title}>
              <div>{item.icon}</div>
              <strong>{item.title}</strong>
              <span>{item.desc}</span>
            </div>
          ))}
        </div>

        <div className="home-workflow">
          <div>
            <p className="home-workflow-label">Quy trình</p>
            <h2>Một đường thẳng từ file thô đến file hoàn chỉnh.</h2>
          </div>
          <div className="home-workflow-steps">
            {workflowSteps.map((step, index) => (
              <div className="home-workflow-step" key={step}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                {step}
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
};

export default Home;
