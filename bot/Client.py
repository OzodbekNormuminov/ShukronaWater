import json
import os
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ============================================================================
# SOZLAMALAR - Environment variables dan o'qish
# ============================================================================

ADMIN_ID = int(os.getenv("ADMIN_ID", "5879651176"))
COMPLAINT_LINK = os.getenv("COMPLAINT_LINK", "https://t.me/questianonbot?start=5879651176")

DATABASE_FILE = 'database.json'
PRODUCTS_FILE = 'products.json'
RATINGS_FILE = 'ratings.json'
COMMENTS_FILE = 'comments.json'
COMPLAINTS_FILE = 'complaints.json'  # Yangi fayl: shikoyatlar uchun
DELIVERY_FILE = 'delivery.json'

# ============================================================================
# FSM STATES
# ============================================================================

class RegistrationStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()
    waiting_location_choice = State()
    waiting_home_location_geo = State()
    waiting_home_location_text = State()
    waiting_current_location_geo = State()
    waiting_current_location_text = State()

class MainMenuStates(StatesGroup):
    main_menu = State()
    products_menu = State()
    complaint_menu = State()
    orders_menu = State()  
    delivery_status_menu = State()

class EditProfileStates(StatesGroup):
    editing_menu = State()
    edit_name = State()
    edit_phone = State()
    edit_location_choice = State()
    edit_home_location_geo = State()
    edit_home_location_text = State()
    edit_current_location_geo = State()
    edit_current_location_text = State()

class OrderStates(StatesGroup):
    choose_cap_type = State()
    waiting_location_choice = State()  
    waiting_current_location_geo = State()  # Yangi: hozirgi joy geo kutish
    waiting_current_location_text = State()  # Yangi: hozirgi joy text kutish
    choose_delivery_time = State()
    waiting_comment = State()
    confirm_location = State()
    waiting_rating = State()

# Yangi: Shikoyat holatlari
class ComplaintStates(StatesGroup):
    waiting_complaint_text = State()

# ============================================================================
# DATABASE FUNKSIYALARI
# ============================================================================

def load_database():
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_database(data):
    with open(DATABASE_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_products():
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def load_ratings():
    if os.path.exists(RATINGS_FILE):
        try:
            with open(RATINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_rating(rating_data):
    ratings = load_ratings()
    ratings.append(rating_data)
    with open(RATINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(ratings, f, ensure_ascii=False, indent=4)

def load_comments():
    if os.path.exists(COMMENTS_FILE):
        try:
            with open(COMMENTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_comment(comment_data):
    comments = load_comments()
    comments.append(comment_data)
    with open(COMMENTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(comments, f, ensure_ascii=False, indent=4)

def load_complaints():
    if os.path.exists(COMPLAINTS_FILE):
        try:
            with open(COMPLAINTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_complaint(complaint_data):
    complaints = load_complaints()
    complaints.append(complaint_data)
    with open(COMPLAINTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(complaints, f, ensure_ascii=False, indent=4)

def load_delivery_boys():
    if os.path.exists(DELIVERY_FILE):
        try:
            with open(DELIVERY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_delivery_boys(data):
    with open(DELIVERY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_data(user_id):
    db = load_database()
    return db.get(str(user_id), None)

def save_user_data(user_id, data):
    db = load_database()
    db[str(user_id)] = data
    save_database(db)

def is_registered(user_id):
    user_data = get_user_data(user_id)
    return bool(user_data and user_data.get('name') and user_data.get('phone') and 
                user_data.get('home_location_geo') and user_data.get('home_location_text'))

# ============================================================================
# KEYBOARD FUNKSIYALARI
# ============================================================================

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Mahsulotlar"), KeyboardButton(text="📦 Buyurtmalarim")],
            [KeyboardButton(text="👤 Ma'lumotlarim"), KeyboardButton(text="📝 Shikoyat va Izoh")],
            # [KeyboardButton(text="🚚 Kuryer statusi")]
        ],
        resize_keyboard=True
    )

def back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Ortga")]],
        resize_keyboard=True
    )

def complaint_menu_keyboard():
    """Yangi: Faqat 2 ta tugma - Shikoyat qilish va Ortga"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Shikoyat qilish")],
            [KeyboardButton(text="⬅️ Ortga")]
        ],
        resize_keyboard=True
    )

def location_choice_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🏠 Mening uyimga"), KeyboardButton(text="📍 Hozirgi joyimga")],
            [KeyboardButton(text="⬅️ Ortga")]
        ],
        resize_keyboard=True
    )

def request_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def request_location_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📍 Lokatsiyani yuborish", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def edit_profile_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Ismni o'zgartirish")],
            [KeyboardButton(text="📱 Telefon raqamni o'zgartirish")],
            [KeyboardButton(text="📍 Lokatsiyani o'zgartirish")],
            [KeyboardButton(text="⬅️ Ortga")]
        ],
        resize_keyboard=True
    )

def profile_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✏️ Tahrirlash")],
            [KeyboardButton(text="⬅️ Ortga")]
        ],
        resize_keyboard=True
    )

def cap_type_keyboard(product_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💧 Suv bachok bilan (15,000 so'm)", 
                                   callback_data=f"with_cap_{product_id}"),
            ],
            [
                InlineKeyboardButton(text="💧 Suv bachoksiz (12,000 so'm)", 
                                   callback_data=f"without_cap_{product_id}"),
            ]
        ]
    )

def delivery_time_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚚 Hozir yetkazish", callback_data="delivery_now"),
                InlineKeyboardButton(text="📅 Boshqa kunga", callback_data="delivery_later")
            ]
        ]
    )

def location_confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, to'g'ri", callback_data="location_correct"),
                InlineKeyboardButton(text="❌ Yo'q, o'zgartirish", callback_data="location_incorrect")
            ]
        ]
    )

def rating_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⭐️", callback_data="rate_1"),
                InlineKeyboardButton(text="⭐️⭐️", callback_data="rate_2"),
                InlineKeyboardButton(text="⭐️⭐️⭐️", callback_data="rate_3"),
            ],
            [
                InlineKeyboardButton(text="⭐️⭐️⭐️⭐️", callback_data="rate_4"),
                InlineKeyboardButton(text="⭐️⭐️⭐️⭐️⭐️", callback_data="rate_5")
            ]
        ]
    )

# ============================================================================
# YORDAMCHI FUNKSIYALAR
# ============================================================================

def remember_product_message_id(user_id: int, product_id: str, message_id: int):
    data = get_user_data(user_id) or {}
    if 'product_messages' not in data:
        data['product_messages'] = {}
    data['product_messages'][product_id] = message_id
    save_user_data(user_id, data)

async def clear_product_buttons_for_user(bot: Bot, user_id: int, product_id: str):
    data = get_user_data(user_id) or {}
    pm = (data.get('product_messages') or {}).get(product_id)
    if pm:
        try:
            await bot.edit_message_reply_markup(chat_id=user_id, message_id=pm, reply_markup=None)
        except Exception:
            pass

def create_location_links(lat, lon):
    google_link = f"https://www.google.com/maps?q={lat},{lon}"
    yandex_link = f"https://yandex.com/maps/?ll={lon},{lat}&z=16&pt={lon},{lat}"
    return google_link, yandex_link

def get_delivery_boy_rating(delivery_boy_id):
    delivery_boys = load_delivery_boys()
    boy = delivery_boys.get(str(delivery_boy_id), {})
    rating = boy.get('rating', 0.0)
    total_ratings = boy.get('total_ratings', 0)
    return f"{rating:.1f} ({total_ratings} baho)"

# ============================================================================
# ROUTER
# ============================================================================

router = Router()

# ============================================================================
# START VA RO'YXATDAN O'TISH
# ============================================================================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if is_registered(user_id):
        await message.answer(
            "Xush kelibsiz! 😊\n\n📱 Asosiy menyu:",
            reply_markup=main_menu_keyboard()
        )
        await state.set_state(MainMenuStates.main_menu)
    else:
        await message.answer(
            "Assalomu alaykum! Shukrona Suvlari Botga Xush Kelibsiz. 😊\n\n"
            "Iltimos, Ismingiz yoki Kompaniya nomingizni kiriting!",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(RegistrationStates.waiting_name)

@router.message(StateFilter(RegistrationStates.waiting_name))
async def process_name(message: Message, state: FSMContext):
    await state.update_data(temp_name=message.text)
    await message.answer(
        "Rahmat! ✅\n\nEndi telefon raqamingizni yuboring:",
        reply_markup=request_phone_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_phone)

@router.message(StateFilter(RegistrationStates.waiting_phone), F.contact)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(temp_phone=message.contact.phone_number)
    await message.answer(
        "Ajoyib! ✅\n\nLokatsiya turini tanlang:",
        reply_markup=location_choice_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_location_choice)

@router.message(StateFilter(RegistrationStates.waiting_phone))
async def process_phone_invalid(message: Message):
    await message.answer(
        "❌ Iltimos, telefon raqamingizni tugma orqali yuboring!",
        reply_markup=request_phone_keyboard()
    )

@router.message(StateFilter(RegistrationStates.waiting_location_choice), F.text == "🏠 Mening uyimga")
async def process_home_location_choice(message: Message, state: FSMContext):
    await message.answer(
        "Endi uy lokatsiyangizni yuboring (tugma orqali):",
        reply_markup=request_location_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_home_location_geo)

@router.message(StateFilter(RegistrationStates.waiting_location_choice), F.text == "📍 Hozirgi joyimga")
async def process_current_location_choice(message: Message, state: FSMContext):
    await message.answer(
        "Endi hozirgi joyingizni yuboring (tugma orqali):",
        reply_markup=request_location_keyboard()
    )
    await state.set_state(RegistrationStates.waiting_current_location_geo)

@router.message(StateFilter(RegistrationStates.waiting_home_location_geo), F.location)
async def process_home_location_geo(message: Message, state: FSMContext):
    await state.update_data(
        temp_home_location_geo={
            'latitude': message.location.latitude,
            'longitude': message.location.longitude
        }
    )
    await message.answer(
        "✅ Uy lokatsiyangiz qabul qilindi!\n\n"
        "Endi yozma manzilingizni kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationStates.waiting_home_location_text)

@router.message(StateFilter(RegistrationStates.waiting_current_location_geo), F.location)
async def process_current_location_geo(message: Message, state: FSMContext):
    await state.update_data(
        temp_current_location_geo={
            'latitude': message.location.latitude,
            'longitude': message.location.longitude
        }
    )
    await message.answer(
        "✅ Hozirgi joyingiz qabul qilindi!\n\n"
        "Endi yozma manzilingizni kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(RegistrationStates.waiting_current_location_text)

@router.message(StateFilter(RegistrationStates.waiting_home_location_geo))
async def process_location_geo_invalid(message: Message):
    await message.answer(
        "❌ Iltimos, lokatsiyangizni tugma orqali yuboring!",
        reply_markup=request_location_keyboard()
    )

@router.message(StateFilter(RegistrationStates.waiting_home_location_text))
async def process_home_location_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    
    user_data = {
        'user_id': user_id,
        'username': message.from_user.username or 'Nomalum',
        'name': data.get('temp_name', ''),
        'phone': data.get('temp_phone', ''),
        'home_location_geo': data.get('temp_home_location_geo', {}),
        'home_location_text': message.text,
        'current_location_geo': data.get('temp_current_location_geo', {}),
        'current_location_text': data.get('temp_current_location_text', ''),
        'cart': {},
        'orders': [],
        'registered_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'product_messages': {}
    }
    
    save_user_data(user_id, user_data)
    await state.clear()
    
    await message.answer(
        "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
        "Botdan foydalanishingiz mumkin.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await message.answer(
        "📱 Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MainMenuStates.main_menu)

@router.message(StateFilter(RegistrationStates.waiting_current_location_text))
async def process_current_location_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    data = await state.get_data()
    
    user_data = {
        'user_id': user_id,
        'username': message.from_user.username or 'Nomalum',
        'name': data.get('temp_name', ''),
        'phone': data.get('temp_phone', ''),
        'home_location_geo': data.get('temp_home_location_geo', {}),
        'home_location_text': data.get('temp_home_location_text', ''),
        'current_location_geo': data.get('temp_current_location_geo', {}),
        'current_location_text': message.text,
        'cart': {},
        'orders': [],
        'registered_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'product_messages': {}
    }
    
    save_user_data(user_id, user_data)
    await state.clear()
    
    await message.answer(
        "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!\n\n"
        "Botdan foydalanishingiz mumkin.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    await message.answer(
        "📱 Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MainMenuStates.main_menu)

# ============================================================================
# SHIKOYAT VA IZOH BO'LIMI (O'ZGARTIRILGAN)
# ============================================================================

@router.message(StateFilter(MainMenuStates.main_menu), F.text == "📝 Shikoyat va Izoh")
async def show_complaint_menu(message: Message, state: FSMContext):
    await message.answer(
        "📝 *Shikoyat va izoh qoldirish*\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        parse_mode='Markdown',
        reply_markup=complaint_menu_keyboard()  # Yangi keyboard
    )
    await state.set_state(MainMenuStates.complaint_menu)

@router.message(StateFilter(MainMenuStates.complaint_menu), F.text == "📝 Shikoyat qilish")
async def make_complaint(message: Message, state: FSMContext):
    # Avval linkni yuboramiz
    await message.answer(
        f"📝 *Shikoyat qilish*\n\n"
        f"Shukrona Zam Zam boti ustidan shikoyat qilish uchun ushbu linkni bosib kirasiz:\n\n"
        f"👉 {COMPLAINT_LINK}",
        parse_mode='Markdown'
    )
    
    # Keyin foydalanuvchidan shikoyat matnini so'raymiz
    await message.answer(
        "📝 Endi o'z shikoyatingizni *tekst shaklida* yuboring:\n\n"
        "_(Shikoyatingizni batafsil yozing, biz uni administratorlarga yuboramiz)_",
        parse_mode='Markdown',
        reply_markup=back_keyboard()
    )
    await state.set_state(ComplaintStates.waiting_complaint_text)

@router.message(StateFilter(MainMenuStates.complaint_menu), F.text == "⬅️ Ortga")
async def back_from_complaint(message: Message, state: FSMContext):
    await message.answer("📱 Asosiy menyu:", reply_markup=main_menu_keyboard())
    await state.set_state(MainMenuStates.main_menu)

@router.message(StateFilter(ComplaintStates.waiting_complaint_text), F.text == "⬅️ Ortga")
async def back_from_complaint_text(message: Message, state: FSMContext):
    await message.answer(
        "📝 *Shikoyat va izoh qoldirish*\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        parse_mode='Markdown',
        reply_markup=complaint_menu_keyboard()
    )
    await state.set_state(MainMenuStates.complaint_menu)

@router.message(StateFilter(ComplaintStates.waiting_complaint_text))
async def save_complaint_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    complaint_data = {
        'user_id': user_id,
        'username': user_data.get('username', 'Nomalum'),
        'name': user_data.get('name', 'Nomalum'),
        'phone': user_data.get('phone', 'Nomalum'),
        'complaint': message.text,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': 'complaint'
    }
    
    # Shikoyatni faylga saqlash
    save_complaint(complaint_data)
    
    # Admin ga xabar yuborish
    try:
        await message.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"⚠️ *YANGI SHIKOYAT*\n\n"
                 f"👤 Foydalanuvchi: @{user_data.get('username', 'Nomalum')}\n"
                 f"📝 Ism: {user_data.get('name', 'Nomalum')}\n"
                 f"📱 Telefon: {user_data.get('phone', 'Nomalum')}\n"
                 f"💬 Shikoyat: {message.text}\n"
                 f"📅 {complaint_data['date']}",
            parse_mode='Markdown'
        )
    except Exception:
        pass
    
    await message.answer(
        "✅ Shikoyatingiz qabul qilindi va administratorga yuborildi!\n\n"
        "Rahmat! Biz sizning fikringizni inobatga olamiz. 😊",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()
    await state.set_state(MainMenuStates.main_menu)

# ============================================================================
# MAHSULOTLAR BO'LIMI
# ============================================================================

@router.message(StateFilter(MainMenuStates.main_menu), F.text == "🛍 Mahsulotlar")
async def show_products(message: Message, state: FSMContext):
    products = load_products()
    if not products:
        await message.answer(
            "❌ Hozircha mahsulotlar mavjud emas.\n\nAdmin hali mahsulot qo'shmagan.",
            reply_markup=back_keyboard()
        )
        return
    
    await message.answer(
        "🛍 Mahsulotlar ro'yxati:\n\nKerakli mahsulotni tanlang va miqdorini belgilang:",
        reply_markup=back_keyboard()
    )
    
    user_id = message.from_user.id
    for product_id, product in products.items():
        await send_product_card(message.bot, user_id, product_id, product)
    
    await state.set_state(MainMenuStates.products_menu)

async def send_product_card(bot: Bot, user_id: int, product_id: str, product: dict):
    user_data = get_user_data(user_id)
    quantity = 0
    if user_data and 'cart' in user_data:
        quantity = user_data['cart'].get(product_id, 0)
    
    if 'price_with_cap' in product and 'price_without_cap' in product:
        price_text = f"💰 Narx: {product['price_with_cap']:,} so'm (bachok bilan)\n       {product['price_without_cap']:,} so'm (bachoksiz)"
    else:
        price_text = f"💰 Narx: {product.get('price', 0):,} so'm"
    
    caption = (
        f"*{product['name']}*\n\n"
        f"📝 {product['description']}\n"
        f"{price_text}\n"
        f"📊 Savatchada: {quantity} ta"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="➖", callback_data=f"dec_{product_id}"),
            InlineKeyboardButton(text=f"📦 {quantity}", callback_data=f"show_{product_id}"),
            InlineKeyboardButton(text="➕", callback_data=f"inc_{product_id}")
        ]
    ]
    if quantity > 0:
        keyboard.append([InlineKeyboardButton(text="🛒 Buyurtma Qilish", callback_data=f"order_{product_id}")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    try:
        if product.get('image'):
            msg = await bot.send_photo(
                chat_id=user_id,
                photo=product['image'],
                caption=caption,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            msg = await bot.send_message(
                chat_id=user_id,
                text=caption,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        remember_product_message_id(user_id, product_id, msg.message_id)
    except Exception:
        msg = await bot.send_message(
            chat_id=user_id,
            text=caption,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        remember_product_message_id(user_id, product_id, msg.message_id)

@router.callback_query(F.data.startswith("inc_"))
async def handle_increase(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    product_id = callback.data.replace("inc_", "")
    
    user_data = get_user_data(user_id)
    if not user_data:
        await callback.message.answer("❌ Xatolik! /start dan boshlang.")
        return
    
    if 'cart' not in user_data:
        user_data['cart'] = {}
    
    user_data['cart'][product_id] = user_data['cart'].get(product_id, 0) + 1
    save_user_data(user_id, user_data)
    
    products = load_products()
    product = products.get(product_id)
    if product:
        await update_product_card(callback.message, product_id, product, user_data['cart'][product_id])

@router.callback_query(F.data.startswith("dec_"))
async def handle_decrease(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    product_id = callback.data.replace("dec_", "")
    
    user_data = get_user_data(user_id)
    if not user_data:
        await callback.message.answer("❌ Xatolik! /start dan boshlang.")
        return
    
    if 'cart' not in user_data:
        user_data['cart'] = {}
    
    if user_data['cart'].get(product_id, 0) > 0:
        user_data['cart'][product_id] -= 1
        if user_data['cart'][product_id] == 0:
            del user_data['cart'][product_id]
        save_user_data(user_id, user_data)
    
    products = load_products()
    product = products.get(product_id)
    if product:
        await update_product_card(callback.message, product_id, product, user_data['cart'].get(product_id, 0))

# ============================================================================
# BUYURTMA JARAYONI - ASOSIY QISMI (O'ZGARTIRILGAN)
# ============================================================================

@router.callback_query(F.data.startswith("order_"))
async def handle_order_request(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    product_id = callback.data.replace("order_", "")
    
    user_data = get_user_data(user_id)
    if not user_data:
        await callback.message.answer("❌ Xatolik! /start dan boshlang.")
        return
    
    products = load_products()
    product = products.get(product_id)
    quantity = user_data.get('cart', {}).get(product_id, 0)
    
    if product and quantity > 0:
        if 'price_with_cap' in product and 'price_without_cap' in product:
            await state.update_data(pending_order_product_id=product_id, pending_order_quantity=quantity)
            await callback.message.answer(
                "💧 *Suv turini tanlang:*",
                parse_mode='Markdown',
                reply_markup=cap_type_keyboard(product_id)
            )
            await state.set_state(OrderStates.choose_cap_type)
        else:
            await state.update_data(pending_order_product_id=product_id, pending_order_quantity=quantity)
            await callback.message.answer(
                "📍 *Yetkazib berish manzilini tanlang:*",
                parse_mode='Markdown',
                reply_markup=location_choice_keyboard()
            )
            await state.set_state(OrderStates.waiting_location_choice)

@router.callback_query(F.data.startswith("with_cap_"))
async def handle_with_cap(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    product_id = callback.data.replace("with_cap_", "")
    await state.update_data(with_cap=True)
    await callback.message.answer(
        "📍 *Yetkazib berish manzilini tanlang:*",
        parse_mode='Markdown',
        reply_markup=location_choice_keyboard()
    )
    await state.set_state(OrderStates.waiting_location_choice)

@router.callback_query(F.data.startswith("without_cap_"))
async def handle_without_cap(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    product_id = callback.data.replace("without_cap_", "")
    await state.update_data(with_cap=False)
    await callback.message.answer(
        "📍 *Yetkazib berish manzilini tanlang:*",
        parse_mode='Markdown',
        reply_markup=location_choice_keyboard()
    )
    await state.set_state(OrderStates.waiting_location_choice)

# O'ZGARTIRILGAN: "🏠 Mening uyimga" tugmasi bosilganda
@router.message(StateFilter(OrderStates.waiting_location_choice), F.text == "🏠 Mening uyimga")
async def handle_home_location_choice(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    # Ro'yxatdan o'tishda kiritilgan uy manzilini olamiz
    location_geo = user_data['home_location_geo']
    location_text = user_data['home_location_text']
    
    await state.update_data(order_location_geo=location_geo, order_location_text=location_text)
    
    await message.answer(
        "⏰ *Yetkazib berish vaqtini tanlang:*",
        parse_mode='Markdown',
        reply_markup=delivery_time_keyboard()
    )
    await state.set_state(OrderStates.choose_delivery_time)

# YANGI: "📍 Hozirgi joyimga" tugmasi bosilganda
@router.message(StateFilter(OrderStates.waiting_location_choice), F.text == "📍 Hozirgi joyimga")
async def handle_current_location_choice(message: Message, state: FSMContext):
    await message.answer(
        "📍 Iltimos, hozirgi joyingizni yuboring (tugma orqali):",
        reply_markup=request_location_keyboard()
    )
    await state.set_state(OrderStates.waiting_current_location_geo)

# YANGI: Hozirgi joy geo lokatsiyasini qabul qilish
@router.message(StateFilter(OrderStates.waiting_current_location_geo), F.location)
async def process_current_location_geo_order(message: Message, state: FSMContext):
    await state.update_data(
        temp_current_location_geo={
            'latitude': message.location.latitude,
            'longitude': message.location.longitude
        }
    )
    await message.answer(
        "✅ Hozirgi joyingiz qabul qilindi!\n\n"
        "Endi yozma manzilingizni kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OrderStates.waiting_current_location_text)

# YANGI: Hozirgi joy matnli manzilini qabul qilish
@router.message(StateFilter(OrderStates.waiting_current_location_text))
async def process_current_location_text_order(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    data = await state.get_data()
    
    # Foydalanuvchi ma'lumotlarini yangilaymiz
    user_data['current_location_geo'] = data.get('temp_current_location_geo', {})
    user_data['current_location_text'] = message.text
    save_user_data(user_id, user_data)
    
    # Buyurtma ma'lumotlariga joyni qo'shamiz
    await state.update_data(
        order_location_geo=data.get('temp_current_location_geo', {}),
        order_location_text=message.text
    )
    
    await message.answer(
        "⏰ *Yetkazib berish vaqtini tanlang:*",
        parse_mode='Markdown',
        reply_markup=delivery_time_keyboard()
    )
    await state.set_state(OrderStates.choose_delivery_time)

@router.message(StateFilter(OrderStates.waiting_location_choice), F.text == "⬅️ Ortga")
async def back_from_order_location(message: Message, state: FSMContext):
    await message.answer("📱 Asosiy menyu:", reply_markup=main_menu_keyboard())
    await state.set_state(MainMenuStates.main_menu)

@router.callback_query(OrderStates.choose_delivery_time, F.data.in_(["delivery_now", "delivery_later"]))
async def handle_delivery_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    delivery_time = "Hozir" if callback.data == "delivery_now" else "Boshqa kunga"
    await state.update_data(order_delivery_time=delivery_time)
    
    await callback.message.answer(
        "💭 *Izoh qoldirish (ixtiyoriy)*\n\n"
        "Kuryerga izoh yoki manzilingizni batafsil yozing:",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(OrderStates.waiting_comment)

@router.message(StateFilter(OrderStates.waiting_comment))
async def handle_order_comment(message: Message, state: FSMContext):
    await state.update_data(order_comment=message.text)
    
    data = await state.get_data()
    user_id = message.from_user.id
    
    lat = data['order_location_geo']['latitude']
    lon = data['order_location_geo']['longitude']
    google_link, yandex_link = create_location_links(lat, lon)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗺 Google Maps", url=google_link)],
            [InlineKeyboardButton(text="🗺 Yandex Maps", url=yandex_link)],
            [
                InlineKeyboardButton(text="✅ Ha, to'g'ri", callback_data="location_correct"),
                InlineKeyboardButton(text="❌ Yo'q, o'zgartirish", callback_data="location_incorrect")
            ]
        ]
    )
    
    await message.answer(
        f"📍 *Lokatsiyangiz to'g'rimi?*\n\n"
        f"📌 Geo lokatsiya:\n`{lat:.6f}, {lon:.6f}`\n\n"
        f"📝 Yozma manzil:\n{data['order_location_text']}\n\n"
        f"Manzilingizni tekshirish uchun xarita linklari:\n"
        f"• Google Maps: {google_link}\n"
        f"• Yandex Maps: {yandex_link}\n\n"
        f"*Lokatsiya to'g'ri bo'lsa 'Ha, to'g'ri' tugmasini bosing.*",
        parse_mode='Markdown',
        reply_markup=keyboard
    )
    await state.set_state(OrderStates.confirm_location)

@router.callback_query(OrderStates.confirm_location, F.data == "location_correct")
async def handle_location_confirmed(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await confirm_order_details(callback, state)

async def confirm_order_details(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    
    user_data = get_user_data(user_id)
    if not user_data:
        await callback.message.answer("❌ Xatolik! /start dan boshlang.")
        return
    
    product_id = data['pending_order_product_id']
    quantity = data['pending_order_quantity']
    
    products = load_products()
    product = products.get(product_id)
    
    if 'price_with_cap' in product and 'price_without_cap' in product:
        if data.get('with_cap', True):
            price = product['price_with_cap']
            cap_text = "bachok bilan"
        else:
            price = product['price_without_cap']
            cap_text = "bachoksiz"
    else:
        price = product['price']
        cap_text = ""
    
    total = price * quantity
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm_order"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_order")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    order_text = (
        f"📋 *BUYURTMA TAFSILOTLARI*\n\n"
        f"🛍 Mahsulot: {product['name']}\n"
        f"📊 Soni: {quantity} ta\n"
        f"💰 Bir dona narxi: {price:,} so'm ({cap_text})\n"
        f"💵 Jami summa: *{total:,} so'm*\n\n"
        f"📍 Manzil: {data['order_location_text']}\n"
        f"⏰ Yetkazish vaqti: {data['order_delivery_time']}\n"
        f"💭 Izoh: {data.get('order_comment', 'Yoʻq')}\n\n"
        f"*Buyurtmani tasdiqlaysizmi?*"
    )
    
    await callback.message.edit_text(
        order_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

@router.callback_query(F.data == "confirm_order")
async def handle_confirm_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    user_id = callback.from_user.id
    data = await state.get_data()
    
    user_data = get_user_data(user_id)
    if not user_data:
        await callback.message.answer("❌ Xatolik! /start dan boshlang.")
        return
    
    product_id = data['pending_order_product_id']
    products = load_products()
    product = products.get(product_id)
    
    if 'price_with_cap' in product and 'price_without_cap' in product:
        if data.get('with_cap', True):
            price = product['price_with_cap']
        else:
            price = product['price_without_cap']
    else:
        price = product['price']
    
    order = {
        'order_id': datetime.now().strftime('%Y%m%d%H%M%S'),
        'product_id': product_id,
        'product_name': product['name'],
        'price': price,
        'quantity': data['pending_order_quantity'],
        'total': price * data['pending_order_quantity'],
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'pending',
        'rated': False,
        'location_geo': data['order_location_geo'],
        'location_text': data['order_location_text'],
        'delivery_time': data['order_delivery_time'],
        'comment': data.get('order_comment', ''),
        'with_cap': data.get('with_cap', True)
    }
    
    if 'orders' not in user_data:
        user_data['orders'] = []
    user_data['orders'].append(order)
    
    if product_id in user_data['cart']:
        del user_data['cart'][product_id]
    
    save_user_data(user_id, user_data)
    
    await send_to_admin(callback.bot, user_id, user_data, product, order)
    
    await callback.message.edit_text(
        "✅ *Buyurtma qabul qilindi!*\n\n"
        "Tez orada kuryer siz bilan bog'lanadi! 📞\n\n"
        "Rahmat! 😊",
        parse_mode='Markdown'
    )
    
    delivery_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Kuryerni Baholang 1 dan 5 gacha", callback_data=f"delivered_{order['order_id']}")]
        ]
    )
    
    await callback.message.answer(
        "📦 *Mahsulotingizni olganingizdan so'ng quyidagi tugmani bosing:*",
        parse_mode='Markdown',
        reply_markup=delivery_keyboard
    )
    
    try:
        await clear_product_buttons_for_user(callback.bot, user_id, product_id)
    except Exception:
        pass
    
    await callback.message.answer(
        "📱 Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MainMenuStates.main_menu)

@router.callback_query(F.data.startswith("delivered_"))
async def handle_delivered(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    order_id = callback.data.replace("delivered_", "")
    
    await state.update_data(rating_order_id=order_id)
    
    await callback.message.edit_text(
        "⭐️ *Xizmatimizni baholang!*\n\n"
        "Kuryer xizmati va Shukrona Zam Zam suvlarini 1 dan 5 gacha baholang:",
        parse_mode='Markdown',
        reply_markup=rating_keyboard()
    )
    await state.set_state(OrderStates.waiting_rating)

@router.callback_query(F.data.startswith("rate_"))
async def handle_rating(callback: CallbackQuery, state: FSMContext):
    rating = int(callback.data.replace("rate_", ""))
    user_id = callback.from_user.id
    user_data = get_user_data(user_id)
    data = await state.get_data()
    order_id = data.get('rating_order_id')
    
    rating_data = {
        'user_id': user_id,
        'username': user_data.get('username', 'Nomalum'),
        'name': user_data.get('name', 'Nomalum'),
        'order_id': order_id,
        'rating': rating,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    save_rating(rating_data)
    
    if user_data and 'orders' in user_data:
        for order in user_data['orders']:
            if order['order_id'] == order_id:
                order['rated'] = True
                order['rating'] = rating
                break
        save_user_data(user_id, user_data)
    
    stars = "⭐️" * rating
    try:
        await callback.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📊 *YANGI BAHOLASH*\n\n"
                 f"👤 Foydalanuvchi: @{user_data.get('username', 'Nomalum')}\n"
                 f"📝 Ism: {user_data.get('name', 'Nomalum')}\n"
                 f"📋 Buyurtma ID: {order_id}\n"
                 f"⭐️ Baho: {stars} ({rating}/5)\n"
                 f"📅 {rating_data['date']}",
            parse_mode='Markdown'
        )
    except Exception:
        pass
    
    await callback.answer("Rahmat! ⭐️")
    await callback.message.edit_text(
        f"✅ *Baholash qabul qilindi!*\n\n"
        f"Sizning bahoyingiz: {stars}\n\n"
        f"Rahmat! 😊"
    )
    
    await callback.message.answer(
        "📱 Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MainMenuStates.main_menu)

@router.callback_query(F.data == "cancel_order")
async def handle_cancel_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("❌ *Buyurtma bekor qilindi.*", parse_mode='Markdown')
    await callback.message.answer(
        "📱 Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MainMenuStates.main_menu)

@router.callback_query(F.data == "location_incorrect")
async def handle_location_change(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(
        "❌ *Buyurtma bekor qilindi.*\n\n"
        "Lokatsiyangizni o'zgartirish uchun 👤 Ma'lumotlarim bo'limiga o'ting.",
        parse_mode='Markdown'
    )
    await callback.message.answer(
        "📱 Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MainMenuStates.main_menu)

async def update_product_card(message: Message, product_id: str, product: dict, quantity: int):
    if 'price_with_cap' in product and 'price_without_cap' in product:
        price_text = f"💰 Narx: {product['price_with_cap']:,} so'm (bachok bilan)\n       {product['price_without_cap']:,} so'm (bachoksiz)"
    else:
        price_text = f"💰 Narx: {product.get('price', 0):,} so'm"
    
    caption = (
        f"*{product['name']}*\n\n"
        f"📝 {product['description']}\n"
        f"{price_text}\n"
        f"📊 Savatchada: {quantity} ta"
    )
    
    keyboard = [
        [
            InlineKeyboardButton(text="➖", callback_data=f"dec_{product_id}"),
            InlineKeyboardButton(text=f"📦 {quantity}", callback_data=f"show_{product_id}"),
            InlineKeyboardButton(text="➕", callback_data=f"inc_{product_id}")
        ]
    ]
    if quantity > 0:
        keyboard.append([InlineKeyboardButton(text="🛒 Buyurtma Qilish", callback_data=f"order_{product_id}")])
    
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    
    try:
        await message.edit_caption(caption=caption, parse_mode='Markdown', reply_markup=reply_markup)
    except Exception:
        try:
            await message.edit_text(text=caption, parse_mode='Markdown', reply_markup=reply_markup)
        except Exception:
            pass

async def send_to_admin(bot: Bot, user_id: int, user_data: dict, product: dict, order: dict):
    lat = order['location_geo']['latitude']
    lon = order['location_geo']['longitude']
    google_link, yandex_link = create_location_links(lat, lon)
    
    cap_text = "Bachok bilan" if order.get('with_cap', True) else "Bachoksiz"
    
    admin_message = (
        f"🔔 *YANGI BUYURTMA!*\n\n"
        f"📋 Buyurtma ID: {order['order_id']}\n\n"
        f"👤 *MIJOZ MA'LUMOTLARI:*\n"
        f"Ism: {user_data['name']}\n"
        f"📱 Telefon: {user_data['phone']}\n"
        f"📍 Koordinatalar: {lat:.6f}, {lon:.6f}\n"
        f"📝 Manzil: {order['location_text']}\n\n"
        f"🛍 *BUYURTMA TAFSILOTLARI:*\n"
        f"Mahsulot: {product['name']}\n"
        f"📊 Soni: {order['quantity']} ta\n"
        f"💰 Narx: {order['price']:,} so'm ({cap_text})\n"
        f"💵 Jami summa: *{order['total']:,} so'm*\n"
        f"⏰ Yetkazish vaqti: {order['delivery_time']}\n"
        f"💭 Izoh: {order['comment']}\n"
        f"📅 Sana: {order['date']}\n\n"
        f"📍 *XARITA LINKLARI:*\n"
        f"Google Maps: {google_link}\n"
        f"Yandex Maps: {yandex_link}"
    )
    
    location_keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🗺 Google Maps ochish", url=google_link)],
            [InlineKeyboardButton(text="🗺 Yandex Maps ochish", url=yandex_link)]
        ]
    )
    
    try:
        if product.get('image'):
            await bot.send_photo(
                chat_id=ADMIN_ID,
                photo=product['image'],
                caption=admin_message,
                parse_mode='Markdown',
                reply_markup=location_keyboard
            )
        else:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown',
                reply_markup=location_keyboard
            )
    except Exception as e:
        print(f"Admin ga yuborishda xatolik: {e}")

# ============================================================================
# BUYURTMALAR BO'LIMI
# ============================================================================

@router.message(StateFilter(MainMenuStates.main_menu), F.text == "📦 Buyurtmalarim")
async def show_orders(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data or not user_data.get('orders'):
        await message.answer(
            "📦 *Buyurtmalar tarixi*\n\n❌ Sizda hali buyurtmalar yo'q.\n\nMahsulotlar bo'limidan buyurtma bering!",
            parse_mode='Markdown',
            reply_markup=back_keyboard()
        )
    else:
        text = "📦 *Sizning buyurtmalaringiz:*\n\n"
        for i, order in enumerate(reversed(user_data['orders']), 1):
            emoji = "⏳" if order.get('status') == 'pending' else "✅"
            status = "Kutilmoqda" if order.get('status') == 'pending' else "Yetkazildi"
            cap_text = " (bachok bilan)" if order.get('with_cap', True) else " (bachoksiz)"
            rating_info = f"⭐️ Baho: {'⭐️' * order.get('rating', 0)}" if order.get('rated') else ""
            text += (
                f"{i}. {emoji} *{order['product_name']}{cap_text}*\n"
                f"   📊 Soni: {order['quantity']} ta\n"
                f"   💰 Jami: {order['total']:,} so'm\n"
                f"   📅 {order['date']}\n"
                f"   📌 {status}\n"
                f"   {rating_info}\n\n"
            )
        
        await message.answer(text, parse_mode='Markdown', reply_markup=back_keyboard())
    
    await state.set_state(MainMenuStates.orders_menu)

@router.message(StateFilter(MainMenuStates.orders_menu), F.text == "⬅️ Ortga")
async def back_from_orders(message: Message, state: FSMContext):
    await message.answer("📱 Asosiy menyu:", reply_markup=main_menu_keyboard())
    await state.set_state(MainMenuStates.main_menu)

# ============================================================================
# PROFIL BO'LIMI
# ============================================================================

@router.message(StateFilter(MainMenuStates.main_menu), F.text == "👤 Ma'lumotlarim")
async def show_profile(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    
    if not user_data:
        await message.answer("❌ Xatolik! /start dan boshlang.")
        return
    
    text = (
        f"👤 *Sizning ma'lumotlaringiz:*\n\n"
        f"📝 Ism: {user_data['name']}\n"
        f"📱 Telefon: {user_data['phone']}\n"
        f"🏠 Uy manzili: {user_data['home_location_text']}\n"
        f"📍 Hozirgi manzil: {user_data.get('current_location_text', 'Kiritilmagan')}\n"
        f"📅 Ro'yxatdan o'tgan: {user_data.get('registered_date', 'Nomaʼlum')}"
    )
    
    await message.answer(text, parse_mode='Markdown', reply_markup=profile_keyboard())

@router.message(StateFilter(MainMenuStates.main_menu), F.text == "✏️ Tahrirlash")
async def edit_profile_menu(message: Message, state: FSMContext):
    await message.answer(
        "✏️ *Profilni tahrirlash*\n\nNimani o'zgartirmoqchisiz?",
        parse_mode='Markdown',
        reply_markup=edit_profile_keyboard()
    )
    await state.set_state(EditProfileStates.editing_menu)

@router.message(StateFilter(EditProfileStates.editing_menu), F.text == "✏️ Ismni o'zgartirish")
async def edit_name(message: Message, state: FSMContext):
    await message.answer("📝 Yangi ismingizni kiriting:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(EditProfileStates.edit_name)

@router.message(StateFilter(EditProfileStates.edit_name))
async def save_new_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        user_data['name'] = message.text
        save_user_data(user_id, user_data)
        await message.answer("✅ Ism o'zgartirildi!")
    
    await message.answer(
        "✏️ Profilni tahrirlash\n\nNimani o'zgartirmoqchisiz?",
        reply_markup=edit_profile_keyboard()
    )
    await state.set_state(EditProfileStates.editing_menu)

@router.message(StateFilter(EditProfileStates.editing_menu), F.text == "📱 Telefon raqamni o'zgartirish")
async def edit_phone(message: Message, state: FSMContext):
    await message.answer("📱 Yangi telefon raqamingizni yuboring:", reply_markup=request_phone_keyboard())
    await state.set_state(EditProfileStates.edit_phone)

@router.message(StateFilter(EditProfileStates.edit_phone), F.contact)
async def save_new_phone(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    if user_data:
        user_data['phone'] = message.contact.phone_number
        save_user_data(user_id, user_data)
        await message.answer("✅ Telefon raqam o'zgartirildi!")
    
    await message.answer(
        "✏️ Profilni tahrirlash\n\nNimani o'zgartirmoqchisiz?",
        reply_markup=edit_profile_keyboard()
    )
    await state.set_state(EditProfileStates.editing_menu)

@router.message(StateFilter(EditProfileStates.edit_phone))
async def save_new_phone_invalid(message: Message):
    await message.answer("❌ Iltimos, tugma orqali yuboring!", reply_markup=request_phone_keyboard())

@router.message(StateFilter(EditProfileStates.editing_menu), F.text == "📍 Lokatsiyani o'zgartirish")
async def edit_location(message: Message, state: FSMContext):
    await message.answer("📍 Qaysi lokatsiyani o'zgartirmoqchisiz?", reply_markup=location_choice_keyboard())
    await state.set_state(EditProfileStates.edit_location_choice)

@router.message(StateFilter(EditProfileStates.edit_location_choice), F.text == "🏠 Mening uyimga")
async def edit_home_location(message: Message, state: FSMContext):
    await message.answer("📍 Yangi uy lokatsiyangizni yuboring:", reply_markup=request_location_keyboard())
    await state.set_state(EditProfileStates.edit_home_location_geo)

@router.message(StateFilter(EditProfileStates.edit_location_choice), F.text == "📍 Hozirgi joyimga")
async def edit_current_location(message: Message, state: FSMContext):
    await message.answer("📍 Yangi hozirgi joyingizni yuboring:", reply_markup=request_location_keyboard())
    await state.set_state(EditProfileStates.edit_current_location_geo)

@router.message(StateFilter(EditProfileStates.edit_home_location_geo), F.location)
async def save_new_home_location_geo(message: Message, state: FSMContext):
    await state.update_data(
        new_home_location_geo={
            'latitude': message.location.latitude,
            'longitude': message.location.longitude
        }
    )
    await message.answer(
        "✅ Uy geo lokatsiya qabul qilindi!\n\n"
        "Endi yozma manzilingizni kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(EditProfileStates.edit_home_location_text)

@router.message(StateFilter(EditProfileStates.edit_current_location_geo), F.location)
async def save_new_current_location_geo(message: Message, state: FSMContext):
    await state.update_data(
        new_current_location_geo={
            'latitude': message.location.latitude,
            'longitude': message.location.longitude
        }
    )
    await message.answer(
        "✅ Hozirgi joy geo lokatsiya qabul qilindi!\n\n"
        "Endi yozma manzilingizni kiriting:",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(EditProfileStates.edit_current_location_text)

@router.message(StateFilter(EditProfileStates.edit_home_location_text))
async def save_new_home_location_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    data = await state.get_data()
    
    if user_data:
        user_data['home_location_geo'] = data.get('new_home_location_geo', user_data['home_location_geo'])
        user_data['home_location_text'] = message.text
        save_user_data(user_id, user_data)
        await message.answer("✅ Uy lokatsiyasi o'zgartirildi!")
    
    await message.answer(
        "✏️ Profilni tahrirlash\n\nNimani o'zgartirmoqchisiz?",
        reply_markup=edit_profile_keyboard()
    )
    await state.set_state(EditProfileStates.editing_menu)

@router.message(StateFilter(EditProfileStates.edit_current_location_text))
async def save_new_current_location_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = get_user_data(user_id)
    data = await state.get_data()
    
    if user_data:
        user_data['current_location_geo'] = data.get('new_current_location_geo', user_data.get('current_location_geo', {}))
        user_data['current_location_text'] = message.text
        save_user_data(user_id, user_data)
        await message.answer("✅ Hozirgi joyingiz o'zgartirildi!")
    
    await message.answer(
        "✏️ Profilni tahrirlash\n\nNimani o'zgartirmoqchisiz?",
        reply_markup=edit_profile_keyboard()
    )
    await state.set_state(EditProfileStates.editing_menu)

@router.message(StateFilter(EditProfileStates.editing_menu), F.text == "⬅️ Ortga")
async def back_from_editing(message: Message, state: FSMContext):
    await message.answer(
        "📱 Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )
    await state.set_state(MainMenuStates.main_menu)

@router.message(StateFilter(MainMenuStates.main_menu), F.text == "⬅️ Ortga")
async def back_from_profile(message: Message, state: FSMContext):
    await message.answer("📱 Asosiy menyu:", reply_markup=main_menu_keyboard())
    await state.set_state(MainMenuStates.main_menu)

# ============================================================================
# ORTGA QAYTISH (Barcha bo'limlar uchun)
# ============================================================================

@router.message(StateFilter(MainMenuStates.products_menu), F.text == "⬅️ Ortga")
async def back_from_products(message: Message, state: FSMContext):
    await message.answer("📱 Asosiy menyu:", reply_markup=main_menu_keyboard())
    await state.set_state(MainMenuStates.main_menu)

# ============================================================================
# HANDLERLARNI BOG'LASH FUNKSIYASI (Main.py uchun)
# ============================================================================

def setup_client_handlers(dp):
    """Client routerini umumiy Dispatcherga bog'laydi."""
    dp.include_router(router)
    print("Client routeri muvaffaqiyatli ulandi.")