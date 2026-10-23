import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# --- DÜZELTME BAŞLANGICI ---
# O sarı uyarı yazılarını görmemek için filtreliyoruz
import warnings
warnings.filterwarnings("ignore") 

# En garanti import yöntemi (Hata vermez)
try:
    from ttkbootstrap.scrolled import ScrolledText
except ImportError:
    from tkinter.scrolledtext import ScrolledText
# --- DÜZELTME BİTİŞİ ---

import pandas as pd
import threading
import sys
import os
import importlib
import time

# Kendi modüllerimiz
import main
import etiket_bas
import pdf_yap

# Dosya Yolları
import sys # sys eklemeyi unutma
# ... (eski BASE_DIR kısmını sil)

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
EXCEL_FILE = os.path.join(DATA_DIR, "urunler.xlsx")
# ... (gerisi aynı)

# --- CANLI LOG YAKALAYICI SINIF ---
class RedirectText(object):
    """Print çıktılarını anlık olarak Text kutusuna yönlendirir"""
    def __init__(self, text_widget):
        self.text_widget = text_widget

    def write(self, string):
        # Arayüz donmasın diye yazdırma işlemini ana döngüye gönderiyoruz
        try:
            self.text_widget.after(0, self._insert, string)
        except:
            pass

    def _insert(self, string):
        try:
            self.text_widget.insert(tk.END, string)
            self.text_widget.see(tk.END)
        except:
            pass

    def flush(self):
        pass

class ModernRobot(ttk.Window):
    def __init__(self):
        super().__init__(themename="yeti") # Tema: yeti, cosmo, litera, minty
        self.title("Uğur Etiket Otomasyonu v2.2")
        self.geometry("1000x750")
        self.place_window_center()
        
        # --- ÜST BAR (HEADER) ---
        header_frame = ttk.Frame(self, bootstyle="primary")
        header_frame.pack(fill=X)
        
        ttk.Label(header_frame, text=" UĞUR ETİKET OTOMASYONU", font=("Impact", 24), bootstyle="inverse-primary").pack(side=LEFT, padx=20, pady=15)
        ttk.Label(header_frame, text="Otomatik Fiyat & Etiket Sistemi", font=("Helvetica", 10), bootstyle="inverse-primary").pack(side=LEFT, pady=25)

        # --- ANA GÖVDE (SEKMELER) ---
        self.tabs = ttk.Notebook(self, bootstyle="primary")
        self.tabs.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # Sekme 1: Operasyon
        self.tab_islem = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_islem, text=" 🖨️ KONTROL PANELİ ")

        # Sekme 2: Liste
        self.tab_liste = ttk.Frame(self.tabs)
        self.tabs.add(self.tab_liste, text=" 📋 ÜRÜN YÖNETİMİ ")

        self.setup_islem_tab()
        self.setup_liste_tab()

        # --- ALT DURUM ÇUBUĞU ---
        self.status_frame = ttk.Frame(self, bootstyle="light")
        self.status_frame.pack(fill=X, side=BOTTOM)
        
        self.lbl_status = ttk.Label(self.status_frame, text="Sistem Hazır.", font=("Arial", 9), bootstyle="inverse-light", padding=5)
        self.lbl_status.pack(side=LEFT)

        self.progress = ttk.Floodgauge(self.status_frame, bootstyle="success", font=("Arial", 8), mask="İşleniyor... {}%", value=0)
        self.progress.pack(side=RIGHT, fill=X, expand=True, padx=10)

    def setup_islem_tab(self):
        # 2 Sütunlu Yapı (Panedwindow düzeltildi)
        paned = ttk.Panedwindow(self.tab_islem, orient=HORIZONTAL)
        paned.pack(fill=BOTH, expand=True, padx=10, pady=10)

        # SOL: BUTONLAR
        left_frame = ttk.Labelframe(paned, text=" İşlem Menüsü ", padding=15, bootstyle="info")
        paned.add(left_frame, weight=1)

        # Büyük Butonlar
        self.btn_veri = ttk.Button(left_frame, text="1. VERİLERİ ÇEK\n(Fiyat Tara)", bootstyle="primary", command=self.baslat_veri_cek)
        self.btn_veri.pack(fill=X, pady=10, ipady=10)

        self.btn_baski = ttk.Button(left_frame, text="2. ETİKETLERİ BAS\n(Resim Oluştur)", bootstyle="warning", command=self.baslat_baski)
        self.btn_baski.pack(fill=X, pady=10, ipady=10)

        self.btn_pdf = ttk.Button(left_frame, text="3. PDF HAZIRLA\n(Baskı Dosyası)", bootstyle="success", command=self.baslat_pdf)
        self.btn_pdf.pack(fill=X, pady=10, ipady=10)

        ttk.Separator(left_frame).pack(fill=X, pady=20)
        
        ttk.Button(left_frame, text="Logları Temizle", bootstyle="secondary-outline", command=self.log_temizle).pack(fill=X)

        # SAĞ: LOG EKRANI (TERMINAL GÖRÜNÜMÜ)
        right_frame = ttk.Labelframe(paned, text=" Canlı İşlem Kayıtları ", padding=5, bootstyle="secondary")
        paned.add(right_frame, weight=3)

        self.txt_log = ScrolledText(right_frame, font=("Consolas", 10), state="normal")
        self.txt_log.pack(fill=BOTH, expand=True, padx=10, pady=10)
        # Hacker modu renkleri
        self.txt_log.configure(bg="#1e1e1e", fg="#00ff00", insertbackground="white")

    def setup_liste_tab(self):
        # Üst: Ekleme
        frame_top = ttk.Frame(self.tab_liste, padding=10)
        frame_top.pack(fill=X)

        self.ent_link = ttk.Entry(frame_top, font=("Arial", 10))
        self.ent_link.pack(side=LEFT, fill=X, expand=True, padx=(0, 10))
        self.ent_link.insert(0, "https://www.ugur.com.tr/urun/...")

        ttk.Button(frame_top, text="➕ LİSTEYE EKLE", bootstyle="success", command=self.urun_ekle).pack(side=RIGHT)

        # Orta: Liste
        columns = ("link",)
        self.tree = ttk.Treeview(self.tab_liste, columns=columns, show="headings", bootstyle="info")
        self.tree.heading("link", text="Takip Edilen Ürün Linkleri")
        self.tree.column("link", width=800)
        
        # Scrollbar
        sb = ttk.Scrollbar(self.tab_liste, orient=VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        
        sb.pack(side=RIGHT, fill=Y)
        self.tree.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # Alt: Silme
        ttk.Button(self.tab_liste, text="🗑️ SEÇİLİ ÜRÜNÜ SİL", bootstyle="danger", command=self.urun_sil).pack(fill=X, padx=10, pady=10)

        self.listeyi_yenile()

    # --- YARDIMCI FONKSİYONLAR ---
    def listeyi_yenile(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        if not os.path.exists(EXCEL_FILE): return
        try:
            df = pd.read_excel(EXCEL_FILE)
            if not df.empty:
                linkler = df.iloc[:, 0].dropna().astype(str).tolist()
                for link in linkler:
                    if "http" in link: self.tree.insert("", END, values=(link,))
        except Exception as e: messagebox.showerror("Hata", str(e))

    def urun_ekle(self):
        link = self.ent_link.get().strip()
        if "http" not in link: return
        try:
            if os.path.exists(EXCEL_FILE): df = pd.read_excel(EXCEL_FILE)
            else: df = pd.DataFrame(columns=["Urun Linkleri"])
            
            yeni = pd.DataFrame([link], columns=[df.columns[0] if len(df.columns)>0 else "Urun Linkleri"])
            df = pd.concat([df, yeni], ignore_index=True)
            df.to_excel(EXCEL_FILE, index=False)
            self.ent_link.delete(0, END)
            self.listeyi_yenile()
            self.log_yaz(f"✅ Eklendi: {link}")
        except Exception as e: messagebox.showerror("Hata", str(e))

    def urun_sil(self):
        sel = self.tree.selection()
        if not sel: return
        link = self.tree.item(sel[0])['values'][0]
        if messagebox.askyesno("Sil?", "Bu ürün silinsin mi?"):
            try:
                df = pd.read_excel(EXCEL_FILE)
                df = df[df.iloc[:, 0] != link]
                df.to_excel(EXCEL_FILE, index=False)
                self.listeyi_yenile()
                self.log_yaz(f"🗑️ Silindi: {link}")
            except Exception as e: messagebox.showerror("Hata", str(e))

    def log_yaz(self, msg):
        try:
            self.txt_log.insert(END, msg + "\n")
            self.txt_log.see(END)
        except: pass
    
    def log_temizle(self):
        self.txt_log.delete('1.0', END)

    def islem_baslat(self, func, name):
        self.btn_veri.config(state="disabled")
        self.btn_baski.config(state="disabled")
        self.btn_pdf.config(state="disabled")
        self.progress.start() 
        self.lbl_status.config(text=f"Çalışıyor: {name}...")

        def thread_target():
            old_stdout = sys.stdout
            sys.stdout = RedirectText(self.txt_log)

            try:
                self.log_yaz(f"\n🚀 {name} BAŞLATILIYOR...\n" + "-"*30)
                importlib.reload(main)
                importlib.reload(etiket_bas)
                importlib.reload(pdf_yap)
                func()
                self.log_yaz("-" * 30 + f"\n✅ {name} TAMAMLANDI.\n")
            except Exception as e:
                self.log_yaz(f"\n❌ HATA OLUŞTU: {e}\n")
            finally:
                sys.stdout = old_stdout 
                self.after(0, self.islem_bitir) 

        threading.Thread(target=thread_target, daemon=True).start()

    def islem_bitir(self):
        try:
            self.btn_veri.config(state="normal")
            self.btn_baski.config(state="normal")
            self.btn_pdf.config(state="normal")
            self.progress.stop()
            self.progress.configure(value=100)
            self.lbl_status.config(text="İşlem Tamamlandı. Yeni görev bekleniyor.")
        except: pass

    def baslat_veri_cek(self): self.islem_baslat(main.veri_cek, "VERİ TARAMA")
    def baslat_baski(self): self.islem_baslat(etiket_bas.etiket_bas, "ETİKET BASIMI")
    def baslat_pdf(self): self.islem_baslat(pdf_yap.pdf_olustur, "PDF OLUŞTURMA")

if __name__ == "__main__":
    app = ModernRobot()
    app.mainloop()