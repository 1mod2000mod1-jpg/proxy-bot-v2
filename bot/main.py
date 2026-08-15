import asyncio
import os
import time

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message, FSInputFile

from bot.keyboards import (
    main_keyboard,
    sources_keyboard,
    scan_keyboard,
    page_keyboard,
)

from collector.manager import CollectorManager
from database.db import Database
from verifier.manager import VerifierManager


# ============================================================
# CONFIG
# ============================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]

ADMIN_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip()
}

DB_PATH = os.getenv(
    "DATABASE_PATH",
    "data/proxies.db"
)


# ============================================================
# BOT
# ============================================================

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


# ============================================================
# DATABASE
# ============================================================

db = Database(DB_PATH)

collector = CollectorManager(db)

verifier = VerifierManager(db)


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def denied():
    return (
        "⛔ <b>غير مصرح</b>\n\n"
        "ليس لديك صلاحية استخدام هذا البوت."
    )


def get_sources_from_env():

    raw = os.getenv(
        "PROXY_SOURCE_URLS",
        ""
    )

    result = []

    for line in raw.splitlines():

        url = line.strip()

        if not url:
            continue

        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            continue

        if url not in result:
            result.append(url)

    return result


def reload_sources():

    sources = get_sources_from_env()

    with db.connection() as conn:

        conn.execute(
            "DELETE FROM sources"
        )

        conn.executemany(
            """
            INSERT OR IGNORE INTO sources(url)
            VALUES(?)
            """,
            [
                (url,)
                for url in sources
            ]
        )

    return sources


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message):

    if not is_admin(message.from_user.id):
        await message.answer(denied())
        return

    reload_sources()

    await message.answer(
        "🚀 <b>PROXPMOY V4</b>\n\n"
        "نظام جمع وفحص وإدارة البروكسيات.\n\n"
        "اختر من الأزرار:",
        reply_markup=main_keyboard()
    )


# ============================================================
# MENU
# ============================================================

@dp.callback_query(F.data == "menu")
async def menu(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    reload_sources()

    await callback.message.edit_text(
        "🚀 <b>PROXPMOY V4</b>\n\n"
        "اختر من الأزرار:",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# SOURCES
# ============================================================

@dp.callback_query(F.data == "sources")
async def show_sources(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    sources = reload_sources()

    if not sources:

        text = (
            "🌐 <b>المصادر</b>\n\n"
            "❌ لا توجد مصادر."
        )

    else:

        text = (
            "🌐 <b>المصادر</b>\n\n"
            f"📊 العدد: <code>{len(sources)}</code>\n\n"
        )

        for index, source in enumerate(
            sources,
            1
        ):

            line = (
                f"<b>{index}</b>. "
                f"<code>{source}</code>\n"
            )

            if len(text) + len(line) > 3900:
                text += "\n... والمزيد موجود في Railway."
                break

            text += line

    await callback.message.edit_text(
        text,
        reply_markup=sources_keyboard()
    )

    await callback.answer()


# ============================================================
# COLLECT
# ============================================================

@dp.callback_query(F.data == "collect")
async def collect(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    # نرد فورًا على callback حتى لا يصبح قديمًا
    await callback.answer(
        "🔎 بدأ الجمع..."
    )

    sources = reload_sources()

    if not sources:

        await callback.message.edit_text(
            "⚠️ <b>لا توجد مصادر</b>\n\n"
            "أضف PROXY_SOURCE_URLS في Railway.",
            reply_markup=main_keyboard()
        )

        return

    await callback.message.edit_text(
        "🔎 <b>جاري الجمع...</b>\n\n"
        f"🌐 المصادر: <code>{len(sources)}</code>\n\n"
        "يرجى الانتظار.",
        reply_markup=sources_keyboard()
    )

    started = time.perf_counter()

    try:

        result = await collector.collect()

        elapsed = (
            time.perf_counter()
            - started
        )

        await callback.message.edit_text(
            "✅ <b>انتهى الجمع</b>\n\n"
            f"🌐 المصادر: <code>{len(sources)}</code>\n"
            f"📥 المكتشف: <code>{result.discovered}</code>\n"
            f"🆕 الجديد: <code>{result.new}</code>\n"
            f"♻️ المكرر: <code>{result.duplicates}</code>\n"
            f"❌ الفاشل: <code>{result.failed_sources}</code>\n"
            f"⏱ الزمن: <code>{elapsed:.1f}s</code>",
            reply_markup=main_keyboard()
        )

    except Exception as exc:

        await callback.message.edit_text(
            "❌ <b>فشل الجمع</b>\n\n"
            f"<code>{str(exc)[:1500]}</code>",
            reply_markup=main_keyboard()
        )


# ============================================================
# SCAN MENU
# ============================================================

@dp.callback_query(F.data == "scan")
async def scan_menu(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    total = db.count()

    await callback.answer()

    await callback.message.edit_text(
        "⚡ <b>فحص البروكسيات</b>\n\n"
        f"📦 الإجمالي: <code>{total}</code>\n\n"
        "اختر نوع الفحص:",
        reply_markup=scan_keyboard()
    )


# ============================================================
# SCAN ALL
# ============================================================

@dp.callback_query(F.data == "scan_all")
async def scan_all(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    # مهم جدًا:
    # الرد على callback قبل بدء العملية الطويلة
    await callback.answer(
        "⚡ بدأ الفحص..."
    )

    total = db.count()

    if total == 0:

        await callback.message.edit_text(
            "⚠️ <b>لا توجد بروكسيات</b>\n\n"
            "اضغط «🔎 جمع البروكسيات» أولًا.",
            reply_markup=main_keyboard()
        )

        return

    if verifier.running:

        await callback.message.edit_text(
            "⏳ <b>يوجد فحص جارٍ بالفعل.</b>\n\n"
            "انتظر حتى ينتهي الفحص الحالي.",
            reply_markup=main_keyboard()
        )

        return

    await callback.message.edit_text(
        "⚡ <b>الفحص بدأ</b>\n\n"
        f"📦 العدد: <code>{total}</code>\n"
        "🔎 HTTP / HTTPS / SOCKS4 / SOCKS5\n\n"
        "جاري الفحص...",
        reply_markup=main_keyboard()
    )

    try:

        result = await verifier.scan_all()

        await callback.message.edit_text(
            "✅ <b>اكتمل الفحص</b>\n\n"
            f"📦 الإجمالي: <code>{result.total}</code>\n"
            f"🟢 صالح: <code>{result.alive}</code>\n"
            f"🔴 فاشل: <code>{result.dead}</code>\n"
            f"⚡ HTTP/HTTPS: <code>{result.http_alive}</code>\n"
            f"🧦 SOCKS4: <code>{result.socks4_alive}</code>\n"
            f"🧦 SOCKS5: <code>{result.socks5_alive}</code>\n"
            f"⏱ المتوسط: <code>{result.avg_latency:.0f} ms</code>",
            reply_markup=main_keyboard()
        )

    except Exception as exc:

        verifier.running = False

        await callback.message.edit_text(
            "❌ <b>حدث خطأ أثناء الفحص</b>\n\n"
            f"<code>{str(exc)[:1500]}</code>",
            reply_markup=main_keyboard()
        )


# ============================================================
# RESULTS
# ============================================================

@dp.callback_query(F.data == "list")
async def results(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    await callback.answer()

    await show_page(
        callback,
        0
    )


@dp.callback_query(F.data.startswith("page:"))
async def page(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    try:
        number = int(
            callback.data.split(":")[1]
        )
    except Exception:

        await callback.answer(
            "صفحة غير صالحة",
            show_alert=True
        )

        return

    await callback.answer()

    await show_page(
        callback,
        number
    )


async def show_page(
    callback: CallbackQuery,
    number: int
):

    per_page = 15

    total = db.count()

    rows = db.page(
        number * per_page,
        per_page
    )

    if not rows:

        text = (
            "📋 <b>النتائج</b>\n\n"
            "لا توجد نتائج."
        )

    else:

        text = (
            "📋 <b>النتائج</b>\n\n"
            f"📄 الصفحة: "
            f"<code>{number + 1}</code>\n\n"
        )

        for row in rows:

            if row["alive"]:
                status = "🟢"
            else:
                status = "🔴"

            protocol = (
                row["protocol"]
                or "unknown"
            )

            latency = (
                row["latency"]
                or 0
            )

            text += (
                f"{status} "
                f"<code>{row['proxy']}</code>\n"
                f"   🔌 {protocol}\n"
                f"   ⚡ {latency} ms\n\n"
            )

        pages = max(
            1,
            (total + per_page - 1)
            // per_page
        )

        text += (
            f"📄 "
            f"<code>{number + 1}/{pages}</code>"
        )

    await callback.message.edit_text(
        text,
        reply_markup=page_keyboard(
            number,
            total,
            per_page
        )
    )


# ============================================================
# STATS
# ============================================================

@dp.callback_query(F.data == "stats")
async def stats(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    await callback.answer()

    stats = db.stats()

    await callback.message.edit_text(
        "📊 <b>الإحصائيات</b>\n\n"
        f"📦 الإجمالي: <code>{stats['total']}</code>\n"
        f"🟢 صالح: <code>{stats['alive']}</code>\n"
        f"🔴 فاشل: <code>{stats['dead']}</code>\n"
        f"🎯 34.*: <code>{stats['filtered']}</code>\n"
        f"🌐 المصادر: <code>{len(get_sources_from_env())}</code>\n"
        f"🕒 آخر تحديث: "
        f"<code>{stats['last_update'] or '—'}</code>",
        reply_markup=main_keyboard()
    )


# ============================================================
# EXPORT
# ============================================================

@dp.callback_query(F.data == "export")
async def export(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    await callback.answer(
        "📤 تجهيز الملف..."
    )

    if db.count() == 0:

        await callback.message.answer(
            "⚠️ لا توجد نتائج للتصدير."
        )

        return

    try:

        path = db.export_txt(
            "/tmp/proxpmoy.txt"
        )

        await callback.message.answer_document(
            FSInputFile(path),
            caption="📤 نتائج PROXPMOY"
        )

    except Exception as exc:

        await callback.message.answer(
            "❌ فشل التصدير:\n\n"
            f"<code>{str(exc)[:1000]}</code>"
        )


# ============================================================
# CLEAR
# ============================================================

@dp.callback_query(F.data == "clear")
async def clear(callback: CallbackQuery):

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    await callback.answer(
        "🗑️ تم التنظيف"
    )

    db.clear()

    await callback.message.edit_text(
        "🗑️ <b>تم تنظيف قاعدة البيانات.</b>",
        reply_markup=main_keyboard()
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    os.makedirs(
        "data",
        exist_ok=True
    )

    db.init()

    sources = reload_sources()

    print(
        f"[PROXPMOY] Loaded "
        f"{len(sources)} proxy sources."
    )

    print(
        "[PROXPMOY] Bot starting..."
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":
    asyncio.run(main())
