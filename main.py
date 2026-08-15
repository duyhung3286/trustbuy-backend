from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import google.generativeai as genai
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# THIẾT LẬP GEMINI AI 
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

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
    # 1. Tính toán TỶ LỆ TRỪ ĐIỂM CHI TIẾT (Cho ra số thập phân)
    bad_reviews_total = data.star1_count + data.star2_count
    total = max(data.total_reviews_count, 1)
    bad_ratio = bad_reviews_total / total
    
    # Trừ điểm tuyến tính: Cứ 1% đánh giá xấu trừ 1.5 điểm
    star_score = max(0.0, 100.0 - (bad_ratio * 100 * 1.5))
    
    # Tính điểm Media
    media_score = 100.0 if (len(data.images) + data.video_count) >= 5 else (50.0 if (len(data.images) + data.video_count) > 0 else 0.0)
    
    # 2. ÉP GEMINI AI PHẢI ĐỌC VÀ SUY LUẬN TỪ DATA
    sampled_reviews = "\n".join(data.reviews[:100]) # Lấy 100 bình luận để AI đọc
    
    prompt = f"""
    Đóng vai trò là một trợ lý AI phân tích chất lượng sản phẩm. Hãy đọc các số liệu và bình luận sau:
    - Sản phẩm: {data.title}
    - Đánh giá xấu (1-2 sao): {bad_reviews_total} trên tổng {data.total_reviews_count}.
    - Nội dung bình luận trích xuất:
    {sampled_reviews}

    YÊU CẦU TRẢ LỜI:
    1. [SCORE: x.x] (Chấm điểm NLP văn bản từ 0 đến 100, có thể dùng số thập phân, trừ điểm nặng nếu có seeding hoặc chửi bới).
    2. Viết một đoạn ngắn (3-4 câu) tóm tắt chính xác những gì khách hàng đang khen/chê dựa trên TỪ KHÓA THỰC TẾ trong bình luận. Không dùng văn mẫu.
    3. Chốt lại bằng: <b>MUA NGAY</b>, <b>CÂN NHẮC</b>, hoặc <b>TRÁNH XA</b>.
    """

    try:
        response = model.generate_content(prompt)
        ai_response_text = response.text
        
        # Bóc tách điểm NLP do AI chấm
        sentiment_score = 70.0
        if "[SCORE:" in ai_response_text:
            try:
                score_str = ai_response_text.split("[SCORE:")[1].split("]")[0]
                sentiment_score = float(score_str.strip())
                ai_response_text = ai_response_text.split("]")[1].strip() # Cắt bỏ phần score trong text
            except: pass
            
        verdict_text = ai_response_text
        
    except Exception as e:
        sentiment_score = 50.0
        verdict_text = f"<b>⚠️ Lỗi kết nối API Gemini.</b> Hệ thống Render của bạn chưa gọi được AI. Lỗi chi tiết: {str(e)[:50]}"

    # Tính điểm tổng (Có số thập phân)
    trust_score = round((star_score * 0.4) + (media_score * 0.2) + (sentiment_score * 0.4), 1)
    trust_score = max(0.0, min(100.0, trust_score))

    if trust_score >= 80:
        label = "MUA NGAY (Rất an toàn)"
        color_code = "#059669"
    elif trust_score >= 60:
        label = "CÂN NHẮC (Có rủi ro nhỏ)"
        color_code = "#D97706"
    else:
        label = "DỪNG LẠI (Tránh xa)"
        color_code = "#DC2626"

    return {
        "success": True,
        "trust_score": trust_score,
        "label": label,
        "color": color_code,
        "warning": "",
        "verdict": verdict_text,
        "details": {
            "tier": "TrustBuy AI-Powered",
            "star_score": round(star_score, 1),
            "media_score": round(media_score, 1),
            "sentiment_score": round(sentiment_score, 1),
            "authenticity_score": round(sentiment_score, 1), # Gộp chung vào NLP do AI tự phân tích
            "crawled_stars": data.average_star,
            "crawled_reviews": len(data.reviews),
            "crawled_images": len(data.images),
            "crawled_videos": data.video_count
        }
    }