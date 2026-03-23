import requests
import time
import argparse

BASE_SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"
BASE_DETAIL_URL = "https://card.wb.ru/cards/v2/detail"

def fetch_search_results(query, max_pages=5):
    nm_ids = []
    print(f"Поиск товаров по запросу: '{query}'")
    for page in range(1, max_pages + 1):
        params = {
            "query": query,
            "resultset": "catalog",
            "page": page,
            "sort": "popular"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        try:
            print(f"Загрузка страницы {page}...")
            response = requests.get(BASE_SEARCH_URL, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
            products = data.get("data", {}).get("products", [])
            if not products:
                print(f"Товары на странице {page} не найдены.")
                break
            for p in products:
                nm_ids.append(p.get("id"))
            time.sleep(1)
        except Exception as e:
            print(f"Ошибка при загрузке страницы {page}: {e}")
            break
    print(f"Найдено {len(nm_ids)} товаров.")
    return nm_ids

def fetch_product_details(nm_ids):
    all_products = []
    batch_size = 50
    print("Загрузка полных данных о товарах...")
    for i in range(0, len(nm_ids), batch_size):
        batch = nm_ids[i:i + batch_size]
        print(f"Обработка партии {i//batch_size + 1}/{len(nm_ids)//batch_size + 1}...")
        nm_str = ";".join(str(nm_id) for nm_id in batch)
        params = {
            "appType": "1",
            "curr": "rub",
            "dest": "-1257786",
            "nm": nm_str
        }
        try:
            response = requests.get(BASE_DETAIL_URL, params=params)
            data = response.json()
            products = data.get("data", {}).get("products", [])
            for p in products:
                nm_id = p.get('id')
                item = {
                    "id": nm_id,
                    "name": p.get('name', ''),
                    "price": p.get('salePriceU', 0) / 100,
                    "rating": p.get('rating', 0),
                    "feedbacks": p.get('feedbacks', 0),
                    "brand": p.get('brand', '')
                }
                all_products.append(item)
            time.sleep(0.5)
        except Exception as e:
            print(f"Ошибка при загрузке деталей товаров: {e}")
    return all_products

def main():
    parser = argparse.ArgumentParser(description="Wildberries Catalog Parser")
    parser.add_argument("--query", default="пальто из натуральной шерсти", help="Поисковый запрос")
    parser.add_argument("--pages", type=int, default=3, help="Количество страниц для обхода")
    args = parser.parse_args()
    
    nm_ids = fetch_search_results(args.query, max_pages=args.pages)
    if not nm_ids:
        print("Не найдено товаров по данному запросу.")
        return
        
    products = fetch_product_details(nm_ids)
    print(f"Спарсено {len(products)} товаров.")
    
    # Дальше нужно добавить экспорт в эксель

if __name__ == "__main__":
    main()
