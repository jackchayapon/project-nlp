import re
from typing import Dict, List

# 🔹 คำที่มักพบในข่าวโรคระบาด
EPIDEMIC_KEYWORDS = [
    "ติดเชื้อ", "ผู้ป่วย", "ระบาด", "โควิด", "ฝีดาษ", "อหิวาต์", "ไวรัส", 
    "ไข้เลือดออก", "โรคติดต่อ", "โรงพยาบาล", "แพร่ระบาด", "ป้องกัน", "วัคซีน"
]

def normalize(text: str) -> str:
    """ลบช่องว่าง, แปลงเป็น lowercase"""
    return re.sub(r'\s+', ' ', text).strip().lower()

def contains_keywords(text: str, keywords: List[str]) -> bool:
    """ตรวจสอบว่า text มีคำใดๆ จาก keyword list"""
    return any(kw in text for kw in keywords)

def is_epidemic_related(article: Dict) -> bool:
    """
    ตรวจสอบว่าข่าวเกี่ยวข้องกับโรคระบาดไหม
    โดยใช้ title และ content_raw ในการพิจารณา
    """
    title = normalize(article.get("title", ""))
    content = normalize(article.get("content_raw", ""))

    # ✅ พบคำที่เกี่ยวข้องใน title หรือ content ถือว่าเกี่ยวข้อง
    return contains_keywords(title, EPIDEMIC_KEYWORDS) or contains_keywords(content, EPIDEMIC_KEYWORDS)
