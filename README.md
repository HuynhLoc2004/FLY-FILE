# Fly FILE - Intelligent PDF Suite & AI Translation Platform

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_18-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Python](https://img.shields.io/badge/Python_3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Google Gemini](https://img.shields.io/badge/Google_Gemini_AI-4285F4?style=for-the-badge&logo=google&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

**Nền tảng xử lý tài liệu số và dịch thuật công chứng thông minh với AI giữ nguyên định dạng layout.**

[Tính Năng](#-tính-năng-nổi-bật) • [Kiến Trúc](#-kiến-trúc-hệ-thống) • [Cài Đặt & Khởi Chạy](#-cài-đặt--khởi-chạy) • [API Documentation](#-api-documentation) • [Điểm Nhấn Kỹ Thuật](#-điểm-nhấn-kỹ-thuật-trong-cv)

</div>

---

## 📖 Giới Thiệu Tổng Quan

**Fly FILE** là hệ thống xử lý tài liệu toàn diện được xây dựng nhằm giải quyết các bài toán số hóa hồ sơ, biên tập và dịch thuật tài liệu pháp lý, công chứng, du học, visa (như giấy khai sinh, đăng ký kết hôn, bảng điểm, hợp đồng lao động,...).

Điểm khác biệt cốt lõi của Fly FILE so với các công cụ thông thường là **pipeline dịch thuật tài liệu ứng dụng AI (Google Gemini Flash)** với khả năng bóc tách, tái tạo và bảo toàn nguyên vẹn cấu trúc giao diện (layout, bảng biểu, font size, căn chỉnh), kết hợp cùng trình soạn thảo song ngữ song song (dual-pane live editor) cho phép người dùng tùy chỉnh trước khi xuất file Word (`.docx`) hoặc PDF (`.pdf`).

---

## ✨ Tính Năng Nổi Bật

### 1. 🤖 AI Document Translation (Dịch thuật AI bảo toàn Layout)
- **OCR & Layout Extraction**: Trích xuất dữ liệu thông minh từ PDF dạng văn bản hoặc dạng scan (ảnh chụp) sử dụng PyMuPDF và Gemini Vision.
- **Visual Structure Preservation**: Chuyển đổi trang tài liệu sang cấu trúc HTML có phân cấp tọa độ, giữ nguyên cấu trúc bảng biểu, căn lề và định dạng.
- **Bilingual Continuous Viewer**: Giao diện cuộn liên tục hiển thị song song bản gốc và bản dịch tiếng Anh.
- **Live WYSIWYG Editor**: Trực tiếp chỉnh sửa câu từ, định dạng (in đậm, căn dòng) trên bản dịch trước khi tải về.
- **Multi-format Export**: Xuất bản dịch tức thì ra file `.docx` (Microsoft Word) hoặc `.pdf` chuẩn in ấn (qua WeasyPrint).

### 2. 🛠️ Bộ Công Cụ Thao Tác PDF Toàn Diện
| Công cụ | Mô tả | Endpoint API |
|---|---|---|
| **Gộp PDF (Merge PDF)** | Gộp nhiều file PDF thành một tài liệu duy nhất | `/api/merge` |
| **Gộp trang tùy chỉnh** | Chọn lọc, sắp xếp lại thứ tự từng trang từ nhiều file | `/api/merge-pages` |
| **Cắt & Xóa trang PDF** | Tách dải trang, loại bỏ các trang không cần thiết, tải về dưới dạng ZIP/PDF | `/api/split`, `/api/remove-pages` |
| **Xoay trang (Rotate PDF)** | Xoay hướng trang (90°, 180°, 270°) trực quan ngay trên trình duyệt | `/api/rotate-pages` |
| **Nén PDF (Compress PDF)** | Giảm dung lượng file với các mức nén linh hoạt mà vẫn giữ độ nét | `/api/compress` |
| **PDF sang Word** | Chuyển đổi PDF sang file `.docx` có thể chỉnh sửa | `/api/pdf-to-word` |
| **Word sang PDF** | Chuyển đổi tài liệu `.docx` sang định dạng `.pdf` | `/api/word-to-pdf` |
| **PDF sang Hình ảnh** | Render từng trang PDF thành ảnh chất lượng cao (PNG/JPG) | `/api/pdf-to-images` |
| **Hình ảnh sang PDF** | Đóng gói nhiều ảnh thành 1 file PDF | `/api/images-to-pdf` |
| **Chuyển đổi ảnh** | Chuyển đổi qua lại giữa các định dạng WebP, PNG, JPG,... | `/api/convert-image` |

---

## 🏗️ Kiến Trúc Hệ Thống

```
Fly-FILE/
├── backend/                        # FastAPI Backend
│   ├── main.py                     # API Routes & App initialization
│   ├── services/
│   │   ├── pdf_merger.py           # Core logic gộp PDF
│   │   ├── pdf_compressor.py       # Thuật toán nén PDF (Ghostscript/pikepdf)
│   │   ├── pdf_to_word.py          # Chuyển đổi PDF -> DOCX
│   │   └── translation/            # Pipeline Dịch thuật AI
│   │       ├── html_extractor.py   # Trích xuất layout PDF sang HTML
│   │       ├── html_translator.py  # Giao tiếp với Gemini AI & Throttling
│   │       ├── docx_builder.py     # Xuất kết quả sang Word
│   │       └── document_detector.py# Nhận diện loại văn bản pháp lý
│   └── tests/                      # Unit test suite (30+ test cases)
│
├── frontend/                       # React 18 + Vite Frontend
│   ├── src/
│   │   ├── pages/                  # Trang chính (Home, ToolPage)
│   │   ├── components/             # Workspace cho từng công cụ (Translate, Merge, Split,...)
│   │   ├── config/api.js           # API Client & Environment configuration
│   │   └── index.css               # Styling & Tailwind CSS
│   └── package.json
└── README.md
```

---

## 🚀 Cài Đặt & Khởi Chạy

### Yêu Cầu Môi Trường
- **Node.js**: v18+ & npm
- **Python**: v3.10+
- (Tùy chọn) Khóa API **Google Gemini** (cho tính năng Dịch AI)

### 1. Khởi Chạy Backend

```bash
cd backend

# Tạo và kích hoạt virtual environment
python -m venv .venv
# Trên Windows:
.venv\Scripts\activate
# Trên macOS/Linux:
source .venv/bin/activate

# Cài đặt thư viện
pip install -r requirements.txt

# Cấu hình biến môi trường
cp .env.example .env
# Điền GEMINI_API_KEY vào file .env vừa tạo

# Chạy server development
uvicorn main:app --reload --port 8000
```
> Swagger API Documentation mở tại: **http://localhost:8000/docs**

### 2. Khởi Chạy Frontend

```bash
cd frontend

# Cài đặt dependencies
npm install

# Khởi chạy dev server
npm run dev
```
> Truy cập ứng dụng tại: **http://localhost:5173**

---

## 🌐 Hướng Dẫn Deploy Production (Render + Vercel)

Dự án được cấu hình sẵn để deploy hoàn toàn miễn phí trên kiến trúc tách rời Frontend & Backend:

### Bước 1: Deploy Backend lên Render (Render.com)

1. Đăng nhập vào [Render.com](https://render.com) và chọn **New +** -> **Web Service** (hoặc dùng **Blueprints** liên kết tới file `render.yaml`).
2. Kết nối tới repository `HuynhLoc2004/FLY-FILE`.
3. Điền các thông số:
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Vào mục **Environment Variables** thêm các biến:
   - `GEMINI_API_KEY`: *(Khóa Gemini API của bạn)*
   - `GEMINI_MODELS`: `gemini-2.5-flash`
   - `CORS_ORIGINS`: `*` *(hoặc điền domain Vercel sau khi deploy)*
5. Bấm **Deploy**. Sau khi hoàn tất, copy URL backend được cấp (ví dụ: `https://fly-file-backend.onrender.com`).

### Bước 2: Deploy Frontend lên Vercel (Vercel.com)

1. Đăng nhập vào [Vercel.com](https://vercel.com) và chọn **Add New...** -> **Project**.
2. Chọn repository `HuynhLoc2004/FLY-FILE`.
3. Trong phần cấu hình dự án:
   - **Root Directory**: Chọn `frontend` (hoặc để mặc định, dự án đã có file `vercel.json` định tuyến SPA).
   - **Framework Preset**: `Vite` (Vercel sẽ tự động nhận diện).
4. Trong mục **Environment Variables**:
   - Thêm `VITE_API_URL` = URL backend Render vừa tạo ở Bước 1 (ví dụ: `https://fly-file-backend.onrender.com`).
5. Bấm **Deploy**. Trang web sẽ được phát hành chỉ sau 1 phút!

---

## 🎯 Điểm Nhấn Kỹ Thuật (CV Highlights)

- **Asynchronous & Streaming Pipeline**: Ứng dụng kiến trúc bất đồng bộ với FastAPI `StreamingResponse` giúp tối ưu dung lượng RAM khi xử lý các file tài liệu dung lượng lớn.
- **AI Rate Limiting & Concurrent Worker Throttling**: Thiết kế cơ chế điều tiết luồng gọi Gemini API song song (concurrency pool với queue và min interval) giúp xử lý đa trang mượt mà mà không bị giới hạn RPM (Requests Per Minute) hoặc Rate Limit Exceeded.
- **High-Fidelity Layout Reconstruction**: Kết hợp giữa PyMuPDF (`fitz`) phân tích tọa độ bounding-box và mô hình Gemini Vision đa phương thức để giải quyết bài toán dịch thuật các mẫu văn bản hành chính phức tạp (khai sinh, bảng điểm, sổ đỏ) mà các công cụ dịch thông thường bị vỡ khung.
- **Dual-Pane Real-Time Editor**: Trình xem và biên tập trang tài liệu liên tục với đồng bộ hóa thời gian thực (state sync qua onBlur và contentEditable), tối ưu hiệu năng render danh sách trang dài.
- **Automated Testing Suite**: Hơn 30 unit tests bao phủ các tình huống xử lý lỗi PDF, mock translation responses và cấu hình hệ thống.

---

## 👨‍💻 Tác Giả

- **Huỳnh Tấn Lộc**
- **GitHub**: [@HuynhLoc2004](https://github.com/HuynhLoc2004)
- **Repository**: [https://github.com/HuynhLoc2004/FLY-FILE](https://github.com/HuynhLoc2004/FLY-FILE)

---

## 📄 Bản Quyền & Giấy Phép

Dự án phát triển phục vụ mục đích học tập, nghiên cứu và làm hồ sơ năng lực (portfolio). Giấy phép mã nguồn mở MIT.
