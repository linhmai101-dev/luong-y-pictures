# -*- coding: utf-8 -*-
"""
Xử lý TOÀN BỘ bộ ảnh lưỡi TCM-Tongue (Dryad, DOI 10.5061/dryad.1c59zw48r) thành kho ảnh học tập.

CÀI ĐẶT (một lần):   pip install pillow

1) TẠO KHO ẢNH (chạy một lần, khoảng 15–40 phút tùy máy):
     python xu-ly-kho-anh.py tao "D:\\duong-dan\\shezhenv3 txt" "D:\\luong-y-pictures"
   Kết quả trong D:\\luong-y-pictures :
     anh/ab/xxxx.webp    bản xem (cạnh dài 560 px, ~20–30 KB/ảnh) cho mọi ảnh
     chi-tiet/xxxx.jpg   bản phóng to (cạnh dài 1000 px, màu giữ nguyên 4:4:4) – chỉ tạo khi được chọn
     danh-muc.json       danh mục: nhãn + khung vị trí của từng ảnh (dùng cho app)
     bao-cao.txt         số ảnh mỗi nhãn, ảnh lỗi bị loại, ảnh trùng
   Đưa cả thư mục lên repo GitHub mới tên "luong-y-pictures" và bật Pages.

2b) TẠO BẢN PHÓNG TO theo mã ảnh:
     python xu-ly-kho-anh.py chitiet "D:\\luong-y-pictures" "D:\\duong-dan\\goc" 05ab68d03a7c 652dab587ffb

2) TÌM ẢNH KHỚP CHÍNH XÁC cho bệnh án (chỉ lấy ảnh có ĐÚNG và ĐỦ các đặc điểm, không thừa nhãn):
     python xu-ly-kho-anh.py tim "D:\\luong-y-pictures" ban-dai xi-ngan bach-thai
   In ra các ảnh phù hợp; thêm --chi-tiet để tạo luôn bản phóng to cho các ảnh đó.

Nguyên tắc: không chỉnh màu, không lọc làm đẹp (màu lưỡi là dữ kiện chẩn đoán).
"""
import sys, os, io, json, hashlib
from pathlib import Path
from PIL import Image, ImageOps, ImageFilter, ImageStat
# Cửa sổ lệnh Windows mặc định không in được tiếng Việt -> ép UTF-8 để không bị dừng giữa chừng
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

CANH_XEM, CL_XEM = 560, 75          # bản xem cả khung: WebP
CANH_LUOI, CL_LUOI = 900, 80        # bản cắt sát lưỡi, lấy từ ảnh GỐC (không phóng to ảnh nhỏ)
LE_CAT = 0.12                       # lề quanh vùng các khung nhãn (giống app)
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

def vung_cat(khung):
    x0 = min(b[1]-b[3]/2 for b in khung); y0 = min(b[2]-b[4]/2 for b in khung)
    x1 = max(b[1]+b[3]/2 for b in khung); y1 = max(b[2]+b[4]/2 for b in khung)
    mx, my = (x1-x0)*LE_CAT, (y1-y0)*LE_CAT
    x0, y0, x1, y1 = max(0, x0-mx), max(0, y0-my), min(1, x1+mx), min(1, y1+my)
    return [round(x0,4), round(y0,4), round(x1-x0,4), round(y1-y0,4)]

LAPLACE = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1)
def do_net(im):
    """Độ nét: phương sai sau lọc Laplace, đo trên vùng lưỡi đã đưa về cùng cỡ để so sánh được."""
    # đưa về CÙNG cạnh dài 512 px (kể cả phóng ảnh nhỏ lên) để ảnh gốc độ phân giải thấp cũng bị chấm là kém nét
    g = im.convert("L"); k = 512 / max(g.size)
    g = g.resize((max(1, round(g.size[0]*k)), max(1, round(g.size[1]*k))), Image.BICUBIC)
    return round(ImageStat.Stat(g.filter(LAPLACE)).var[0], 1)

def _ma_hoa(viec):
    """Chạy trong tiến trình con: mở, kiểm tra, nén một ảnh.
    Trả về (lỗi, có_cờ_xoay, thông_tin) với thông_tin = {w,h,cat,net,lw,lh}."""
    duong_dan, ra_file, ra_luoi, khung = viec
    try:
        im = Image.open(duong_dan); im.load()
        # chỉ giữ hồ sơ màu khi ảnh gốc là RGB (hồ sơ CMYK gắn vào ảnh RGB sẽ làm sai màu)
        icc = im.info.get("icc_profile") if im.mode in ("RGB", "RGBA", "P", "L") else None
        try:
            huong = im.getexif().get(274, 1)
        except Exception:
            huong = 1
        # Khung nhãn của bộ dữ liệu được vẽ trên ảnh ĐÃ xoay đúng chiều theo cờ EXIF
        # (đã kiểm chứng bằng mắt trên ảnh thật), nên phải xoay ảnh theo cờ này.
        im = ImageOps.exif_transpose(im).convert("RGB")
        W, H = im.size
        luu(im, Path(ra_file), CANH_XEM, "webp", CL_XEM, icc)
        x, y, w, h = cat = vung_cat(khung)
        luoi = im.crop((round(x*W), round(y*H), round((x+w)*W), round((y+h)*H)))
        luu(luoi, Path(ra_luoi), CANH_LUOI, "webp", CL_LUOI, icc)      # thumbnail() không phóng to ảnh nhỏ
        return None, huong not in (1, None), {"w": W, "h": H, "cat": cat, "net": do_net(luoi), "lw": luoi.size[0], "lh": luoi.size[1]}
    except Exception as e:
        return str(e), False, None

def tao(goc, ra):
    import time
    from concurrent.futures import ProcessPoolExecutor
    t0 = time.time()
    goc, ra = Path(goc), Path(ra); (ra/"anh").mkdir(parents=True, exist_ok=True)
    danh_muc, loi, trung, dem, thay, xoay = [], [], 0, {k:0 for k in NHAN}, {}, []
    # Lượt 1 (nhanh, tuần tự): đọc nhãn, bỏ ảnh trùng, lập danh sách việc
    viec, ung_vien, nhan_cua, xung_dot = [], [], {}, {}
    for a, f, phan in sorted(cap_anh_nhan(goc), key=lambda x: str(x[0])):   # sắp xếp để kết quả luôn giống nhau
        try:
            h = hashlib.sha1(a.read_bytes()).hexdigest()[:12]
        except Exception as e:
            loi.append(f"{a.name}: {e}"); continue
        khung_tho = doc_khung(f)
        khung = [b for b in khung_tho if b[0] in NHAN]          # bỏ nhãn lạ ngoài 20 loại đã biết
        tap = frozenset(b[0] for b in khung)
        if h in thay:
            trung += 1
            if tap != nhan_cua[h]:                                # cùng một ảnh nhưng nhãn khác nhau
                xung_dot.setdefault(h, {thay[h]}).add(str(a.relative_to(goc)))
            continue
        thay[h] = str(a.relative_to(goc)); nhan_cua[h] = tap
        if len(khung) < len(khung_tho): loi.append(f"{a.name}: bỏ {len(khung_tho)-len(khung)} nhãn lạ")
        if not khung: loi.append(f"{a.name}: không có nhãn"); continue
        viec.append((str(a), str(ra/"anh"/thu_muc_con(h)/f"{h}.webp"), str(ra/"luoi"/thu_muc_con(h)/f"{h}.webp"), khung))
        ung_vien.append({"id":h,"goc":str(a.relative_to(goc)).replace("\\","/"),"phan":phan,"khung":khung})
    print(f"Tìm thấy {len(viec)} ảnh cần nén (trùng bỏ {trung}). Đang nén bằng {os.cpu_count()} nhân CPU…")
    # Lượt 2 (nặng, song song): nén ảnh
    with ProcessPoolExecutor() as ex:
        for i, (muc, (err, co_xoay, tt)) in enumerate(zip(ung_vien, ex.map(_ma_hoa, viec, chunksize=16)), 1):
            if err: loi.append(f"{muc['goc']}: {err}"); continue
            muc.update(tt)
            if co_xoay: xoay.append(muc["goc"])
            for k in {b[0] for b in muc["khung"]}: dem[k] = dem.get(k,0)+1
            if muc["id"] in xung_dot: muc["xung_dot"] = 1        # app sẽ không dùng ảnh này để hỏi/chấm
            danh_muc.append(muc)
            if i % 500 == 0: print(f"  đã nén {i}/{len(viec)} ảnh… ({time.time()-t0:.0f} giây)")
    if danh_muc:
        thu_tu = sorted(range(len(danh_muc)), key=lambda i: danh_muc[i]["net"])
        for hang, i in enumerate(thu_tu):
            danh_muc[i]["q"] = round(100 * hang / max(1, len(danh_muc) - 1))
    if not danh_muc:
        print("LỖI: không tìm thấy cặp ảnh + nhãn YOLO nào (cần thư mục images/ và labels/ cạnh nhau).")
        print("Cấu trúc thư mục nhận được:")
        for i, p in enumerate(sorted(Path(goc).rglob("*"))):
            if i >= 40: break
            print("  ", p.relative_to(goc))
        sys.exit(1)
    meta = {"nguon":"TCM-Tongue, Dryad DOI 10.5061/dryad.1c59zw48r",
            "nhan":{v[0]:{"ten":v[1],"nhom":v[2],"giao_trinh":v[3]} for v in NHAN.values()},
            "ma_so":{str(k):v[0] for k,v in NHAN.items()}, "anh":danh_muc}
    (ra/"danh-muc.json").write_text(json.dumps(meta, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    # danh mục gọn cho app: chỉ những trường app dùng (nhẹ hơn ~40%, tải nhanh hơn trên điện thoại)
    GIU = ("id", "khung", "cat", "q", "xung_dot")
    gon = dict(meta); gon["anh"] = [{k: m[k] for k in GIU if k in m} for m in danh_muc]
    (ra/"danh-muc-app.json").write_text(json.dumps(gon, ensure_ascii=False, separators=(",",":")), encoding="utf-8")
    dung = sum(p.stat().st_size for p in (ra/"anh").rglob("*.webp"))
    dung_luoi = sum(p.stat().st_size for p in (ra/"luoi").rglob("*.webp")) if (ra/"luoi").exists() else 0
    bc = [f"Ảnh dùng được: {len(danh_muc)} | trùng bỏ: {trung} | lỗi: {len(loi)} | bản xem: {dung/1e6:.0f} MB | bản cắt sát lưỡi: {dung_luoi/1e6:.0f} MB", ""]
    if danh_muc:
        import statistics as st
        rong = sorted(m["w"] for m in danh_muc); luoi_rong = sorted(m["lw"] for m in danh_muc)
        pv = lambda a, p: a[min(len(a)-1, int(p*len(a)))]
        bc += [f"Chiều rộng ảnh gốc (px): nhỏ nhất {rong[0]}, 10% {pv(rong,.1)}, trung vị {pv(rong,.5)}, lớn nhất {rong[-1]}",
               f"Chiều rộng vùng lưỡi đã cắt (px): 10% {pv(luoi_rong,.1)}, trung vị {pv(luoi_rong,.5)}",
               f"Ảnh có vùng lưỡi hẹp dưới 300 px (gốc độ phân giải thấp): {sum(1 for x in luoi_rong if x < 300)}", ""]
    bc += [f"{NHAN[k][1]:32s} {dem.get(k,0):5d}" + ("" if NHAN[k][3] else "   (ngoài giáo trình – tham khảo)") for k in NHAN]
    bc += ["", f"Ảnh có cờ xoay EXIF (đã xoay đúng chiều): {len(xoay)}"] + xoay[:50]
    bc += ["", f"Ảnh trùng nhưng nhãn KHÁC nhau (đã đánh dấu, app không dùng để hỏi): {len(xung_dot)}"]
    bc += ["  " + " | ".join(sorted(v)) for v in list(xung_dot.values())[:50]]
    bc += ["", "Ảnh lỗi:"] + loi
    (ra/"bao-cao.txt").write_text("\n".join(bc), encoding="utf-8")
    (ra/"goc-duong-dan.txt").write_text(str(Path(goc).resolve()), encoding="utf-8")
    print("\n".join(bc[:len(NHAN)+2]))
    print(f"\nXong sau {time.time()-t0:.0f} giây. Kho ảnh ở: {ra}")

def tim(kho, ma_can, chi_tiet=False):
    kho = Path(kho); meta = json.loads((kho/"danh-muc.json").read_text(encoding="utf-8"))
    can = {MA[m] for m in ma_can if m in MA}
    sai = [m for m in ma_can if m not in MA]
    if sai: print("Mã không đúng:", sai, "\nCác mã:", ", ".join(MA)); return
    khop = [a for a in meta["anh"] if {b[0] for b in a["khung"]} == can and not a.get("xung_dot")]
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
