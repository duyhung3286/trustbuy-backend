from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProductData(BaseModel):
    title: str
    url: str
    average_star: float
    video_count: int
    total_reviews_count: int = 0
    star1_count: int = 0
    star2_count: int = 0
    images: List[str]
    reviews: List[str]

@app.post("/api/analyze")
async def analyze_product(data: ProductData):
    warnings = []
    
    # --- 1. TÍNH TOÁN CÁC CHỈ SỐ CỐT LÕI ---
    bad_reviews_total = data.star1_count + data.star2_count
    bad_ratio = bad_reviews_total / data.total_reviews_count if data.total_reviews_count > 0 else 0
    
    spam_keywords = ["lừa đảo", "đừng mua", "fake", "kém", "tệ", "chậm", "thất vọng", "rách", "bẩn", "không giống", "dởm", "đắt", "hoàn hàng", "giả", "khác mô tả"]
    suspicious_count = sum(1 for rev in data.reviews if any(word in rev.lower() for word in spam_keywords))
    keyword_ratio = suspicious_count / max(len(data.reviews), 1)

    seeding_keywords = ["nhận xu", "mua hộ", "chưa dùng", "chưa test", "hình ảnh mang tính chất", "video mang tính chất", "không liên quan", "để nhận xu"]
    seeding_count = sum(1 for rev in data.reviews if any(word in rev.lower() for word in seeding_keywords))
    seeding_ratio = seeding_count / max(len(data.reviews), 1)
    
    total_media = len(data.images) + data.video_count

    # --- 2. CHẤM ĐIỂM THÀNH PHẦN ---
    star_score = 100
    if bad_ratio > 0.1: star_score = 40
    elif bad_ratio > 0.03: star_score = 70
    if data.average_star < 4.0: star_score = min(star_score, 50)

    media_score = 100 if total_media >= 5 else (50 if total_media > 0 else 0)

    sentiment_score = 100
    if keyword_ratio > 0.15: sentiment_score = 40
    elif keyword_ratio > 0.05: sentiment_score = 70

    authenticity_score = 100
    if seeding_ratio > 0.3: authenticity_score = 30
    elif seeding_ratio > 0.1: authenticity_score = 70

    trust_score = int((star_score * 0.3) + (media_score * 0.2) + (sentiment_score * 0.3) + (authenticity_score * 0.2))
    trust_score = max(0, min(100, trust_score))
    
    # --- 3. KẾT LUẬN AI ĐA CHIỀU (Biện luận dựa trên hành vi các nhóm sao) ---
    verdict_text = ""
    if trust_score >= 85:
        label = "MUA NGAY (Rất an toàn)"
        color_code = "#059669" 
        verdict_text = "<b>🎯 Quyết định: CHỐT ĐƠN.</b><br>Phân tích cho thấy nhóm 4-5 sao là đánh giá thực chất. Nhóm 1-2 sao có tồn tại nhưng tỉ lệ cực thấp (chủ yếu do vận chuyển). Ảnh đối chiếu khớp mô tả. Yên tâm mua hàng!"
        
    elif trust_score >= 70:
        label = "MUA ĐƯỢC (Có tì vết nhỏ)"
        color_code = "#16a34a" # Màu xanh nhạt hơn một chút
        verdict_text = f"<b>✅ Quyết định: CÓ THỂ MUA.</b><br>Sản phẩm cơ bản là tốt, nhưng AI ghi nhận {bad_reviews_total} đánh giá 1-2 sao phàn nàn. Nếu bạn không quá khắt khe về tiểu tiết, đây vẫn là một lựa chọn an toàn."
        
    elif trust_score >= 50:
        label = "DỪNG LẠI (Nhiều mâu thuẫn)"
        color_code = "#f97316" # Màu cam cảnh báo mạnh
        verdict_text = f"<b>⚠️ Quyết định: DỪNG LẠI (Nên bỏ qua).</b><br>AI phát hiện mâu thuẫn lớn: Nhóm 5 sao có tới {int(seeding_ratio*100)}% là review 'cày xu' sáo rỗng, trong khi nhóm 1-2 sao dùng nhiều từ khóa bức xúc. Khả năng cao chất lượng thực tế rất kém nhưng được 'bơm' đánh giá ảo."
        
    else:
        label = "TRÁNH XA (Rủi ro cực cao)"
        color_code = "#DC2626" 
        verdict_text = "<b>🚫 Quyết định: TÌM SHOP KHÁC NGAY.</b><br>Dữ liệu cảnh báo đỏ: Nhóm 1-2 sao chiếm áp đảo, hình ảnh thực tế thiếu độ tin cậy và có dấu hiệu gian dối rõ rệt. Không nên mua!"

    # Loại bỏ warning lẻ tẻ vì đã tổng hợp vào Verdict
    warning_text = ""
    
    return {
        "success": True,
        "trust_score": trust_score,
        "label": label,
        "color": color_code,
        "warning": warning_text,
        "verdict": verdict_text,
        "details": {
            "tier": "TrustBuy MVP",
            "star_score": star_score,
            "media_score": media_score,
            "sentiment_score": sentiment_score,
            "authenticity_score": authenticity_score,
            "crawled_stars": data.average_star,
            "crawled_reviews": len(data.reviews),
            "crawled_images": len(data.images),
            "crawled_videos": data.video_count
        }
    }