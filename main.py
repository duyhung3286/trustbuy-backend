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
    
    # 1. Điểm Uy tín Sao
    star_score = 100
    bad_reviews_total = data.star1_count + data.star2_count
    if data.total_reviews_count > 0:
        bad_ratio = bad_reviews_total / data.total_reviews_count
        if bad_ratio > 0.1: 
            star_score = 40
            warnings.append(f"Có {bad_reviews_total} đánh giá 1-2 Sao.")
        elif bad_ratio > 0.03: 
            star_score = 70
    if data.average_star < 4.0:
        star_score = min(star_score, 50)

    # 2. Điểm Trực quan Media
    media_score = 100
    total_media = len(data.images) + data.video_count
    if total_media == 0:
        media_score = 0
        warnings.append("Thiếu hình ảnh/video thực tế từ người mua.")
    elif total_media < 5:
        media_score = 50
        
    # 3. Điểm Đánh giá từ khách (NLP)
    sentiment_score = 100
    spam_keywords = ["lừa đảo", "đừng mua", "fake", "kém", "tệ", "chậm", "thất vọng", "rách", "bẩn", "không giống", "dởm", "đắt", "hoàn hàng", "giả", "khác mô tả"]
    suspicious_count = sum(1 for rev in data.reviews if any(word in rev.lower() for word in spam_keywords))
            
    keyword_ratio = suspicious_count / max(len(data.reviews), 1)
    if keyword_ratio > 0.15: 
        sentiment_score = 40
        warnings.append("Phát hiện nhiều ngôn từ tiêu cực/phàn nàn.")
    elif keyword_ratio > 0.05:
        sentiment_score = 70

    # 4. CHỈ SỐ MỚI: Độ Chân Thực (Chống Seeding/Cày xu)
    authenticity_score = 100
    seeding_keywords = ["nhận xu", "mua hộ", "chưa dùng", "chưa test", "hình ảnh mang tính chất", "video mang tính chất", "không liên quan", "để nhận xu"]
    seeding_count = sum(1 for rev in data.reviews if any(word in rev.lower() for word in seeding_keywords))
    
    seeding_ratio = seeding_count / max(len(data.reviews), 1)
    if seeding_ratio > 0.3:
        authenticity_score = 30
    elif seeding_ratio > 0.1:
        authenticity_score = 70

    # TÍNH ĐIỂM TỔNG HỢP (Đã chia lại trọng số cho 4 thanh)
    trust_score = int((star_score * 0.3) + (media_score * 0.2) + (sentiment_score * 0.3) + (authenticity_score * 0.2))
    trust_score = max(0, min(100, trust_score))
    
    # KẾT LUẬN & ĐIỀU HƯỚNG QUYẾT ĐỊNH MUA (Chuẩn Pháp Lý theo Đề cương)
    verdict_text = ""
    if trust_score >= 80:
        label = "Đáng tin cậy (Có thể yên tâm)"
        color_code = "#059669" 
        verdict_text = "Sản phẩm có độ uy tín cao, dữ liệu nhất quán và ít dấu hiệu đánh giá bất thường. Bạn có thể an tâm tham khảo."
    elif trust_score >= 60:
        label = "Cần thận trọng (Có dấu hiệu rủi ro)"
        color_code = "#D97706" 
        verdict_text = "Phát hiện một số dấu hiệu bất thường về đánh giá hoặc chất lượng. Cần đọc kỹ phần bình luận trước khi quyết định."
    else:
        label = "Rủi ro cao (Khuyến nghị cân nhắc lại)"
        color_code = "#DC2626" 
        verdict_text = "Cảnh báo: Tỉ lệ đánh giá tiêu cực hoặc bất thường rất cao. Khuyến nghị tham khảo thêm các gian hàng khác."
        
    warning_text = " | ".join(warnings) if warnings else ""
    
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