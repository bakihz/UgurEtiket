from PIL import Image
import os
import sys
import platform
import subprocess
import tkinter as tk
from tkinter import filedialog

## --- GÜNCEL AYARLAR ---
import sys # sys eklemeyi unutma
# ... (eski BASE_DIR kısmını sil)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

GIRIS_KLASORU = os.path.join(BASE_DIR, "output", "Resimler")
VARSAYILAN_CIKTI_KLASORU = os.path.join(BASE_DIR, "output")

# A4 Boyutu (300 DPI)
A4_GENISLIK = 2480
A4_YUKSEKLIK = 3508

def dosyayi_ac(dosya_yolu):
    """PDF dosyasını işletim sisteminin varsayılan programıyla açar"""
    try:
        if platform.system() == 'Windows':
            os.startfile(dosya_yolu)
        elif platform.system() == 'Darwin':  # macOS
            subprocess.call(('open', dosya_yolu))
        else:  # Linux
            subprocess.call(('xdg-open', dosya_yolu))
        print("✅ Dosya otomatik açıldı.")
    except Exception as e:
        print(f"⚠️ Dosya açılırken hata: {e}")

def pdf_olustur():
    # 1. Klasördeki PNG dosyalarını bul
    if not os.path.exists(GIRIS_KLASORU):
        print(f"❌ Hata: '{GIRIS_KLASORU}' klasörü bulunamadı.")
        return

    dosyalar = [f for f in os.listdir(GIRIS_KLASORU) if f.endswith(".png")]
    # Windows sıralaması (1, 10, 2 yerine 1, 2, 10 sıralaması için)
    dosyalar.sort(key=lambda x: int(x.split('_')[0]) if x.split('_')[0].isdigit() else x)

    if not dosyalar:
        print("⚠️ Klasörde hiç PNG dosyası yok. Önce etiket basmalısın.")
        return

    print(f"📄 Toplam {len(dosyalar)} etiket bulundu. PDF hazırlanıyor...")

    pdf_sayfalari = []

    # 2. Dosyaları ikili ikili al (0 ve 1, 2 ve 3 gibi)
    for i in range(0, len(dosyalar), 2):
        # A4 boyutunda boş beyaz bir sayfa oluştur
        sayfa = Image.new('RGB', (A4_GENISLIK, A4_YUKSEKLIK), 'white')

        # --- ÜST ETİKET (1. Resim) ---
        img1_yolu = os.path.join(GIRIS_KLASORU, dosyalar[i])
        img1 = Image.open(img1_yolu)
        img1 = img1.resize((A4_GENISLIK, A4_YUKSEKLIK // 2))
        sayfa.paste(img1, (0, 0))

        # --- ALT ETİKET (2. Resim - Varsa) ---
        if i + 1 < len(dosyalar):
            img2_yolu = os.path.join(GIRIS_KLASORU, dosyalar[i+1])
            img2 = Image.open(img2_yolu)
            img2 = img2.resize((A4_GENISLIK, A4_YUKSEKLIK // 2))
            sayfa.paste(img2, (0, A4_YUKSEKLIK // 2))

        pdf_sayfalari.append(sayfa)
        print(f"✅ Sayfa {len(pdf_sayfalari)} işlendi...")

    if not pdf_sayfalari:
        return

    # 3. KULLANICIYA NEREYE KAYDEDECEĞİNİ SOR (Save As Dialog)
    # Eğer arayüzden çalışıyorsa zaten bir root pencere vardır, yoksa gizli oluştur
    root = tk.Tk()
    root.withdraw() # Pencereyi gizle
    
    # Pencerenin her zaman üstte kalmasını sağla
    root.attributes('-topmost', True)

    kayit_yolu = filedialog.asksaveasfilename(
        initialdir=VARSAYILAN_CIKTI_KLASORU,
        title="PDF Dosyasını Kaydet",
        initialfile="Ugur_Etiketleri.pdf",
        defaultextension=".pdf",
        filetypes=[("PDF Dosyası", "*.pdf")]
    )
    
    # İşimiz bitince pencereyi yok et
    root.destroy()

    # Kullanıcı "İptal" derse
    if not kayit_yolu:
        print("❌ Kayıt işlemi iptal edildi.")
        return

    # 4. KAYDET
    ilk_sayfa = pdf_sayfalari[0]
    ilk_sayfa.save(kayit_yolu, save_all=True, append_images=pdf_sayfalari[1:])
    
    print(f"🎉 PDF Başarıyla Kaydedildi:\n📂 {kayit_yolu}")

    # 5. OTOMATİK AÇ
    dosyayi_ac(kayit_yolu)

if __name__ == "__main__":
    pdf_olustur()