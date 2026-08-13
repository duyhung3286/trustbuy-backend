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

# 1. Cập nhật Model để nhận đủ dữ liệu từ Gói Free
class ProductData(BaseModel):
    title: str
    url: str
    average_star: float
    video_count: int
    images: List[str]
    reviews: List[str]

@app.post("/api/analyze")
async def analyze_product(data: ProductData):
    trust_score = 100
    warnings = []
    
    # --- THUẬT TOÁN ĐÁNH GIÁ (BẢN BASIC) ---
    
    # 1. Đánh giá qua Điểm Sao (Trọng số 20%)
    if data.average_star < 4.0:
        trust_score -= 20
        warnings.append(f"Đánh giá tổng quan thấp ({data.average_star} Sao).")
    elif data.average_star < 4.5:
        trust_score -= 10
        warnings.append(f"Điểm sao trung bình ({data.average_star} Sao).")

    # 2. Đánh giá qua Hình ảnh & Video thực tế (Trọng số 10%)
    total_media = len(data.images) + data.video_count
    if total_media == 0:
        trust_score -= 10
        warnings.append("Cảnh báo: Không có ảnh hoặc video thực tế từ người dùng.")
        
    # 3. Phân tích Ngôn ngữ Bình luận (Trọng số 70%)
    spam_keywords = ["lừa đảo", "đừng mua", "fake", "kém", "tệ", "chậm", "thất vọng", "rách", "bẩn", "không giống", "dởm", "đắt", "hoàn hàng", "giả"]
    suspicious_count = 0
    
    for rev in data.reviews:
        rev_lower = rev.lower()
        if any(word in rev_lower for word in spam_keywords):
            suspicious_count += 1
            
    if len(data.reviews) > 0:
        spam_ratio = suspicious_count / len(data.reviews)
        if spam_ratio > 0.15: 
            trust_score -= 40
            warnings.append(f"Nguy hiểm: Tới {int(spam_ratio*100)}% bình luận chứa phàn nàn/chê bai.")
        elif spam_ratio > 0.05:
            trust_score -= 20
            warnings.append("Lưu ý: Phát hiện nhiều đánh giá không hài lòng.")
    else:
        trust_score -= 30
        warnings.append("Rủi ro: Không thu thập được đủ bình luận để phân tích.")

    # 4. Chuẩn hóa kết quả
    trust_score = max(0, min(100, trust_score))
    
    if trust_score >= 80:
        label = "An toàn (Nên mua)"
    elif trust_score >= 50:
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