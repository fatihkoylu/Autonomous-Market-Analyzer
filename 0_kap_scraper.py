import time
import csv
import os
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def formatla_tarih(tarih_metni):
    """'Dün 14:30' veya 'Bugün' gibi metinleri standart takvim formatına (GG.AA.YYYY) çevirir."""
    bugun = datetime.now()
    if "Bugün" in tarih_metni or "Bugun" in tarih_metni:
        return bugun.strftime("%d.%m.%Y")
    elif "Dün" in tarih_metni or "Dun" in tarih_metni:
        dun = bugun - timedelta(days=1)
        return dun.strftime("%d.%m.%Y")
    else:
        
        return tarih_metni[:10] if len(tarih_metni) >= 10 else tarih_metni

def kap_hizli_kaziyici():
    print("🟢 KAP Kazıyıcı (Yüksek Tolerans & Tarih Düzeltme) Başlatıldı...")
    
    chrome_options = Options()
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.maximize_window()
    
    driver.get("https://www.kap.org.tr/tr/")
    
    print("\n" + "="*50)
    print("🚨 TARAYICI AÇILDI. KONTROL SİZDE!")
    print("1. Tarihi ayarla (1 Aylık parçalar halinde yapman önerilir).")
    print("2. Şirket Tipi: BIST Şirketleri.")
    print("3. Bildirim Tipi: Özel Durum Açıklaması ve Finansal Rapor.")
    print("4. Ara butonuna bas ve haberler listelenene kadar bekle.")
    print("="*50 + "\n")
    
    input(">>> Haberleri ekranda gördüyseniz ENTER tuşuna basın... ")
    
    print("\n🤖 Butona basılarak liste genişletiliyor. Sunucu gecikmelerine karşı inatçı mod aktif...")
    
    bos_tiklama = 0
    onceki_satir_sayisi = 0
    
    while True:
        try:
            satirlar = driver.find_elements(By.TAG_NAME, "tr")
            mevcut_satir = len(satirlar)
            
            if mevcut_satir == onceki_satir_sayisi:
                bos_tiklama += 1
                
                if bos_tiklama >= 10:
                    print("\n✅ Liste sonuna gelindi veya sunucu daha fazla veri vermiyor.")
                    break
                
                time.sleep(1.5)
            else:
                bos_tiklama = 0
                onceki_satir_sayisi = mevcut_satir

            buton = driver.find_element(By.XPATH, "//*[contains(text(), 'Daha Fazla Göster')]")
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", buton)
            time.sleep(1)
            driver.execute_script("arguments[0].click();", buton)
            print(f"Tablo genişletiliyor... Ekranda {mevcut_satir} satır var.")
            
            
            time.sleep(3)
            
        except Exception:
            print("\n✅ 'Daha Fazla Göster' butonu kayboldu, tıklama işlemi bitti.")
            break

    print(f"\n⚡ Veriler okunuyor ve filtreleniyor...")
    
    html_kaynagi = driver.page_source
    driver.quit() 
    
    soup = BeautifulSoup(html_kaynagi, 'html.parser')
    satirlar = soup.find_all('tr')
    
    tum_haberler = []
    
    for satir in satirlar:
        hucreler = satir.find_all('td')
        
        if len(hucreler) >= 8:
            tarih_metni_ham = hucreler[2].get_text(strip=True)
            hisse_kodu_ham = hucreler[3].get_text(strip=True)
            konu = hucreler[6].get_text(strip=True)
            ozet = hucreler[7].get_text(strip=True)
            
            baslik = f"{konu} - {ozet}"
            
            
            tarih = formatla_tarih(tarih_metni_ham)
            
            
            hisse_kodu = hisse_kodu_ham.split(',')[0].strip()
            
            
            if hisse_kodu and len(hisse_kodu) >= 2 and len(hisse_kodu) <= 7 and " " not in hisse_kodu:
                tum_haberler.append({
                    "Hisse": hisse_kodu.upper(), 
                    "Tarih": tarih, 
                    "Baslik": baslik
                })
                
    
    benzersiz_haberler = []
    gorulenler = set()
    for h in tum_haberler:
        kimlik = f"{h['Hisse']}-{h['Tarih']}-{h['Baslik']}"
        if kimlik not in gorulenler:
            gorulenler.add(kimlik)
            benzersiz_haberler.append(h)

    dosya_adi = "kap_otonom_veri.csv"
    dosya_var_mi = os.path.isfile(dosya_adi)
    
    if benzersiz_haberler:
        with open(dosya_adi, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=["Hisse", "Tarih", "Baslik"])
            if not dosya_var_mi or os.stat(dosya_adi).st_size == 0:
                writer.writeheader()
            for h in benzersiz_haberler:
                writer.writerow(h)
        print(f"\n🎉 İşlem Başarılı! {len(benzersiz_haberler)} adet haber '{dosya_adi}' dosyasına eklendi.")
    else:
        print("\n⚠️ Tabloda kriterlere uygun geçerli haber bulunamadı.")

if __name__ == "__main__":
    kap_hizli_kaziyici()