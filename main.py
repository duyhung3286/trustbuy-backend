from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from google import genai
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# THIẾT LẬP CLIENT BẢO MẬT (Hỗ trợ định dạng khóa AQ...)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

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
    bad_reviews_total = data.star1_count + data.star2_count
    total = max(data.total_reviews_count, 1)
    bad_ratio = bad_reviews_total / total
    
    star_score = max(0.0, 100.0 - (bad_ratio * 100 * 1.5))
    media_score = 100.0 if (len(data.images) + data.video_count) >= 5 else (50.0 if (len(data.images) + data.video_count) > 0 else 0.0)
    
    ai_response_text = ""
    sentiment_score = 50.0
    last_error = ""
    
    if len(data.reviews) == 0:
        verdict_text = "<b>⚠️ Không thu thập được bình luận.</b> Hãy kéo cuộn chuột xuống dưới cùng để Shopee hiển thị bình luận, sau đó ấn F5 và quét lại!"
    elif not client:
        verdict_text = "<b>⚠️ Thiếu API Key.</b> Bạn chưa thiết lập biến môi trường GEMINI_API_KEY trên Render."
    else:
        try:
            sampled_reviews = "\n".join(data.reviews[:60]) 
            prompt = f"""
            Bạn là một chuyên gia mua sắm AI. Đưa ra LỜI KHUYÊN DỨT KHOÁT để quyết định mua hay không.
            - Tên SP: {data.title}
            - Đánh giá xấu (1-2 sao): {bad_reviews_total}/{data.total_reviews_count}.
            - Bình luận thực tế:
            {sampled_reviews}

            YÊU CẦU:
            1. [SCORE: x.x] (Chấm điểm uy tín NLP từ 0-100).
            2. Phân tích 2 câu ngắn gọn, rạch ròi.
            3. Chốt lại bằng 1 trong 3 câu in đậm: <b>MUA NGAY KHÔNG DO DỰ!</b> hoặc <b>CẦN CÂN NHẮC KỸ!</b> hoặc <b>TRÁNH XA KẺO MẤT TIỀN!</b>
            """

            # SỬ DỤNG CÁC ĐỜI AI MỚI NHẤT TRONG TÀI LIỆU
            models_to_try = ['gemini-3.6-flash', 'gemini-3.5-flash', 'gemini-2.5-flash']
            
            for model_name in models_to_try:
                try:
                    # GỌI API THEO ĐÚNG HƯỚNG DẪN MỚI TỪ GOOGLE
                    interaction = client.interactions.create(
                        model=model_name,
                        input=prompt
                    )
                    if interaction.output_text:
                        ai_response_text = interaction.output_text
                        break 
                except Exception as inner_e:
                    last_error = str(inner_e)
                    continue 
                    
            if not ai_response_text:
                raise Exception(f"{last_error}")
            
            # Xử lý cắt chuỗi lấy điểm số
            if "[SCORE:" in ai_response_text:
                try:
                    score_str = ai_response_text.split("[SCORE:")[1].split("]")[0]
                    sentiment_score = float(score_str.strip())
                    ai_response_text = ai_response_text.split("]")[1].strip()
                except: pass
                
            verdict_text = ai_response_text
            
        except Exception as e:
            sentiment_score = 50.0
            verdict_text = f"<b>⚠️ Lỗi API Gemini:</b> {str(e)[:250]}"

    # Tính toán điểm tổng Trust Score
    trust_score = round((star_score * 0.4) + (media_score * 0.2) + (sentiment_score * 0.4), 1)
    trust_score = max(0.0, min(100.0, trust_score))

    # Gắn nhãn màu sắc
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
            "tier": "TrustBuy AI",
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