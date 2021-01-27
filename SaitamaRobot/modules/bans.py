import html

from telegram import ParseMode, Update
from telegram.error import BadRequest
from telegram.ext import CallbackContext, CommandHandler, Filters, run_async
from telegram.utils.helpers import mention_html

from SaitamaRobot import (DEV_USERS, LOGGER, OWNER_ID, DRAGONS, DEMONS, TIGERS,
                          WOLVES, dispatcher)
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.chat_status import (
    bot_admin, can_restrict, connection_status, is_user_admin,
    is_user_ban_protected, is_user_in_chat, user_admin, user_can_ban)
from SaitamaRobot.modules.helper_funcs.extraction import extract_user_and_text
from SaitamaRobot.modules.helper_funcs.string_handling import extract_time
from SaitamaRobot.modules.log_channel import gloggable, loggable


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot = context.bot
    args = context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir istifadəçi olduğuna şübhə edirəm.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "İstifadəçi tapılmadı.":
            message.reply_text("Bu adamı tapmaq olmur.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Oh bəli, özümü qadağan et, noob!")
        return log_message

    if is_user_ban_protected(chat, user_id, member) and user not in DEV_USERS:
        if user_id == OWNER_ID:
            message.reply_text(
                "Məni Gorilla səviyyəsində bir fəlakətə qarşı qoymağa çalışıram ha?")
            return log_message
        elif user_id in DEV_USERS:
            message.reply_text("Özümüzün əleyhinə hərəkət edə bilmərəm.")
            return log_message
        elif user_id in DRAGONS:
            message.reply_text(
                "Bu Ejderha ilə döyüşmək mülki həyatını riskə atacaq.")
            return log_message
        elif user_id in DEMONS:
            message.reply_text(
                "Bir Şeytan fəlakəti ilə mübarizə aparmaq üçün Heroes dərnəyindən bir sifariş gətirin."
            )
            return log_message
        elif user_id in TIGERS:
            message.reply_text(
                "Pələng fəlakəti ilə mübarizə aparmaq üçün Heroes dərnəyindən bir əmr gətirin."
            )
            return log_message
        elif user_id in WOLVES:
            message.reply_text("Kurt qabiliyyətləri onları immunitetə ​​qadağa qoyur!")
            return log_message
        else:
            message.reply_text("Bu istifadəçinin toxunulmazlığı var və qadağan edilə bilməz.")
            return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#BANNED\n"
        f"<b>İdarəçi:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>İstifadəçi:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += "\n<b>Səbəb:</b> {}".format(reason)

    try:
        chat.kick_member(user_id)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        reply = (
            f"<code>❕</code><b>Tədbiri Qadağan Edin:</b>\n"
            f"<code> </code><b>• İstifadəçi:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
        )
        if reason:
            reply += f"\n<code> </code><b>•  Səbəb:</b> \n{html.escape(reason)}"
        bot.sendMessage(chat.id, reply, parse_mode=ParseMode.HTML, quote=False)
        return log

    except BadRequest as excp:
        if excp.message == "Cavab mesajı tapılmadı":
            # Do not reply
            message.reply_text('Qadağandır!', quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("istifadəçisini %s söhbətində %s (%s) qadağan edən XETA %s",
                             user_id, chat.title, chat.id, excp.message)
            message.reply_text("Uhm ... işə yaramadı ...")

    return log_message


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def temp_ban(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir istifadəçi olduğuna şübhə edirəm.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "İstifadəçi tapılmadı":
            message.reply_text("Görünür bu istifadəçini tapa bilmirəm.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Mən özümə Qadağa qoymayacağam, dəli olmusan?")
        return log_message

    if is_user_ban_protected(chat, user_id, member):
        message.reply_text("Mən bunu hiss etmirəm.")
        return log_message

    if not reason:
        message.reply_text("Bu istifadəçini qadağan edəcək bir vaxt təyin etməmisiniz!")
        return log_message

    split_reason = reason.split(None, 1)

    time_val = split_reason[0].lower()
    if len(split_reason) > 1:
        reason = split_reason[1]
    else:
        reason = ""

    bantime = extract_time(message, time_val)

    if not bantime:
        return log_message

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        "#TEMP BANNED\n"
        f"<b>İdarəçi:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>İstifadəçi:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}\n"
        f"<b>Vaxt:</b> {time_val}")
    if reason:
        log += "\n<b>Səbəb:</b> {}".format(reason)

    try:
        chat.kick_member(user_id, until_date=bantime)
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"Qadağandır! İstifadəçi {mention_html(member.user.id, html.escape(member.user.first_name))} "
            f"will be banned for {time_val}.",
            parse_mode=ParseMode.HTML)
        return log

    except BadRequest as excp:
        if excp.message == "Cavab mesajı tapılmadı":
            # Do not reply
            message.reply_text(
                f"Qadağandır! İstifadəçi {time_val}.", quote=False)
            return log
        else:
            LOGGER.warning(update)
            LOGGER.exception("istifadəçini %s söhbətində %s (%s) qadağan edən xeta %s",
                             user_id, chat.title, chat.id, excp.message)
            message.reply_text("Lənətə gəlsin, mən o istifadəçini qadağan edə bilmərəm.")

    return log_message


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def punch(update: Update, context: CallbackContext) -> str:
    chat = update.effective_chat
    user = update.effective_user
    message = update.effective_message
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir istifadəçi olduğuna şübhə edirəm.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "İstifadəçi tapılmadı":
            message.reply_text("Görünür bu istifadəçini tapa bilmirəm.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Bəli, mən bunu etməyəcəyəm.")
        return log_message

    if is_user_ban_protected(chat, user_id):
        message.reply_text("Kaş ki, bu istifadəçiyə yumruq verə bilərdim .....")
        return log_message

    res = chat.unban_member(user_id)  # unban on current user = kick
    if res:
        # bot.send_sticker(chat.id, BAN_STICKER)  # banhammer marie sticker
        bot.sendMessage(
            chat.id,
            f"Bir Yumruq! {mention_html(member.user.id, html.escape(member.user.first_name))}.",
            parse_mode=ParseMode.HTML)
        log = (
            f"<b>{html.escape(chat.title)}:</b>\n"
            f"#KICKED\n"
            f"<b>İdarəçi:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
            f"<b>İstifadəçi:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
        )
        if reason:
            log += f"\n<b>Səbəb:</b> {reason}"

        return log

    else:
        message.reply_text("Yaxşı lənət olsun, mən o istifadəçiyə yumruq ata bilmirəm.")

    return log_message


@run_async
@bot_admin
@can_restrict
def punchme(update: Update, context: CallbackContext):
    user_id = update.effective_message.from_user.id
    if is_user_admin(update.effective_chat, user_id):
        update.effective_message.reply_text(
            "Kaş ki, edə bilərdim ... amma sən adminsən.")
        return

    res = update.effective_chat.unban_member(
        user_id)  # unban on current user = kick
    if res:
        update.effective_message.reply_text("*sizi qrupdan çıxarır*")
    else:
        update.effective_message.reply_text("Yaxşı? Bilmirəm :/")


@run_async
@connection_status
@bot_admin
@can_restrict
@user_admin
@user_can_ban
@loggable
def unban(update: Update, context: CallbackContext) -> str:
    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    log_message = ""
    bot, args = context.bot, context.args
    user_id, reason = extract_user_and_text(message, args)

    if not user_id:
        message.reply_text("Bir istifadəçi olduğuna şübhə edirəm.")
        return log_message

    try:
        member = chat.get_member(user_id)
    except BadRequest as excp:
        if excp.message == "User not found":
            message.reply_text("Görünür bu istifadəçini tapa bilmirəm.")
            return log_message
        else:
            raise

    if user_id == bot.id:
        message.reply_text("Burda olmasaydım özümü necə açardım ...?")
        return log_message

    if is_user_in_chat(chat, user_id):
        message.reply_text("Bu adam artıq buradadır?")
        return log_message

    chat.unban_member(user_id)
    message.reply_text("Yess, bu istifadəçi qoşula bilər!")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>İdarəçi:</b> {mention_html(user.id, html.escape(user.first_name))}\n"
        f"<b>İstifadəçi:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )
    if reason:
        log += f"\n<b>Səbəb:</b> {reason}"

    return log


@run_async
@connection_status
@bot_admin
@can_restrict
@gloggable
def selfunban(context: CallbackContext, update: Update) -> str:
    message = update.effective_message
    user = update.effective_user
    bot, args = context.bot, context.args
    if user.id not in DRAGONS or user.id not in TIGERS:
        return

    try:
        chat_id = int(args[0])
    except:
        message.reply_text("Etibarlı bir chat kimliyi verin.")
        return

    chat = bot.getChat(chat_id)

    try:
        member = chat.get_member(user.id)
    except BadRequest as excp:
        if excp.message == "İstifadəçi tapılmadı":
            message.reply_text("Görünür bu istifadəçini tapa bilmirəm.")
            return
        else:
            raise

    if is_user_in_chat(chat, user.id):
        message.reply_text("Onsuz da söhbətdə deyilsiniz?")
        return

    chat.unban_member(user.id)
    message.reply_text("Yeea, sənin qadağanlıqıvı leğv etdim.")

    log = (
        f"<b>{html.escape(chat.title)}:</b>\n"
        f"#UNBANNED\n"
        f"<b>İstifadəçi:</b> {mention_html(member.user.id, html.escape(member.user.first_name))}"
    )

    return log


__help__ = """
 • `/punchme`*:* punchs the user who issued the command

*Admins only:*
 • `/ban <userhandle>`*:* bans a user. (via handle, or reply)
 • `/tban <userhandle> x(m/h/d)`*:* bans a user for `x` time. (via handle, or reply). `m` = `minutes`, `h` = `hours`, `d` = `days`.
 • `/unban <userhandle>`*:* unbans a user. (via handle, or reply)
 • `/punch <userhandle>`*:* Punches a user out of the group, (via handle, or reply)
"""

BAN_HANDLER = CommandHandler("ban", ban)
TEMPBAN_HANDLER = CommandHandler(["tban"], temp_ban)
PUNCH_HANDLER = CommandHandler("punch", punch)
UNBAN_HANDLER = CommandHandler("unban", unban)
ROAR_HANDLER = CommandHandler("roar", selfunban)
PUNCHME_HANDLER = DisableAbleCommandHandler(
    "punchme", punchme, filters=Filters.group)

dispatcher.add_handler(BAN_HANDLER)
dispatcher.add_handler(TEMPBAN_HANDLER)
dispatcher.add_handler(PUNCH_HANDLER)
dispatcher.add_handler(UNBAN_HANDLER)
dispatcher.add_handler(ROAR_HANDLER)
dispatcher.add_handler(PUNCHME_HANDLER)

__mod_name__ = "Bans"
__handlers__ = [
    BAN_HANDLER, TEMPBAN_HANDLER, PUNCH_HANDLER, UNBAN_HANDLER, ROAR_HANDLER,
    PUNCHME_HANDLER
]
