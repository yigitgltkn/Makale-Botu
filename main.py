import os
import random
import json
import requests
import logging
import html
import traceback
from requests.auth import HTTPBasicAuth
from google import genai
from google.genai import types

# ==========================================
# AYARLAR VE YAPILANDIRMA (Güvenli Sistem)
# ==========================================
# Bilgiler dış ortamdan (GitHub Secrets veya .env) güvenle çekiliyor
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
WP_APP_PASS = os.getenv("WP_APP_PASS")
WP_USER = os.getenv("WP_USER")
WP_URL = os.getenv("WP_URL")

# Güvenlik Kilidi: Şifreler eksikse bot çalışmayı durdurur
if not all([GEMINI_API_KEY, WP_APP_PASS, WP_USER, WP_URL]):
    raise ValueError("❌ KRİTİK HATA: Çevre değişkenleri (Environment Variables) eksik! Lütfen GitHub Secrets ayarlarınızı kontrol edin.")

WP_CATEGORIES = {
    "Hydraulic Modeling": 408,
    "Infrastructure": 401,
    "SCADA": 283,
    "Energy": 496,
    "GIS & Mapping": 524,
    "IIoT & Edge": 523,
    "AI & Automation": 281
}

# Loglama ayarları (Profesyonel sistem standartı)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WordPressClient:
    """WordPress ile olan tüm REST API haberleşmesini yöneten sınıf."""
    
    def __init__(self, url, user, app_pass):
        self.url = url
        self.auth = HTTPBasicAuth(user, app_pass)

    def get_latest_posts(self, limit=5):
        logger.info("Siteden güncel makale linkleri çekiliyor...")
        endpoint = f"{self.url}/wp-json/wp/v2/posts"
        params = {"per_page": limit, "status": "publish", "_fields": "title,link"}
        
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            makaleler = response.json()
            link_listesi = [
                f"- Title: '{html.unescape(m.get('title', {}).get('rendered', ''))}' | URL: {m.get('link', '')}"
                for m in makaleler
            ]
            logger.info(f"{len(link_listesi)} adet makale başarıyla çekildi.")
            return "\n".join(link_listesi) if link_listesi else ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Makale çekme hatası: {e}")
            return ""

    def upload_media_from_memory(self, image_bytes, filename):
        logger.info(f"Görsel (RAM üzerinden) WP'ye yükleniyor: {filename}")
        endpoint = f"{self.url}/wp-json/wp/v2/media"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "image/jpeg"
        }
        
        response = requests.post(endpoint, headers=headers, data=image_bytes, auth=self.auth)
        if response.status_code == 201:
            media_id = response.json().get("id")
            logger.info(f"Görsel başarıyla yüklendi. Medya ID: {media_id}")
            return media_id
        logger.error(f"Görsel yüklenirken hata: {response.text}")
        return None

    def get_or_create_tag(self, tag_name):
        endpoint = f"{self.url}/wp-json/wp/v2/tags"
        
        # Önce etiketi ara
        search_response = requests.get(endpoint, params={"search": tag_name}, auth=self.auth)
        if search_response.status_code == 200 and search_response.json():
            for t in search_response.json():
                if t['name'].lower() == tag_name.lower():
                    return t['id']
            return search_response.json()[0]['id']
            
        # Bulunamazsa yeni oluştur
        create_response = requests.post(endpoint, json={"name": tag_name}, auth=self.auth)
        if create_response.status_code == 201:
            return create_response.json().get("id")
        return None

    def publish_post(self, title, content, category_id, media_id, tag_ids):
        logger.info("Makale ve kapak fotoğrafı WP'ye gönderiliyor...")
        endpoint = f"{self.url}/wp-json/wp/v2/posts"
        payload = {
            "title": title,
            "content": content,
            "status": "publish",
            "categories": [category_id],
            "tags": tag_ids
        }
        if media_id:
            payload["featured_media"] = media_id
            
        headers = {"Content-Type": "application/json"}
        response = requests.post(endpoint, json=payload, auth=self.auth, headers=headers)
        
        if response.status_code == 201:
            logger.info(f"HARİKA! Makale yayımlandı. Link: {response.json().get('link')}")
            return True
        logger.error(f"WordPress'e gönderilirken hata oluştu: {response.text}")
        return False


class ContentAgent:
    """Gemini modelleri ile metin ve görsel üretimini yöneten otonom ajan."""
    
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def generate_title(self, topic, persona, audience):
        logger.info("Yapay zeka rekabetçi bir başlık düşünüyor...")
        prompt = f"""Act as {persona} writing for a B2B engineering blog. 
        Generate ONE highly engaging, click-worthy, SEO-optimized blog post title specifically about '{topic}'. 
        Target audience: {audience}.
        CRITICAL RULE 1: Use click-trigger formats like "How-To:", "The Ultimate Guide:", "Practical Examples:".
        CRITICAL RULE 2: It must sound like an advanced engineering guide.
        Return ONLY the exact title text. No quotes."""
        
        response = self.client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.8)
        )
        return response.text.strip().replace('"', '')

    def generate_article(self, title, topic, persona, audience, structure, internal_links_str):
        logger.info("Makale sentezleniyor, iç linkler ve yapılandırılmış JSON oluşturuluyor...")
        kategoriler_str = json.dumps(WP_CATEGORIES)
        
        prompt = f"""
        Act as {persona}. Write a highly competitive, expert-level B2B technical article in English about "{title}".
        Target audience: {audience}.

        CRITICAL RULES:
        1. STRUCTURE: Format: {structure} Must be at least 800 words.
        2. META DESCRIPTION: The FIRST paragraph MUST be 1-2 sentences acting as an SEO Meta Description.
        3. PRACTICAL VALUE: Include at least one detailed code block (C#, Python, SQL) in <pre><code>.
        4. COMPARISON/DATA: Include at least one detailed HTML <table>.
        5. FORMATTING: Use strict HTML (<h2>, <h3>, <ul>, <strong>). NO markdown blocks.
        6. SEO TAGS: Provide 3 to 5 highly relevant SEO tags.
        7. CATEGORY ASSIGNMENT: Assign the best category ID from this dict: {kategoriler_str}
        
        8. INTERNAL LINKING: 
        Recent articles:
        {internal_links_str}
        Embed 1-2 HTML <a> tags pointing EXACTLY to these URLs naturally. Do NOT invent fake URLs.

        Output format MUST be a single valid JSON object with EXACTLY three keys: 
        - "content": Full HTML article string.
        - "tags": Array of strings.
        - "category_id": Integer.
        """
        
        response = self.client.models.generate_content(
            model='gemini-3-flash-preview',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.6
            )
        )
        return json.loads(response.text)

    def generate_cover_image(self, title):
        logger.info("Kapak görseli oluşturuluyor (Multimodal Generation)...")
        styles = [
            "Blueprint/schematic technical drawing style, dark mode",
            "Photorealistic industrial control room, cinematic lighting",
            "High-tech server rack and SCADA screens, isometric 3D render",
            "Futuristic AI laboratory setting, high contrast"
        ]
        chosen_style = random.choice(styles)
        prompt = f"A professional blog cover image for the engineering topic: '{title}'. Art style: {chosen_style}. Clean composition, NO text, NO letters, NO words."
        
        response = self.client.models.generate_content(
            model='gemini-3.1-flash-image-preview',
            contents=[prompt]
        )
        
        for part in response.parts:
            if part.inline_data is not None:
                logger.info(f"Görsel başarıyla oluşturuldu. (Stil: {chosen_style})")
                return part.inline_data.data
        raise ValueError("Modelden görsel verisi alınamadı!")


# ==========================================
# ANA ÇALIŞTIRMA (ORCHESTRATION)
# ==========================================
def main():
    logger.info("Otonom İçerik Ajanı başlatılıyor...")
    
    # 1. Sınıfları Başlat
    wp_client = WordPressClient(WP_URL, WP_USER, WP_APP_PASS)
    ai_agent = ContentAgent(GEMINI_API_KEY)
    
    # 2. Dosya Okuma
    dosya_adi = "keywords.txt"
    if not os.path.exists(dosya_adi):
        logger.error(f"'{dosya_adi}' bulunamadı!")
        return
        
    with open(dosya_adi, "r", encoding="utf-8") as file:
        satirlar = [satir.strip() for satir in file.readlines() if satir.strip()]
        
    if not satirlar:
        logger.error(f"'{dosya_adi}' boş! Yeni konular ekleyin.")
        return
        
    hedef_konu = satirlar[0]
    logger.info(f"Hedeflenen Niş Konu: {hedef_konu} (Kalan: {len(satirlar)})")
    
    try:
        # 3. Dinamik Personalar
        kitle = random.choice(["Senior SCADA Engineers in NA/EU", "Water Infrastructure Managers", "Industrial Software Developers"])
        persona = random.choice(["a strict, data-driven Senior SCADA Architect", "a highly practical Field Automation Engineer"])
        yapi = random.choice(["A step-by-step technical troubleshooting guide.", "A deep-dive technical case study."])
        
        # 4. Pipeline Akışı
        mevcut_makaleler = wp_client.get_latest_posts(limit=5)
        
        baslik = ai_agent.generate_title(hedef_konu, persona, kitle)
        makale_verisi = ai_agent.generate_article(baslik, hedef_konu, persona, kitle, yapi, mevcut_makaleler)
        
        icerik = makale_verisi.get("content", "")
        kategori_id = makale_verisi.get("category_id", 401)
        etiketler = makale_verisi.get("tags", [])
        
        # WP Etiket İşlemleri
        tag_ids = [wp_client.get_or_create_tag(tag) for tag in etiketler if wp_client.get_or_create_tag(tag)]
        
        # Multimodal Görsel İşlemleri
        resim_bytes = ai_agent.generate_cover_image(baslik)
        dosya_adi_medya = f"cover_{random.randint(1000,9999)}.jpg"
        media_id = wp_client.upload_media_from_memory(resim_bytes, dosya_adi_medya)
        
        # Yayınlama
        basari = wp_client.publish_post(baslik, icerik, kategori_id, media_id, tag_ids)
        
        # Başarılıysa Dosyadan Sil
        if basari:
            satirlar.pop(0)
            with open(dosya_adi, "w", encoding="utf-8") as file:
                file.writelines(f"{satir}\n" for satir in satirlar)
            logger.info(f"İşlem tamam! '{hedef_konu}' listeden silindi.")
            
    except Exception as e:
        logger.error(f"Kritik hata oluştu: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
