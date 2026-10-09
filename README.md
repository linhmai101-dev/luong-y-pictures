# Kho ảnh lưỡi cho app "YHCT 15 phút"

Ảnh được nén từ bộ dữ liệu TCM-Tongue (Gao Longfei và cộng sự), Dryad, DOI 10.5061/dryad.1c59zw48r.
Nội dung trên Dryad được cấp phép cho tái sử dụng (xem datadryad.org/terms).

- `anh/xx/<mã>.webp` – bản xem (560 px) của mọi ảnh
- `goc/xx/<mã>.jpg` – **ảnh gốc nguyên bản**, chép đúng từng byte từ bộ dữ liệu (chế độ mặc định `CHE_DO = "goc"`); app tự phóng vào vùng lưỡi
- `luoi/xx/<mã>.jpg` – bản cắt sát lưỡi lấy từ ảnh gốc (tối đa 900 px, JPEG 95, màu 4:4:4), chỉ tạo khi đặt `CHE_DO = "luoi"` (nhẹ hơn, dùng nếu kho vượt giới hạn dung lượng)
- `chi-tiet/<mã>.jpg` – bản phóng to (1000 px), chỉ cho ảnh dùng trong bài học, bệnh án
- `danh-muc.json` – nhãn và khung vị trí của từng ảnh
- `danh-muc-app.json` – bản gọn của danh mục, chỉ gồm trường app cần (app đọc bản này trước)
- `bao-cao.txt` – số ảnh mỗi nhãn, ảnh lỗi, ảnh có cờ xoay
- `sha256-ban-goc.txt` – mã kiểm tra file gốc đã tải

## Bản lưu trữ dữ liệu gốc
Lần đầu tải thành công, workflow tự cất bộ dữ liệu gốc vào mục **Releases → du-lieu-goc** (chia phần dưới 2 GB, kèm mã SHA256). Các lần chạy sau chọn nguồn `kho-luu-tru` (mặc định) để lấy từ đây, không phải tải lại từ Google Drive hay Dryad.
