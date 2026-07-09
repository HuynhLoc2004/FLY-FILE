# Fly FILE Folder Index

Root: `D:\FlyImmagration-fix\Fly-FILE`

## Top-level

- `backend/` — FastAPI backend bê từ Smart-PDF, giữ endpoints xử lý PDF.
- `frontend/` — Vite React frontend, giao diện chỉnh theo phong cách Fly_PTE.
- `bruno/` — API request collection từ Smart-PDF.
- `.gitignore` — Loại trừ dependency, build output, env, cache.
- `README.md` — Hướng dẫn chạy và deploy.

## Backend

- `main.py` — API routes và FastAPI app.
- `requirements.txt` — Python dependencies.
- `services/pdf_merger.py` — Gộp PDF.
- `services/pdf_page_merger.py` — Gộp trang theo manifest.
- `services/pdf_compressor.py` — Nén PDF.
- `services/pdf_to_word.py` — Chuyển PDF sang DOCX.
- `services/translation/` — Pipeline dịch PDF và xuất DOCX.

## Frontend

- `package.json` — Scripts và dependencies.
- `vite.config.js` — Vite config.
- `src/App.jsx` — Routing.
- `src/pages/Home.jsx` — Trang tổng quan công cụ.
- `src/pages/ToolPage.jsx` — Điều phối workspace theo tool id.
- `src/components/*Workspace.jsx` — UI từng công cụ PDF.
- `src/components/Layout.jsx`, `Sidebar.jsx` — Shell giao diện Fly FILE.
- `src/index.css` — Theme và style workspace.
