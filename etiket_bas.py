import pandas as pd
import qrcode
from PIL import Image, ImageDraw, ImageFont
import os
import glob 

# --- GÜNCEL AYARLAR ---
import sys # sys eklemeyi unutma
# ... (eski BASE_DIR kısmını sil)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "Resimler")

CSV_FILE = os.path.join(DATA_DIR, "basilacaklar.csv")
SABLON = os.path.join(ASSETS_DIR, "sablon.png")
KLASOR = OUTPUT_DIR 

# Fontlar (Assets klasöründe)
FONT_FIYAT_DOSYASI = os.path.join(ASSETS_DIR, "bauhaus.ttf")
FONT_BASLIK_DOSYASI = os.path.join(ASSETS_DIR, "Montserrat-Bold.ttf")
FONT_OZELLIK_DOSYASI = os.path.join(ASSETS_DIR, "Montserrat-Regular.ttf")
FONT_OZELLIK_BOLD_DOSYASI = os.path.join(ASSETS_DIR, "Montserrat-Bold.ttf")

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def klasoru_temizle():
    """Baskılar klasöründeki eski resimleri siler"""
    dosyalar = glob.glob(f"{KLASOR}/*.png")
    for f in dosyalar:
        try:
            os.remove(f)
        except:
            pass
    print(f"🧹 Klasör temizlendi.")

def metni_satirlara_bol(draw, text, font, max_genislik):
    """Metni kelimelere bölüp sığdırır"""
    words = text.split()
    if not words: return []
    
    satirlar = []
    current_line = words[0]
    
    for word in words[1:]:
        test_line = current_line + " " + word
        bbox = draw.textbbox((0, 0), test_line, font=font)
        w = bbox[2] - bbox[0]
        
        if w <= max_genislik:
            current_line = test_line
        else:
            satirlar.append(current_line)
            current_line = word
            
    satirlar.append(current_line)
    return satirlar


def turkce_buyuk_harf(text):
    """Türkçe i/ı harflerini doğru büyük harf karşılıklarına dönüştürür."""
    return str(text).translate(str.maketrans({"i": "İ", "ı": "I"})).upper()


def etiket_bas():
    if not os.path.exists(CSV_FILE):
        print("❌ CSV yok! Önce main.py çalıştır.")
        return

    klasoru_temizle()
    df = pd.read_csv(CSV_FILE)
    
    if len(df) == 0:
        print("🎉 Değişiklik yok.")
        return

    print(f"🎨 {len(df)} etiket hazırlanıyor...")

    try:
        font_fiyat = ImageFont.truetype(FONT_FIYAT_DOSYASI, 170) 
        font_baslik = ImageFont.truetype(FONT_BASLIK_DOSYASI, 60) 
        font_ozellik = ImageFont.truetype(FONT_OZELLIK_DOSYASI, 32)
        font_ozellik_bold = ImageFont.truetype(FONT_OZELLIK_BOLD_DOSYASI, 32)
    except:
        print("❌ Font hatası! Varsayılan fontlar kullanılıyor.")
        font_fiyat = font_baslik = font_ozellik = font_ozellik_bold = ImageFont.load_default()

    for index, row in df.iterrows():
        try:
            img = Image.open(SABLON)
            draw = ImageDraw.Draw(img)
            
            # --- 1. ÜRÜN ADI ---
            urun_adi = turkce_buyuk_harf(row['Urun Adi'])
            KUTU_SOL, KUTU_SAG = 1100, 1925
            KUTU_GENISLIK = KUTU_SAG - KUTU_SOL
            KUTU_MERKEZ = KUTU_SOL + (KUTU_GENISLIK / 2)
            BASLIK_Y = 50
            
            mevcut_boyut = 60
            font_dinamik = ImageFont.truetype(FONT_BASLIK_DOSYASI, mevcut_boyut)
            while True:
                bbox = draw.textbbox((0, 0), urun_adi, font=font_dinamik)
                w = bbox[2] - bbox[0]
                if w < KUTU_GENISLIK: break
                mevcut_boyut -= 2
                if mevcut_boyut < 30: break
                font_dinamik = ImageFont.truetype(FONT_BASLIK_DOSYASI, mevcut_boyut)

            bbox = draw.textbbox((0, 0), urun_adi, font=font_dinamik)
            w = bbox[2] - bbox[0]
            draw.text((KUTU_MERKEZ - (w/2), BASLIK_Y), urun_adi, fill="white", font=font_dinamik)

            # --- 2. FİYAT ---
            fiyat_text = str(row['Fiyat'])
            fiyat_kutu_genisligi = 780
            fiyat_kutu_yuksekligi = 180
            fiyat_boyutu = 170
            try:
                while True:
                    font_fiyat = ImageFont.truetype(FONT_FIYAT_DOSYASI, fiyat_boyutu)
                    bbox = draw.textbbox((0, 0), fiyat_text, font=font_fiyat)
                    fiyat_genisligi = bbox[2] - bbox[0]
                    fiyat_yuksekligi = bbox[3] - bbox[1]
                    if (
                        fiyat_genisligi <= fiyat_kutu_genisligi
                        and fiyat_yuksekligi <= fiyat_kutu_yuksekligi
                    ) or fiyat_boyutu <= 60:
                        break
                    fiyat_boyutu -= 2
            except OSError:
                font_fiyat = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), fiyat_text, font=font_fiyat)
                fiyat_genisligi = bbox[2] - bbox[0]
                fiyat_yuksekligi = bbox[3] - bbox[1]

            fiyat_x = 540 - (fiyat_genisligi / 2) - bbox[0]
            fiyat_y = 700 - (fiyat_yuksekligi / 2) - bbox[1]
            draw.text((fiyat_x, fiyat_y), fiyat_text, fill="black", font=font_fiyat)

            # --- 3. ÖZELLİKLER ---
            ozellik_listesi = row['Ozellikler'].split("|") if isinstance(row['Ozellikler'], str) else []
            x_liste = 1100  
            y_liste = 160   
            max_metin_genisligi = 800 
            
            # Satır Yüksekliği (Line Height)
            SATIR_YUKSEKLIGI = 40 
            # Madde Boşluğu (Margin Bottom - Bunu azalttım!)
            MADDE_BOSLUGU = 50

            for oz in ozellik_listesi:
                # --- YAMA: Garanti Süresi Düzeltmesi ---
                # Eğer "Garanti Süresi" var ama ":" yoksa, araya ":" ekle
                if "Garanti Süresi" in oz and ":" not in oz:
                     oz = oz.replace("Garanti Süresi", "Garanti Süresi:")
                # ---------------------------------------

                if ":" in oz:
                    parcalar = oz.split(":", 1)
                    baslik = parcalar[0] + ":" 
                    deger = parcalar[1].strip() # Başındaki boşluğu al, biz ekleriz       
                    
                    # 1. Başlığı Kalın Yaz
                    draw.text((x_liste, y_liste), baslik, fill="black", font=font_ozellik_bold)
                    
                    # 2. Başlığın Genişliğini Ölç
                    bbox_baslik = draw.textbbox((0, 0), baslik, font=font_ozellik_bold)
                    baslik_genisligi = bbox_baslik[2] - bbox_baslik[0]
                    
                    # 3. Değeri Yanına Yaz
                    kalan_genislik = max_metin_genisligi - baslik_genisligi
                    
                    bolunmus_degerler = metni_satirlara_bol(draw, deger, font_ozellik, kalan_genislik)
                    
                    if bolunmus_degerler:
                        # İlk satır başlığın yanına (10px boşlukla)
                        draw.text((x_liste + baslik_genisligi + 10, y_liste), bolunmus_degerler[0], fill="black", font=font_ozellik)
                        
                        # Varsa diğer satırlar aşağıya
                        for ek_satir in bolunmus_degerler[1:]:
                            y_liste += SATIR_YUKSEKLIGI
                            if y_liste < 1400:
                                draw.text((x_liste, y_liste), ek_satir, fill="black", font=font_ozellik)

                else:
                    bolunmus_satirlar = metni_satirlara_bol(draw, oz, font_ozellik, max_metin_genisligi)
                    for satir in bolunmus_satirlar:
                        if y_liste < 1400:
                            draw.text((x_liste, y_liste), satir, fill="black", font=font_ozellik)
                        y_liste += SATIR_YUKSEKLIGI
                
                # Bir sonraki maddeyi son satırın altından başlat.
                y_liste += MADDE_BOSLUGU

            # --- 4. QR KOD ---
            qr = qrcode.QRCode(box_size=10, border=1)
            qr.add_data(row['QR Link'])
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white").resize((225,225))
            img.paste(qr_img, (760, 980))

            # --- 5. KAYDET ---
            temiz_ad = str(row['Urun Adi'])[:15].replace(' ', '_').replace('/', '-')
            img.save(f"{KLASOR}/{index+1}_{temiz_ad}.png")
            print(f"✅ Hazır: {row['Urun Adi']}")

        except Exception as e:
            print(f"❌ Hata ({row.get('Urun Adi', '?')}): {e}")

if __name__ == "__main__":
    etiket_bas()