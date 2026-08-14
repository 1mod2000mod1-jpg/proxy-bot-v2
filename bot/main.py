import asyncio
import os

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message, FSInputFile

from database.db import Database
from collector.manager import CollectorManager
from verifier.manager import VerifierManager
from bot.keyboards import main_keyboard, sources_keyboard, scan_keyboard, page_keyboard


BOT_TOKEN = os.environ["BOT_TOKEN"]

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
}

DB_PATH = os.getenv("DATABASE_PATH", "data/proxies.db")

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()

db = Database(DB_PATH)
collector = CollectorManager(db)
verifier = VerifierManager(db)


def admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def denied() -> str:
    return "⛔ غير مصرح لك باستخدام هذا البوت."


@dp.message(CommandStart())
async def start(message: Message):
    if not admin(message.from_user.id):
        await message.answer(denied())
        return

    await message.answer(
        "🚀 <b>PROXPMOY V3</b>\n\n"
        "نظام إدارة وتجميع وفحص البروكسيات العامة.\n\n"
        "اختر العملية:",
        reply_markup=main_keyboard()
    )


@dp.callback_query(F.data == "menu")
async def menu(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    await callback.message.edit_text(
        "🚀 <b>PROXPMOY V3</b>\n\nاختر العملية:",
        reply_markup=main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "collect")
async def collect(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    await callback.message.edit_text(
        "🔎 <b>جاري جمع المصادر...</b>\n\n"
        "يتم تحليل القوائم العامة المهيأة وإزالة التكرارات.",
        reply_markup=sources_keyboard()
    )

    result = await collector.collect()

    await callback.message.edit_text(
        "🔎 <b>انتهى الجمع</b>\n\n"
        f"📥 المكتشف: <code>{result.discovered}</code>\n"
        f"🆕 جديد: <code>{result.new}</code>\n"
        f"♻️ مكرر: <code>{result.duplicates}</code>\n"
        f"❌ مصادر فاشلة: <code>{result.failed_sources}</code>",
        reply_markup=main_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "sources")
async def sources(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    sources = db.sources()

    if not sources:
        text = (
            "🌐 <b>المصادر</b>\n\n"
            "لا توجد مصادر مهيأة.\n"
            "أضفها من متغير <code>PROXY_SOURCE_URLS</code> في Railway."
        )
    else:
        text = "🌐 <b>المصادر المهيأة</b>\n\n"

        for i, source in enumerate(sources, 1):
            text += f"{i}. <code>{source}</code>\n"

    await callback.message.edit_text(
        text,
        reply_markup=sources_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "scan")
async def scan(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    total = db.count()

    await callback.message.edit_text(
        "⚡ <b>فحص البروكسيات</b>\n\n"
        f"الموجود في قاعدة البيانات: <code>{total}</code>\n\n"
        "اختر نوع الفحص:",
        reply_markup=scan_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "scan_all")
async def scan_all(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    await callback.message.edit_text(
        "⚡ <b>بدأ الفحص</b>\n\n"
        "يتم اختبار الاتصال والبروتوكول الأولي فقط."
    )

    result = await verifier.scan_all()

    await callback.message.edit_text(
        "⚡ <b>انتهى الفحص</b>\n\n"
        f"📦 الإجمالي: <code>{result.total}</code>\n"
        f"🟢 متاح TCP: <code>{result.alive}</code>\n"
        f"🔴 غير متاح: <code>{result.dead}</code>\n"
        f"⏱ متوسط زمن الاستجابة: <code>{result.avg_latency:.0f} ms</code>",
        reply_markup=main_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "list")
async def list_proxies(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    await show_page(callback, 0)


@dp.callback_query(F.data.startswith("page:"))
async def page(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    number = int(callback.data.split(":")[1])
    await show_page(callback, number)
    await callback.answer()


async def show_page(callback: CallbackQuery, page_number: int):
    per_page = 15

    rows = db.page(
        page_number * per_page,
        per_page
    )

    total = db.count()

    if not rows:
        text = "📋 <b>البروكسيات</b>\n\nلا توجد نتائج."
    else:
        text = (
            "📋 <b>البروكسيات</b>\n\n"
            f"الصفحة: <code>{page_number + 1}</code>\n\n"
        )

        for row in rows:
            status = "🟢" if row["alive"] else "⚪"
            text += (
                f"{status} <code>{row['proxy']}</code>\n"
                f"   {row['latency']} ms | "
                f"{row['protocol'] or 'unknown'}\n\n"
            )

        pages = max(1, (total + per_page - 1) // per_page)

        text += f"صفحة <code>{page_number + 1}/{pages}</code>"

    await callback.message.edit_text(
        text,
        reply_markup=page_keyboard(
            page_number,
            total,
            per_page
        )
    )


@dp.callback_query(F.data == "stats")
async def stats(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    s = db.stats()

    await callback.message.edit_text(
        "📊 <b>الإحصائيات</b>\n\n"
        f"📦 الإجمالي: <code>{s['total']}</code>\n"
        f"🟢 متاحة TCP: <code>{s['alive']}</code>\n"
        f"🔴 غير متاحة: <code>{s['dead']}</code>\n"
        f"🎯 34.*: <code>{s['filtered']}</code>\n"
        f"🕒 آخر تحديث: <code>{s['last_update'] or '—'}</code>",
        reply_markup=main_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "export")
async def export(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    path = db.export_txt("/tmp/proxpmoy.txt")

    await callback.message.answer_document(
        FSInputFile(path),
        caption="📤 <b>PROXPMOY Export</b>"
    )

    await callback.answer()


@dp.callback_query(F.data == "clear")
async def clear(callback: CallbackQuery):
    if not admin(callback.from_user.id):
        await callback.answer("غير مصرح", show_alert=True)
        return

    db.clear()

    await callback.message.edit_text(
        "🗑️ تم تنظيف قاعدة البيانات.",
        reply_markup=main_keyboard()
    )

    await callback.answer()


async def main():
    os.makedirs("data", exist_ok=True)

    db.init()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
