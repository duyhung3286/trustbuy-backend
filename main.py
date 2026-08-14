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
    
    # 1. ĐÁNH GIÁ QUA BẢNG THỐNG KÊ SAO (Phân tích bất thường)
    bad_reviews_total = data.star1_count + data.star2_count
    if data.total_reviews_count > 0:
        bad_ratio = bad_reviews_total / data.total_reviews_count
        if bad_ratio > 0.1: 
            trust_score -= 30
            warnings.append(f"Có dấu hiệu bất thường: {bad_reviews_total} đánh giá 1-2 Sao (Tỉ lệ {int(bad_ratio*100)}%).")
        elif bad_ratio > 0.03: 
            trust_score -= 10
            warnings.append(f"Cần lưu ý: Ghi nhận {bad_reviews_total} đánh giá ở mức 1-2 Sao.")
            
    # 2. ĐÁNH GIÁ QUA ĐIỂM SAO TRUNG BÌNH
    if data.average_star < 4.0:
        trust_score -= 20
        warnings.append(f"Điểm sao trung bình ở mức thấp ({data.average_star}/5.0).")

    # 3. ĐÁNH GIÁ QUA MEDIA (Tính nhất quán sản phẩm)
    total_media = len(data.images) + data.video_count
    if total_media == 0:
        trust_score -= 10
        warnings.append("Thiếu dữ liệu hình ảnh/video thực tế từ người dùng để đối chiếu.")
        
    # 4. PHÂN TÍCH TEXT BÌNH LUẬN (NLP Basic)
    # Lưu ý: Người dùng có thể chửi là "lừa đảo", nhưng Output của AI chỉ được báo là "ngôn từ phàn nàn"
    spam_keywords = ["lừa đảo", "đừng mua", "fake", "kém", "tệ", "chậm", "thất vọng", "rách", "bẩn", "không giống", "dởm", "đắt", "hoàn hàng", "giả"]
    suspicious_count = 0
    
    for rev in data.reviews:
        rev_lower = rev.lower()
        if any(word in rev_lower for word in spam_keywords):
            suspicious_count += 1
            
    if data.total_reviews_count > 0:
        keyword_ratio = suspicious_count / data.total_reviews_count
    elif len(data.reviews) > 0:
        keyword_ratio = suspicious_count / len(data.reviews)
    else:
        keyword_ratio = 0
        
    if keyword_ratio > 0.15: 
        trust_score -= 20
        warnings.append("Tần suất xuất hiện từ khóa phàn nàn/tiêu cực trong bình luận cao.")

    # 5. CHUẨN HÓA ĐIỂM SỐ VÀ PHÂN LOẠI (Theo chuẩn Mục IV của Đề cương)
    trust_score = max(0, min(100, trust_score))
    
    if trust_score >= 80:
        label = "Đáng tin cậy cao (Có thể yên tâm)"
    elif trust_score >= 60:
        label = "Tương đối tin cậy (Nên đọc thêm review)"
    elif trust_score >= 40:
        label = "Cần thận trọng (Có chỉ số bất thường)"
    else:
        label = "Rủi ro cao (Khuyến nghị cân nhắc lại)"
        
    warning_text = " | ".join(warnings) if warnings else "Các chỉ số hiện tại ở mức ổn định."
    
    return {
        "success": True,
        "trust_score": trust_score,
        "label": label,
        "warning": warning_text,
        "disclaimer": "Trust Score là công cụ hỗ trợ tham khảo tự động, không phải kết luận pháp lý.", # Thêm dòng cam kết pháp lý
        "details": {
            "tier": "TrustBuy Basic (Waze Model)",
            "crawled_stars": data.average_star,
            "crawled_reviews": len(data.reviews),
            "crawled_images": len(data.images),
            "crawled_videos": data.video_count
        }
    }