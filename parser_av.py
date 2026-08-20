import aiohttp
from bs4 import BeautifulSoup
import logging
import re
from datetime import datetime
from config import REGION

logger = logging.getLogger(__name__)

BASE_URL = f"https://cars.av.by/filter?region={REGION}"

async def get_new_ads():
    """Получение новых объявлений с av.by"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(BASE_URL, headers=headers, timeout=15) as response:
                html = await response.text()
                
        soup = BeautifulSoup(html, 'html.parser')
        ads = []
        listing_items = soup.find_all('div', class_=re.compile('listing-item'))
        
        for item in listing_items:
            try:
                ad = await parse_ad_item(item)
                if ad:
                    ads.append(ad)
            except Exception as e:
                logger.debug(f"Ошибка парсинга: {e}")
                continue
                
        return ads
        
    except Exception as e:
        logger.error(f"Ошибка получения объявлений: {e}")
        return []

async def parse_ad_item(item):
    """Парсинг одного объявления с полной информацией"""
    try:
        ad_id = item.get('data-id', '')
        if not ad_id:
            return None
            
        # Заголовок и ссылка
        title_elem = item.find('a', class_=re.compile('link'))
        if not title_elem:
            return None
            
        title = title_elem.text.strip()
        link = title_elem.get('href', '')
        if link and link.startswith('/'):
            link = f"https://cars.av.by{link}"
            
        # Цена
        price_elem = item.find('span', class_=re.compile('price'))
        price_byn = "0"
        price_usd = "0"
        if price_elem:
            price_text = price_elem.text.strip()
            price_byn = ''.join(filter(str.isdigit, price_text))
            # Конвертация в USD (примерный курс)
            if price_byn:
                try:
                    price_usd = str(round(int(price_byn) / 3.0))
                except:
                    price_usd = "0"
            
        # Фото (берём первое доступное)
        img_elem = item.find('img')
        photo_url = None
        if img_elem:
            photo_url = img_elem.get('src')
            if not photo_url:
                photo_url = img_elem.get('data-src')
            if photo_url and photo_url.startswith('//'):
                photo_url = f"https:{photo_url}"
        
        # Все параметры автомобиля
        params = {}
        param_items = item.find_all('span', class_=re.compile('param'))
        
        # Год
        year = ''
        mileage = ''
        engine = ''
        transmission = ''
        
        for p in param_items:
            text = p.text.strip()
            if re.search(r'\d{4}', text) and ('г' in text or 'год' in text):
                year = text
            elif 'км' in text:
                mileage = text
            elif 'л' in text and any(x in text for x in ['бензин', 'дизель', 'электро', 'гибрид']):
                engine = text
            elif any(x in text for x in ['механика', 'автомат', 'робот', 'вариатор']):
                transmission = text
        
        # Время добавления
        time_elem = item.find('span', class_=re.compile('time'))
        time_added = time_elem.text.strip() if time_elem else ''

        # Город/регион
        location_elem = item.find('span', class_=re.compile('location'))
        location = location_elem.text.strip() if location_elem else 'Витебская область'
        
        # Пробег (отдельно)
        mileage_elem = item.find('span', class_=re.compile('mileage'))
        if mileage_elem:
            mileage = mileage_elem.text.strip()
        
        return {
            'id': ad_id,
            'title': title,
            'price_byn': price_byn,
            'price_usd': price_usd,
            'link': link,
            'photo_url': photo_url,
            'region': location,
            'year': year,
            'mileage': mileage,
            'engine': engine,
            'transmission': transmission,
            'time_added': time_added,
            'timestamp': datetime.now().isoformat(),
            'discount_ok': False,
            'discount_percent': 0,
            'market_price': 'Н/Д'
        }
        
    except Exception as e:
        logger.debug(f"Ошибка парсинга: {e}")
        return None