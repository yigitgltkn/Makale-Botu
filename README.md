# 🤖 Otonom İçerik Ajanı (Agentic WP Publisher)

Bu depo (repository), son derece teknik B2B mühendislik makaleleri sentezleyen, bağlama uygun kapak görselleri üreten ve bunları REST API'ler aracılığıyla bir CMS'e (WordPress) otomatik olarak dağıtan uçtan uca, otonom bir Üretken Yapay Zeka (Generative AI) boru hattını (pipeline) içermektedir.

## 🚀 Sistem Mimarisi ve Özellikler

* **Otonom İş Akışı (Agentic Workflow) ve Persona Enjeksiyonu:** Genelgeçer (generic) içeriklerden kaçınmak için dinamik olarak uzman personalar (örn. "Kıdemli SCADA Mimarı", "Siber Güvenlik Denetçisi") atanır ve LLM bu spesifik rollerde hedef kitleye yönelik içerik üretir.
* **Yapılandırılmış Çıktı (Structured Output) ve RAG Elementleri:** Sistem entegrasyonunun güvenilirliği için LLM, katı bir JSON formatında çıktı vermeye zorlanır. Ayrıca sistem, CMS üzerinden son yayınlanan makaleleri API ile çeker ve LLM'e bağlam (context) olarak sunar. Böylece model, doğal ve anlamsal (semantic) iç linkleme yapar.
* **Çoklu Modalite (Multimodal Generation):** Sadece metin değil, `gemini-3.1-flash-image-preview` modeli kullanılarak makale bağlamına uygun, profesyonel teknik çizim veya şematik kapak görselleri sıfırdan üretilir.
* **Otomatize Edilmiş Dağıtım (Deployment) Süreci:** Medya yüklemeleri (disk I/O darboğazını önlemek için doğrudan RAM byte'ları üzerinden), etiket (tag) eşleştirme/oluşturma, kategori atama ve nihai HTML yayınlama işlemleri sıfır insan müdahalesi ile gerçekleşir.
* **Teknoloji Yığını (Tech Stack):** Python 3.14, Google GenAI SDK, WordPress REST API, JSON.

## ⚙️ Sistem Nasıl Çalışıyor?
1. **Bağlam Çıkarımı (Context Retrieval):** Hedef platformdan güncel veriler (son makaleler) çekilir.
2. **Görev Ataması:** Anahtar kelime kuyruğundan sıradaki hedef konu alınır.
3. **LLM Sentezi (Metin):** SEO optimizasyonlu başlık, meta açıklaması ve HTML formatında kapsamlı teknik rehber üretilir.
4. **LLM Sentezi (Görsel):** Seçilen sanat stiline göre konuya uygun bir kapak görseli oluşturulur.
5. **Yayınlama ve Durum Güncelleme:** Sentezlenen veri paketi CMS'e itilir (push) ve işlem başarılıysa kuyruk (state) güncellenir.
