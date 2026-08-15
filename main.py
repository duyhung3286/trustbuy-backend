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

# THIẾT LẬP GEMINI AI (Lấy key từ Biến môi trường)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
    # 1. TÍNH TOÁN TỶ LỆ TRỪ ĐIỂM
    bad_reviews_total = data.star1_count + data.star2_count
    total = max(data.total_reviews_count, 1)
    bad_ratio = bad_reviews_total / total
    
    star_score = max(0.0, 100.0 - (bad_ratio * 100 * 1.5))
    media_score = 100.0 if (len(data.images) + data.video_count) >= 5 else (50.0 if (len(data.images) + data.video_count) > 0 else 0.0)
    
    # 2. ÉP GEMINI AI SUY LUẬN VÀ CHỐT QUYẾT ĐỊNH
    # Chỉ lấy 100 bình luận để tránh làm quá tải bộ nhớ AI
    sampled_reviews = "\n".join(data.reviews[:100]) 
    
    prompt = f"""
    Bạn là một chuyên gia mua sắm AI. Người dùng đang cần một LỜI KHUYÊN DỨT KHOÁT để quyết định mua hay không mua sản phẩm này.
    
    THÔNG SỐ:
    - Tên SP: {data.title}
    - Đánh giá xấu (1-2 sao): {bad_reviews_total} trên tổng {data.total_reviews_count}.
    - Bình luận thực tế:
    {sampled_reviews}

    YÊU CẦU BẮT BUỘC (Trả về HTML):
    1. [SCORE: x.x] (Bạn hãy tự chấm điểm uy tín NLP từ 0 đến 100).
    2. Viết 2 câu phân tích thẳng thắn, rạch ròi về chất lượng cốt lõi dựa trên bình luận. 
    3. CÂU CHỐT HẠ: Phải xuống dòng và in đậm 1 trong 3 câu sau: <b>MUA NGAY KHÔNG DO DỰ!</b> hoặc <b>CẦN CÂN NHẮC KỸ!</b> hoặc <b>TRÁNH XA KẺO MẤT TIỀN!</b>
    """

    ai_response_text = ""
    sentiment_score = 50.0
    
    # KIỂM TRA XEM CÓ API KEY CHƯA
    if not GEMINI_API_KEY:
        verdict_text = "<b>⚠️ Thiếu API Key.</b> Bạn chưa nhập GEMINI_API_KEY vào biến môi trường của Render."
    else:
        try:
            # VÒNG LẶP DÒ TÌM MÔ HÌNH CHỐNG 404
            models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-1.0-pro', 'gemini-pro']
            
            for model_name in models_to_try:
                try:
                    model = genai.GenerativeModel(model_name)
                    response = model.generate_content(prompt)
                    if response.text:
                        ai_response_text = response.text
                        break # Nếu thành công, thoát vòng lặp ngay
                except Exception as inner_e:
                    continue # Bị lỗi thì thử mô hình tiếp theo
                    
            if not ai_response_text:
                raise Exception("Tất cả các phiên bản AI đều bị Google từ chối đối với API Key này.")
            
            # Bóc tách điểm NLP do AI chấm
            if "[SCORE:" in ai_response_text:
                try:
                    score_str = ai_response_text.split("[SCORE:")[1].split("]")[0]
                    sentiment_score = float(score_str.strip())
                    ai_response_text = ai_response_text.split("]")[1].strip()
                except: pass
                
            verdict_text = ai_response_text
            
        except Exception as e:
            sentiment_score = 50.0
            verdict_text = f"<b>⚠️ Lỗi hệ thống AI.</b> Chi tiết: {str(e)[:150]}"

    # 3. TÍNH ĐIỂM TỔNG HỢP
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
            "authenticity_score": round(sentiment_score, 1), 
            "crawled_stars": data.average_star,
            "crawled_reviews": len(data.reviews),
            "crawled_images": len(data.images),
            "crawled_videos": data.video_count
        }
    }