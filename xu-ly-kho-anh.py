# -*- coding: utf-8 -*-
"""
Xử lý TOÀN BỘ bộ ảnh lưỡi TCM-Tongue (Dryad, DOI 10.5061/dryad.1c59zw48r) thành kho ảnh học tập.

CÀI ĐẶT (một lần):   pip install pillow

1) TẠO KHO ẢNH (chạy một lần, khoảng 15–40 phút tùy máy):
     python xu-ly-kho-anh.py tao "D:\\duong-dan\\shezhenv3 txt" "D:\\luong-y-picures"
   Kết quả trong D:\\luong-y-picures :
     anh/ab/xxxx.webp    bản xem (cạnh dài 560 px, ~20–30 KB/ảnh) cho mọi ảnh
     chi-tiet/xxxx.jpg   bản phóng to (cạnh dài 1000 px, màu giữ nguyên 4:4:4) – chỉ tạo khi được chọn
     danh-muc.json       danh mục: nhãn + khung vị trí của từng ảnh (dùng cho app)
     bao-cao.txt         số ảnh mỗi nhãn, ảnh lỗi bị loại, ảnh trùng
   Đưa cả thư mục lên repo GitHub mới tên "luong-y-picures" và bật Pages.

2b) TẠO BẢN PHÓNG TO theo mã ảnh:
     python xu-ly-kho-anh.py chitiet "D:\\luong-y-picures" "D:\\duong-dan\\goc" 05ab68d03a7c 652dab587ffb

2) TÌM ẢNH KHỚP CHÍNH XÁC cho bệnh án (chỉ lấy ảnh có ĐÚNG và ĐỦ các đặc điểm, không thừa nhãn):
     python xu-ly-kho-anh.py tim "D:\\luong-y-picures" ban-dai xi-ngan bach-thai
   In ra các ảnh phù hợp; thêm --chi-tiet để tạo luôn bản phóng to cho các ảnh đó.

Nguyên tắc: không chỉnh màu, không lọc làm đẹp (màu lưỡi là dữ kiện chẩn đoán).
"""
import sys, os, io, json, hashlib
from pathlib import Path
from PIL import Image
# Cửa sổ lệnh Windows mặc định không in được tiếng Việt -> ép UTF-8 để không bị dừng giữa chừng
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CANH_XEM, CL_XEM = 560, 75          # bản xem: WebP
CANH_CT, CL_CT = 1000, 85           # bản phóng to: JPEG 4:4:4 (giữ màu ở mép chấm đỏ, viền lưỡi)

# id YOLO -> (mã, tên Việt, nhóm loại trừ lẫn nhau, có trong giáo trình?)
NHAN = {
 0:("binh-thuong","Lưỡi bình thường","toan-the",True), 1:("bac-thai","Bác thai (rêu bong)","chat-reu",True),
 2:("hong-thiet","Hồng thiệt (lưỡi đỏ)","mau-luoi",True), 3:("tu-thiet","Tử thiệt (lưỡi tím)","mau-luoi",True),
 4:("ban-dai","Lưỡi bệu (bàn đại)","hinh",True), 5:("sau-bac","Lưỡi gầy mỏng","hinh",True),
 6:("diem-do","Điểm đỏ","dau-hieu",True), 7:("liet-van","Lưỡi nứt (liệt văn)","dau-hieu",True),
 8:("xi-ngan","Dấu răng (xỉ ngân)","dau-hieu",True), 9:("bach-thai","Rêu trắng","mau-reu",True),
 10:("hoang-thai","Rêu vàng","mau-reu",True), 11:("hac-thai","Rêu đen","mau-reu",True),
 12:("hoat-thai","Rêu trơn ướt (hoạt thai)","chat-reu",True),
 13:("than-lom","Vùng thận lõm","vung",False), 14:("than-loi","Vùng thận lồi","vung",False),
 15:("can-dom-lom","Vùng can đởm lõm","vung",False), 16:("can-dom-loi","Vùng can đởm lồi","vung",False),
 17:("ty-vi-lom","Vùng tỳ vị lõm","vung",False), 18:("tam-phe-lom","Vùng tâm phế lõm","vung",False),
 19:("tam-phe-loi","Vùng tâm phế lồi","vung",False),
}
MA = {v[0]: k for k, v in NHAN.items()}

def cap_anh_nhan(goc):
    for f in Path(goc).rglob("*.txt"):
        if f.parent.name.lower() != "labels": continue
        for d in (".jpg",".jpeg",".png",".JPG",".PNG",".JPEG"):
            a = f.parent.parent / "images" / (f.stem + d)
            if a.exists():
                yield a, f, f.parent.parent.name; break

def doc_khung(f):
    out = []
    for dong in f.read_text(encoding="utf-8", errors="ignore").splitlines():
        p = dong.split()
        if len(p) >= 5 and p[0].isdigit():
            out.append([int(p[0])] + [round(float(x), 4) for x in p[1:5]])
    return out

def luu(im, path, canh, fmt, q, icc=None):
    im = im.copy(); im.thumbnail((canh, canh), Image.LANCZOS)
    path.parent.mkdir(parents=True, exist_ok=True)
    kw = {"icc_profile": icc} if icc else {}          # giữ hồ sơ màu gốc để màu lưỡi không bị lệch
    if fmt == "webp": im.save(path, "WEBP", quality=q, method=4, **kw)
    else: im.save(path, "JPEG", quality=q, optimize=True, subsampling=0, **kw)

def thu_muc_con(h):
    return h[:2]   # chia 256 thư mục con để GitHub và máy tính duyệt nhanh

def tao(goc, ra):
    ra = Path(ra); (ra/"anh").mkdir(parents=True, exist_ok=True)
    danh_muc, loi, trung, dem, thay, xoay = [], [], 0, {k:0 for k in NHAN}, {}, []
    for i, (a, f, phan) in enumerate(cap_anh_nhan(goc), 1):
        try:
            raw = a.read_bytes(); h = hashlib.sha1(raw).hexdigest()[:12]
            if h in thay: trung += 1; continue
            im = Image.open(io.BytesIO(raw)); im.load()
            icc = im.info.get("icc_profile")
            try:
                huong = im.getexif().get(274, 1)
            except Exception:
                huong = 1
            if huong not in (1, None): xoay.append(a.name)   # ảnh có cờ xoay: báo để kiểm tra, không tự xoay (khung nhãn tính theo ảnh gốc)
            im = im.convert("RGB")
        except Exception as e:
            loi.append(f"{a.name}: {e}"); continue
        thay[h] = a.name
        khung = doc_khung(f)
        if not khung: loi.append(f"{a.name}: không có nhãn"); continue
        luu(im, ra/"anh"/thu_muc_con(h)/f"{h}.webp", CANH_XEM, "webp", CL_XEM, icc)
        for k in {b[0] for b in khung}: dem[k] = dem.get(k,0)+1
        danh_muc.append({"id":h,"goc":str(a.relative_to(goc)).replace("\\","/"),"phan":phan,"khung":khung})
        if i % 500 == 0: print(f"  đã xử lý {i} ảnh…")
    meta = {"nguon":"TCM-Tongue, Dryad DOI 10.5061/dryad.1c59zw48r",
            "nhan":{v[0]:{"ten":v[1],"nhom":v[2],"giao_trinh":v[3]} for v in NHAN.values()},
            "ma_so":{str(k):v[0] for k,v in NHAN.items()}, "anh":danh_muc}
    (ra/"danh-muc.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    dung = sum(p.stat().st_size for p in (ra/"anh").rglob("*.webp"))
    bc = [f"Ảnh dùng được: {len(danh_muc)} | trùng bỏ: {trung} | lỗi: {len(loi)} | dung lượng bản xem: {dung/1e6:.0f} MB", ""]
    bc += [f"{NHAN[k][1]:32s} {dem.get(k,0):5d}" + ("" if NHAN[k][3] else "   (ngoài giáo trình – tham khảo)") for k in NHAN]
    bc += ["", f"Ảnh có cờ xoay EXIF (cần mở xem thử vài ảnh): {len(xoay)}"] + xoay[:50]
    bc += ["", "Ảnh lỗi:"] + loi
    (ra/"bao-cao.txt").write_text("\n".join(bc), encoding="utf-8")
    (ra/"goc-duong-dan.txt").write_text(str(Path(goc).resolve()), encoding="utf-8")
    print("\n".join(bc[:len(NHAN)+2]))
    print(f"\nXong. Kho ảnh ở: {ra}")

def tim(kho, ma_can, chi_tiet=False):
    kho = Path(kho); meta = json.loads((kho/"danh-muc.json").read_text(encoding="utf-8"))
    can = {MA[m] for m in ma_can if m in MA}
    sai = [m for m in ma_can if m not in MA]
    if sai: print("Mã không đúng:", sai, "\nCác mã:", ", ".join(MA)); return
    khop = [a for a in meta["anh"] if {b[0] for b in a["khung"]} == can]
    print(f"{len(khop)} ảnh có ĐÚNG và ĐỦ: {', '.join(NHAN[k][1] for k in sorted(can))}")
    for a in khop[:40]: print(" ", a["id"], a["goc"])
    if chi_tiet and khop:
        goc = Path((kho/"goc-duong-dan.txt").read_text(encoding="utf-8"))
        n = 0
        for a in khop[:40]:
            p = goc / a["goc"]
            if p.exists():
                im = Image.open(p); icc = im.info.get("icc_profile")
                luu(im.convert("RGB"), kho/"chi-tiet"/f"{a['id']}.jpg", CANH_CT, "jpg", CL_CT, icc); n += 1
        print(f"Đã tạo {n} bản phóng to trong thư mục chi-tiet/")

def chitiet(kho, goc, ids):
    """Tạo bản phóng to cho các ảnh theo mã (dùng khi soạn bệnh án)."""
    kho, goc = Path(kho), Path(goc)
    meta = json.loads((kho/"danh-muc.json").read_text(encoding="utf-8"))
    theo_id = {a["id"]: a for a in meta["anh"]}
    n = 0
    for i in ids:
        a = theo_id.get(i)
        if not a: print("Không có mã:", i); continue
        p = goc / a["goc"]
        if not p.exists(): print("Không thấy ảnh gốc:", a["goc"]); continue
        im = Image.open(p); icc = im.info.get("icc_profile")
        luu(im.convert("RGB"), kho/"chi-tiet"/f"{i}.jpg", CANH_CT, "jpg", CL_CT, icc)
        n += 1
    print(f"Đã tạo {n} bản phóng to.")

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "tao": tao(sys.argv[2], sys.argv[3])
    elif len(sys.argv) >= 5 and sys.argv[1] == "chitiet": chitiet(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif len(sys.argv) >= 4 and sys.argv[1] == "tim": tim(sys.argv[2], [x for x in sys.argv[3:] if not x.startswith("--")], "--chi-tiet" in sys.argv)
    else: print(__doc__)
