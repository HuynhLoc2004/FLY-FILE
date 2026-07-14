# Fly FILE

Fly FILE là workspace xử lý PDF được chuyển từ Smart-PDF, giữ nguyên backend FastAPI và làm mới frontend theo phong cách Fly_PTE.

## Chạy local

Mở 2 terminal riêng:

### Backend

```bash
cd backend
.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## Biến môi trường

Tạo `backend/.env` nếu cần:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODELS=gemini-2.5-pro,gemini-2.5-flash
DEEPL_API_KEY=your_key_here
```

`GEMINI_API_KEY` là bắt buộc cho chức năng Dịch PDF. Sau khi sửa `.env`, hãy
khởi động lại backend để nạp cấu hình mới.

Frontend dùng `VITE_API_URL` để trỏ tới backend khi deploy:

```env
VITE_API_URL=https://your-backend-url
```

## Chức năng

| Công cụ | API |
|---|---|
| Gộp PDF | `/api/merge`, `/api/merge-pages` |
| Nén PDF | `/api/compress` |
| Cắt PDF | `/api/split` |
| PDF sang Word | `/api/pdf-to-word` |
| Word sang PDF | `/api/word-to-pdf` |
| PDF sang hình ảnh | `/api/pdf-to-images` |
| Hình ảnh sang PDF | `/api/images-to-pdf` |
| Chuyển đổi ảnh | `/api/convert-image` |
| Dịch PDF | `/api/translate-pdf/html` |
