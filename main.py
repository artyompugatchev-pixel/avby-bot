import asyncio
import logging
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.utils import executor
from config import TOKEN, CHECK_INTERVAL
from parser_av import get_new_ads
from database import load_sent_ids, save_sent_id

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)
sent_ids = load_sent_ids()

# Глобальная переменная для хранения ID чата
CHAT_ID = None

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    global CHAT_ID
    CHAT_ID = message.chat.id
    await message.answer(
        "🚗 Бот мониторинга av.by запущен!\n\n"
        "Я автоматически ищу новые объявления в Витебской области "
        "и присылаю только те, где цена НИЖЕ РЫНКА (скидка 40%+).\n"
        "Проверка каждые 5 минут.\n\n"
        "Команды:\n"
        "/start - показать это сообщение\n"
        "/status - статус бота\n"
        "/reset - сбросить историю отправленных объявлений\n"
        "/test - отправить тестовое объявление"
    )

@dp.message_handler(commands=['status'])
async def show_status(message: types.Message):
    await message.answer(
        f"📊 Статус бота:\n"
        f"✅ Бот работает\n"
        f"📍 Регион: Витебская область\n"
        f"⏱ Интервал: {CHECK_INTERVAL//60} минут\n"
        f"📦 Отправлено объявлений: {len(sent_ids)}\n"
        f"🔥 Фильтр: только цена ниже рынка (40%+)"
    )

@dp.message_handler(commands=['reset'])
async def reset_history(message: types.Message):
    global sent_ids
    sent_ids = set()
    save_sent_id(0, reset=True)
    await message.answer("✅ История отправленных объявлений сброшена")

@dp.message_handler(commands=['test'])
async def send_test_ad(message: types.Message):
    """Отправка тестового объявления"""
    test_ad = {
        'id': 'test_123456',
        'title': 'Volkswagen Caddy 2011',
        'price_byn': '15000',
        'price_usd': '6950',
        'region': 'Витебская область',
        'year': '2011 г.',
        'engine': '1.6 л дизель',
        'transmission': 'механика',
        'mileage': '308 000 км',
        'link': 'https://cars.av.by/example',
        'photo_url': None,
        'time_added': '14 мин назад',
        'discount_ok': True,
        'discount_percent': 36,
        'market_price': '~10 900 USD'
    }
    await send_ad_with_chat(test_ad, message.chat.id)

async def check_ads():
    global sent_ids, CHAT_ID
    while True:
        try:
            logger.info("🔍 Проверка новых объявлений...")
            new_ads = await get_new_ads()
            
            if not new_ads:
                logger.info("Новых выгодных объявлений нет")
            else:
                logger.info(f"Найдено {len(new_ads)} выгодных объявлений")
                
                for ad in new_ads:
                    ad_id = ad.get('id')
                    if ad_id in sent_ids:
                        continue
                    
                    if CHAT_ID:
                        await send_ad_with_chat(ad, CHAT_ID)
                        sent_ids.add(ad_id)
                        save_sent_id(ad_id)
                        await asyncio.sleep(2)
                        
        except Exception as e:
            logger.error(f"Ошибка в check_ads: {e}")
            
        await asyncio.sleep(CHECK_INTERVAL)

async def send_ad_with_chat(ad, chat_id):
    """Отправка объявления с фото и полной информацией"""
    try:
        # Формируем красивое сообщение
        message_text = (
            f"🚗 <b>{ad['title']}</b>\n\n"
        )
        
        # Добавляем информацию о скидке
        if ad.get('discount_ok'):
            discount = ad.get('discount_percent', 0)
            market = ad.get('market_price', '')
            message_text += (
                f"🔥 <b>ВЫГОДНО</b>\n"
                f"💰 <b>{ad['price_usd']} USD</b> вместо ~{market} по рынку\n"
                f"📉 <b>На {discount}% ниже</b> рынка\n\n"
            )
        else:
            message_text += f"💰 <b>{ad['price_usd']} USD</b>\n\n"
        
        # Параметры автомобиля
        params = []
        if ad.get('year'):
            params.append(ad['year'])
        if ad.get('engine'):
            params.append(ad['engine'])
        if ad.get('transmission'):
            params.append(ad['transmission'])
        if ad.get('mileage'):
            params.append(ad['mileage'])
            
        message_text += " · ".join(params) + "\n\n"
        
        # Регион и время
        message_text += (
            f"📍 {ad['region']}\n"
            f"🕐 {ad.get('time_added', 'Недавно')}\n\n"
        )
        
        # Ссылка
        message_text += f"<a href='{ad['link']}'>🔗 Открыть объявление</a>"
        
        # Отправляем с фото, если оно есть
        if ad.get('photo_url'):
            try:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=ad['photo_url'],
                    caption=message_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                # Если фото не загружается, отправляем без фото
                logger.warning(f"Не удалось отправить фото: {e}")
                await bot.send_message(
                    chat_id=chat_id,
                    text=message_text,
                    parse_mode="HTML"
                )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=message_text,
                parse_mode="HTML"
            )
            
        logger.info(f"Отправлено: {ad['title']} - {ad['price_usd']} USD")

    except Exception as e:
        logger.error(f"Ошибка отправки: {e}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(check_ads())
    executor.start_polling(dp, skip_updates=True)