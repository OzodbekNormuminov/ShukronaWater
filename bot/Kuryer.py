import os 
import time
import json 
import asyncio 
from datetime import datetime, timedelta # UTC+5 uchun qo'shildi
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.utils.markdown import html_decoration as hd
from pathlib import Path 
from aiogram.fsm.context import FSMContext # State uchun qo'shildi
from aiogram.fsm.state import StatesGroup, State # State uchun qo'shildi

# ----------------- Konstanta -----------------
# Kuryer uchun komissiya foizi (10%)
COMMISSION_RATE = 0.10 # 10%

# ----------------- Fayl yo'llari -----------------
COURIER_SESSION_FILE = Path(__file__).parent / 'courier_sessions.json' 
COURIERS_FILE = Path(__file__).parent / 'couriers.json' 
DATABASE_FILE = Path(__file__).parent / 'database.json' 

# ----------------- Maxfiy Ma'lumotlar -----------------
KURYER_PASSWORD_RAW = os.getenv("KURYER_PASSWORD") 

if not KURYER_PASSWORD_RAW:
    KURYER_PASSWORD_FALLBACK = "MaxfiyParol" 
    KURYER_PASSWORD_RAW = KURYER_PASSWORD_FALLBACK 
    print(f"XATO: .env faylidan KURYER_PASSWORD topilmadi. HARDCODE qiymat ('{KURYER_PASSWORD_FALLBACK}') ishlatildi.")

COURIER_PASSWORD = KURYER_PASSWORD_RAW.strip()

# ----------------- YANGI: FSM States -----------------
class CourierHistoryState(StatesGroup):
    waiting_for_day = State()
    # Oraliq kunlarni so'rash uchun yangi holatlar
    waiting_for_start_date = State()
    waiting_for_end_date = State()

# ----------------- YANGI: Vaqt Funksiyasi (UTC+5) -----------------
def get_uzb_now():
    """O'zbekiston vaqtini qaytaradi (UTC+5)."""
    return datetime.utcnow() + timedelta(hours=5)

# --------------------------------------------------------------------------------------
# JSON bilan ishlash funksiyalari (DATABASE.JSON BILAN ISHLAYDI)
# --------------------------------------------------------------------------------------

def load_couriers():
    """couriers.json faylidan rasmiy kuryerlar ro'yxatini o'qiydi."""
    if not COURIERS_FILE.exists():
        return {}
    try:
        with open(COURIERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def load_courier_sessions():
    """JSON fayldan kuryer sessiyalarini o'qiydi."""
    if not COURIER_SESSION_FILE.exists():
        return {}
    try:
        with open(COURIER_SESSION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_courier_session(user_id, message_data):
    """Kuryerning sessiya ma'lumotlarini JSON faylga yozadi."""
    sessions = load_courier_sessions()
    session_data = {
        'id': user_id,
        'username': message_data.from_user.username,
        'first_name': message_data.from_user.first_name,
        'login_time': get_uzb_now().strftime("%Y-%m-%d %H:%M:%S"), # To'g'rilandi
        'timestamp': time.time()
    }
    sessions[str(user_id)] = session_data
    try:
        with open(COURIER_SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"XATO: Kuryer sessiyasini saqlashda xato yuz berdi: {e}")
    return session_data

def load_database():
    """database.json faylidan barcha ma'lumotlarni o'qiydi."""
    if not DATABASE_FILE.exists():
        return {}
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_database(data):
    """Barcha ma'lumotlarni database.json fayliga yozadi."""
    try:
        with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"XATO: database.json ga saqlashda xato yuz berdi: {e}")
        return False
        
# --------------------------------------------------------------------------------------
# YANGILANGAN FUNKSIYA: Kuryer statistikasini hisoblash (Range filtri qo'shildi)
# --------------------------------------------------------------------------------------
def aggregate_courier_stats(courier_id: str, target_date: str = None, start_date: str = None, end_date: str = None):
    """
    Berilgan kuryer ID bo'yicha yetkazilgan buyurtmalar statistikasini hisoblaydi.
    start_date va end_date berilsa, oraliq bo'yicha hisoblaydi.
    """
    db_data = load_database()
    delivered_orders = []
    total_delivered_count = 0
    total_sales_amount = 0 
    total_commission = 0   
    
    for _, user_data in db_data.items():
        user_orders = user_data.get('orders', [])
        
        for order in user_orders:
            if order.get('status') == 'delivered' and str(order.get('courier_id')) == courier_id:
                
                full_date = order.get('delivered_at', order.get('date', ''))
                order_day = full_date.split(' ')[0]

                # 1. Aniq bir kunlik filtr
                if target_date and order_day != target_date:
                    continue
                
                # 2. Oraliq kunlik filtr (Range)
                if start_date and end_date:
                    if not (start_date <= order_day <= end_date):
                        continue

                total_delivered_count += 1
                order_total = order.get('total', 0)
                commission = int(order_total * COMMISSION_RATE)
                
                total_sales_amount += order_total
                total_commission += commission
                
                delivered_orders.append({
                    'order_id': order.get('order_id'),
                    'total': order_total,
                    'commission': commission,
                    'date': full_date
                })
                
    delivered_orders.sort(key=lambda x: x['date'], reverse=True)
    
    return {
        'orders_list': delivered_orders,
        'count': total_delivered_count,
        'total_sales': total_sales_amount,
        'total_commission': total_commission
    }


# --------------------------------------------------------------------------------------
# Pending buyurtmalarni olish (O'ZGARMADI)
# --------------------------------------------------------------------------------------
def aggregate_pending_orders():
    """database.json dan barcha pending buyurtmalarni yig'adi."""
    db_data = load_database()
    pending_orders_list = []
    
    for user_id_str, user_data in db_data.items():
        user_orders = user_data.get('orders', [])
        
        user_phone = user_data.get('phone', '---')
        user_address_data = user_data.get('location', {})
        
        for order in user_orders:
            if order.get('status') == 'pending' and order.get('courier_id') is None:
                
                try:
                    timestamp = time.mktime(time.strptime(order.get('date'), "%Y-%m-%d %H:%M:%S"))
                except (ValueError, TypeError):
                    timestamp = time.time() 

                aggregated_order = {
                    'order_id': order.get('order_id'),
                    'user_id': user_id_str, 
                    'phone_number': user_phone,
                    'location': user_address_data,
                    'total_amount': order.get('total'),
                    'items': f"{order.get('product_name')} ({order.get('quantity')}x)", 
                    'status': 'pending',
                    'timestamp': timestamp
                }
                pending_orders_list.append(aggregated_order)
                
    pending_orders_list.sort(key=lambda x: x['timestamp'])
    
    return pending_orders_list


# --------------------------------------------------------------------------------------
# KURYER KEYBOARD VA CALLBACKS
# --------------------------------------------------------------------------------------

def get_courier_keyboard():
    btn_orders = types.KeyboardButton(text="📦 Buyurtmalar") 
    btn_history = types.KeyboardButton(text="📜 Zakazlarim tarixi") 
    btn_balance = types.KeyboardButton(text="💰 Balans / Hisobot") 
    btn_rating = types.KeyboardButton(text="⭐ My Reyting") 
    
    keyboard_rows = [
        [btn_orders], 
        [btn_history, btn_balance],
        [btn_rating]
    ]

    markup = types.ReplyKeyboardMarkup(
        keyboard=keyboard_rows, 
        resize_keyboard=True, 
        input_field_placeholder="Kuryer buyrug'ini kiriting...",
    )
    return markup

def get_history_filter_keyboard():
    kb = [
        [types.KeyboardButton(text="📅 Bugun"), types.KeyboardButton(text="🔍 Boshqa kun")],
        [types.KeyboardButton(text="⬅️ Orqaga")]
    ]
    return types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_balance_inline_keyboard():
    """Balans ostidagi haftalik va oraliq sana tugmalari."""
    ikb = [
        [
            types.InlineKeyboardButton(text="📅 Haftalik", callback_data="report_weekly"),
            types.InlineKeyboardButton(text="📆 Boshqa kunlar", callback_data="report_range")
        ]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=ikb)

def get_order_inline_keyboard(user_id: str, order_id: str):
    """Buyurtmani qabul qilish uchun inline keyboard yaratadi."""
    btn_accept = types.InlineKeyboardButton(
        text="✅ Buyurtmani olish",
        callback_data=f"courier_accept_{user_id}_{order_id}"
    )
    
    keyboard = [
        [btn_accept]
    ]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)


# --------------------------------------------------------------------------------------
# KURYER ROUTER VA HANDLERLAR
# --------------------------------------------------------------------------------------
courier_router = Router()

# 1. /kuryer buyrug'i
@courier_router.message(Command("kuryer"))
async def cmd_courier(message: types.Message):
    user_id = message.from_user.id
    user_id_str = str(user_id)
    
    if not COURIER_PASSWORD:
        await message.answer("❌ Kuryer paroli o'rnatilmagan.")
        return
        
    couriers_list = load_couriers()
    if user_id_str not in couriers_list:
        await message.answer("⚠️ Uzr, siz bot kuryerlari ro'yxatida yo'qsiz. Admin bilan bog'laning.")
        return

    sessions = load_courier_sessions()
    
    if user_id_str in sessions:
        response_text = (
            f"💡 {hd.bold('Siz allaqachon Kuryer paneldasiz!')}\n\n"
            f"👤 {hd.bold('ID:')} <code>{user_id}</code>\n"
            f"✨ {hd.bold('Username:')} @{message.from_user.username or 'Noma\'lum'}\n"
            f"Marhamat, paneldan foydalaning."
        )
        await message.answer(response_text, parse_mode="HTML", reply_markup=get_courier_keyboard())
        return

    parts = message.text.split()
    
    if len(parts) < 2:
        await message.answer("🔐 Iltimos, parolni /kuryer dan keyin yozing.")
        return

    kiritilgan_parol = parts[1].strip()
    
    if kiritilgan_parol == COURIER_PASSWORD:
        save_courier_session(user_id, message)
        
        await message.answer("✅ Parol to'g'ri. Kuryer paneliga xush kelibsiz!", reply_markup=get_courier_keyboard())
        
        await message.answer(f"💾 {hd.bold('Sessiya saqlandi!')}...", parse_mode="HTML")
        
    else:
        await message.answer("❌ Noto'g'ri parol.")

# ----------------------------------------------------------------------------------
# YANGILANGAN HANDLER: My Reyting (Siz aytgan formatda)
# ----------------------------------------------------------------------------------
@courier_router.message(F.text == "⭐ My Reyting")
async def handle_my_rating(message: types.Message):
    user_id_str = str(message.from_user.id)
    couriers = load_couriers()
    
    # Bazadan kuryer ma'lumotlarini olish
    c_info = couriers.get(user_id_str, {})
    
    # Agar bazada bu ma'lumotlar bo'lsa chiqadi, bo'lmasa siz bergan defaultlar
    admin_id = c_info.get('added_by_id', "248902490")
    admin_username = c_info.get('added_by_username', "Admin")
    created_at = c_info.get('created_at', "No'malum")

    response = (
        f"⭐ {hd.bold('MY REYTING / PROFIL')}\n\n"
        f"🆔 {hd.bold('My ID:')} <code>{user_id_str}</code>\n"
        f"👨‍💻 {hd.bold('Admin ID:')} <code>{admin_id}</code>\n"
        f"👤 {hd.bold('Admin Username:')} @{admin_username}\n"
        f"📅 {hd.bold('Siz qo\'shilgan kun:')} {created_at}\n\n"
        f"💡 {hd.italic('Hozircha reyting tizimi shakllantirilmoqda.')}"
    )
    await message.answer(response, parse_mode="HTML")

# ----------------------------------------------------------------------------------
# 2. ASOSIY TUGMALAR HANDLERI
# ----------------------------------------------------------------------------------
@courier_router.message(F.text.in_({"📦 Buyurtmalar", "📜 Zakazlarim tarixi", "💰 Balans / Hisobot", "⬅️ Orqaga"}))
async def handle_courier_buttons(message: types.Message, state: FSMContext):
    # Har safar asosiy menyu tugmasi bosilganda eski statelarni tozalaymiz (Xato format chiqmasligi uchun)
    await state.clear()
    
    user_id = message.from_user.id
    user_id_str = str(user_id)
    sessions = load_courier_sessions()
    
    if user_id_str not in sessions or user_id_str not in load_couriers():
        await message.answer("⚠️ Kirish uchun ruxsat yo'q. /kuryer [parol] orqali kiring.")
        return

    if message.text == "📦 Buyurtmalar":
        pending_orders = aggregate_pending_orders()
        
        if not pending_orders:
            await message.answer("📋 <b>Yangi Buyurtmalar</b>\n\n🎉 Ayni damda yangi buyurtmalar mavjud emas.", parse_mode="HTML")
            return
            
        await message.answer("📋 <b>Yangi Buyurtmalar Ro'yxati:</b>", parse_mode="HTML")
        
        for order in pending_orders:
            lat, lon = order['location'].get('latitude', 0), order['location'].get('longitude', 0)
            map_link = f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"
            
            order_details = (
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"🆔 {hd.bold('ID:')} <code>#{order.get('order_id')}</code>\n"
                f"👤 {hd.bold('Mijoz ID:')} <code>{order.get('user_id')}</code>\n"
                f"⏰ {hd.bold('Vaqt:')} {order.get('date')}\n"
                f"📞 {hd.bold('Mijoz Tel:')} {hd.bold(order.get('phone_number'))}\n"
                f"🗺️ {hd.bold('Manzil:')} <a href='{map_link}'>Xarita</a>\n"
                f"🛍️ {hd.bold('Mahsulotlar:')} {order.get('items')}\n"
                f"💰 {hd.bold('Jami:')} {hd.bold(f'{order.get('total_amount', 0):,}')} so'm"
            )
            
            await message.answer(order_details, parse_mode="HTML", reply_markup=get_order_inline_keyboard(order.get('user_id'), order.get('order_id')))
            await asyncio.sleep(0.1) 

    elif message.text == "📜 Zakazlarim tarixi":
        await message.answer("📜 Zakazlar tarixini ko'rish uchun vaqtni tanlang:", reply_markup=get_history_filter_keyboard())

    elif message.text == "💰 Balans / Hisobot":
        stats = aggregate_courier_stats(user_id_str)
        response = (
            f"💵 {hd.bold('BALANS VA UMUMIY HISOBOT')}\n\n"
            f"📊 {hd.bold('Zakazlar soni:')} {stats['count']} ta\n"
            f"💰 {hd.bold('Umumiy savdo:')} {stats['total_sales']:,} so'm\n"
            f"💲 {hd.bold('Sizning daromadingiz (10%):')}\n"
            f"   {hd.bold(f'{stats['total_commission']:,} so\'m')}\n\n"
            f"Batafsil hisobot uchun pastdagi tugmalardan foydalaning:"
        )
        await message.answer(response, parse_mode="HTML", reply_markup=get_balance_inline_keyboard())
        
    elif message.text == "⬅️ Orqaga":
        await message.answer("Asosiy kuryer menyusi:", reply_markup=get_courier_keyboard())

# ----------------------------------------------------------------------------------
# INLINE CALLBACKS: Balans Hisoboti (Haftalik va Range)
# ----------------------------------------------------------------------------------
@courier_router.callback_query(F.data == "report_weekly")
async def callback_report_weekly(call: types.CallbackQuery):
    user_id_str = str(call.from_user.id)
    # Kechadan boshlab 7 kun orqaga (Bugun hisobga olinmaydi)
    yesterday = get_uzb_now() - timedelta(days=1)
    start_dt = yesterday - timedelta(days=6)
    
    start_date_str = start_dt.strftime("%Y-%m-%d")
    end_date_str = yesterday.strftime("%Y-%m-%d")
    
    stats = aggregate_courier_stats(user_id_str, start_date=start_date_str, end_date=end_date_str)
    
    res = (
        f"📅 {hd.bold('OXIRGI 1 HAFTALIK HISOBOT')}\n"
        f"({start_date_str} dan {end_date_str} gacha)\n\n"
        f"📦 {hd.bold('Zakazlar soni:')} {stats['count']} ta\n"
        f"💵 {hd.bold('Jami komissiya:')} {stats['total_commission']:,} so'm"
    )
    await call.message.answer(res, parse_mode="HTML")
    await call.answer()

@courier_router.callback_query(F.data == "report_range")
async def callback_report_range(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("📅 Boshlanish kunini kiriting (Masalan: 05.12.2025):")
    await state.set_state(CourierHistoryState.waiting_for_start_date)
    await call.answer()

@courier_router.message(CourierHistoryState.waiting_for_start_date)
async def process_start_date(message: types.Message, state: FSMContext):
    # Agar foydalanuvchi menyu tugmasini bossa
    if message.text in ["📦 Buyurtmalar", "📜 Zakazlarim tarixi", "💰 Balans / Hisobot", "⬅️ Orqaga"]:
        await state.clear()
        return
        
    try:
        date_obj = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        await state.update_data(start_date=date_obj.strftime("%Y-%m-%d"))
        await message.answer("📅 Oxirgi kunni kiriting (Masalan: 17.12.2025):")
        await state.set_state(CourierHistoryState.waiting_for_end_date)
    except ValueError:
        await message.answer("❌ Xato format. Iltimos DD.MM.YYYY formatida yozing:")

@courier_router.message(CourierHistoryState.waiting_for_end_date)
async def process_end_date(message: types.Message, state: FSMContext):
    if message.text in ["📦 Buyurtmalar", "📜 Zakazlarim tarixi", "💰 Balans / Hisobot", "⬅️ Orqaga"]:
        await state.clear()
        return

    try:
        date_obj = datetime.strptime(message.text.strip(), "%d.%m.%Y")
        end_date = date_obj.strftime("%Y-%m-%d")
        data = await state.get_data()
        start_date = data.get('start_date')
        
        stats = aggregate_courier_stats(str(message.from_user.id), start_date=start_date, end_date=end_date)
        
        res = (
            f"🔍 {hd.bold('ORALIQ MUDDAT HISOBOTI')}\n"
            f"({start_date} dan {end_date} gacha)\n\n"
            f"📦 {hd.bold('Zakazlar soni:')} {stats['count']} ta\n"
            f"💵 {hd.bold('Jami komissiya:')} {stats['total_commission']:,} so'm"
        )
        await state.clear()
        await message.answer(res, parse_mode="HTML", reply_markup=get_courier_keyboard())
    except ValueError:
        await message.answer("❌ Xato format. Iltimos DD.MM.YYYY formatida yozing:")

# ----------------------------------------------------------------------------------
# TARIX: Bugun va Boshqa kun
# ----------------------------------------------------------------------------------
@courier_router.message(F.text == "📅 Bugun")
async def history_today_handler(message: types.Message):
    user_id_str = str(message.from_user.id)
    today_date = get_uzb_now().strftime("%Y-%m-%d")
    stats = aggregate_courier_stats(user_id_str, target_date=today_date)
    
    response = f"📊 {hd.bold('BUGUNGI HISOBOT (' + today_date + ')')}\n\n"
    await send_history_stats(message, stats, response)

@courier_router.message(F.text == "🔍 Boshqa kun")
async def history_other_day_handler(message: types.Message, state: FSMContext):
    await message.answer("📅 Kunning raqamini kiriting (1-31):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(CourierHistoryState.waiting_for_day)

@courier_router.message(CourierHistoryState.waiting_for_day)
async def process_day_input(message: types.Message, state: FSMContext):
    if message.text in ["📦 Buyurtmalar", "📜 Zakazlarim tarixi", "💰 Balans / Hisobot", "⬅️ Orqaga"]:
        await state.clear()
        return

    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting:")
        return
    
    kun = int(message.text)
    if not (1 <= kun <= 31):
        await message.answer("❌ 1-31 oralig'ida raqam kiriting:")
        return

    now = get_uzb_now()
    target_date = f"{now.year}-{now.month:02d}-{kun:02d}"
    stats = aggregate_courier_stats(str(message.from_user.id), target_date=target_date)
    await state.clear()
    
    response = f"📊 {hd.bold(target_date + ' HISOBOTI')}\n\n"
    await send_history_stats(message, stats, response, show_main_kb=True)

async def send_history_stats(message, stats, response, show_main_kb=False):
    if stats['count'] == 0:
        response += "❌ Buyurtmalar topilmadi."
    else:
        response += f"✅ Yetkazilgan: {stats['count']} ta\n"
        response += f"💰 Savdo: {stats['total_sales']:,} so'm\n"
        response += f"💵 Foyda: {hd.bold(f'{stats['total_commission']:,}')} so'm\n"
        response += "\n----------------------------------------\n"
        for order in stats['orders_list'][:10]:
            response += f"🆔 #{order['order_id']} | {order['total']:,} so'm | Foyda: {order['commission']:,}\n"
            
    markup = get_courier_keyboard() if show_main_kb else None
    await message.answer(response, parse_mode="HTML", reply_markup=markup)

# ----------------------------------------------------------------------------------
# CALLBACKS: Qabul va Yetkazish
# ----------------------------------------------------------------------------------
@courier_router.callback_query(F.data.startswith("courier_accept_"))
async def callback_accept_order(call: types.CallbackQuery, bot: Bot):
    await call.answer("Qabul qilinmoqda...")
    courier_id = str(call.from_user.id)
    parts = call.data.split('_')
    target_user_id, order_id = parts[-2], parts[-1]
    
    db_data = load_database()
    user_data = db_data.get(target_user_id)
    if not user_data: return

    order_found = False
    for order in user_data['orders']:
        if order.get('order_id') == order_id and order.get('status') == 'pending':
            order.update({'status': 'on_delivery', 'courier_id': courier_id, 'accepted_at': get_uzb_now().strftime("%Y-%m-%d %H:%M:%S")})
            order_found = True
            break

    if not order_found:
        await call.message.edit_text("❌ Xatolik!")
        return

    if save_database(db_data):
        await call.message.edit_text(f"✅ Olingan: #{order_id}", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="✔️ Yetkazildi", callback_data=f"courier_delivered_{target_user_id}_{order_id}")]]))
        try:
            await bot.send_message(target_user_id, f"🛵 Buyurtmangiz #{order_id} yo'lda!")
        except Exception: pass

@courier_router.callback_query(F.data.startswith("courier_delivered_"))
async def callback_delivered_order(call: types.CallbackQuery, bot: Bot):
    await call.answer("Tasdiqlandi.")
    courier_id = str(call.from_user.id)
    parts = call.data.split('_')
    target_user_id, order_id = parts[-2], parts[-1]
    
    db_data = load_database()
    user_data = db_data.get(target_user_id)
    if not user_data: return

    order_found = False
    for order in user_data['orders']:
        if order.get('order_id') == order_id and order.get('courier_id') == courier_id:
            total = order.get('total', 0)
            order.update({'status': 'delivered', 'delivered_at': get_uzb_now().strftime("%Y-%m-%d %H:%M:%S"), 'commission_amount': int(total * COMMISSION_RATE)})
            order_found = True
            break
            
    if order_found and save_database(db_data):
        await call.message.edit_text(f"🏁 #{order_id} yetkazildi!") 
        try:
            await bot.send_message(target_user_id, f"🎉 Buyurtma #{order_id} yetkazildi!")
        except Exception: pass

def setup_kuryer_handlers(dp):
    dp.include_router(courier_router)
    print("Kuryer routeri muvaffaqiyatli ulandi.")