from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, ConversationHandler
import logging
import os
import openpyxl
from datetime import datetime

# تنظیمات
TOKEN = "7265240527:AAEQwHkTYRidmH6-_MLdIuLgg0izdSbQAgw"
ADMIN_CHAT_ID = -1002393195820
EXCEL_FILE = "payments.xlsx"

# مرحله‌ها
NAME, PHONE, AMOUNT, DATE, FILE = range(5)

# ربات و فلَسک
bot = Bot(token=TOKEN)
app = Flask(__name__)

# ثبت لاگ‌ها
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ذخیره اطلاعات
def save_to_excel(data):
    if not os.path.exists(EXCEL_FILE):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["Name", "Phone", "Amount", "Date", "File"])
        wb.save(EXCEL_FILE)

    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append(data)
    wb.save(EXCEL_FILE)

# استارت
def start(update, context):
    update.message.reply_text("👋 لطفاً نام و نام خانوادگی خود را وارد کنید:")
    return NAME

def get_name(update, context):
    context.user_data["name"] = update.message.text
    update.message.reply_text("📱 لطفاً شماره تماس یا شماره دانش‌آموزی خود را وارد کنید:")
    return PHONE

def get_phone(update, context):
    context.user_data["phone"] = update.message.text
    update.message.reply_text("💰 مبلغ واریزی را وارد کنید:")
    return AMOUNT

def get_amount(update, context):
    context.user_data["amount"] = update.message.text
    update.message.reply_text("📅 تاریخ واریز را وارد کنید (مثلاً 1403/03/01):")
    return DATE

def get_date(update, context):
    context.user_data["date"] = update.message.text
    update.message.reply_text("🧾 لطفاً تصویر یا فایل فیش را ارسال کنید:")
    return FILE

def get_file(update, context):
    file = update.message.document or update.message.photo[-1]
    file_id = file.file_id
    file_path = f"receipt_{update.message.from_user.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    bot.get_file(file_id).download(file_path)

    context.user_data["file"] = file_path

    # ذخیره در فایل اکسل
    save_to_excel([
        context.user_data["name"],
        context.user_data["phone"],
        context.user_data["amount"],
        context.user_data["date"],
        file_path
    ])

    # ارسال به گروه
    caption = (
        f"🧾 فیش جدید:\n"
        f"👤 نام: {context.user_data['name']}\n"
        f"📞 شماره: {context.user_data['phone']}\n"
        f"💰 مبلغ: {context.user_data['amount']}\n"
        f"📅 تاریخ: {context.user_data['date']}"
    )

    with open(file_path, "rb") as f:
        bot.send_photo(chat_id=ADMIN_CHAT_ID, photo=f, caption=caption)

    update.message.reply_text("✅ فیش با موفقیت ثبت شد. سپاسگزاریم!")
    return ConversationHandler.END

def cancel(update, context):
    update.message.reply_text("⛔ عملیات لغو شد.")
    return ConversationHandler.END

def report(update, context):
    if update.effective_chat.id == ADMIN_CHAT_ID:
        if os.path.exists(EXCEL_FILE):
            bot.send_document(chat_id=ADMIN_CHAT_ID, document=open(EXCEL_FILE, "rb"))
        else:
            update.message.reply_text("❗ فایل گزارش پیدا نشد.")
    else:
        update.message.reply_text("⛔ فقط ادمین به این دستور دسترسی دارد.")

# تعریف دیسپچر برای هندل کردن پیام‌ها
dispatcher = Dispatcher(bot, None, use_context=True)
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        NAME: [MessageHandler(Filters.text & ~Filters.command, get_name)],
        PHONE: [MessageHandler(Filters.text & ~Filters.command, get_phone)],
        AMOUNT: [MessageHandler(Filters.text & ~Filters.command, get_amount)],
        DATE: [MessageHandler(Filters.text & ~Filters.command, get_date)],
        FILE: [MessageHandler(Filters.document | Filters.photo, get_file)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
dispatcher.add_handler(conv_handler)
dispatcher.add_handler(CommandHandler("report", report))

# route اصلی webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# route تست
@app.route('/')
def index():
    return "ربات فعال است ✅"

# اجرای Flask
if __name__ == '__main__':
    app.run(port=8080)

