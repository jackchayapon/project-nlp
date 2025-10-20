# summarizer.py

from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
from typing import Literal
import re
from pythainlp.tokenize import sent_tokenize

# ─────────────────────────────────────────────────────────
# CONFIG: Load summarization model (English only)
# ─────────────────────────────────────────────────────────

model_name = "facebook/bart-large-cnn"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
summarizer_pipeline = pipeline("summarization", model=model, tokenizer=tokenizer)

# ─────────────────────────────────────────────────────────
# UTIL: แบ่งข้อความยาวเป็น Chunk ตามย่อหน้า
# ─────────────────────────────────────────────────────────

def split_into_chunks(text: str, max_chunk_chars: int = 1000):
    """
    แบ่งข้อความตามย่อหน้าหรือจุด จนกว่าจะครบความยาว max_chunk_chars
    """
    paragraphs = re.split(r'(?<=[.!?])\s+', text)
    chunks, current_chunk = [], ""

    for para in paragraphs:
        if len(current_chunk) + len(para) <= max_chunk_chars:
            current_chunk += " " + para
        else:
            chunks.append(current_chunk.strip())
            current_chunk = para
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

# ─────────────────────────────────────────────────────────
# SUMMARIZER: ภาษาอังกฤษ
# ─────────────────────────────────────────────────────────

def summarize_en(text: str, max_length=150, min_length=30) -> str:
    if not text.strip():
        return ""
    
    chunks = split_into_chunks(text, max_chunk_chars=1000)
    summaries = []

    for i, chunk in enumerate(chunks):
        print(f"🧠 สรุป Chunk {i+1}/{len(chunks)} …")
        try:
            word_count = len(chunk.split())
            # ปรับ max/min ตามความยาวจริง
            dynamic_max = min(max_length, max(30, int(word_count * 0.7)))
            dynamic_min = min(min_length, max(10, int(word_count * 0.3)))

            if dynamic_min >= dynamic_max:
                dynamic_min = max(5, dynamic_max - 5)

            summary = summarizer_pipeline(
                chunk,
                max_length=dynamic_max,
                min_length=dynamic_min,
                do_sample=False
            )
            summaries.append(summary[0]['summary_text'].strip())
        except Exception as e:
            summaries.append(f"[ERROR] {e}")

    return " ".join(summaries)


# ─────────────────────────────────────────────────────────
# SUMMARIZER: ภาษาไทย (ตัดประโยค)
# ─────────────────────────────────────────────────────────

def summarize_th(text: str, max_sentences=3) -> str:
    if not text.strip():
        return ""
    sentences = sent_tokenize(text)
    return " ".join(sentences[:max_sentences])

# ─────────────────────────────────────────────────────────
# UNIVERSAL ENTRY
# ─────────────────────────────────────────────────────────

def summarize(text: str, lang: Literal["en", "th", "ko"] = "en") -> str:
    """
    ใช้ summarize_en สำหรับ en/ko (ผ่าน Pivot แล้ว),
    ใช้ตัดประโยคสำหรับ th
    """
    if lang == "en" or lang == "ko":
        return summarize_en(text)
    elif lang == "th":
        return summarize_th(text)
    else:
        return "[ERROR] Unsupported language"
    
print(f"✅ ใช้ device: {model.device}")

