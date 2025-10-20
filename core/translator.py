import logging
import re
from typing import Dict, List, Tuple, Optional
import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration
import psycopg2
from psycopg2.extras import RealDictCursor
import nltk
from nltk.tokenize import sent_tokenize
from pythainlp.tokenize import sent_tokenize as th_sent_tokenize # For Thai
import kss # For Korean

# Configure logging
logging.basicConfig(
    filename='epidemic_news_pipeline.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Download NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Database connection parameters
DB_PARAMS = {
    "dbname": "neondb",
    "user": "neondb_owner",
    "password": "npg_o6AY4XRynVZK",
    "host": "ep-wandering-grass-a1ha7u59-pooler.ap-southeast-1.aws.neon.tech",
    "sslmode": "require"
}

# Glossary for protected terms (expanded for Thai provinces, diseases, countries)
# Stores Thai term -> English equivalent
GLOSSARY = {
    # Names and Titles (Thai -> English)
    "นพ.อัษฎางค์ รวยอาจิณ": "Dr. Assarangchai Ruayajin",
    "พิชามญชุ์ วรรณสาร": "Pichamchhun Wannasart",
    "พรนภัส ชำนาญค้า": "Pornnaphat Chamnanaka",
    "ภาวิกา ขันติศรีสกุล": "Phawika Khantisrisakul",
    "เทียนจรัส วงศ์พิเศษกุล": "Thianjarat Wongphisetsakul",
    "สมชาย": "Somchai", "สุภาพร": "Supaporn", "ชยพล": "Chayapol", "อินทรามะ": "Intarama",
    "วีระ": "Veera", "มณี": "Manee", "สุดา": "Suda", "ประสิทธิ์": "Prasit", "สมศรี": "Somsri",
    "บุญมา": "Boonma", "ดวงใจ": "Duangjai", "ชัยวัฒน์": "Chaiwat", "อรุณ": "Arun", "พรทิพย์": "Porntip",
    "สุชาติ": "Suchart", "นภา": "Napa", "วิชัย": "Vichai", "ลำดวน": "Lamduan", "สมศักดิ์": "Somsak",
    "สมหญิง": "Somying", "สมคิด": "Somkid", "สมปอง": "Sompong", "สมหวัง": "Somwang", "สมบัติ": "Sombat",
    "สมบูรณ์": "Sombun", "สมจิต": "Somjit", "สมจิตต์": "Somjit", "สมจิตร": "Somjit", "สมใจ": "Somjai",
    # Prefixes and Ranks (Thai -> English)
    "นาย": "Mr.", "นาง": "Mrs.", "นางสาว": "Ms.", "ดร.": "Dr.", "คุณ": "Khun", "ศ.": "Prof.",
    "ผศ.": "Asst. Prof.", "รศ.": "Assoc. Prof.", "ด.ต.": "Pol. Sgt. Maj.", "จ.ส.ต.": "Sgt. Maj. 1st Class",
    "พล.ต.อ.": "Pol. Gen.", "พล.อ.": "Gen.", "พล.ท.": "Lt. Gen.", "พล.ต.": "Maj. Gen.", "พ.อ.": "Col.",
    "พ.ท.": "Lt. Col.", "พ.ต.": "Maj.", "ร.อ.": "Capt.", "ร.ท.": "Lt.", "ร.ต.": "Sub-Lt.",
    "จ.ส.อ.": "Sgt. Maj. 1st Class", "จ.ส.ท.": "Sgt. Maj. 2nd Class", "ส.อ.": "Sgt.", "ส.ท.": "Cpl.",
    "ส.ต.": "Pte.", "พล.ต.ท.": "Pol. Lt. Gen.", "พล.ต.ต.": "Pol. Maj. Gen.", "พ.ต.อ.": "Pol. Col.",
    "พ.ต.ท.": "Pol. Lt. Col.", "พ.ต.ต.": "Pol. Maj.", "ร.ต.อ.": "Pol. Capt.", "ร.ต.ท.": "Pol. Lt.",
    "ร.ต.ต.": "Pol. Sub-Lt.",
    # Provinces of Thailand (Thai -> English)
    'กรุงเทพมหานคร': 'Bangkok', 'กระบี่': 'Krabi', 'กาญจนบุรี': 'Kanchanaburi', 'กาฬสินธุ์': 'Kalasin',
    'กำแพงเพชร': 'Kamphaeng Phet', 'ขอนแก่น': 'Khon Kaen', 'จันทบุรี': 'Chanthaburi', 'ฉะเชิงเทรา': 'Chachoengsao',
    'ชลบุรี': 'Chonburi', 'ชัยนาท': 'Chai Nat', 'ชัยภูมิ': 'Chaiyaphum', 'ชุมพร': 'Chumphon',
    'เชียงราย': 'Chiang Rai', 'เชียงใหม่': 'Chiang Mai', 'ตรัง': 'Trang', 'ตราด': 'Trat', 'ตาก': 'Tak',
    'นครนายก': 'Nakhon Nayok', 'นครปฐม': 'Nakhon Pathom', 'นครพนม': 'Nakhon Phanom', 'นครราชสีมา': 'Nakhon Ratchasima',
    'นครศรีธรรมราช': 'Nakhon Si Thammarat', 'นครสวรรค์': 'Nakhon Sawan', 'นนทบุรี': 'Nonthaburi',
    'นราธิวาส': 'Narathiwat', 'น่าน': 'Nan', 'บึงกาฬ': 'Bueng Kan', 'บุรีรัมย์': 'Buriram',
    'ปทุมธานี': 'Pathum Thani', 'ประจวบคีรีขันธ์': 'Prachuap Khiri Khan', 'ปราจีนบุรี': 'Prachinburi',
    'ปัตตานี': 'Pattani', 'พระนครศรีอยุธยา': 'Phra Nakhon Si Ayutthaya', 'พะเยา': 'Phayao',
    'พังงา': 'Phang Nga', 'พัทลุง': 'Phatthalung', 'พิจิตร': 'Phichit', 'พิษณุโลก': 'Phitsanulok',
    'เพชรบุรี': 'Phetchaburi', 'เพชรบูรณ์': 'Phetchabun', 'แพร่': 'Phrae', 'ภูเก็ต': 'Phuket',
    'มหาสารคาม': 'Maha Sarakham', 'มุกดาหาร': 'Mukdahan', 'แม่ฮ่องสอน': 'Mae Hong Son', 'ยโสธร': 'Yasothon',
    'ยะลา': 'Yala', 'ร้อยเอ็ด': 'Roi Et', 'ระนอง': 'Ranong', 'ระยอง': 'Rayong', 'ราชบุรี': 'Ratchaburi',
    'ลพบุรี': 'Lopburi', 'ลำปาง': 'Lampang', 'ลำพูน': 'Lamphun', 'เลย': 'Loei', 'ศรีสะเกษ': 'Sisaket',
    'สกลนคร': 'Sakon Nakhon', 'สงขลา': 'Songkhla', 'สตูล': 'Satun', 'สมุทรปราการ': 'Samut Prakan',
    'สมุทรสงคราม': 'Samut Songkhram', 'สมุทรสาคร': 'Samut Sakhon', 'สระแก้ว': 'Sa Kaeo', 'สระบุรี': 'Saraburi',
    'สิงห์บุรี': 'Sing Buri', 'สุโขทัย': 'Sukhothai', 'สุพรรณบุรี': 'Suphan Buri', 'สุราษฎร์ธานี': 'Surat Thani',
    'สุรินทร์': 'Surin', 'หนองคาย': 'Nong Khai', 'หนองบัวลำภู': 'Nong Bua Lamphu', 'อ่างทอง': 'Ang Thong',
    'อำนาจเจริญ': 'Amnat Charoen', 'อุดรธานี': 'Udon Thani', 'อุตรดิตถ์': 'Uttaradit', 'อุทัยธานี': 'Uthai Thani',
    'อุบลราชธานี': 'Ubon Ratchathani',
    # Epidemic and Related Terms (Thai -> English)
    "โควิด-19": "COVID-19", "โควิด": "COVID", "เดงกี่": "Dengue", "ชิคุนกุนยา": "Chikungunya",
    "หมอพร้อม": "Mor Prom", "ไข้หวัดใหญ่": "Influenza", "โรคระบาด": "Epidemic", "วัคซีน": "Vaccine",
    "การระบาด": "Outbreak", "ผู้ป่วย": "Patient", "ติดเชื้อ": "Infected", "กักตัว": "Quarantine",
    "มาตรการ": "Measures", "สาธารณสุข": "Public Health", "กระทรวงสาธารณสุข": "Ministry of Public Health",
    "โรงพยาบาล": "Hospital", "คลัสเตอร์": "Cluster", "ผู้สัมผัสเสี่ยงสูง": "High-risk contact",
    "ผู้ติดเชื้อรายใหม่": "New cases", "ผู้เสียชีวิต": "Deaths", "หายป่วย": "Recovered",
    "ผู้ป่วยสะสม": "Accumulated cases", "ผู้ป่วยวิกฤต": "Critical patients", "เตียงผู้ป่วย": "Hospital beds",
    "ชุดตรวจ ATK": "ATK test kit", "RT-PCR": "RT-PCR", "โอมิครอน": "Omicron", "เดลต้า": "Delta",
    "อัลฟ่า": "Alpha", "เบต้า": "Beta", "แกมม่า": "Gamma", "สายพันธุ์ใหม่": "New variant",
    "การฉีดวัคซีน": "Vaccination", "ภูมิคุ้มกันหมู่": "Herd immunity", "การเฝ้าระวัง": "Surveillance",
    "การควบคุมโรค": "Disease control", "ศูนย์บริหารสถานการณ์โควิด-19 (ศบค.)": "Centre for Covid-19 Situation Administration (CCSA)",
    "มาตรการป้องกัน": "Preventive measures", "การเว้นระยะห่างทางสังคม": "Social distancing",
    "การสวมหน้ากากอนามัย": "Wearing face masks", "การล้างมือบ่อยๆ": "Frequent hand washing",
    # Countries and cities for hashtag detection
    "ประเทศไทย": "Thailand", "เกาหลีใต้": "South Korea", "สหรัฐอเมริกา": "United States", "จีน": "China",
    "ญี่ปุ่น": "Japan", "สิงคโปร์": "Singapore", "มาเลเซีย": "Malaysia", "อินเดีย": "India",
    "โซล": "Seoul", "ปูซาน": "Busan", "นิวยอร์ก": "New York", "ลอนดอน": "London", "ปารีส": "Paris"
}

# Reverse GLOSSARY (English -> Thai)
REVERSE_GLOSSARY_EN_TH = {v: k for k, v in GLOSSARY.items()}

# Korean equivalents for common terms (simplified for example, ideally a full Korean glossary)
# For the sake of this example, some direct translations or transliterations are used.
GLOSSARY_KO = {
    "COVID-19": "코로나19",
    "Dengue": "뎅기열",
    "Chikungunya": "치쿤구니아열",
    "Influenza": "인플루엔자",
    "Thailand": "태국",
    "Bangkok": "방콕",
    "South Korea": "대한민국",
    "Seoul": "서울",
    "Epidemic": "전염병",
    "Vaccine": "백신",
    "Patient": "환자",
    "Ministry of Public Health": "공중보건부"
}

class EpidemicNewsPipeline:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {self.device}")
        self.tokenizer = T5Tokenizer.from_pretrained("google/flan-t5-large", legacy=False)
        self.model = T5ForConditionalGeneration.from_pretrained("google/flan-t5-large").to(self.device)
        self.model_max_input_length = 512 # This is the tokenizer/model's hard limit
        self.prompt_buffer = 100 # Generous buffer for various prompts (translate, summarize, hashtags)
        self.max_chunk_tokens = self.model_max_input_length - self.prompt_buffer 
        logger.info(f"Calculated max_chunk_tokens for content: {self.max_chunk_tokens}")

        # Compile regex patterns for faster hashtag detection
        self.country_patterns = self._compile_patterns([k for k in GLOSSARY.keys() if 'ประเทศ' in k or 'South Korea' in GLOSSARY[k] or 'United States' in GLOSSARY[k] or 'China' in GLOSSARY[k] or 'Japan' in GLOSSARY[k] or 'Singapore' in GLOSSARY[k] or 'Malaysia' in GLOSSARY[k] or 'India' in GLOSSARY[k]], GLOSSARY)
        self.province_city_patterns = self._compile_patterns([k for k in GLOSSARY.keys() if k not in self.country_patterns and 'จังหวัด' not in k and GLOSSARY[k] in ['Bangkok', 'Seoul', 'Busan', 'New York', 'London', 'Paris']], GLOSSARY)
        self.disease_patterns = self._compile_patterns([k for k in GLOSSARY.keys() if 'โควิด' in k or 'เดงกี่' in k or 'ชิคุนกุนยา' in k or 'ไข้หวัดใหญ่' in k], GLOSSARY)

    def _compile_patterns(self, terms_th: List[str], glossary: Dict[str, str]) -> Dict[str, re.Pattern]:
        """Compiles regex patterns for glossary terms and their English equivalents."""
        patterns = {}
        for term_th in terms_th:
            term_en = glossary.get(term_th, term_th) # Fallback to Thai if no English equivalent
            # Use | for OR to match either Thai or English term (case-insensitive for English)
            pattern_str = r'\b(?:' + re.escape(term_th) + r'|' + re.escape(term_en) + r')\b'
            patterns[term_en] = re.compile(pattern_str, re.IGNORECASE)
        return patterns

    def get_sentence_splitter(self, lang: str):
        if lang == "th":
            return th_sent_tokenize
        elif lang == "en":
            return sent_tokenize
        elif lang == "ko":
            return kss.split_sentences
        else:
            return sent_tokenize # Default to NLTK for unknown/other

    def detect_language(self, text: str, db_language: Optional[str]) -> str:
        """Use the language column from the database; if not available, detect using simple heuristics."""
        if db_language in ['th', 'en', 'ko']:
            return db_language
        if not text:
            return "unknown"
        if any(0x0E00 <= ord(c) <= 0x0E7F for c in text): # Thai Unicode range
            return "th"
        if any(0xAC00 <= ord(c) <= 0xD7AF for c in text): # Korean Unicode range (Hangul Syllables)
            return "ko"
        return "en"

    def replace_glossary_terms(self, text: str) -> Tuple[str, Dict[str, Tuple[str, str]]]:
        """Replace glossary terms with unique placeholders. Stores (original Thai term, English equivalent)."""
        if not text:
            return text, {}
        term_map = {} # Maps placeholder -> (original Thai term, English equivalent)
        idx = 1
        # Sort terms by length in descending order to prevent partial matches
        sorted_terms = sorted(GLOSSARY.items(), key=lambda item: len(item[0]), reverse=True)
        
        for term_th, term_en in sorted_terms:
            pattern = r'\b' + re.escape(term_th) + r'\b'
            if re.search(pattern, text):
                # Placeholder contains original Thai term and English equivalent for easy lookup
                unique_placeholder = f"[[GLOSSARY_{idx:03d}_{term_en.replace(' ', '_')}]]"
                term_map[unique_placeholder] = (term_th, term_en) 
                text = re.sub(pattern, unique_placeholder, text)
                idx += 1
        return text, term_map

    def restore_glossary_terms(self, text: str, term_map: Dict[str, Tuple[str, str]], target_lang: str) -> str:
        """Restores terms from placeholders based on the target language."""
        if not text:
            return text
        
        for placeholder, (original_th_term, english_equivalent) in term_map.items():
            if target_lang == "th":
                text = text.replace(placeholder, original_th_term)
            elif target_lang == "en":
                text = text.replace(placeholder, english_equivalent)
            elif target_lang == "ko":
                korean_equivalent = GLOSSARY_KO.get(english_equivalent, english_equivalent) # Lookup in KO glossary, fallback to EN
                text = text.replace(placeholder, korean_equivalent)
            # For other languages or if not found, the placeholder might remain or need more complex handling.
            # Currently, it falls back to the English equivalent if no direct KO translation in GLOSSARY_KO.
        return text

    def split_into_chunks(self, text: str, lang: str) -> List[str]:
        """
        Splits text into chunks respecting sentence boundaries, ensuring no chunk exceeds max_chunk_tokens.
        For sentences that are individually too long, they are further split by token count.
        """
        if not text:
            return []

        sentence_splitter = self.get_sentence_splitter(lang)
        sentences = sentence_splitter(text)
        chunks = []
        current_chunk_sentences = []
        current_chunk_token_count = 0

        for sentence in sentences:
            # Encode sentence to get actual token count
            sentence_tokens = len(self.tokenizer.encode(sentence, add_special_tokens=False))

            # If a single sentence is larger than the chunk limit
            if sentence_tokens > self.max_chunk_tokens:
                # Add any accumulated sentences as a separate chunk
                if current_chunk_sentences:
                    chunks.append(" ".join(current_chunk_sentences))
                    current_chunk_sentences = []
                    current_chunk_token_count = 0

                logger.warning(
                    f"Sentence too long ({sentence_tokens} tokens) for max_chunk_tokens ({self.max_chunk_tokens}). "
                    f"Breaking down the long sentence into sub-token chunks."
                )
                
                # Directly encode and split by tokens for oversized sentences
                encoded_sentence = self.tokenizer.encode(sentence, add_special_tokens=False)
                start_idx = 0
                while start_idx < len(encoded_sentence):
                    end_idx = min(start_idx + self.max_chunk_tokens, len(encoded_sentence))
                    token_chunk_text = self.tokenizer.decode(encoded_sentence[start_idx:end_idx], skip_special_tokens=True)
                    chunks.append(token_chunk_text)
                    start_idx = end_idx
                
                continue # Move to the next original sentence

            # Check if adding this sentence will exceed the token limit for the current chunk
            # Add a small buffer for potential spaces between sentences when joining
            # +1 is for the space that would be added if joining with previous sentences
            potential_new_token_count = current_chunk_token_count + sentence_tokens + (1 if current_chunk_sentences else 0)

            if potential_new_token_count <= self.max_chunk_tokens:
                current_chunk_sentences.append(sentence)
                current_chunk_token_count = potential_new_token_count
            else:
                # Current sentence doesn't fit, finalize current chunk and start new one
                if current_chunk_sentences:
                    chunks.append(" ".join(current_chunk_sentences))
                current_chunk_sentences = [sentence]
                current_chunk_token_count = sentence_tokens

        # Add any remaining sentences as the last chunk
        if current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))

        return chunks

    def translate_text(self, text: str, source_lang: str, target_lang: str) -> str:
        """Translates text. Guarantees input respects model_max_input_length."""
        if not text:
            return ""
        
        prompt = f"Translate from {source_lang} to {target_lang}: {text}"
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=self.model_max_input_length, truncation=True).to(self.device)
        
        # Log if truncation happened at tokenizer level
        if inputs['input_ids'].shape[1] > self.model_max_input_length:
            logger.warning(f"Translation input was truncated to {self.model_max_input_length} tokens after prompt. Original text length: {len(self.tokenizer.encode(text, add_special_tokens=False))} tokens.")

        try:
            outputs = self.model.generate(
                **inputs,
                max_length=self.model_max_input_length, 
                num_beams=4,
                early_stopping=True,
                do_sample=False # For more deterministic output
            )
            translated = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translated
        except Exception as e:
            logger.error(f"Error during translation from {source_lang} to {target_lang} for text '{text[:50]}...': {str(e)}")
            return "" # Return empty string on failure

    def summarize_text(self, text: str, lang: str) -> str:
        """
        Summarizes text. Truncates input to fit model_max_input_length.
        Aim for 500-700 characters.
        """
        if not text:
            return ""
        
        # Calculate max tokens for the text content, considering prompt length
        prompt_prefix = f"Summarize the following text in {lang} to 500-700 characters: "
        prompt_prefix_tokens = len(self.tokenizer.encode(prompt_prefix, add_special_tokens=False))
        max_text_tokens_for_summarization = self.model_max_input_length - prompt_prefix_tokens

        # Truncate text *before* tokenizing and adding prompt, to ensure it fits.
        encoded_text = self.tokenizer.encode(text, add_special_tokens=False)
        
        if len(encoded_text) > max_text_tokens_for_summarization:
            logger.warning(
                f"Full text for summarization is too long ({len(encoded_text)} tokens). "
                f"Truncating to {max_text_tokens_for_summarization} tokens for summary generation in {lang}."
            )
            text_to_summarize = self.tokenizer.decode(encoded_text[:max_text_tokens_for_summarization], skip_special_tokens=True)
        else:
            text_to_summarize = text

        prompt = prompt_prefix + text_to_summarize
        inputs = self.tokenizer(prompt, return_tensors="pt", max_length=self.model_max_input_length, truncation=True).to(self.device)
        
        try:
            outputs = self.model.generate(
                **inputs,
                max_length=150, # Sufficient for 500-700 chars usually
                min_length=50,
                length_penalty=1.0,
                num_beams=4,
                early_stopping=True,
                do_sample=False
            )
            summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            return summary[:700] # Truncate to character limit after generation
        except Exception as e:
            logger.error(f"Error during summarization for language {lang} for text '{text[:50]}...': {str(e)}")
            return "" # Return empty string on failure

    def extract_hashtags(self, text: str, lang: str) -> List[str]:
        """
        Extracts 3-5 relevant hashtags (country, province/city, disease).
        Operates on the provided text (e.g., summary or beginning of content).
        """
        hashtags = set()
        
        # Convert text to lowercase for case-insensitive matching
        lower_text = text.lower()

        # Helper to add hashtags and limit count
        def add_hashtag(tag_key: str, glossary_map: Dict[str, str], current_lang: str):
            if tag_key in glossary_map:
                if current_lang == "en":
                    hashtags.add(f"#{glossary_map[tag_key].replace(' ', '')}")
                elif current_lang == "th":
                    hashtags.add(f"#{tag_key.replace(' ', '')}")
                elif current_lang == "ko":
                    ko_equiv = GLOSSARY_KO.get(glossary_map[tag_key], glossary_map[tag_key]) # Try KO, fallback to EN
                    hashtags.add(f"#{ko_equiv.replace(' ', '')}")
            if len(hashtags) >= 5: return True
            return False

        # 1. Detect Countries
        for th_term, en_term in GLOSSARY.items():
            if 'ประเทศ' in th_term or en_term in ['Thailand', 'South Korea', 'United States', 'China', 'Japan', 'Singapore', 'Malaysia', 'India']:
                 if re.search(r'\b(?:' + re.escape(th_term) + r'|' + re.escape(en_term) + r')\b', text, re.IGNORECASE):
                    if add_hashtag(th_term, GLOSSARY, lang): break

        # 2. Detect Provinces/Cities (more specific for each language)
        if lang == "th":
            for th_term, en_term in GLOSSARY.items():
                if th_term in self.province_city_patterns and self.province_city_patterns[en_term].search(text):
                    if add_hashtag(th_term, GLOSSARY, lang): break
        elif lang == "en":
            for th_term, en_term in GLOSSARY.items():
                if en_term in ['Bangkok', 'Seoul', 'Busan', 'New York', 'London', 'Paris'] and re.search(r'\b' + re.escape(en_term) + r'\b', text, re.IGNORECASE):
                    if add_hashtag(th_term, GLOSSARY, lang): break
        elif lang == "ko":
            for th_term, en_term in GLOSSARY.items():
                ko_equiv = GLOSSARY_KO.get(en_term)
                if ko_equiv and re.search(r'\b' + re.escape(ko_equiv) + r'\b', text, re.IGNORECASE):
                    if add_hashtag(th_term, GLOSSARY, lang): break
                elif en_term in ['Seoul', 'Busan'] and re.search(r'\b' + re.escape(en_term) + r'\b', text, re.IGNORECASE): # Fallback if no KO in glossary for common cities
                    if add_hashtag(th_term, GLOSSARY, lang): break


        # 3. Detect Diseases
        for th_term, en_term in GLOSSARY.items():
            if 'โควิด' in th_term or 'เดงกี่' in th_term or 'ชิคุนกุนยา' in th_term or 'ไข้หวัดใหญ่' in th_term:
                if re.search(r'\b(?:' + re.escape(th_term) + r'|' + re.escape(en_term) + r')\b', text, re.IGNORECASE):
                    if add_hashtag(th_term, GLOSSARY, lang): break

        return list(hashtags)[:5] # Return up to 5 hashtags

    def process_text(self, text: str, source_lang: str, target_langs: List[str]) -> Dict[str, str]:
        """Process text: protect terms, chunk, translate, summarize, generate hashtags."""
        if not text:
            empty_results = {lang: "" for lang in target_langs}
            empty_summaries = {f"summary_{lang}": "" for lang in target_langs}
            empty_hashtags = {f"hashtags_{lang}": [] for lang in target_langs}
            return {**empty_results, **empty_summaries, **empty_hashtags}

        protected_text, term_map = self.replace_glossary_terms(text)
        chunks = self.split_into_chunks(protected_text, source_lang) # Pass source_lang for appropriate splitter
        
        # Initialize results structure
        translated_chunks_by_lang = {lang: [] for lang in target_langs}

        # If source language is a target language, populate its chunks directly (restored)
        if source_lang in target_langs:
            for chunk in chunks:
                # Restore original Thai terms into Thai chunks
                translated_chunks_by_lang[source_lang].append(self.restore_glossary_terms(chunk, term_map, source_lang))

        # Process translation for other target languages
        for i, chunk in enumerate(chunks):
            current_chunk_id = f"Chunk {i+1}/{len(chunks)}"
            
            # Pivot through English for better quality, unless source is already English
            en_chunk_for_pivot = ""
            if source_lang == "en":
                en_chunk_for_pivot = chunk
            else:
                en_chunk_for_pivot = self.translate_text(chunk, source_lang, "en")
                if not en_chunk_for_pivot:
                    logger.warning(f"Skipping translation for {current_chunk_id} due to English pivot failure.")
                    continue

            # Translate to English (if not source language)
            if "en" in target_langs and source_lang != "en":
                translated_chunks_by_lang["en"].append(self.restore_glossary_terms(en_chunk_for_pivot, term_map, "en"))

            # Translate to Thai (if not source language)
            if "th" in target_langs and source_lang != "th":
                th_chunk = self.translate_text(en_chunk_for_pivot, "en", "th")
                if th_chunk:
                    translated_chunks_by_lang["th"].append(self.restore_glossary_terms(th_chunk, term_map, "th"))
                else:
                    logger.warning(f"Skipping Thai translation for {current_chunk_id} due to failure.")

            # Translate to Korean (if not source language)
            if "ko" in target_langs and source_lang != "ko":
                ko_chunk = self.translate_text(en_chunk_for_pivot, "en", "ko")
                if ko_chunk:
                    translated_chunks_by_lang["ko"].append(self.restore_glossary_terms(ko_chunk, term_map, "ko"))
                else:
                    logger.warning(f"Skipping Korean translation for {current_chunk_id} due to failure.")

        final_processed_data = {}
        for lang in target_langs:
            concatenated_text = " ".join(translated_chunks_by_lang[lang])
            final_processed_data[lang] = concatenated_text

            # For summarization and hashtag generation, use the concatenated text
            # The summarize_text and generate_hashtags functions handle their own truncation
            summary = self.summarize_text(concatenated_text, lang)
            # Generate hashtags from the summary for conciseness
            hashtags = self.extract_hashtags(summary, lang) 
            
            final_processed_data[f"summary_{lang}"] = summary
            final_processed_data[f"hashtags_{lang}"] = hashtags

        return final_processed_data

    def process_row(self, row: Dict) -> Dict:
        """Process a database row."""
        try:
            title = row.get('title', '') or ''
            content = row.get('content_raw', '') or ''
            source_lang = self.detect_language(title + " " + content, row.get('language'))
            logger.info(f"Processing row {row.get('id', 'unknown')}, detected language: {source_lang}")

            target_langs = ["th", "en", "ko"]
            
            # Process title (typically short, so less prone to chunking issues)
            title_processed_data = self.process_text(title, source_lang, target_langs)

            # Process content
            content_processed_data = self.process_text(content, source_lang, target_langs)

            update_data = {
                'title_th': title_processed_data.get('th', title),
                'title_en': title_processed_data.get('en', title),
                'title_ko': title_processed_data.get('ko', title),
                'content_translated_th': content_processed_data.get('th', content),
                'content_translated_en': content_processed_data.get('en', content),
                'content_translated_ko': content_processed_data.get('ko', content),
                'summary_th': content_processed_data.get('summary_th', ''),
                'summary_en': content_processed_data.get('summary_en', ''),
                'summary_ko': content_processed_data.get('summary_ko', ''),
                'hashtags_th': content_processed_data.get('hashtags_th', []),
                'hashtags_en': content_processed_data.get('hashtags_en', []),
                'hashtags_ko': content_processed_data.get('hashtags_ko', []),
                'is_translated': True,
                'is_summarized': True
            }
            return update_data
        except Exception as e:
            logger.error(f"Error processing row {row.get('id', 'unknown')}: {str(e)}")
            return {}

    def run(self):
        """Run the main pipeline."""
        conn = None
        cursor = None
        try:
            conn = psycopg2.connect(**DB_PARAMS)
            conn.autocommit = False # Ensure transactions are explicit
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Fetch only rows that haven't been processed yet and lock them
            cursor.execute("SELECT id, title, content_raw, language FROM epidemic_news WHERE is_translated = FALSE OR is_summarized = FALSE FOR UPDATE SKIP LOCKED") 
            rows = cursor.fetchall()
            total_rows = len(rows)
            logger.info(f"Found {total_rows} rows to process (untranslated/unsummarized)")

            if total_rows == 0:
                print("No new rows to process. Pipeline finished.")
                logger.info("No new rows to process. Pipeline finished.")
                return

            for idx, row_dict in enumerate(rows, 1):
                print(f"Processing row {idx}/{total_rows} (ID: {row_dict.get('id', 'N/A')})")
                update_data = self.process_row(row_dict)
                if update_data:
                    update_query = """
                        UPDATE epidemic_news
                        SET
                            title_th = %s,
                            title_en = %s,
                            title_ko = %s,
                            content_translated_th = %s,
                            content_translated_en = %s,
                            content_translated_ko = %s,
                            summary_th = %s,
                            summary_en = %s,
                            summary_ko = %s,
                            hashtags_th = %s,
                            hashtags_en = %s,
                            hashtags_ko = %s,
                            is_translated = %s,
                            is_summarized = %s
                        WHERE id = %s
                    """
                    try:
                        cursor.execute(update_query, (
                            update_data['title_th'],
                            update_data['title_en'],
                            update_data['title_ko'],
                            update_data['content_translated_th'],
                            update_data['content_translated_en'],
                            update_data['content_translated_ko'],
                            update_data['summary_th'],
                            update_data['summary_en'],
                            update_data['summary_ko'],
                            update_data['hashtags_th'],
                            update_data['hashtags_en'],
                            update_data['hashtags_ko'],
                            update_data['is_translated'],
                            update_data['is_summarized'],
                            row_dict['id']
                        ))
                        conn.commit() # Commit each row individually
                        logger.info(f"Successfully updated row {row_dict['id']}")
                    except Exception as e:
                        conn.rollback() # Rollback if update fails for this row
                        logger.error(f"Failed to update row {row_dict.get('id', 'unknown')}: {str(e)}")
                else:
                    logger.warning(f"Skipping update for row {row_dict.get('id', 'unknown')} due to processing error.")

            logger.info("Pipeline run completed.")
            print("Pipeline run completed.")
        except Exception as e:
            logger.error(f"Pipeline failed: {str(e)}")
            print(f"Pipeline failed: {str(e)}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

if __name__ == "__main__":
    pipeline = EpidemicNewsPipeline()
    pipeline.run()