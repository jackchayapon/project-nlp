import streamlit as st
import psycopg2
import pandas as pd
import numpy as np
import re
from typing import List, Dict, Any, Tuple

from sentence_transformers import SentenceTransformer, util

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# ==============================
# Config
# ==============================
DB_URI = "postgresql://neondb_owner:npg_o6AY4XRynVZK@ep-wandering-grass-a1ha7u59-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"

EMBED_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
GEN_MODEL_NAME   = "Qwen/Qwen2.5-1.5B-Instruct"

CONTEXT_BUDGET_CHARS = 6000
PER_DOC_MAX_CHARS    = 1800
MIN_SIM_THRESHOLD    = 0.35
MAX_TURNS_CONTEXT    = 3

# Hook สำหรับคำถามนับจำนวนข่าวโควิด
COVID_PAT = re.compile(r"(covid|covid-?19|โควิด|โควิด-?19)", re.IGNORECASE)
COUNT_PAT = re.compile(r"(กี่ข่าว|กี่บทความ|จำนวนข่าว|how\s+many)", re.IGNORECASE)

# ==============================
# DB
# ==============================
def get_db_connection():
    try:
        return psycopg2.connect(DB_URI)
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

@st.cache_data(ttl=3600)
def load_all_news(lang: str) -> pd.DataFrame:
    conn = get_db_connection()
    if not conn: return pd.DataFrame()
    try:
        cur = conn.cursor()
        title_col, summary_col = f"title_{lang}", f"summary_{lang}"
        content_col = "content_raw" if lang == "th" else f"content_translated_{lang}"
        cur.execute(f"""
            SELECT id, source, url, date, language,
                   {title_col}   AS title,
                   {summary_col} AS summary,
                   {content_col} AS content
            FROM epidemic_news
            ORDER BY date DESC;
        """)
        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]
        return pd.DataFrame(rows, columns=cols)
    except Exception as e:
        st.error(f"Error loading news: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

def count_covid_news(lang_for_db: str) -> int:
    conn = get_db_connection()
    if not conn: return 0
    try:
        cur = conn.cursor()
        title_col, summary_col = f"title_{lang_for_db}", f"summary_{lang_for_db}"
        content_col = "content_raw" if lang_for_db == "th" else f"content_translated_{lang_for_db}"
        cur.execute(f"""
            SELECT COUNT(*) FROM epidemic_news
            WHERE
              {title_col}   ILIKE '%covid%' OR {title_col}   ILIKE '%โควิด%'
              OR {summary_col} ILIKE '%covid%' OR {summary_col} ILIKE '%โควิด%'
              OR {content_col} ILIKE '%covid%' OR {content_col} ILIKE '%โควิด%';
        """)
        n = cur.fetchone()[0]
        return int(n or 0)
    except Exception as e:
        st.error(f"Error counting COVID news: {e}")
        return 0
    finally:
        conn.close()

# ==============================
# Models (cache)
# ==============================
@st.cache_resource(show_spinner=False)
def get_embedder():
    return SentenceTransformer(EMBED_MODEL_NAME)

@st.cache_resource(show_spinner=False)
def get_chat_model():
    tok = AutoTokenizer.from_pretrained(GEN_MODEL_NAME, use_fast=True, trust_remote_code=True)
    mdl = AutoModelForCausalLM.from_pretrained(
        GEN_MODEL_NAME,
        trust_remote_code=True,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        device_map="auto" if torch.cuda.is_available() else None,
    )
    return tok, mdl

def chat_generate(messages: list, max_new_tokens: int = 320) -> str:
    tok, mdl = get_chat_model()
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt")
    if torch.cuda.is_available():
        inputs = {k: v.to(mdl.device) for k, v in inputs.items()}
    with torch.no_grad():
        ids = mdl.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            eos_token_id=tok.eos_token_id,
        )
    out = tok.decode(ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return out.strip()

# ==============================
# Retrieval (auto pack)
# ==============================
@st.cache_data(ttl=3600, show_spinner=False)
def build_corpus_embeddings(df: pd.DataFrame) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    if df.empty:
        return np.zeros((0, 384)), []
    texts, meta = [], []
    for _, row in df.iterrows():
        t = f"{row.get('title','')}\n{row.get('summary','')}\n{row.get('content','')}"
        t = re.sub(r"\s+", " ", (t or ""))[:10000]
        texts.append(t)
        meta.append({
            "id": row["id"],
            "title": row.get("title") or "(no title)",
            "summary": row.get("summary") or "",
            "content": (row.get("content") or "")[:PER_DOC_MAX_CHARS],
            "source": row.get("source") or "",
            "url": row.get("url") or "",
            "date": row.get("date"),
        })
    emb = get_embedder().encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=True)
    return emb, meta

def retrieve_and_pack(query: str, df: pd.DataFrame, emb: np.ndarray, meta: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if df.empty: return []

    mask = (df["title"].fillna("").str.contains(query, case=False, regex=False)) | \
           (df["summary"].fillna("").str.contains(query, case=False, regex=False)) | \
           (df["content"].fillna("").str.contains(query, case=False, regex=False))
    pre_idx = np.where(mask.values)[0]

    qv = get_embedder().encode([query], convert_to_numpy=True, normalize_embeddings=True)[0]
    if len(pre_idx) > 0:
        cos = util.cos_sim(qv, emb[pre_idx]).cpu().numpy()[0]
        ranked = [(pre_idx[i], float(cos[i])) for i in np.argsort(cos)[::-1]]
    else:
        cos = util.cos_sim(qv, emb).cpu().numpy()[0]
        ranked = [(i, float(cos[i])) for i in np.argsort(cos)[::-1]]

    packed, used = [], 0
    for idx, score in ranked:
        if score < MIN_SIM_THRESHOLD and len(packed) > 0:
            break
        d = meta[idx]
        text_len = len((d.get("title","")) + (d.get("summary","")) + (d.get("content","")))
        if used + text_len > CONTEXT_BUDGET_CHARS:
            remain = max(0, CONTEXT_BUDGET_CHARS - used - len(d.get("title","")) - len(d.get("summary","")) - 10)
            if remain > 0:
                clipped = d.copy()
                clipped["content"] = (clipped.get("content","")[:remain]).rstrip()
                packed.append({**clipped, "score": score})
            break
        packed.append({**d, "score": score})
        used += text_len
        if used >= CONTEXT_BUDGET_CHARS: break

    if not packed and ranked:
        idx, score = ranked[0]
        packed = [{**meta[idx], "score": score}]
    return packed

def build_sources_block(docs: List[Dict[str, Any]]) -> str:
    parts = []
    for i, d in enumerate(docs, start=1):
        date_s = d["date"].strftime("%Y-%m-%d") if hasattr(d["date"], "strftime") else str(d["date"] or "")
        parts.append(
            f"[{i}] {d.get('title','')}\n"
            f"{d.get('summary','')}\n"
            f"{date_s} {d.get('url','')}\n"
            f"{d.get('content','')}"
        )
    return "\n\n---\n\n".join(parts)

# ==============================
# Answering (3 โหมด)
# ==============================
def answer_auto(query: str, docs: List[Dict[str, Any]], lang: str, history_pairs: List[Dict[str,str]]) -> str:
    sys = (
        "You are a friendly multilingual assistant. "
        "Hold a natural conversation. When sources from a proprietary database are provided, "
        "blend in relevant facts and add bracket citations like [1], [2]. "
        "If sources are not relevant, you may answer from general knowledge. "
        "Be concise and accurate."
    )
    hist_parts = []
    for t in history_pairs[-MAX_TURNS_CONTEXT:]:
        hist_parts += [{"role":"user","content":t["q"]},{"role":"assistant","content":t["a"]}]
    sources = build_sources_block(docs) if docs else ""
    msgs = [{"role":"system","content":sys}] + hist_parts + [
        {"role":"user","content": f"Answer in {lang}. Question: {query}\n\nSources (use if helpful):\n{sources}"}
    ]
    return chat_generate(msgs, max_new_tokens=320)

def answer_chat_only(query: str, lang: str, history_pairs: List[Dict[str,str]]) -> str:
    sys = "You are a friendly multilingual assistant who can chit-chat naturally and helpfully."
    hist_parts = []
    for t in history_pairs[-MAX_TURNS_CONTEXT:]:
        hist_parts += [{"role":"user","content":t["q"]},{"role":"assistant","content":t["a"]}]
    msgs = [{"role":"system","content":sys}] + hist_parts + [
        {"role":"user","content": f"Please answer in {lang}. {query}"}
    ]
    return chat_generate(msgs, max_new_tokens=240)

def answer_db_focused(query: str, docs: List[Dict[str, Any]], lang: str, history_pairs: List[Dict[str,str]]) -> str:
    sys = (
        "You are a public-health assistant. Prefer facts from the provided sources. "
        "Cite like [1], [2]. If evidence is missing, you may add general context but make that clear."
    )
    hist_parts = []
    for t in history_pairs[-MAX_TURNS_CONTEXT:]:
        hist_parts += [{"role":"user","content":t["q"]},{"role":"assistant","content":t["a"]}]
    sources = build_sources_block(docs) if docs else ""
    msgs = [{"role":"system","content":sys}] + hist_parts + [
        {"role":"user","content": f"Answer in {lang}. Question: {query}\n\nSources:\n{sources}"}
    ]
    return chat_generate(msgs, max_new_tokens=320)

# ==============================
# Streamlit Page (ใช้ st.chat_input — ไม่มีปุ่ม)
# ==============================
def show():
    lang = st.session_state.get("language", "th")
    st.title({"th":"💬 แชทบอทข่าวโรคระบาด (คุยรู้เรื่อง + ผสมฐานข้อมูลได้)",
              "en":"💬 Epidemic Chatbot (Conversational + DB-aware)"}[lang])
    st.caption({"th":"โหมด Auto จะผสมข้อมูลจากฐานข่าวเมื่อเกี่ยวข้อง • ไม่ต้องตั้งค่า top-k/ไม่ต้องกดปุ่ม",
                "en":"Auto blends DB facts when relevant • no top-k/no button"}[lang])

    mode = st.radio(
        {"th":"โหมดการตอบ","en":"Answering mode"}[lang],
        options=["Auto (DB-aware)", "Chat only", "DB-focused"],
        index=0, horizontal=True
    )
    show_src = st.checkbox({"th":"แสดงแหล่งอ้างอิง","en":"Show sources"}[lang], value=True)

    # โหลดข้อมูล + ฝังเวกเตอร์ครั้งเดียว
    with st.spinner({"th":"กำลังเตรียมข้อมูล...","en":"Preparing data..."}[lang]):
        lang_for_db = lang if lang in ("th","en","ko","jp") else "en"
        df = load_all_news(lang_for_db)
        emb, meta = build_corpus_embeddings(df)

    # ประวัติข้อความแบบ chat UI
    st.session_state.setdefault("messages", [])  # [{role: "user"/"assistant", content: "..."}]
    st.session_state.setdefault("chat_pairs", [])  # [{q:"...", a:"..."}], สำหรับส่งเข้า LLM เป็น history สั้น ๆ

    # แสดงบทสนทนาที่ผ่านมา
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])

    # รับอินพุตจากผู้ใช้ (กด Enter เพื่อส่ง)
    user_msg = st.chat_input({"th":"พิมพ์ข้อความที่นี่...","en":"Type your message..."}[lang])

    if user_msg:
        # แสดงข้อความผู้ใช้ทันที
        st.session_state["messages"].append({"role":"user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        # Hook: คำถามนับจำนวนข่าวโควิด → ตอบตรงจาก DB
        if COUNT_PAT.search(user_msg) and COVID_PAT.search(user_msg):
            n = count_covid_news(lang_for_db)
            ans = {"th": f"มีข่าวเกี่ยวกับโควิดทั้งหมด {n} ข่าวในฐานข้อมูลของเรา",
                   "en": f"There are {n} COVID-related news articles in our database."}[lang]

            st.session_state["messages"].append({"role":"assistant", "content": ans})
            st.session_state["chat_pairs"].append({"q": user_msg, "a": ans})

            with st.chat_message("assistant"):
                st.markdown(ans)
            return

        # โหมดแตะ DB จะดึงเอกสารอัตโนมัติ
        docs = []
        if mode != "Chat only":
            candidates = retrieve_and_pack(user_msg, df, emb, meta)
            if candidates and (mode == "DB-focused" or candidates[0]["score"] >= MIN_SIM_THRESHOLD):
                docs = candidates

        # ตอบตามโหมด
        if mode == "Chat only":
            ans = answer_chat_only(user_msg, lang, st.session_state["chat_pairs"])
        elif mode == "DB-focused":
            ans = answer_db_focused(user_msg, docs, lang, st.session_state["chat_pairs"])
        else:
            ans = answer_auto(user_msg, docs, lang, st.session_state["chat_pairs"])

        # แสดงคำตอบ
        st.session_state["messages"].append({"role":"assistant", "content": ans})
        st.session_state["chat_pairs"].append({"q": user_msg, "a": ans})

        with st.chat_message("assistant"):
            st.markdown(ans)
            if show_src and docs:
                st.markdown("**Sources**")
                for i, d in enumerate(docs, start=1):
                    date_s = d["date"].strftime("%Y-%m-%d") if hasattr(d["date"], "strftime") else str(d["date"] or "")
                    line = f"[{i}] {d['title']} — {d['source']} — {date_s}"
                    if d["url"]:
                        line += f" — [link]({d['url']})"
                    st.markdown(f"- {line}")