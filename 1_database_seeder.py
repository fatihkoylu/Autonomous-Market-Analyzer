import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import uuid
import warnings
from tqdm import tqdm

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Distance, VectorParams
from sentence_transformers import SentenceTransformer

warnings.filterwarnings("ignore")

def generate_deterministic_id(ticker, date_str, news):
    
    unique_string = f"{ticker}_{date_str}_{news}"
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, unique_string))

def main():
    print("1. Ham CSV verisi yükleniyor...")
    
    df_kap = pd.read_csv("kap_otonom_veri.csv")
    
    print("2. Gömme (Embedding) Modeli yükleniyor...")
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    
    print("3. Qdrant Veritabanı başlatılıyor...")
    client = QdrantClient(path="./qdrant_db")
    collection_name = "kap_history"
    
    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=model.get_sentence_embedding_dimension(),
                distance=Distance.COSINE
            )
        )

    
    print("4. Borsa geçmişleri topluca indiriliyor (Anti-Ban)...")
    unique_tickers = df_kap['Hisse'].unique()
    stock_histories = {}
    
    for ticker in tqdm(unique_tickers, desc="Hisse Verileri Çekiliyor"):
        yf_ticker = f"{ticker}.IS"
        stock = yf.Ticker(yf_ticker)
        
        try:
            hist = stock.history(period="1y")
            if not hist.empty:
                hist.index = hist.index.tz_localize(None).normalize()
                stock_histories[ticker] = hist
        except Exception:
            continue

    points = []
    print("5. Haberler analiz ediliyor ve Vektörleştiriliyor...")
    
    
    for index, row in tqdm(df_kap.iterrows(), total=df_kap.shape[0], desc="Vektörleştirme"):
        ticker = row['Hisse']
        date_str = row['Tarih']
        news = row['Baslik']
        
        impact_pct = 0.0
        
        
        if ticker in stock_histories:
            hist = stock_histories[ticker]
            available_dates = hist.index.tolist()
            
            
            try:
                if "." in str(date_str):
                    date_obj = datetime.strptime(str(date_str), "%d.%m.%Y")
                else:
                    date_obj = datetime.strptime(str(date_str), "%Y-%m-%d")
                
                
                event_day = next((d for d in available_dates if d >= date_obj), None)
                
                if event_day:
                    idx = available_dates.index(event_day)
                    target_idx = min(idx + 1, len(available_dates) - 1)
                    target_day = available_dates[target_idx]
                    
                    price_before = hist.loc[event_day]["Open"]
                    price_after = hist.loc[target_day]["Close"]
                    
                    if price_before > 0:
                        impact_pct = ((price_after - price_before) / price_before) * 100
                        impact_pct = round(impact_pct, 2)
            except Exception:
                pass 

        
        vector = model.encode(str(news)).tolist()
        
        point = PointStruct(
            id=generate_deterministic_id(ticker, str(date_str), str(news)),
            vector=vector,
            payload={
                "ticker": ticker,
                "news": str(news),
                "date": str(date_str),
                "real_price_impact_pct": impact_pct
            }
        )
        points.append(point)
        
        
        if len(points) >= 500:
            client.upsert(collection_name=collection_name, points=points)
            points = []

    
    if points:
        client.upsert(collection_name=collection_name, points=points)
        
    print("\nİşlem Tamam! Tüm veriler başarıyla Qdrant veritabanına işlendi.")

if __name__ == "__main__":
    main()