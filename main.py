import requests
from bs4 import BeautifulSoup
import pandas as pd
import urllib3
import re 
import os
import json
from decimal import Decimal, InvalidOperation
from urllib.parse import urljoin, urlparse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- GÜNCEL AYARLAR ---
import sys # sys eklemeyi unutma
# ... (eski BASE_DIR kısmını sil)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
LINK_DOSYASI = os.path.join(DATA_DIR, "urunler.xlsx")
VERITABANI_DOSYASI = os.path.join(DATA_DIR, "veritabani.csv")
BASILACAK_DOSYA = os.path.join(DATA_DIR, "basilacaklar.csv")

# Klasör yoksa hata vermesin diye kontrol
if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
PRODUCT_DATA_PATTERN = re.compile(
    r"PRODUCT_DATA\.push\(JSON\.parse\('((?:\\.|[^'\\])*)'\)\);",
    re.DOTALL,
)

def linkleri_yukle():
    """Excel (XLSX) dosyasından linkleri okur"""
    if not os.path.exists(LINK_DOSYASI):
        print(f"❌ HATA: '{LINK_DOSYASI}' dosyası bulunamadı!")
        print("Lütfen önce 'excel_hazirla.py' dosyasını çalıştır.")
        return []

    try:
        # Excel dosyasını oku
        df = pd.read_excel(LINK_DOSYASI)
        
        # İlk sütunu al (Başlık ne olursa olsun)
        linkler = df.iloc[:, 0].dropna().astype(str).tolist()
        
        # Sadece http ile başlayanları al
        gecerli_linkler = [link.strip() for link in linkler if link.strip().startswith("http")]
        
        print(f"📄 Excel dosyasından {len(gecerli_linkler)} adet link okundu.")
        return gecerli_linkler

    except Exception as e:
        print(f"❌ Dosya okuma hatası: {e}")
        return []

def sayfa_urun_verilerini_oku(html):
    """Uğur sayfalarındaki gömülü ürün/fiyat JSON kayıtlarını döndürür."""
    urunler = []
    for match in PRODUCT_DATA_PATTERN.finditer(html):
        try:
            json_metni = json.loads(f'"{match.group(1)}"')
            urun = json.loads(json_metni)
        except (json.JSONDecodeError, TypeError) as e:
            raise ValueError(f"Ürün verisi çözümlenemedi: {e}") from e
        if isinstance(urun, dict):
            urunler.append(urun)

    if not urunler:
        raise ValueError("Sayfada Uğur ürün verisi (PRODUCT_DATA) bulunamadı.")
    return urunler


def fiyati_duzenle(urun):
    """Site fiyatını etiketlerde kullanılan Türkçe biçime dönüştürür."""
    ham_fiyat = next(
        (
            urun.get(alan)
            for alan in ("sale_price", "total_sale_price", "price", "total_price")
            if urun.get(alan) not in (None, "")
        ),
        None,
    )
    if ham_fiyat is None:
        raise ValueError(f"{urun.get('name', 'Bilinmeyen ürün')} için fiyat bulunamadı.")

    try:
        tutar = Decimal(str(ham_fiyat))
    except InvalidOperation as e:
        raise ValueError(f"Geçersiz ürün fiyatı: {ham_fiyat}") from e
    if not tutar.is_finite():
        raise ValueError(f"Geçersiz ürün fiyatı: {ham_fiyat}")

    yerel_tutar = f"{tutar:,.2f}".replace(",", "\0").replace(".", ",").replace("\0", ".")
    para_birimi = str(urun.get("currency") or "TL").strip()
    return f"{yerel_tutar} {para_birimi}".strip()


def urun_ozelliklerini_oku(soup, sayfa_url, urun):
    """Ürün detay tablosunu; kategori sayfalarında ürün kısa bilgisini kullanır."""
    ozellikler = []
    if "/urun/" in urlparse(sayfa_url).path:
        detay = soup.select_one('[data-qa="product-detail-content"]')
        if detay is None:
            detay = soup.select_one("#product-detail")
        if detay is not None:
            for satir in detay.find_all("tr"):
                hucreler = satir.find_all(["th", "td"], recursive=False)
                for i in range(0, len(hucreler) - 1, 2):
                    baslik = hucreler[i].get_text(" ", strip=True)
                    deger = hucreler[i + 1].get_text(" ", strip=True)
                    if baslik and deger:
                        ozellikler.append(f"• {baslik}: {deger}")

    if not ozellikler:
        kisa_bilgi = str(urun.get("supplier_code") or "").strip()
        if kisa_bilgi:
            ozellikler.append(f"• {kisa_bilgi}")

    return "|".join(ozellikler)


def sayfadan_urunleri_cek(response):
    """Ürün detay veya kategori sayfasından etiket kayıtlarını hazırlar."""
    soup = BeautifulSoup(response.content, "html.parser")
    urunler = sayfa_urun_verilerini_oku(response.text)
    sonuc = []

    for urun in urunler:
        ad = str(urun.get("name") or "").strip()
        if not ad:
            raise ValueError("Sayfadaki bir ürünün adı bulunamadı.")

        urun_url = urljoin(response.url, str(urun.get("url") or response.url))
        sonuc.append(
            {
                "Urun Adi": ad,
                "Fiyat": fiyati_duzenle(urun),
                "Ozellikler": urun_ozelliklerini_oku(soup, response.url, urun),
                "QR Link": urun_url,
            }
        )

    return sonuc

def veri_cek():
    # 0. LİNKLERİ EXCEL'DEN OKU
    URUN_LINKLERI = linkleri_yukle()
    if not URUN_LINKLERI: return 

    # 1. ESKİ VERİLERİ YÜKLE
    eski_veriler = {}
    if os.path.exists(VERITABANI_DOSYASI):
        try:
            df_eski = pd.read_csv(VERITABANI_DOSYASI)
            for index, row in df_eski.iterrows():
                eski_veriler[row['Urun Adi']] = {
                    'Fiyat': str(row['Fiyat']).strip(),
                    'Ozellikler': str(row['Ozellikler']).strip()
                }
            print(f"🧠 Hafızada {len(eski_veriler)} ürün kaydı var.")
        except:
            print("⚠️ Hafıza dosyası sıfırdan oluşturulacak.")

    yeni_tum_urunler = []
    basilacak_urunler = []

    print(f"🚀 {len(URUN_LINKLERI)} ürün taranıyor...\n")

    for url in URUN_LINKLERI:
        try:
            response = requests.get(url, headers=HEADERS, verify=False, timeout=30)
            response.raise_for_status()
            sayfa_urunleri = sayfadan_urunleri_cek(response)
            print(f"📦 {len(sayfa_urunleri)} ürün sayfadan okundu: {url}")

            for yeni_veri in sayfa_urunleri:
                ad = yeni_veri["Urun Adi"]
                fiyat = yeni_veri["Fiyat"]
                ozellik_metni = yeni_veri["Ozellikler"]
                yeni_tum_urunler.append(yeni_veri)

                degisiklik_var = False
                if ad in eski_veriler:
                    eski_kayit = eski_veriler[ad]
                    if eski_kayit["Fiyat"] != fiyat:
                        print(f"🔄 FİYAT DEĞİŞTİ: {ad} ({eski_kayit['Fiyat']} -> {fiyat})")
                        degisiklik_var = True
                    elif eski_kayit["Ozellikler"] != ozellik_metni:
                        print(f"📝 ÖZELLİK GÜNCELLENDİ: {ad}")
                        degisiklik_var = True
                    else:
                        print(f"💤 Aynı: {ad}")
                else:
                    print(f"✨ YENİ ÜRÜN: {ad}")
                    degisiklik_var = True

                if degisiklik_var:
                    basilacak_urunler.append(yeni_veri)

        except Exception as e:
            print(f"❌ Hata: {url} -> {e}")

    # KAYDET
    pd.DataFrame(yeni_tum_urunler).to_csv(VERITABANI_DOSYASI, index=False, encoding="utf-8-sig")
    
    if basilacak_urunler:
        pd.DataFrame(basilacak_urunler).to_csv(BASILACAK_DOSYA, index=False, encoding="utf-8-sig")
        print(f"\n✅ {len(basilacak_urunler)} adet etiket güncellendi. 'etiket_bas.py' çalıştırabilirsin.")
    else:
        print("\n🎉 Değişiklik yok.")
        # Hata vermemesi için boş dosya oluştur
        pd.DataFrame(columns=["Urun Adi", "Fiyat", "Ozellikler", "QR Link"]).to_csv(BASILACAK_DOSYA, index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    veri_cek()