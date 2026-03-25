from curl_cffi import requests
import json
import time
import os
from openpyxl import Workbook
from openpyxl.styles import Font
import argparse

BASE_SEARCH_URL = "https://search.wb.ru/exactmatch/ru/common/v4/search"
BASE_DETAIL_URL = "https://card.wb.ru/cards/v2/detail"

def get_basket_id(short_id):
    vol = short_id // 100000
    if 0 <= vol <= 143: return "01"
    elif 144 <= vol <= 287: return "02"
    elif 288 <= vol <= 431: return "03"
    elif 432 <= vol <= 719: return "04"
    elif 720 <= vol <= 1007: return "05"
    elif 1008 <= vol <= 1061: return "06"
    elif 1062 <= vol <= 1115: return "07"
    elif 1116 <= vol <= 1169: return "08"
    elif 1170 <= vol <= 1313: return "09"
    elif 1314 <= vol <= 1601: return "10"
    elif 1602 <= vol <= 1655: return "11"
    elif 1656 <= vol <= 1919: return "12"
    elif 1920 <= vol <= 2045: return "13"
    elif 2046 <= vol <= 2189: return "14"
    elif 2190 <= vol <= 2405: return "15"
    elif 2406 <= vol <= 2621: return "16"
    elif 2622 <= vol <= 2837: return "17"
    elif 2838 <= vol <= 3053: return "18"
    elif 3054 <= vol <= 3269: return "19"
    elif 3270 <= vol <= 3485: return "20"
    elif 3486 <= vol <= 3701: return "21"
    elif 3702 <= vol <= 3917: return "22"
    elif 3918 <= vol <= 4133: return "23"
    elif 4134 <= vol <= 4349: return "24"
    elif 4350 <= vol <= 4565: return "25"
    else: return "26"

def get_images(nm_id, count=3):
    vol = nm_id // 100000
    part = nm_id // 1000
    basket = get_basket_id(nm_id)
    urls = []
    for i in range(1, count + 1):
        url = f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{nm_id}/images/c516x688/{i}.webp"
        urls.append(url)
    return urls

def fetch_search_results(query, max_pages=5):
    nm_ids = []
    print(f"Поиск товаров по запросу: '{query}'")
    for page in range(1, max_pages + 1):
        params = {
            "query": query,
            "resultset": "catalog",
            "page": page,
            "sort": "popular",
            "appType": "1",
            "curr": "rub",
            "dest": "-1257786",
            "spp": "30"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        try:
            print(f"Загрузка страницы {page}...")
            response = requests.get(BASE_SEARCH_URL, params=params, headers=headers, impersonate="chrome110")
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        try:
            response = requests.get(BASE_DETAIL_URL, params=params, headers=headers, impersonate="chrome110")
            data = response.json()
            products = data.get("data", {}).get("products", [])
            for p in products:
                nm_id = p.get('id')
                options = p.get('grouped_options', [])
                charcs = {}
                for group in options:
                    group_name = group.get('groupName', '')
                    for opt in group.get('options', []):
                        key = f"{group_name}: {opt.get('name')}" if group_name else opt.get('name')
                        charcs[key] = opt.get('value')
                if not charcs and p.get('options'):
                    for opt in p.get('options', []):
                        charcs[opt.get('name', '')] = opt.get('value', '')
                country = next((v for k, v in charcs.items() if 'страна производства' in k.lower()), "")
                total_stock = 0
                sizes = []
                for size in p.get('sizes', []):
                    size_name = size.get('origName', '')
                    if size_name:
                        sizes.append(size_name)
                    for stock in size.get('stocks', []):
                        total_stock += stock.get('qty', 0)
                price = 0
                if p.get('sizes'):
                    price_info = p.get('sizes')[0].get('price', {})
                    if price_info:
                        price = price_info.get('product', 0) / 100
                if price == 0 and p.get('salePriceU'):
                    price = p.get('salePriceU', 0) / 100
                supplier_id = p.get('supplierId')
                supplier_name = p.get('supplier')
                supplier_url = f"https://www.wildberries.ru/seller/{supplier_id}" if supplier_id else ""
                images_urls = get_images(nm_id, p.get('pics', 3))
                item = {
                    "url": f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx",
                    "id": nm_id,
                    "name": p.get('name', ''),
                    "price": price,
                    "description": p.get('description', ''),
                    "images": ", ".join(images_urls),
                    "seller": supplier_name,
                    "seller_url": supplier_url,
                    "sizes": ", ".join(sizes),
                    "stock": total_stock,
                    "rating": p.get('rating', 0),
                    "feedbacks": p.get('feedbacks', 0),
                    "country": country,
                    "characteristics": charcs
                }
                all_products.append(item)
            time.sleep(0.5)
        except Exception as e:
            print(f"Ошибка при загрузке деталей товаров: {e}")
    return all_products

def fetch_dynamic_product_details(nm_ids):
    all_products_detailed = []
    fast_details = fetch_product_details(nm_ids)
    print("Загрузка полных описаний и характеристик...")
    for item in fast_details:
        nm_id = item['id']
        vol = nm_id // 100000
        part = nm_id // 1000
        basket = get_basket_id(nm_id)
        info_url = f"https://basket-{basket}.wbbasket.ru/vol{vol}/part{part}/{nm_id}/info/ru/card.json"
        try:
            resp = requests.get(info_url, timeout=5, impersonate="chrome110")
            if resp.status_code == 200:
                data = resp.json()
                item['description'] = data.get('description', '')
                options = data.get('grouped_options', [])
                if options:
                    for group in options:
                        group_name = group.get('groupName', '')
                        for opt in group.get('options', []):
                            key = f"{group_name}: {opt.get('name', '')}" if group_name else opt.get('name', '')
                            item['characteristics'][key] = opt.get('value', '')
                if not item['seller'] and 'seller_name' in data:
                    item['seller'] = data.get('seller_name')
        except Exception:
            pass
        if not item['country']:
            for k, v in item['characteristics'].items():
                if 'страна производства' in k.lower():
                    item['country'] = v
                    break
        all_products_detailed.append(item)
    return all_products_detailed

def export_to_xlsx(products, filepath):
    if not products:
        print(f"Нет данных для экспорта в {filepath}")
        return
    wb = Workbook()
    ws = wb.active
    ws.title = "Catalog"
    headers = [
        "Ссылка на товар", "Артикул", "Название", "Цена", "Описание",
        "Ссылки на изображения", "Название селлера", "Ссылка на селлера",
        "Размеры товара", "Остатки", "Рейтинг", "Количество отзывов"
    ]
    all_charcs = set()
    for p in products:
        for k in p.get("characteristics", {}).keys():
            all_charcs.add(k)
    charc_headers = sorted(list(all_charcs))
    headers.extend(charc_headers)
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for p in products:
        row = [
            p['url'],
            p['id'],
            p['name'],
            p['price'],
            p['description'],
            p['images'],
            p['seller'],
            p['seller_url'],
            p['sizes'],
            p['stock'],
            p['rating'],
            p['feedbacks']
        ]
        charcs = p.get('characteristics', {})
        for ch in charc_headers:
            row.append(charcs.get(ch, ""))
        ws.append(row)
    wb.save(filepath)
    print(f"Сохранено {len(products)} товаров в {filepath}")

def main():
    parser = argparse.ArgumentParser(description="Wildberries Catalog Parser")
    parser.add_argument("--query", default="пальто из натуральной шерсти", help="Поисковый запрос")
    parser.add_argument("--pages", type=int, default=10, help="Количество страниц для обхода")
    args = parser.parse_args()
    
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(out_dir, exist_ok=True)
    full_path = os.path.join(out_dir, "catalog_full.xlsx")
    filtered_path = os.path.join(out_dir, "catalog_filtered.xlsx")
    
    nm_ids = fetch_search_results(args.query, max_pages=args.pages)
    products = []
    if nm_ids:
        products = fetch_dynamic_product_details(nm_ids)
    if not products:
        print("Не найдено товаров по данному запросу через API. Возможно IP заблокирован WB (429).")
        print("Попытка загрузки локальных тестовых данных (data/sample_data.json)...")
        sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sample_data.json")
        if os.path.exists(sample_path):
            with open(sample_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            for p in raw_data:
                nm_id = p.get('id')
                total_stock = 0
                sizes = []
                for size in p.get('sizes', []):
                    size_name = size.get('origName', '')
                    if size_name:
                        sizes.append(size_name)
                    for stock in size.get('stocks', []):
                        total_stock += stock.get('qty', 0)
                charcs = {}
                for group in p.get('grouped_options', []):
                    group_name = group.get('groupName', '')
                    for opt in group.get('options', []):
                        key = f"{group_name}: {opt.get('name', '')}" if group_name else opt.get('name', '')
                        charcs[key] = opt.get('value', '')
                country = ""
                for k, v in charcs.items():
                    if 'страна производства' in k.lower():
                        country = v
                        break
                supplier_id = p.get('supplierId')
                supplier_name = p.get('supplier')
                supplier_url = f"https://www.wildberries.ru/seller/{supplier_id}" if supplier_id else ""
                images_urls = get_images(nm_id, 3)
                item = {
                    "url": f"https://www.wildberries.ru/catalog/{nm_id}/detail.aspx",
                    "id": nm_id,
                    "name": p.get('name', ''),
                    "price": p.get('price', 0),
                    "description": p.get('description', ''),
                    "images": ", ".join(images_urls),
                    "seller": supplier_name,
                    "seller_url": supplier_url,
                    "sizes": ", ".join(sizes),
                    "stock": total_stock,
                    "rating": p.get('rating', 0),
                    "feedbacks": p.get('feedbacks', 0),
                    "country": country,
                    "characteristics": charcs
                }
                products.append(item)
        else:
            print("Локальные тестовые данные не найдены.")
            return
    
    export_to_xlsx(products, full_path)
    
    filtered_products = []
    for p in products:
        rating_ok = p.get('rating', 0) >= 4.5
        price_ok = p.get('price', float('inf')) <= 10000
        country_ok = False
        c = p.get('country', '')
        if isinstance(c, list):
            country_ok = any('россия' in str(x).lower() for x in c)
        else:
            country_ok = 'россия' in str(c).lower()
        if rating_ok and price_ok and country_ok:
            filtered_products.append(p)
    print(f"Найдено {len(filtered_products)} товаров, подходящих под критерии фильтрации.")
    export_to_xlsx(filtered_products, filtered_path)

if __name__ == "__main__":
    main()
