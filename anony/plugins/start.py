# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import asyncio
from xxlimited import new
from pyrogram import enums, filters, types

from anony import app, config, db, lang
from anony.helpers import buttons, utils


@app.on_message(filters.command(["help"]) & filters.private & ~app.bl_users)
@lang.language()
async def _help(_, m: types.Message):
    await m.reply_text(
        text=m.lang["help_menu"],
        reply_markup=buttons.help_markup(m.lang),
        quote=True,
    )


@app.on_message(filters.command(["start"]))
@lang.language()
async def start(_, message: types.Message):
    if message.from_user.id in app.bl_users and message.from_user.id not in db.notified:
        return await message.reply_text(message.lang["bl_user_notify"])

    if len(message.command) > 1 and message.command[1] == "help":
        return await _help(_, message)

    private = message.chat.type == enums.ChatType.PRIVATE
    _text = (
        message.lang["start_pm"].format(message.from_user.first_name, app.name)
        if private
        else message.lang["start_gp"].format(app.name)
    )

    key = buttons.start_key(message.lang, private)
    await message.reply_photo(
        photo=config.START_IMG,
        caption=_text,
        reply_markup=key,
        quote=not private,
    )

    if private:
        if await db.is_active_user(message.from_user.id):
            return
        await utils.send_log(message)
        await db.register_active_user(message.from_user.id)
    else:
        if await db.is_chat_active(message.chat.id):
            return
        await utils.send_log(message, True)
        await db.register_active_chat(message.chat.id)


@app.on_message(
    filters.command(["playmode", "settings"]) & filters.group & ~app.bl_users
)
@lang.language()
async def settings(_, message: types.Message):
    admin_only = await db.get_play_mode(message.chat.id)
    cmd_delete = await db.get_cmd_delete(message.chat.id)
    _language = await db.get_lang(message.chat.id)
    await message.reply_text(
        text=message.lang["start_settings"].format(message.chat.title),
        reply_markup=buttons.settings_markup(
            message.lang, admin_only, cmd_delete, _language, message.chat.id
        ),
        quote=True,
    )


@app.on_chat_member_updated(group=7)
@lang.language()
async def _bot_membership_update(_, update: types.ChatMemberUpdated) -> None:
    new = update.new_chat_member

    # Only care about updates to the bot's own membership, not other users'
    if new is None or new.user.id != app.id:
        return

    if update.chat.type != enums.ChatType.SUPERGROUP:
        return await update.chat.leave()

    is_new_active = not (await db.is_chat_active(update.chat.id))

    if new.status in (enums.ChatMemberStatus.LEFT, enums.ChatMemberStatus.BANNED):
        if not is_new_active:
            await db.unregister_chat(update.chat.id)
        return

    if is_new_active:
        await utils.send_log(update, True)
        await db.register_active_chat(update.chat.id)
        await app.send_message(
            update.chat.id,
            update.lang["welcome_msg"],
            reply_markup=buttons.start_key(update.lang, False),
        )

    is_admin = new.status == enums.ChatMemberStatus.ADMINISTRATOR
    perms = new.privileges

    required_perms = [
        "can_manage_voice_chats",
        "can_invite_users",
    ]

    missing_perms = []
    for perm in required_perms:
        if not is_admin or not getattr(perms, perm):
            missing_perms.append(update.lang[f"perm_{perm}"])

    if missing_perms:
        text = "\n".join(f"• {perm}" for perm in missing_perms)
        await app.send_photo(
            update.chat.id,
            "anony/assets/permissions.png",
            caption=update.lang["missing_perms_warning"].format(text),
        )
