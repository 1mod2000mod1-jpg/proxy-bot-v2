from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔎 جمع البروكسيات",
                    callback_data="collect"
                ),
                InlineKeyboardButton(
                    text="⚡ الفحص",
                    callback_data="scan"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 النتائج",
                    callback_data="list"
                ),
                InlineKeyboardButton(
                    text="📊 الإحصائيات",
                    callback_data="stats"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🌐 المصادر",
                    callback_data="sources"
                ),
                InlineKeyboardButton(
                    text="📤 تصدير",
                    callback_data="export"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ تنظيف",
                    callback_data="clear"
                )
            ]
        ]
    )


def sources_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 جمع الآن",
                    callback_data="collect"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ الرئيسية",
                    callback_data="menu"
                )
            ]
        ]
    )


def scan_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚡ فحص الكل",
                    callback_data="scan_all"
                )
            ],
            [
                InlineKeyboardButton(
                    text="◀️ الرئيسية",
                    callback_data="menu"
                )
            ]
        ]
    )


def page_keyboard(page, total, per_page):
    pages = max(
        1,
        (total + per_page - 1) // per_page
    )

    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="⬅️ السابق",
                callback_data=f"page:{page - 1}"
            )
        )

    if page + 1 < pages:
        buttons.append(
            InlineKeyboardButton(
                text="التالي ➡️",
                callback_data=f"page:{page + 1}"
            )
        )

    rows = []

    if buttons:
        rows.append(buttons)

    rows.append([
        InlineKeyboardButton(
            text="◀️ الرئيسية",
            callback_data="menu"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )
