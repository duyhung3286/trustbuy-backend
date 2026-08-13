from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Khai báo cấu trúc dữ liệu khổng lồ nhận từ Extension
class ProductData(BaseModel):
    title: str
    url: str
    raw_text: str
    images: List[str]
    reviews: List[str]

@app.post("/api/analyze")
def analyze_product(data: ProductData):
    print(f"Đang phân tích: {data.title[:30]}...")
    warnings = []
    
    # ---------------------------------------------------------
    # MÔ HÌNH TÍNH TRUST SCORE THEO TRỌNG SỐ (Thang 100)
    # ---------------------------------------------------------
    
    # 1. Điểm Shop & Nhất quán (Tối đa 45 điểm)
    shop_score = 45
    if "đã hủy" in data.raw_text.lower() or "vi phạm" in data.raw_text.lower():
        shop_score -= 10
        warnings.append("Shop có dấu hiệu tỉ lệ hoàn/hủy đơn cao.")

    # 2. Phân tích Nội dung & Review bất thường (Tối đa 40 điểm) [Trọng số: 40%]
    review_score = 40
    spam_keywords = ["seeding", "lừa đảo", "đừng mua", "hàng fake", "kém chất lượng", "treo đầu dê"]
    suspicious_count = 0
    
    for rev in data.reviews:
        rev_lower = rev.lower()
        # NLP cơ bản: Phát hiện cảm xúc tiêu cực và từ khóa cảnh báo
        if any(word in rev_lower for word in spam_keywords):
            suspicious_count += 1
        # Phát hiện bất thường: review quá ngắn hoặc vô nghĩa
        if len(rev) < 15:
            suspicious_count += 0.5 

    if len(data.reviews) > 0:
        spam_ratio = suspicious_count / len(data.reviews)
        if spam_ratio > 0.3:
            review_score -= 25
            warnings.append(f"Cảnh báo: Phát hiện {int(spam_ratio*100)}% review có dấu hiệu bất thường/tiêu cực!")
        elif spam_ratio > 0.1:
            review_score -= 10
    else:
        review_score -= 15
        warnings.append("Sản phẩm có quá ít review để AI phân tích chính xác.")

    # 3. Phân tích Hình ảnh / Thị giác máy tính (Tối đa 15 điểm) [Trọng số: 15%]
    image_score = 15
    # Thực tế sẽ dùng Computer Vision soi watermark/ảnh mạng, MVP tạm đếm số lượng
    if len(data.images) < 2:
        image_score -= 10
        warnings.append("Thiếu hình ảnh thực tế, nguy cơ chênh lệch so với mô tả.")
    elif len(data.images) > 10:
        image_score = 15 # Shop có đầu tư hình ảnh đầy đủ

    # ---------------------------------------------------------
    # TỔNG KẾT KẾT QUẢ
    # ---------------------------------------------------------
    total_score = shop_score + review_score + image_score
    total_score = max(0, min(100, int(total_score))) # Đảm bảo điểm từ 0-100
    
    # Ngưỡng phân loại điểm
    if total_score >= 80:
        label = "Đáng tin cậy cao"
    elif total_score >= 60:
        label = "Tương đối tin cậy"
    elif total_score >= 40:
        label = "Cần thận trọng"
    else:
        label = "Rủi ro cao"

    warning_msg = " | ".join(warnings) if warnings else "An toàn: Không phát hiện bất thường đáng kể."

    return {
        "success": True,
        "trust_score": total_score,
        "label": label,
        "warning": warning_msg,
        "details": {
            "crawled_images": len(data.images),
            "crawled_reviews": len(data.reviews)
        }
    }