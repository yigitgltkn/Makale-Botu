import os
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
    "Energy": 496,
    "GIS & Mapping": 524,
    "IIoT & Edge": 523,
    "AI & Automation": 281
}

# ==========================================
# 2. WORDPRESS HABERLEŞME MODÜLÜ
# ==========================================
def wp_son_makaleleri_getir(limit=5):
    """Sitedeki en son yayınlanan makaleleri çeker (İç linkleme için)"""
    print("\nSiteden güncel makale linkleri çekiliyor...")
    url = f"{WP_URL}/wp-json/wp/v2/posts"
    params = {
        "per_page": limit,
        "status": "publish",
        "_fields": "title,link"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            makaleler = response.json()
            link_listesi = []
            for m in makaleler:
                baslik = html.unescape(m.get("title", {}).get("rendered", ""))
                link = m.get("link", "")
                link_listesi.append(f"- Title: '{baslik}' | URL: {link}")
            
            if link_listesi:
                print(f"✅ {len(link_listesi)} adet makale başarıyla çekildi.")
                return "\n".join(link_listesi)
            else:
                print("⚠️ Sitede henüz yayınlanmış makale bulunamadı.")
                return ""
        else:
            print("❌ Makaleler çekilemedi:", response.text)
            return ""
    except Exception as e:
        print("❌ Makale çekme hatası:", e)
        return ""

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
        return True
    else:
        print("\n❌ WordPress'e gönderilirken bir hata oluştu:", response.text)
        return False

# ==========================================
# 3. ANA ÇALIŞTIRMA MANTIĞI
# ==========================================
try:
    print("Bot başlatılıyor, lütfen bekleyin...\n")
    
    if not GEMINI_API_KEY or not WP_APP_PASS:
        raise ValueError("❌ API Anahtarları eksik! Lütfen ortam değişkenlerini kontrol edin.")

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 1. Siteden Mevcut Makaleleri Çek (İç Linkleme İçin)
    mevcut_makaleler_str = wp_son_makaleleri_getir(limit=5)

    # 2. Dosyadan Konu Okuma (HENÜZ SİLME)
    dosya_adi = "keywords.txt"
    if not os.path.exists(dosya_adi):
        raise FileNotFoundError(f"❌ '{dosya_adi}' bulunamadı! Lütfen kelime listenizi ekleyin.")

    with open(dosya_adi, "r", encoding="utf-8") as file:
        satirlar = [satir.strip() for satir in file.readlines() if satir.strip()]

    if not satirlar:
        raise ValueError(f"❌ '{dosya_adi}' dosyası boş! Lütfen yeni konular ekleyin.")

    secilen_hedef_konu = satirlar[0]

    print(f"🎯 Hedeflenen Niş Konu: {secilen_hedef_konu}")
    print(f"Kalan Konu Sayısı: {len(satirlar)}")

    # 3. Dinamik Şablon ve Persona Seçimi
    hedef_kitleler = ["Senior SCADA Engineers in NA/EU", "Water Infrastructure Managers", "Industrial Software Developers", "Energy Grid Architects"]
    yazar_personasi = [
        "a strict, data-driven Senior SCADA Architect",
        "a highly practical Field Automation Engineer",
        "an academic researcher focusing on Water Infrastructure AI",
        "a pragmatic Industrial Cybersecurity (IEC 62443) Auditor"
    ]
    makale_yapisi = [
        "A step-by-step technical troubleshooting and implementation guide.",
        "A deep-dive technical case study focusing on real-world engineering constraints.",
        "A rigorous comparison format highlighting hidden technical pitfalls and performance metrics.",
        "A highly practical 'How-To' guide featuring copy-pasteable solutions."
    ]

    secilen_kitle = random.choice(hedef_kitleler)
    secilen_persona = random.choice(yazar_personasi)
    secilen_yapi = random.choice(makale_yapisi)

    # --- BAŞLIK ÜRETİMİ ---
    print("\nYapay zeka bu konu için rekabetçi bir başlık düşünüyor...")
    baslik_prompt = f"""Act as {secilen_persona} writing for a B2B engineering blog. 
    Generate ONE highly engaging, click-worthy, SEO-optimized blog post title specifically about '{secilen_hedef_konu}'. 
    Target audience: {secilen_kitle}.
    CRITICAL RULE 1: The title MUST use click-trigger formats such as "How-To:", "The Ultimate Guide:", "Practical Examples:", or "Step-by-Step:".
    CRITICAL RULE 2: It must sound like an advanced engineering guide, NOT a boring academic paper.
    Return ONLY the exact title text. No quotes, no extra formatting."""
    
    baslik_yaniti = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=baslik_prompt,
        config=types.GenerateContentConfig(temperature=0.8)
    )
    uretilen_baslik = baslik_yaniti.text.strip().replace('"', '')
    print(f"🤖 Üretilen Başlık: {uretilen_baslik}")
    
    # --- UZMAN SEVİYESİ MAKALE, AKILLI KATEGORİ VE İÇ LİNKLEME ---
    print(f"\n1. Makale yazılıyor, iç linkler yerleştiriliyor ve kategori seçiliyor...")
    kategoriler_str = json.dumps(WP_CATEGORIES)

    makale_prompt = f"""
    Act as {secilen_persona}. Write a highly competitive, expert-level B2B technical article in English about "{uretilen_baslik}".
    Target audience: {secilen_kitle}.

    CRITICAL RULES:
    1. STRUCTURE: Format: {secilen_yapi} The article MUST be comprehensive (at least 800 words).
    2. META DESCRIPTION: The VERY FIRST paragraph MUST be exactly 1-2 sentences acting as a high-converting SEO Meta Description.
    3. PRACTICAL VALUE: Include at least one detailed code block (C#, Python, SQL) or configuration snippet in <pre><code> tags.
    4. COMPARISON/DATA: MUST include at least one detailed HTML <table>.
    5. FORMATTING: Use strict, clean HTML (<h2>, <h3>, <ul>, <strong>). Do NOT wrap the HTML in markdown blocks.
    6. SEO TAGS: Provide 3 to 5 highly relevant SEO tags.
    7. CATEGORY ASSIGNMENT: Analyze the topic and assign the most appropriate category ID from this dictionary: {kategoriler_str}
    
    8. INTERNAL LINKING (CRITICAL): 
    Here are the recently published articles on our site:
    {mevcut_makaleler_str}
    If the list above is not empty, you MUST naturally embed 1-2 HTML <a> tags pointing EXACTLY to those URLs. Match the context of your current article to the title of the provided links. Use varied and natural anchor text (do not just copy the exact title). Do NOT invent fake URLs. If no provided link is relevant, skip internal linking.

    Output format MUST be a single valid JSON object with EXACTLY three keys: 
    - "content": A string containing the full HTML article.
    - "tags": An array of strings containing the tags.
    - "category_id": An integer representing the chosen category ID.
    """
    
    response_text = client.models.generate_content(
        model='gemini-3-flash-preview',
        contents=makale_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.6
        )
    )
    
    makale_verisi = json.loads(response_text.text)
    icerik = makale_verisi.get("content", "")
    uretilen_etiketler = makale_verisi.get("tags", [])
    
    # Kategori İşlemleri
    kategori_id = makale_verisi.get("category_id", 401) 
    kategori_isim_list = [k for k, v in WP_CATEGORIES.items() if v == kategori_id]
    kategori_isim = kategori_isim_list[0] if kategori_isim_list else "Infrastructure"
    
    print("✅ Uzman seviyesi makale başarıyla oluşturuldu!")
    print(f"📂 Yapay Zekanın Seçtiği Kategori: {kategori_isim} (ID: {kategori_id})")

    # --- ETİKETLER ---
    print(f"\nEtiketler WordPress'e işleniyor: {uretilen_etiketler}")
    etiket_id_listesi = []
    for etiket in uretilen_etiketler:
        e_id = wp_etiket_bul_veya_olustur(etiket)
        if e_id:
            etiket_id_listesi.append(e_id)

    # --- GÖRSEL ÜRETİMİ ---
    print(f"\n2. Kapak görseli oluşturuluyor ('gemini-3.1-flash-image-preview')...")
    gorsel_stilleri = [
        "Blueprint/schematic technical drawing style, dark mode",
        "Photorealistic industrial control room, cinematic lighting",
        "Minimalist modern tech corporate illustration",
        "High-tech server rack and SCADA screens, isometric 3D render",
        "Futuristic AI laboratory setting, high contrast"
    ]
    secilen_stil = random.choice(gorsel_stilleri)
    gorsel_prompt = f"A professional blog cover image for the engineering topic: '{uretilen_baslik}'. Art style: {secilen_stil}. Clean composition, NO text, NO letters, NO words."
    
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
    print(f"✅ Görsel başarıyla oluşturuldu! (Kullanılan Stil: {secilen_stil})")

    # --- YAYINLAMA ---
    dosya_adi_medya = f"kapak_{kategori_isim.replace(' ', '_').replace('&', 'and').lower()}_{random.randint(1000,9999)}.jpg"
    medya_id = wp_medya_yukle_hafizadan(resim_bytes, dosya_adi=dosya_adi_medya)
    
    basari_durumu = makale_yayinla(uretilen_baslik, icerik, kategori_id, medya_id, etiket_id_listesi)

    # ==========================================
    # BAŞARILI YAYIN SONRASI DOSYADAN SİLME
    # ==========================================
    if basari_durumu:
        satirlar.pop(0) 
        with open(dosya_adi, "w", encoding="utf-8") as file:
            for satir in satirlar:
                file.write(satir + "\n")
        print(f"✅ İşlem tamamlandı! '{secilen_hedef_konu}' listeden güvenli bir şekilde silindi.")
    else:
        print("⚠️ Makale yayınlanamadığı için kelime dosyadan silinmedi. Bir sonraki çalışmada tekrar denenecek.")

except json.JSONDecodeError:
    print("\n❌ Makale JSON formatında oluşturulamadı. Lütfen logu inceleyin.")
    traceback.print_exc()
except Exception as e:
    print(f"\n❌ Beklenmeyen bir hata oluştu: {e}")
    traceback.print_exc()
