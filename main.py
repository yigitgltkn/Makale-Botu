import random
import json
import requests
import traceback
from requests.auth import HTTPBasicAuth

# YENİ KÜTÜPHANE İMPORTLARI
from google import genai
from google.genai import types

# ==========================================
# 1. AYARLAR (Şifrelerini Buraya Yapıştır)
# ==========================================
GEMINI_API_KEY = "AIzaSyDnYQcCC1hcHd5AMe2aubSh0Mg_jApFgSM"
WP_URL = "https://www.hidrosoft.net"
WP_USER = "u2304978"
WP_APP_PASS = "c9Ms KS7o 1AeJ 0Djp h9EJ lcL8"

WP_CATEGORIES = {
    "Hydraulic Modeling": 408,
    "Infrastructure": 401,
    "SCADA": 283,
    "Water - AI": 281
}
# ==========================================
# 2. WORDPRESS HABERLEŞME MODÜLÜ
# ==========================================
def wp_medya_yukle_hafizadan(resim_bytes, dosya_adi="kapak_fotografi.jpg"):
    print(f"\nGörsel (RAM üzerinden) WordPress'e yükleniyor: {dosya_adi}")
    url = f"{WP_URL}/wp-json/wp/v2/media"
    headers = {
        "Content-Disposition": f'attachment; filename="{dosya_adi}"',
        "Content-Type": "image/jpeg"
    }
    response = requests.post(url, headers=headers, data=resim_bytes, auth=HTTPBasicAuth(WP_USER, WP_APP_PASS))
    
    if response.status_code == 201:
        medya_id = response.json().get("id")
        print(f"✅ Görsel başarıyla yüklendi! Medya ID: {medya_id}")
        return medya_id
    else:
        print("❌ Görsel yüklenirken hata:", response.text)
        return None

def wp_etiket_bul_veya_olustur(etiket_adi):
    url = f"{WP_URL}/wp-json/wp/v2/tags"
    auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
    
    search_response = requests.get(url, params={"search": etiket_adi}, auth=auth)
    if search_response.status_code == 200 and len(search_response.json()) > 0:
        for t in search_response.json():
            if t['name'].lower() == etiket_adi.lower():
                return t['id']
        return search_response.json()[0]['id']
    
    create_response = requests.post(url, json={"name": etiket_adi}, auth=auth)
    if create_response.status_code == 201:
        return create_response.json().get("id")
    return None

def makale_yayinla(baslik, icerik, kategori_id, medya_id, etiket_id_listesi):
    print("\nWordPress'e bağlanılıyor, makale ve kapak fotoğrafı gönderiliyor...")
    url = f"{WP_URL}/wp-json/wp/v2/posts"
    
    payload = {
        "title": baslik,
        "content": icerik,
        "status": "publish",
        "categories": [kategori_id],
        "tags": etiket_id_listesi
    }
    
    if medya_id:
        payload["featured_media"] = medya_id
    
    auth = HTTPBasicAuth(WP_USER, WP_APP_PASS)
    headers = {"Content-Type": "application/json"}
    
    response = requests.post(url, json=payload, auth=auth, headers=headers)
    
    if response.status_code == 201:
        print(f"\n✅ HARİKA! Makale başarıyla sitende yayımlandı!")
        print(f"Makale Linki: {response.json().get('link')}")
    else:
        print("\n❌ WordPress'e gönderilirken bir hata oluştu:", response.text)

# ==========================================
# 3. ANA ÇALIŞTIRMA MANTIĞI
# ==========================================
try:
    print("Bot başlatılıyor, lütfen bekleyin...\n")
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    secilen_kategori_adi = random.choice(list(WP_CATEGORIES.keys()))
    kategori_id = WP_CATEGORIES[secilen_kategori_adi]
    print(f"Seçilen Kategori: {secilen_kategori_adi} (ID: {kategori_id})")
    
    print("Yapay zeka bu kategori için rekabetçi bir başlık düşünüyor...")
    baslik_prompt = f"""Act as an expert technical editor. Generate a highly engaging, SEO-optimized blog post title about '{secilen_kategori_adi}' in the energy, water software, SCADA, or AI engineering industry. 
    CRITICAL RULE: The title MUST be either:
1.	A competitive comparison (e.g., 'A vs B: Which is better for...', 'Claude vs ChatGPT for...').
2.	A 'Top X' list (e.g., 'Top 5 SCADA Screen Design Tools...').
3.	A specific 'Best for' guide (e.g., 'Best Hydraulic Modeling Software for Beginners').
4.	Ultrasonic vs electromagnetic flowmeter, which is more suitable?
5.	How to develop SCADA with Claude AI from start to finish? Learning from scratch.
    Return ONLY the exact title text. No quotes."""
    
    baslik_yaniti = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=baslik_prompt
    )
    uretilen_baslik = baslik_yaniti.text.strip().replace('"', '')
    print(f"🤖 Üretilen Başlık: {uretilen_baslik}")
    
    print(f"\n1. Makale, tablolar ve etiketler yazılıyor ('gemini-3-flash-preview')...")
    
    # YENİ: Meta Açıklaması kuralı eklendi!
    makale_prompt = f"""
    Write a highly competitive, engaging, and SEO-optimized technical article in English about "{uretilen_baslik}".
    Target audience: Software engineers, SCADA developers, and water infrastructure professionals.
    
    CRITICAL RULES:
    1. META DESCRIPTION HOOK: The VERY FIRST paragraph MUST be exactly 1-2 sentences (strictly under 160 characters). It must act as a high-converting SEO Meta Description that perfectly summarizes the value of the article and compels the user to click.
    2. The article MUST be at least 700 words.
    3. MUST include at least one detailed HTML comparison <table> (e.g., comparing features, pricing, or pros/cons). Use proper <table>, <tr>, <th>, <td> tags.
    4. Use proper HTML formatting overall (<h2>, <h3>, <ul>, <strong>).
    5. Provide 3 to 5 highly relevant SEO tags as a JSON array.
    
    You MUST return the response ONLY as a valid JSON object exactly like this:
    {{"content": "...", "tags": ["tag1", "tag2", "tag3"]}}
    """
    
    response_text = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=makale_prompt
    )
    raw_text = response_text.text.strip()
    
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
        
    makale_verisi = json.loads(raw_text.strip())
    icerik = makale_verisi.get("content", "")
    uretilen_etiketler = makale_verisi.get("tags", [])
    print("✅ Makale metni ve tablolar başarıyla oluşturuldu!")

    print(f"\nEtiketler WordPress'e işleniyor: {uretilen_etiketler}")
    etiket_id_listesi = []
    for etiket in uretilen_etiketler:
        e_id = wp_etiket_bul_veya_olustur(etiket)
        if e_id:
            etiket_id_listesi.append(e_id)

    print(f"\n2. Kapak görseli oluşturuluyor ('gemini-3.1-flash-image-preview')...")
    gorsel_prompt = f"A high-quality, professional, realistic blog cover image for the technical topic: '{uretilen_baslik}'. Industrial, modern, clean style, no text in the image."
    
    response_image = client.models.generate_content(
        model='gemini-3.1-flash-image-preview',
        contents=[gorsel_prompt]
    )
    
    resim_bytes = None
    for part in response_image.parts:
        if part.inline_data is not None:
            resim_bytes = part.inline_data.data 
            break
            
    if not resim_bytes:
        raise ValueError("Modelden görsel verisi alınamadı!")
    print("✅ Görsel başarıyla oluşturuldu!")

    dosya_adi = f"kapak_{secilen_kategori_adi.replace(' ', '_').lower()}.jpg"
    medya_id = wp_medya_yukle_hafizadan(resim_bytes, dosya_adi=dosya_adi)
    
    makale_yayinla(uretilen_baslik, icerik, kategori_id, medya_id, etiket_id_listesi)

except json.JSONDecodeError:
    print("\n❌ Makale JSON formatında oluşturulamadı. Lütfen prompt'u veya model yanıtını kontrol edin.")
    traceback.print_exc()
except Exception as e:
    print(f"\n❌ Beklenmeyen bir hata oluştu: {e}")
    traceback.print_exc()
finally:
    input("\nÇıkmak için Enter tuşuna basın...")
