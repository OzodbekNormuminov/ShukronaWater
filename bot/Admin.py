# bot/Admin.py (Yakuniy versiya: Kuryer sessiyasini avtomatik yaratish qo'shildi)

import os 
import json 
import time
import asyncio 
from pathlib import Path 
from aiogram.utils.markdown import html_decoration as hd

# ---------------- Aiogram Importlari ----------------
from aiogram import Router, F, types, Bot 
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Kuryer funksiyalarini import qilish: get_courier_keyboard va save_courier_session
try:
    from .Kuryer import get_courier_keyboard, save_courier_session
except ImportError:
    # Agar import xato bo'lsa, 'dummy' funksiyalarni yaratish
    def get_courier_keyboard():
        return types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="Kuryer Paneli Xato")]],
            resize_keyboard=True
        )
    def save_courier_session(user_id, message_data):
        # Admin Kuryer sessiyasini saqlay olmaganini ko'rsatuvchi xabar
        print(f"XATO: Kuryer sessiyasini saqlash funksiyasi (save_courier_session) yuklanmadi. ID: {user_id}")
        return {}

# ----------------- Konstanta -----------------
COMMISSION_RATE = 0.10 

# ----------------- Fayl yo'llari -----------------
SESSION_FILE = Path(__file__).parent / 'admin.json' 
DATABASE_FILE = Path(__file__).parent / 'database.json' 
PRODUCTS_FILE = Path(__file__).parent / 'products.json' 
COURIERS_FILE = Path(__file__).parent / 'couriers.json' 

# --------------------------------------------------------------------------------------
# FSM (Holatlar)
# --------------------------------------------------------------------------------------
class AdminStates(StatesGroup):
    broadcast_message = State()
    add_product_name = State()
    add_product_description = State()
    add_product_price = State()
    add_product_photo = State() 
    delete_product_id = State() 
    add_courier_id = State()
    add_courier_username = State()
    delete_courier_id = State() 
    waiting_for_courier_id_report = State() 

# --------------------------------------------------------------------------------------
# JSON bilan ishlash funksiyalari (Admin sessiya, DB, Product, Courier)
# --------------------------------------------------------------------------------------

def load_admin_sessions():
    if not SESSION_FILE.exists():
        return {}
    try:
        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_admin_session(user_id, message_data):
    sessions = load_admin_sessions()
    session_data = {
        'id': user_id,
        'username': message_data.from_user.username,
        'first_name': message_data.from_user.first_name,
        'login_time': time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
        'timestamp': time.time()
    }
    sessions[str(user_id)] = session_data
    try:
        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"XATO: Admin sessiyasini saqlashda xato yuz berdi: {e}")
    return session_data

def load_products():
    if not PRODUCTS_FILE.exists():
        return {}
    try:
        with open(PRODUCTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_products(data):
    try:
        with open(PRODUCTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"XATO: products.json ga saqlashda xato yuz berdi: {e}")
        return False

def load_couriers():
    if not COURIERS_FILE.exists():
        return {}
    try:
        with open(COURIERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_couriers(data):
    try:
        with open(COURIERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"XATO: couriers.json ga saqlashda xato yuz berdi: {e}")
        return False

def load_database():
    if not DATABASE_FILE.exists():
        return {}
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def get_all_user_ids():
    if not DATABASE_FILE.exists():
        return []
    try:
        with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            user_ids = [int(user_id) for user_id in data.keys()] 
            return user_ids
        return []
    except Exception:
        return []

# --------------------------------------------------------------------------------------
# Kuryer.py dagi Hisobot Mantiqi (local nusxasi)
# --------------------------------------------------------------------------------------
def aggregate_courier_stats(courier_id: str):
    db_data = load_database()
    delivered_orders = []
    total_delivered_count = 0
    total_sales_amount = 0
    total_commission = 0
    
    for _, user_data in db_data.items():
        user_orders = user_data.get('orders', [])
        
        for order in user_orders:
            if order.get('status') == 'delivered' and str(order.get('courier_id')) == courier_id:
                
                total_delivered_count += 1
                order_total = order.get('total', 0)
                commission = int(order_total * COMMISSION_RATE)
                
                total_sales_amount += order_total
                total_commission += commission
                
                delivered_orders.append({
                    'order_id': order.get('order_id'),
                    'total': order_total,
                    'commission': commission,
                    'date': order.get('delivered_at', order.get('date', 'Noma\'lum sana'))
                })
                
    delivered_orders.sort(key=lambda x: x['date'], reverse=True)
    
    return {
        'orders_list': delivered_orders,
        'count': total_delivered_count,
        'total_sales': total_sales_amount,
        'total_commission': total_commission
    }


# --------------------------------------------------------------------------------------
# ADMIN ID'LARINI VA PAROLINI YUKLASH 
# --------------------------------------------------------------------------------------
ADMIN_IDS_STR = os.getenv("ADMIN_IDS")
ADMIN_PASSWORD_RAW = os.getenv("ADMIN_PASSWORD") 

# FALLBACK
if not ADMIN_IDS_STR:
    ADMIN_IDS_STR = "6415095591, 5879651176, 5111382924" 

if not ADMIN_PASSWORD_RAW:
    ADMIN_PASSWORD_RAW = "Shukrona" 

ADMIN_PASSWORD = ADMIN_PASSWORD_RAW.strip() if ADMIN_PASSWORD_RAW else None

if ADMIN_IDS_STR:
    try:
        ADMINS = [int(i.strip()) for i in ADMIN_IDS_STR.split(',')]
    except ValueError:
        ADMINS = []
else:
    ADMINS = [] 
# --------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------
# KEYBOARDS
# ----------------------------------------------------------------------------------
def get_products_inline_keyboard():
    btn_add = types.InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="prod_add")
    btn_delete = types.InlineKeyboardButton(text="🗑️ Mahsulot o'chirish", callback_data="prod_delete")
    keyboard = [[btn_add, btn_delete]]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_courier_inline_keyboard():
    btn_add = types.InlineKeyboardButton(text="➕ Kuryer qo'shish", callback_data="courier_add")
    btn_delete = types.InlineKeyboardButton(text="🗑️ Kuryerni o'chirish", callback_data="courier_delete") 
    btn_report = types.InlineKeyboardButton(text="📝 Kuryer hisoboti", callback_data="courier_report")
    btn_back = types.InlineKeyboardButton(text="🔙 Ortga", callback_data="courier_control_back")

    keyboard = [[btn_add, btn_delete], [btn_report], [btn_back]]
    return types.InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_keyboard():
    btn_stats = types.KeyboardButton(text="📊 Umumiy Statistika") 
    btn_courier_stats = types.KeyboardButton(text="🏍️ Kuryer nazorati") 
    btn_products = types.KeyboardButton(text="🛍️ Mahsulotlar") 
    btn_broadcast = types.KeyboardButton(text="📢 Xabarnoma yuborish")
    keyboard_rows = [[btn_stats, btn_courier_stats], [btn_products, btn_broadcast]]
    markup = types.ReplyKeyboardMarkup(
        keyboard=keyboard_rows, 
        resize_keyboard=True, 
        input_field_placeholder="Admin buyrug'ini kiriting...",
    )
    return markup


# --------------------------------------------------------------------------------------
# ADMIN ROUTER VA HANDLERLAR
# --------------------------------------------------------------------------------------
admin_router = Router()

# ----------------------------------------------------------------------------------
# YORDAMCHI FUNKSIYA: MAHSULOTNI SAQLASH MANTIQI
# ----------------------------------------------------------------------------------
async def _save_product_data(message: types.Message, state: FSMContext, photo_file_id: str | None):
    data = await state.get_data()
    products = load_products()
    
    new_id = "1"
    if products:
        try:
            last_id = max([int(key) for key in products.keys()])
            new_id = str(last_id + 1)
        except ValueError:
             new_id = "1"
    
    new_product = {
        "id": new_id,
        "name": data.get('new_product_name'),
        "description": data.get('new_product_description'),
        "price": data.get('new_product_price'),
        "image": photo_file_id, 
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    products[new_id] = new_product
    
    if save_products(products):
        await message.answer(
            hd.bold("✅ Mahsulot muvaffaqiyatli qo'shildi!") + "\n\n"
            f"ID: {hd.code(new_id)}\n"
            f"Nomi: {hd.bold(new_product['name'])}\n"
            f"Narxi: {hd.bold(f'{new_product['price']:,}')} so'm",
            parse_mode='HTML',
            reply_markup=get_admin_keyboard() 
        )
    else:
         await message.answer("❌ <b>Xatolik!</b> Mahsulotni saqlashda muammo yuz berdi.", parse_mode='HTML', reply_markup=get_admin_keyboard())

    await state.clear()


# ----------------------------------------------------------------------------------
# 1. /admin buyrug'i (Kirish)
# ----------------------------------------------------------------------------------
@admin_router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMINS:
        await message.answer("⛔ Kirish huquqi yo'q.")
        return
        
    sessions = load_admin_sessions()
    
    if str(user_id) in sessions:
        response_text = (
            f"💡 {hd.bold('Siz allaqachon Admin paneldasiz!')}\n\n"
            f"👤 ID: {hd.code(user_id)}\n"
            f"Marhamat, paneldan foydalaning."
        )
        await message.answer(response_text, parse_mode="HTML", reply_markup=get_admin_keyboard())
        return

    parts = message.text.split()
    
    if len(parts) < 2 or parts[1].strip() != ADMIN_PASSWORD:
        await message.answer("❌ Noto'g'ri parol. Parolni /admin dan keyin yozing.")
        return

    save_admin_session(user_id, message)
    await message.answer("✅ Parol to'g'ri. Admin paneliga xush kelibsiz!", reply_markup=get_admin_keyboard())
    await message.answer(f"💾 {hd.bold('Sessiya saqlandi!')}...", parse_mode="HTML")
        
# ----------------------------------------------------------------------------------
# 2. Xabarnoma yuborish (START / PROCESS)
# ----------------------------------------------------------------------------------
@admin_router.message(F.text == "📢 Xabarnoma yuborish")
async def start_broadcast(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if user_id not in ADMINS or str(user_id) not in load_admin_sessions():
        await message.answer("⚠️ Kirish uchun ruxsat yo'q.")
        return
    
    await message.answer("✉️ <b>Yuboriladigan xabarnoma matnini (yoki rasm/video) kiriting</b>:", parse_mode='HTML')
    await state.set_state(AdminStates.broadcast_message)


@admin_router.message(AdminStates.broadcast_message, F.content_type.in_({'text', 'photo', 'video', 'document'}))
async def process_broadcast(message: types.Message, state: FSMContext):
    admin_id = message.from_user.id
    
    try:
        await state.clear() 
        await message.answer("🚀 Xabarnoma yuborish boshlandi...")

        recipient_ids = get_all_user_ids()
        if admin_id in recipient_ids:
            recipient_ids.remove(admin_id) 
            
        success_count = 0
        failed_count = 0
        
        if len(recipient_ids) > 0:
            for user_id in recipient_ids:
                try:
                    await message.copy_to(chat_id=user_id) 
                    success_count += 1
                except Exception:
                    failed_count += 1
                await asyncio.sleep(0.05)
                
        await message.answer(
            (f"✅ {hd.bold('Xabarnoma yakunlandi!')}\n\n"
             f"📤 Yuborildi: {hd.bold(str(success_count))} ta\n"
             f"❌ Yuborilmadi (bloklangan/xato): {hd.bold(str(failed_count))} ta"),
            parse_mode="HTML",
            reply_markup=get_admin_keyboard() 
        )

    except Exception as handler_error:
        await message.answer(f"❌ <b>Xabarnoma Yuborishda Kritik xato!</b>\n\nXato: <code>{handler_error}</code>", parse_mode='HTML')

# ----------------------------------------------------------------------------------
# 3. Statistika tugmasi
# ----------------------------------------------------------------------------------
@admin_router.message(F.text == "📊 Umumiy Statistika")
async def handle_admin_stats(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMINS or str(user_id) not in load_admin_sessions():
        await message.answer("⚠️ Kirish uchun ruxsat yo'q.")
        return

    total_users = len(get_all_user_ids())
    
    response = (
        f"📈 {hd.bold('UMUMIY BOT STATISTIKASI')}\n\n"
        f"👥 {hd.bold('Jami foydalanuvchilar:')} {total_users:,} ta\n"
        f"📦 {hd.bold('Mahsulotlar soni:')} {len(load_products()):,} ta\n"
        f"🏍️ {hd.bold('Kuryerlar soni:')} {len(load_couriers()):,} ta\n"
    )

    await message.answer(response, parse_mode="HTML")


# ----------------------------------------------------------------------------------
# 4. Kuryer Nazorati tugmasi (Asosiy kuryer menyusi)
# ----------------------------------------------------------------------------------
@admin_router.message(F.text == "🏍️ Kuryer nazorati")
async def handle_courier_management(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMINS or str(user_id) not in load_admin_sessions():
        await message.answer("⚠️ Kirish uchun ruxsat yo'q.")
        return

    couriers = load_couriers()
    
    courier_list_text = f"🏍️ {hd.bold('KURYERLARNI BOSHQARISH PANELI')}\n\n"
    
    if not couriers:
        courier_list_text += "👥 Hozircha hech qanday kuryer qo'shilmagan."
    else:
        courier_list_text += f"👥 {hd.bold('Mavjud Kuryerlar:')}\n"
        for idx, (courier_id, data) in enumerate(couriers.items(), 1):
             username = data.get('username', 'Noma\'lum')
             courier_list_text += f"{idx}. ID: {hd.code(courier_id)} | Username: {hd.bold(f'@{username}')}\n"

    courier_list_text += "\nKerakli amalni tanlang:"
        
    await message.answer(courier_list_text, parse_mode="HTML", reply_markup=get_courier_inline_keyboard())

# ----------------------------------------------------------------------------------
# 4.6. Kuryer nazorati menyusidan ortga qaytish
# ----------------------------------------------------------------------------------
@admin_router.callback_query(F.data == "courier_control_back")
async def callback_courier_control_back(call: types.CallbackQuery):
    if call.from_user.id not in ADMINS or str(call.from_user.id) not in load_admin_sessions():
        await call.answer("⚠️ Kirish uchun ruxsat yo'q.", show_alert=True)
        return
        
    await call.answer()
    
    await call.message.delete()
    await call.message.answer("Admin Panelga qaytildi.", reply_markup=get_admin_keyboard())


# ----------------------------------------------------------------------------------
# KURYER QO'SHISH HANDLERLARI (FSM)
# ----------------------------------------------------------------------------------

# 4.1. Kuryer qo'shishni boshlash (courier_add callback)
@admin_router.callback_query(F.data == "courier_add")
async def callback_add_courier_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS or str(call.from_user.id) not in load_admin_sessions():
        await call.answer("⚠️ Kirish uchun ruxsat yo'q.", show_alert=True)
        return
        
    await call.answer()
    
    await call.message.edit_text("➕ <b>Yangi kuryer qo'shish jarayoni boshlandi.</b>\n\n🆔 Iltimos, kuryerning <b>Telegram ID</b> raqamini kiriting. Jarayonni bekor qilish uchun: <code>/cancel</code>", parse_mode="HTML")
    await state.set_state(AdminStates.add_courier_id)

# 4.2. Kuryer ID ni qabul qilish
@admin_router.message(AdminStates.add_courier_id, F.text)
async def process_add_courier_id(message: types.Message, state: FSMContext):
    courier_id_str = message.text.strip()
    
    try:
        courier_id = int(courier_id_str)
        courier_id_to_save = str(courier_id) 
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, <b>faqat butun son</b> (ID) kiriting:", parse_mode='HTML')
        return

    couriers = load_couriers()
    if courier_id_to_save in couriers:
        await message.answer(f"❌ <b>ID <code>{courier_id_to_save}</code></b> ro'yxatda allaqachon mavjud.", parse_mode="HTML")
        return
        
    await state.update_data(new_courier_id=courier_id_to_save)
    await message.answer("✅ ID qabul qilindi.\n\n👤 Endi kuryerning <b>Username</b>'ini kiriting (Agar Username bo'lmasa, <b>-</b> belgisini kiriting):", parse_mode='HTML')
    await state.set_state(AdminStates.add_courier_username)

# 4.3. Kuryer Username ni qabul qilish va saqlash
@admin_router.message(AdminStates.add_courier_username, F.text)
async def process_add_courier_username(message: types.Message, state: FSMContext, bot: Bot):
    username = message.text.strip()
    
    final_username = username.lstrip('@') if username != "-" else "Noma'lum"
        
    data = await state.get_data()
    courier_id = data.get('new_courier_id')
    courier_id_int = int(courier_id)
    
    couriers = load_couriers()
    
    new_courier = {
        "id": courier_id,
        "username": final_username,
        "added_by": str(message.from_user.id),
        "added_at": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    couriers[courier_id] = new_courier
    
    if save_couriers(couriers):
        
        # 1. Kuryer sessiyasini yaratish (Darhol kirish uchun)
        temp_message = types.Message(message_id=0, date=int(time.time()), chat=types.Chat(id=courier_id_int, type='private'), from_user=types.User(id=courier_id_int, is_bot=False, first_name=final_username, username=final_username))
        
        # save_courier_session funksiyasi Admin.py ning boshida import qilingan
        save_courier_session(courier_id_int, temp_message) 
        
        courier_message = (
            f"🎉 {hd.bold('Tabriklaymiz!')}\n\n"
            f"Siz botning kuryerlar ro'yxatiga qo'shildingiz.\n"
            f"ID: <code>{courier_id}</code>.\n\n"
            f"Kuryer paneli faollashtirildi. Marhamat, quyidagi klaviaturadan foydalaning."
        )
        
        try:
            await bot.send_message(
                chat_id=courier_id_int, 
                text=courier_message,
                parse_mode='HTML',
                reply_markup=get_courier_keyboard() 
            )
            courier_status = "✅ Kuryerga xabar yuborildi va paneli faollashtirildi."
        except Exception as e:
            courier_status = f"❌ Kuryerga xabar yuborilmadi. (Botni bloklagan bo'lishi mumkin. Xato: {e})"
        
        await message.answer(
            f"✅ {hd.bold('Kuryer muvaffaqiyatli qo\'shildi!')}\n\n"
            f"ID: {hd.code(courier_id)}\n"
            f"Username: {hd.bold(f'@{final_username}')}\n"
            f"Xabar holati: {courier_status}",
            parse_mode='HTML',
            reply_markup=get_admin_keyboard()
        )
    else:
         await message.answer("❌ <b>Xatolik!</b> Kuryerni saqlashda muammo yuz berdi.", parse_mode='HTML', reply_markup=get_admin_keyboard())

    await state.clear()
    
# ----------------------------------------------------------------------------------
# KURYER O'CHIRISH HANDLERLARI (FSM)
# ----------------------------------------------------------------------------------

# 4.4. Kuryer o'chirishni boshlash (courier_delete callback)
@admin_router.callback_query(F.data == "courier_delete")
async def callback_delete_courier_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS or str(call.from_user.id) not in load_admin_sessions():
        await call.answer("⚠️ Kirish uchun ruxsat yo'q.", show_alert=True)
        return
        
    await call.answer()
    
    await call.message.edit_text("🗑️ <b>Kuryerni o'chirish jarayoni boshlandi.</b>\n\n🆔 Iltimos, o'chiriladigan kuryerning <b>ID raqamini</b> kiriting:", parse_mode="HTML")
    await state.set_state(AdminStates.delete_courier_id)

# 4.5. Kuryer ID ni qabul qilish va o'chirish
@admin_router.message(AdminStates.delete_courier_id, F.text)
async def process_delete_courier(message: types.Message, state: FSMContext, bot: Bot):
    target_id_str = message.text.strip()
    
    try:
        target_id_int = int(target_id_str)
        target_id_str = str(target_id_int) 
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, <b>faqat raqamli ID</b> kiriting:", parse_mode='HTML')
        return

    couriers = load_couriers()
    
    if target_id_str not in couriers:
        await message.answer(f"❌ <b>ID <code>{target_id_str}</code></b> raqamli kuryer topilmadi.", parse_mode="HTML")
        return
        
    deleted_courier = couriers.pop(target_id_str) 
    
    if save_couriers(couriers): 
        try:
            await bot.send_message(
                chat_id=target_id_int,
                text=f"⛔ {hd.bold('DIQQAT!')} Siz Kuryerlar ro'yxatidan o'chirildingiz.",
                parse_mode='HTML',
                reply_markup=types.ReplyKeyboardRemove() 
            )
            delete_status = "✅ Kuryerga xabar yuborildi."
        except Exception:
            delete_status = "❌ Kuryerga xabar yuborilmadi."
            
        await message.answer(
            f"✅ {hd.bold('Kuryer muvaffaqiyatli o\'chirildi!')}\n\n"
            f"ID: {hd.code(target_id_str)}\n"
            f"Username: {hd.bold(f'@{deleted_courier.get('username', 'Noma\'lum')}')}\n"
            f"Xabar holati: {delete_status}",
            parse_mode='HTML',
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ <b>Kritik Xatolik!</b> Kuryerni o'chirishdan so'ng saqlashda muammo yuz berdi.", parse_mode='HTML', reply_markup=get_admin_keyboard())
        
    await state.clear()
    
# ----------------------------------------------------------------------------------
# 5. Kuryer hisoboti
# ----------------------------------------------------------------------------------
# 5.1. Kuryer hisoboti (courier_report callback) - ID so'rash
@admin_router.callback_query(F.data == "courier_report")
async def callback_courier_report_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS or str(call.from_user.id) not in load_admin_sessions():
        await call.answer("⚠️ Kirish uchun ruxsat yo'q.", show_alert=True)
        return
        
    await call.answer()
    
    await call.message.edit_text(
        f"📝 {hd.bold('Kuryer hisobotini olish.')}\n\n🆔 Iltimos, hisoboti kerak bo'lgan kuryerning <b>Telegram ID'sini</b> kiriting:", 
        parse_mode="HTML", 
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Ortga", callback_data="courier_control_back")]])
    )
    await state.set_state(AdminStates.waiting_for_courier_id_report)

# 5.2. Kuryer ID ni qabul qilish va hisobot chiqarish
@admin_router.message(AdminStates.waiting_for_courier_id_report, F.text)
async def process_courier_report(message: types.Message, state: FSMContext):
    
    courier_id = message.text.strip()
    await state.clear() 

    if not courier_id.isdigit():
        await message.answer("❌ Noto'g'ri format. Iltimos, faqat raqamlardan iborat ID kiriting.", reply_markup=get_admin_keyboard())
        return

    couriers_list = load_couriers()
    courier_data = couriers_list.get(courier_id, {})
    courier_name = courier_data.get('username', "Noma'lum Kuryer")
    is_official = courier_id in couriers_list

    stats = aggregate_courier_stats(courier_id)

    response = f"📊 {hd.bold('Kuryer Hisoboti')} - ID: <code>{courier_id}</code>\n"
    response += f"👤 {hd.bold('Ism:')} {courier_name}\n"
    response += f"⭐ {hd.bold('Rasmiy kuryer:')} {'✅ Ha' if is_official else '❌ Yo\'q'}\n\n"

    response += f"📈 {hd.bold('Umumiy Ma\'lumotlar:')}\n"
    response += f"  - {hd.bold('Yetkazilgan zakazlar soni:')} {stats['count']} ta\n"
    response += f"  - {hd.bold('Umumiy savdo summasi:')} {stats['total_sales']:,} so'm\n"
    response += f"  - {hd.bold('Kuryerning umumiy komissiyasi (10%):')}\n"
    response += f"    {hd.bold(f'{stats['total_commission']:,} so\'m')}\n\n"
    
    response += "----------------------------------------\n"
    response += hd.bold("Oxirgi yetkazilgan zakazlar (Max. 10 ta):") + "\n"

    if stats['count'] == 0:
        response += "❌ Ushbu kuryer tomonidan yetkazilgan buyurtmalar mavjud emas."
    else:
        for order in stats['orders_list'][:10]:
            response += (
                f"  - 🆔 #{order['order_id']} ({order['date'].split(' ')[0]})\n"
                f"    Summa: {order['total']:,} | Foyda: {hd.bold(f"{order['commission']:,}")} so'm\n"
            )
        
        if stats['count'] > 10:
             response += f"\n...va yana {stats['count'] - 10} ta zakaz."
    
    await message.answer(response, parse_mode="HTML", reply_markup=get_admin_keyboard())

# ----------------------------------------------------------------------------------
# 6. MAHSULOTLAR tugmasi va uning inline/fsm handlerlari
# ----------------------------------------------------------------------------------

@admin_router.message(F.text == "🛍️ Mahsulotlar")
async def handle_products_button(message: types.Message):
    user_id = message.from_user.id
    if user_id not in ADMINS or str(user_id) not in load_admin_sessions():
        await message.answer("⚠️ Kirish uchun ruxsat yo'q.")
        return
    
    products = load_products()
    product_list_text = f"🛍️ {hd.bold('MAHSULOTLAR RO\'YXATI')}\n\n"
    
    if not products:
        product_list_text += "❌ Hozircha hech qanday mahsulot mavjud emas."
    else:
        sorted_products = dict(sorted(products.items(), key=lambda item: int(item[0])))
        
        for product_id, product_data in sorted_products.items():
            name = product_data.get('name', 'Nomsiz mahsulot')
            price = product_data.get('price', 0)
            
            product_list_text += (
                f"➖➖➖➖➖➖➖➖➖➖\n"
                f"🆔 {hd.bold('ID:')} {hd.code(product_id)}\n"
                f"🏷️ {hd.bold('Nomi:')} {name}\n"
                f"💰 {hd.bold('Narxi:')} {price:,} so'm\n"
            )
        
        product_list_text += "\n"
        
    product_list_text += "Kerakli amalni tanlang:"

    await message.answer(product_list_text, parse_mode="HTML", reply_markup=get_products_inline_keyboard())

# 6.1. Mahsulot o'chirishni boshlash (prod_delete callback)
@admin_router.callback_query(F.data == "prod_delete")
async def callback_delete_product_start(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS or str(call.from_user.id) not in load_admin_sessions():
        await call.answer("⚠️ Kirish uchun ruxsat yo'q.", show_alert=True)
        return
        
    await call.answer()
    
    await call.message.edit_text("🗑️ <b>Mahsulot o'chirish jarayoni boshlandi.</b>\n\nIltimos, o'chiriladigan mahsulotning <b>ID raqamini</b> kiriting:", parse_mode='HTML', reply_markup=None)
    
    await state.set_state(AdminStates.delete_product_id)

# 6.2. Mahsulot o'chirishni yakunlash (ID ni qabul qilish)
@admin_router.message(AdminStates.delete_product_id, F.text)
async def process_delete_product(message: types.Message, state: FSMContext):
    
    target_id_str = message.text.strip()
    
    try:
        target_id_int = int(target_id_str)
        target_id_str = str(target_id_int) 
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Iltimos, <b>faqat raqamli ID</b> kiriting:", parse_mode='HTML')
        return

    products = load_products()
    
    if target_id_str not in products:
        await message.answer(f"❌ <b>ID <code>{target_id_str}</code></b> raqamli mahsulot topilmadi. Ro'yxatni tekshiring va ID ni qayta kiriting:", parse_mode="HTML")
        return
        
    deleted_product = products.pop(target_id_str)
    
    if save_products(products):
        await message.answer(
            f"✅ {hd.bold('Mahsulot muvaffaqiyatli o\'chirildi!')}\n\n"
            f"ID: {hd.code(target_id_str)}\n"
            f"Nomi: {hd.bold(deleted_product.get('name', 'Noma\'lum'))}\n\n"
            f"Admin panelga qaytishingiz mumkin.",
            parse_mode='HTML',
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer("❌ <b>Kritik Xatolik!</b> Mahsulotni o'chirishdan so'ng saqlashda muammo yuz berdi.", parse_mode='HTML', reply_markup=get_admin_keyboard())
        
    await state.clear()


# 7. MAHSULOT QO'SHISH HANDLERLARI (FSM)
# 7.1. Mahsulot qo'shishni boshlash (prod_add callback)
@admin_router.callback_query(F.data == "prod_add")
async def callback_add_product(call: types.CallbackQuery, state: FSMContext):
    if call.from_user.id not in ADMINS or str(call.from_user.id) not in load_admin_sessions():
        await call.answer("⚠️ Kirish uchun ruxsat yo'q.", show_alert=True)
        return
        
    await call.answer()
    
    await call.message.edit_text("➕ <b>Yangi mahsulot qo'shish jarayoni boshlandi.</b>\n\n📝 Iltimos, <b>mahsulot nomini</b> kiriting:", parse_mode='HTML', reply_markup=None)
    
    await state.set_state(AdminStates.add_product_name)

# 7.2. Nomni qabul qilish
@admin_router.message(AdminStates.add_product_name, F.text)
async def process_add_product_name(message: types.Message, state: FSMContext):
    await state.update_data(new_product_name=message.text.strip())
    await message.answer("✅ Nom qabul qilindi.\n\n📄 Endi mahsulot <b>ta'rifini</b> (description) kiriting:", parse_mode='HTML')
    await state.set_state(AdminStates.add_product_description)

# 7.3. Ta'rifni qabul qilish
@admin_router.message(AdminStates.add_product_description, F.text)
async def process_add_product_description(message: types.Message, state: FSMContext):
    await state.update_data(new_product_description=message.text.strip())
    await message.answer("✅ Ta'rif qabul qilindi.\n\n💰 Endi mahsulot <b>narxini</b> (butun son) kiriting:", parse_mode='HTML')
    await state.set_state(AdminStates.add_product_price)

# 7.4. Narxni qabul qilish (Tekshiruv bilan)
@admin_router.message(AdminStates.add_product_price, F.text)
async def process_add_product_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text.strip())
        if price <= 0:
             raise ValueError
    except ValueError:
        await message.answer("❌ Noto'g'ri qiymat. Iltimos, narxni <b>faqat butun musbat son</b> bilan kiriting:", parse_mode='HTML')
        return
        
    await state.update_data(new_product_price=price)
    
    await message.answer("✅ Narx qabul qilindi.\n\n🖼️ Endi mahsulot <b>rasmini</b> yuboring (Bu ixtiyoriy, agar rasm bo'lmasa, shunchaki <code>/skip</code> buyrug'ini yuboring):", parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AdminStates.add_product_photo)

# 7.5. Rasmni qabul qilish (faqat F.photo bo'lsa)
@admin_router.message(AdminStates.add_product_photo, F.photo)
async def process_add_product_photo_with_file(message: types.Message, state: FSMContext):
    photo_file_id = message.photo[-1].file_id
    await _save_product_data(message, state, photo_file_id)

# 7.6. /skip buyrug'ini qabul qilish
@admin_router.message(AdminStates.add_product_photo, Command("skip"))
async def process_add_product_photo_skip(message: types.Message, state: FSMContext):
    await _save_product_data(message, state, photo_file_id=None)

# 7.7. Boshqa matn yoki fayllarni rad etish
@admin_router.message(AdminStates.add_product_photo)
async def process_add_product_photo_invalid(message: types.Message):
    await message.answer("❌ Noto'g'ri format. Iltimos, <b>rasm</b> yuboring yoki <code>/skip</code> ni bosing.", parse_mode='HTML')

# ----------------------------------------------------------------------------------
# FSM ni Bekor qilish Handleri
# ----------------------------------------------------------------------------------
@admin_router.message(Command("cancel"))
@admin_router.message(F.text.lower() == "bekor qilish")
async def cancel_handler(message: types.Message, state: FSMContext):
    """FSM jarayonini bekor qilish va Admin keyboardni qaytarish"""
    current_state = await state.get_state()
    
    if current_state is None:
        if message.from_user.id in ADMINS and str(message.from_user.id) in load_admin_sessions():
             await message.answer("❌ Hozirda hech qanday faol jarayon yo'q.", reply_markup=get_admin_keyboard())
        else:
             await message.answer("❌ Hozirda hech qanday faol jarayon yo'q.")
        return 
    
    await state.clear() 
    
    if message.from_user.id in ADMINS and str(message.from_user.id) in load_admin_sessions():
        await message.answer("✅ Jorayon bekor qilindi. Admin panelga qaytildi.", reply_markup=get_admin_keyboard())
    else:
        await message.answer("✅ Jorayon bekor qilindi.", reply_markup=types.ReplyKeyboardRemove())

# ----------------------------------------------------------------------------------
# HANDLERLARNI BOG'LASH FUNKSIYASI
# ----------------------------------------------------------------------------------

def setup_admin_handlers(dp): 
    """Admin routerini umumiy Dispatcherga bog'laydi."""
    dp.include_router(admin_router)
    print("Admin routeri muvaffaqiyatli ulandi.")