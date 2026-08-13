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
    trust_score = 100
    warnings = []
    
    # 1. ĐÁNH GIÁ QUA BẢNG THỐNG KÊ SAO (Bức tranh toàn cảnh)
    bad_reviews_total = data.star1_count + data.star2_count
    if data.total_reviews_count > 0:
        bad_ratio = bad_reviews_total / data.total_reviews_count
        if bad_ratio > 0.1: # Nếu hơn 10% khách hàng chê 1-2 sao
            trust_score -= 30
            warnings.append(f"Rủi ro: Có {bad_reviews_total} đánh giá 1-2 Sao (Chiếm {int(bad_ratio*100)}% tổng số).")
        elif bad_ratio > 0.03: # Nếu hơn 3% khách chê
            trust_score -= 10
            warnings.append(f"Lưu ý: Tồn tại {bad_reviews_total} đánh giá 1-2 Sao.")
            
    # 2. ĐÁNH GIÁ QUA ĐIỂM SAO TRUNG BÌNH
    if data.average_star < 4.0:
        trust_score -= 20
        warnings.append(f"Điểm sao trung bình thấp ({data.average_star} Sao).")

    # 3. ĐÁNH GIÁ QUA MEDIA
    total_media = len(data.images) + data.video_count
    if total_media == 0:
        trust_score -= 10
        warnings.append("Sản phẩm thiếu hình ảnh/video thực tế.")
        
    # 4. PHÂN TÍCH TEXT BÌNH LUẬN (Khắc phục lỗi Thiên kiến chọn mẫu)
    spam_keywords = ["lừa đảo", "đừng mua", "fake", "kém", "tệ", "chậm", "thất vọng", "rách", "bẩn", "không giống", "dởm", "đắt", "hoàn hàng", "giả"]
    suspicious_count = 0
    
    for rev in data.reviews:
        rev_lower = rev.lower()
        if any(word in rev_lower for word in spam_keywords):
            suspicious_count += 1
            
    # SỬA LỖI Ở ĐÂY: Tính tỷ lệ trên TỔNG SỐ (Ví dụ: 8 / 96 thay vì 8 / 16)
    if data.total_reviews_count > 0:
        keyword_ratio = suspicious_count / data.total_reviews_count
    elif len(data.reviews) > 0:
        keyword_ratio = suspicious_count / len(data.reviews)
    else:
        keyword_ratio = 0
        
    if keyword_ratio > 0.15: 
        trust_score -= 20
        warnings.append("AI phát hiện nhiều ngôn từ phàn nàn gay gắt.")

    # Chuẩn hóa điểm số
    trust_score = max(0, min(100, trust_score))
    
    if trust_score >= 85:
        label = "An toàn (Nên mua)"
    elif trust_score >= 60:
        label = "Cần cân nhắc (Nên đọc kỹ)"
    else:
        label = "Rủi ro cao (Tránh mua)"
        
    warning_text = " | ".join(warnings) if warnings else "Không phát hiện rủi ro nào."
    
    return {
        "success": True,
        "trust_score": trust_score,
        "label": label,
        "warning": warning_text,
        "details": {
            "tier": "TrustBuy Basic",
            "crawled_stars": data.average_star,
            "crawled_reviews": len(data.reviews),
            "crawled_images": len(data.images),
            "crawled_videos": data.video_count
        }
    }