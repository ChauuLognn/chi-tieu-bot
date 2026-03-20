import os
import time
import json
from telegram import Update
from groq import Groq
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from database import init_db, add_expense, get_summary, get_recent, delete_last
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


SYSTEM_PROMPT = """Bạn là trợ lý phân tích chi tiêu. Khi người dùng nhắn tin mô tả một khoản chi tiêu,
hãy trả về JSON với format sau và KHÔNG có gì khác, không có markdown, không có backtick:
{"amount": <số tiền dạng số>, "category": "<danh mục>", "description": "<mô tả ngắn>"}

Các danh mục: ăn uống, di chuyển, mua sắm, giải trí, sức khỏe, hóa đơn, khác

Ví dụ:
- "ăn sáng 35k" → {"amount": 35000, "category": "ăn uống", "description": "ăn sáng"}
- "đổ xăng 100 nghìn" → {"amount": 100000, "category": "di chuyển", "description": "đổ xăng"}
- "mua áo 250k" → {"amount": 250000, "category": "mua sắm", "description": "mua áo"}

Nếu tin nhắn KHÔNG phải chi tiêu, trả về: {"amount": null}"""

import time

def parse_expense(text, retry=3):
    for i in range(retry):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0
            )
            raw = response.choices[0].message.content.strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            return json.loads(raw)
        except Exception as e:
            if i < retry - 1:
                time.sleep(3)
                continue
            raise e

def format_money(amount):
    if amount >= 1000000:
        return f"{amount/1000000:.1f}tr"
    return f"{int(amount/1000)}k"

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Chào! Mình là bot quản lý chi tiêu.\n\n"
        "Nhắn tin tự nhiên để ghi chi tiêu:\n"
        "  • _ăn sáng 35k_\n"
        "  • _đổ xăng 100 nghìn_\n"
        "  • _mua áo 250k_\n\n"
        "Lệnh:\n"
        "  /today — chi tiêu hôm nay\n"
        "  /week — 7 ngày qua\n"
        "  /month — tháng này\n"
        "  /recent — 5 khoản gần nhất\n"
        "  /undo — xóa khoản vừa thêm",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.chat.send_action("typing")

    try:
        data = parse_expense(text)
        if not data.get("amount"):
            await update.message.reply_text(
                "Mình không nhận ra khoản chi tiêu. Thử lại nhé!\nVí dụ: _ăn trưa 50k_",
                parse_mode="Markdown"
            )
            return

        add_expense(data["amount"], data["category"], data["description"])
        await update.message.reply_text(
            f"✅ Đã ghi: *{data['description']}* — {format_money(data['amount'])}\n"
            f"📂 Danh mục: {data['category']}",
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"LỖI: {e}")
        await update.message.reply_text("Có lỗi xảy ra, thử lại nhé!")

async def summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE, period: str):
    rows = get_summary(period)
    label = {"today": "hôm nay", "week": "7 ngày qua", "month": "tháng này"}[period]

    if not rows:
        await update.message.reply_text(f"Chưa có chi tiêu nào {label}.")
        return

    total = sum(r["total"] for r in rows)
    lines = [f"📊 *Chi tiêu {label}*\n"]
    for r in rows:
        pct = r["total"] / total * 100
        lines.append(f"  {r['category']}: {format_money(r['total'])} ({pct:.0f}%)")
    lines.append(f"\n💰 *Tổng: {format_money(total)}*")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_today(u, c): await summary(u, c, "today")
async def cmd_week(u, c):  await summary(u, c, "week")
async def cmd_month(u, c): await summary(u, c, "month")

async def cmd_recent(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = get_recent()
    if not rows:
        await update.message.reply_text("Chưa có giao dịch nào.")
        return
    lines = ["🕐 *5 khoản gần nhất:*\n"]
    for r in rows:
        lines.append(f"  {r['date']} — {r['description']} ({r['category']}): {format_money(r['amount'])}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

async def cmd_undo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if delete_last():
        await update.message.reply_text("🗑 Đã xóa khoản chi tiêu vừa thêm.")
    else:
        await update.message.reply_text("Không có gì để xóa.")

if __name__ == "__main__":
    init_db()
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("month", cmd_month))
    app.add_handler(CommandHandler("recent", cmd_recent))
    app.add_handler(CommandHandler("undo", cmd_undo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot đang chạy...")
    app.run_polling()