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
from bot.keyboards import (
    main_keyboard,
    sources_keyboard,
    scan_keyboard,
    page_keyboard,
)


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
# DATABASE / MANAGERS
# ============================================================

db = Database(DB_PATH)

collector = CollectorManager(db)

verifier = VerifierManager(db)


# ============================================================
# HELPERS
# ============================================================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def denied_text() -> str:
    return (
        "⛔ <b>غير مصرح</b>\n\n"
        "ليس لديك صلاحية استخدام هذا البوت."
    )


def sources_from_env():
    """
    قراءة PROXY_SOURCE_URLS مباشرة من Railway.
    كل رابط في سطر مستقل.
    """

    raw = os.getenv(
        "PROXY_SOURCE_URLS",
        ""
    )

    sources = []

    for line in raw.splitlines():

        url = line.strip()

        if not url:
            continue

        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            continue

        if url not in sources:
            sources.append(url)

    return sources


def reload_sources():
    """
    تحديث جدول المصادر من متغير Railway.
    """

    sources = sources_from_env()

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

    if not is_admin(
        message.from_user.id
    ):
        await message.answer(
            denied_text()
        )
        return

    reload_sources()

    await message.answer(
        "🚀 <b>PROXPMOY V3</b>\n\n"
        "نظام جمع وإدارة وفحص البروكسيات العامة.\n\n"
        "اختر العملية:",
        reply_markup=main_keyboard()
    )


# ============================================================
# MAIN MENU
# ============================================================

@dp.callback_query(F.data == "menu")
async def menu(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    reload_sources()

    await callback.message.edit_text(
        "🚀 <b>PROXPMOY V3</b>\n\n"
        "اختر العملية:",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# COLLECT
# ============================================================

@dp.callback_query(F.data == "collect")
async def collect(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    # مهم:
    # إعادة قراءة PROXY_SOURCE_URLS من Railway
    sources = reload_sources()

    if not sources:

        await callback.message.edit_text(
            "⚠️ <b>لا توجد مصادر</b>\n\n"
            "متغير <code>PROXY_SOURCE_URLS</code> "
            "فارغ أو لم يتم تحميله.",
            reply_markup=main_keyboard()
        )

        await callback.answer()
        return

    await callback.message.edit_text(
        "🔎 <b>جاري جمع البروكسيات...</b>\n\n"
        f"🌐 عدد المصادر: <code>{len(sources)}</code>\n\n"
        "يرجى الانتظار...",
        reply_markup=sources_keyboard()
    )

    try:

        result = await collector.collect()

        await callback.message.edit_text(
            "✅ <b>انتهى الجمع</b>\n\n"
            f"🌐 المصادر: <code>{len(sources)}</code>\n"
            f"📥 المكتشف: <code>{result.discovered}</code>\n"
            f"🆕 الجديد: <code>{result.new}</code>\n"
            f"♻️ المكرر: <code>{result.duplicates}</code>\n"
            f"❌ المصادر الفاشلة: <code>{result.failed_sources}</code>",
            reply_markup=main_keyboard()
        )

    except Exception as error:

        await callback.message.edit_text(
            "❌ <b>حدث خطأ أثناء الجمع</b>\n\n"
            f"<code>{str(error)[:1000]}</code>",
            reply_markup=main_keyboard()
        )

    await callback.answer()


# ============================================================
# SOURCES
# ============================================================

@dp.callback_query(F.data == "sources")
async def sources(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    # قراءة Railway مباشرة
    source_list = reload_sources()

    if not source_list:

        text = (
            "🌐 <b>مصادر البروكسيات</b>\n\n"
            "❌ لا توجد مصادر حاليًا.\n\n"
            "تأكد من أن متغير:\n"
            "<code>PROXY_SOURCE_URLS</code>\n"
            "موجود في Railway."
        )

    else:

        text = (
            "🌐 <b>مصادر البروكسيات</b>\n\n"
            f"📊 العدد: <code>{len(source_list)}</code>\n\n"
        )

        for index, url in enumerate(
            source_list,
            start=1
        ):

            # Telegram لديه حد لطول الرسالة،
            # لذلك نعرض الرابط كاملًا لكن نحمي الرسالة.
            text += (
                f"<b>{index}.</b> "
                f"<code>{url}</code>\n\n"
            )

            if len(text) > 3800:

                text += (
                    "\n... والمزيد من المصادر موجودة."
                )

                break

    await callback.message.edit_text(
        text,
        reply_markup=sources_keyboard()
    )

    await callback.answer()


# ============================================================
# SCAN MENU
# ============================================================

@dp.callback_query(F.data == "scan")
async def scan(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    total = db.count()

    await callback.message.edit_text(
        "⚡ <b>فحص البروكسيات</b>\n\n"
        f"📦 الموجود في قاعدة البيانات: "
        f"<code>{total}</code>\n\n"
        "اختر نوع الفحص:",
        reply_markup=scan_keyboard()
    )

    await callback.answer()


# ============================================================
# SCAN ALL
# ============================================================

@dp.callback_query(F.data == "scan_all")
async def scan_all(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    total = db.count()

    if total == 0:

        await callback.message.edit_text(
            "⚠️ <b>لا توجد بروكسيات للفحص</b>\n\n"
            "اضغط «🔎 جمع البروكسيات» أولًا.",
            reply_markup=main_keyboard()
        )

        await callback.answer()
        return

    await callback.message.edit_text(
        "⚡ <b>بدأ الفحص</b>\n\n"
        f"📦 العدد: <code>{total}</code>\n\n"
        "جاري الفحص..."
    )

    try:

        result = await verifier.scan_all()

        await callback.message.edit_text(
            "✅ <b>انتهى الفحص</b>\n\n"
            f"📦 الإجمالي: <code>{result.total}</code>\n"
            f"🟢 متاح TCP: <code>{result.alive}</code>\n"
            f"🔴 غير متاح: <code>{result.dead}</code>\n"
            f"⏱ متوسط الاستجابة: "
            f"<code>{result.avg_latency:.0f} ms</code>",
            reply_markup=main_keyboard()
        )

    except Exception as error:

        await callback.message.edit_text(
            "❌ <b>حدث خطأ أثناء الفحص</b>\n\n"
            f"<code>{str(error)[:1000]}</code>",
            reply_markup=main_keyboard()
        )

    await callback.answer()


# ============================================================
# LIST
# ============================================================

@dp.callback_query(F.data == "list")
async def list_proxies(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    await show_page(
        callback,
        0
    )


# ============================================================
# PAGINATION
# ============================================================

@dp.callback_query(F.data.startswith("page:"))
async def page(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    try:

        page_number = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError
    ):

        await callback.answer(
            "صفحة غير صالحة",
            show_alert=True
        )

        return

    await show_page(
        callback,
        page_number
    )

    await callback.answer()


async def show_page(
    callback: CallbackQuery,
    page_number: int
):

    per_page = 15

    total = db.count()

    rows = db.page(
        page_number * per_page,
        per_page
    )

    if not rows:

        text = (
            "📋 <b>البروكسيات</b>\n\n"
            "لا توجد نتائج."
        )

    else:

        text = (
            "📋 <b>البروكسيات</b>\n\n"
            f"📄 الصفحة: "
            f"<code>{page_number + 1}</code>\n\n"
        )

        for row in rows:

            status = (
                "🟢"
                if row["alive"]
                else "⚪"
            )

            protocol = (
                row["protocol"]
                or "unknown"
            )

            latency = row["latency"] or 0

            text += (
                f"{status} "
                f"<code>{row['proxy']}</code>\n"
                f"   ⚡ {latency} ms"
                f"  |  {protocol}\n\n"
            )

        pages = max(
            1,
            (total + per_page - 1)
            // per_page
        )

        text += (
            f"📄 صفحة "
            f"<code>{page_number + 1}"
            f"/{pages}</code>"
        )

    await callback.message.edit_text(
        text,
        reply_markup=page_keyboard(
            page_number,
            total,
            per_page
        )
    )


# ============================================================
# STATS
# ============================================================

@dp.callback_query(F.data == "stats")
async def stats(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    statistics = db.stats()

    await callback.message.edit_text(
        "📊 <b>إحصائيات PROXPMOY</b>\n\n"
        f"📦 الإجمالي: "
        f"<code>{statistics['total']}</code>\n"
        f"🟢 TCP متاح: "
        f"<code>{statistics['alive']}</code>\n"
        f"🔴 غير متاح: "
        f"<code>{statistics['dead']}</code>\n"
        f"🎯 34.*: "
        f"<code>{statistics['filtered']}</code>\n"
        f"🌐 المصادر: "
        f"<code>{len(sources_from_env())}</code>\n"
        f"🕒 آخر تحديث: "
        f"<code>{statistics['last_update'] or '—'}</code>",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# EXPORT
# ============================================================

@dp.callback_query(F.data == "export")
async def export(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    total = db.count()

    if total == 0:

        await callback.answer(
            "لا توجد نتائج للتصدير",
            show_alert=True
        )

        return

    try:

        path = db.export_txt(
            "/tmp/proxpmoy.txt"
        )

        await callback.message.answer_document(
            FSInputFile(path),
            caption=(
                "📤 <b>PROXPMOY Export</b>\n\n"
                f"📦 العدد: <code>{total}</code>"
            )
        )

        await callback.answer(
            "تم التصدير"
        )

    except Exception as error:

        await callback.answer(
            f"خطأ: {str(error)[:150]}",
            show_alert=True
        )


# ============================================================
# CLEAR
# ============================================================

@dp.callback_query(F.data == "clear")
async def clear(callback: CallbackQuery):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    db.clear()

    await callback.message.edit_text(
        "🗑️ <b>تم تنظيف قاعدة البيانات.</b>\n\n"
        "يمكنك البدء بجمع جديد.",
        reply_markup=main_keyboard()
    )

    await callback.answer()


# ============================================================
# UNKNOWN CALLBACK
# ============================================================

@dp.callback_query()
async def unknown_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        await callback.answer(
            "غير مصرح",
            show_alert=True
        )
        return

    await callback.answer(
        "هذا الزر غير متاح حاليًا."
    )


# ============================================================
# MAIN
# ============================================================

async def main():

    os.makedirs(
        "data",
        exist_ok=True
    )

    # إنشاء الجداول
    db.init()

    # تحميل المصادر من Railway
    sources = reload_sources()

    print(
        f"[PROXPMOY] Loaded "
        f"{len(sources)} proxy sources."
    )

    for index, source in enumerate(
        sources,
        start=1
    ):
        print(
            f"[SOURCE {index}] {source}"
        )

    print(
        "[PROXPMOY] Bot starting..."
    )

    await dp.start_polling(
        bot
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print(
            "[PROXPMOY] Stopped."
        )
