import re, ast
from io import BytesIO
import random
from typing import Optional

import SaitamaRobot.modules.sql.notes_sql as sql
from SaitamaRobot import LOGGER, JOIN_LOGGER, SUPPORT_CHAT, dispatcher, DRAGONS
from SaitamaRobot.modules.disable import DisableAbleCommandHandler
from SaitamaRobot.modules.helper_funcs.handlers import MessageHandlerChecker
from SaitamaRobot.modules.helper_funcs.chat_status import user_admin, connection_status
from SaitamaRobot.modules.helper_funcs.misc import (build_keyboard,
                                                    revert_buttons)
from SaitamaRobot.modules.helper_funcs.msg_types import get_note_type
from SaitamaRobot.modules.helper_funcs.string_handling import escape_invalid_curly_brackets
from telegram import (MAX_MESSAGE_LENGTH, InlineKeyboardMarkup, Message,
                      ParseMode, Update, InlineKeyboardButton)
from telegram.error import BadRequest
from telegram.utils.helpers import escape_markdown, mention_markdown
from telegram.ext import (CallbackContext, CommandHandler, CallbackQueryHandler,
                          Filters, MessageHandler)
from telegram.ext.dispatcher import run_async

FILE_MATCHER = re.compile(r"^###file_id(!photo)?###:(.*?)(?:\s|$)")
STICKER_MATCHER = re.compile(r"^###sticker(!photo)?###:")
BUTTON_MATCHER = re.compile(r"^###button(!photo)?###:(.*?)(?:\s|$)")
MYFILE_MATCHER = re.compile(r"^###file(!photo)?###:")
MYPHOTO_MATCHER = re.compile(r"^###photo(!photo)?###:")
MYAUDIO_MATCHER = re.compile(r"^###audio(!photo)?###:")
MYVOICE_MATCHER = re.compile(r"^###voice(!photo)?###:")
MYVIDEO_MATCHER = re.compile(r"^###video(!photo)?###:")
MYVIDEONOTE_MATCHER = re.compile(r"^###video_note(!photo)?###:")

ENUM_FUNC_MAP = {
    sql.Types.TEXT.value: dispatcher.bot.send_message,
    sql.Types.BUTTON_TEXT.value: dispatcher.bot.send_message,
    sql.Types.STICKER.value: dispatcher.bot.send_sticker,
    sql.Types.DOCUMENT.value: dispatcher.bot.send_document,
    sql.Types.PHOTO.value: dispatcher.bot.send_photo,
    sql.Types.AUDIO.value: dispatcher.bot.send_audio,
    sql.Types.VOICE.value: dispatcher.bot.send_voice,
    sql.Types.VIDEO.value: dispatcher.bot.send_video
}


# Do not async
def get(update, context, notename, show_none=True, no_format=False):
    bot = context.bot
    chat_id = update.effective_message.chat.id
    note_chat_id = update.effective_chat.id
    note = sql.get_note(note_chat_id, notename)
    message = update.effective_message  # type: Optional[Message]

    if note:
        if MessageHandlerChecker.check_user(update.effective_user.id):
            return
        # If we're replying to a message, reply to that message (unless it's an error)
        if message.reply_to_message:
            reply_id = message.reply_to_message.message_id
        else:
            reply_id = message.message_id
        if note.is_reply:
            if JOIN_LOGGER:
                try:
                    bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=JOIN_LOGGER,
                        message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Göndərmə mesajı tapılmadı":
                        message.reply_text(
                            "Bu mesaj itirilmiş kimi görünür - siləcəm "
                            "qeydlər siyahınızdan.")
                        sql.rm_note(note_chat_id, notename)
                    else:
                        raise
            else:
                try:
                    bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=chat_id,
                        message_id=note.value)
                except BadRequest as excp:
                    if excp.message == "Göndərmə mesajı tapılmadı":
                        message.reply_text(
                            "Deyəsən bu qeydin orijinal göndəricisi silindi "
                            "mesajları - bağışlayın! bot admininizi istifadə etməyə başlasın "
                            "bunun qarşısını almaq üçün mesaj atın. Bu qeyddən siləcəm "
                            "qeyd etdiyiniz qeydlər.")
                        sql.rm_note(note_chat_id, notename)
                    else:
                        raise
        else:
            VALID_NOTE_FORMATTERS = [
                'first', 'last', 'fullname', 'username', 'id', 'chatname',
                'mention'
            ]
            valid_format = escape_invalid_curly_brackets(
                note.value, VALID_NOTE_FORMATTERS)
            if valid_format:
                if not no_format:
                    if '%%%' in valid_format:
                        split = valid_format.split('%%%')
                        if all(split):
                            text = random.choice(split)
                        else:
                            text = valid_format
                    else:
                        text = valid_format
                else:
                    text = valid_format
                text = text.format(
                    first=escape_markdown(message.from_user.first_name),
                    last=escape_markdown(message.from_user.last_name or
                                         message.from_user.first_name),
                    fullname=escape_markdown(
                        " ".join([
                            message.from_user.first_name, message.from_user
                            .last_name
                        ] if message.from_user.last_name else
                                 [message.from_user.first_name])),
                    username="@" + message.from_user.username
                    if message.from_user.username else mention_markdown(
                        message.from_user.id, message.from_user.first_name),
                    mention=mention_markdown(message.from_user.id,
                                             message.from_user.first_name),
                    chatname=escape_markdown(
                        message.chat.title if message.chat.type != "private"
                        else message.from_user.first_name),
                    id=message.from_user.id)
            else:
                text = ""

            keyb = []
            parseMode = ParseMode.MARKDOWN
            buttons = sql.get_buttons(note_chat_id, notename)
            if no_format:
                parseMode = None
                text += revert_buttons(buttons)
            else:
                keyb = build_keyboard(buttons)

            keyboard = InlineKeyboardMarkup(keyb)

            try:
                if note.msgtype in (sql.Types.BUTTON_TEXT, sql.Types.TEXT):
                    bot.send_message(
                        chat_id,
                        text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        disable_web_page_preview=True,
                        reply_markup=keyboard)
                else:
                    ENUM_FUNC_MAP[note.msgtype](
                        chat_id,
                        note.file,
                        caption=text,
                        reply_to_message_id=reply_id,
                        parse_mode=parseMode,
                        disable_web_page_preview=True,
                        reply_markup=keyboard)

            except BadRequest as excp:
                if excp.message == "Entity_mention_user_invalid":
                    message.reply_text(
                        "Deyəsən əvvəllər görmədiyim birinin adını çəkməyə çalışdın. Həqiqətənsə "
                        "onlardan bəhs etmək istəyirəm, mesajlarından birini mənə çatdırın və bacaracağam "
                        "onları etiketləmək üçün!")
                elif FILE_MATCHER.match(note.value):
                    message.reply_text(
                        "Bu qeyd başqa bir botdan səhvən gətirilmiş bir fayl idi - istifadə edə bilmirəm "
                        "Əgər həqiqətən ehtiyacınız varsa, onu yenidən saxlamalısınız. İçərisində "
                        "bu vaxt qeydlər siyahınızdan siləcəm.")
                    sql.rm_note(note_chat_id, notename)
                else:
                    message.reply_text(
                        "Səhv biçimlendirildiyi üçün bu qeyd göndərilə bilmədi. Soruşun "
                        f"@{SUPPORT_CHAT} Səbəbini anlaya bilmirsinizsə!")
                    LOGGER.exception("söhbətində #%s mesajı təhlil edilə bilmədi %s",
                                     notename, str(note_chat_id))
                    LOGGER.warning("Mesaj: %s", str(note.value))
        return
    elif show_none:
        message.reply_text("Bu qeyd yoxdur")


@run_async
@connection_status
def cmd_get(update: Update, context: CallbackContext):
    bot, args = context.bot, context.args
    if len(args) >= 2 and args[1].lower() == "noformat":
        get(update, context, args[0].lower(), show_none=True, no_format=True)
    elif len(args) >= 1:
        get(update, context, args[0].lower(), show_none=True)
    else:
        update.effective_message.reply_text("Get rekt")


@run_async
@connection_status
def hash_get(update: Update, context: CallbackContext):
    message = update.effective_message.text
    fst_word = message.split()[0]
    no_hash = fst_word[1:].lower()
    get(update, context, no_hash, show_none=False)


@run_async
@connection_status
def slash_get(update: Update, context: CallbackContext):
    message, chat_id = update.effective_message.text, update.effective_chat.id
    no_slash = message[1:]
    note_list = sql.get_all_chat_notes(chat_id)

    try:
        noteid = note_list[int(no_slash) - 1]
        note_name = str(noteid).strip(">").split()[1]
        get(update, context, note_name, show_none=False)
    except IndexError:
        update.effective_message.reply_text("Wrong Note ID 😾")


@run_async
@user_admin
@connection_status
def save(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    msg = update.effective_message  # type: Optional[Message]

    note_name, text, data_type, content, buttons = get_note_type(msg)
    note_name = note_name.lower()
    if data_type is None:
        msg.reply_text("Dostum, qeyd yoxdur")
        return

    sql.add_note_to_db(
        chat_id, note_name, text, data_type, buttons=buttons, file=content)

    msg.reply_text(
        f"Yes! əlavə edildi `{note_name}`.\nəldə edin / əldə edin `{note_name}`, və ya `#{note_name}`",
        parse_mode=ParseMode.MARKDOWN)

    if msg.reply_to_message and msg.reply_to_message.from_user.is_bot:
        if text:
            msg.reply_text(
                "Bir mesajı botdan qurtarmaq istədiyin kimi görünür. Təəssüf ki, "
                "botlar bot mesajlarını ötürə bilmir, ona görə də dəqiq mesajı saxlaya bilmirəm. "
                "\nBacardığım bütün mətni saxlayacam, amma daha çoxunu istəyirsənsə etməli olacaqsan "
                "mesajı özünüz yönləndirin və sonra qeyd edin.")
        else:
            msg.reply_text(
                "Botlar telegramla əlil olur və botların işini çətinləşdirir "
                "digər botlarla qarşılıqlı əlaqədə olduğum üçün bu mesajı saxlaya bilmirəm "
                "adətən istədiyim kimi - yönləndirməyi düşünmürsən və "
                "sonra yeni mesajı saxlayırsınız? Təşəkkürlər!")
        return


@run_async
@user_admin
@connection_status
def clear(update: Update, context: CallbackContext):
    args = context.args
    chat_id = update.effective_chat.id
    if len(args) >= 1:
        notename = args[0].lower()

        if sql.rm_note(chat_id, notename):
            update.effective_message.reply_text("Qeyd uğurla silindi.")
        else:
            update.effective_message.reply_text(
                "Bu mənim verilənlər bazamda bir qeyd deyil!")


@run_async
def clearall(update: Update, context: CallbackContext):
    chat = update.effective_chat
    user = update.effective_user
    member = chat.get_member(user.id)
    if member.status != "creator" and user.id not in DRAGONS:
        update.effective_message.reply_text(
            "Yalnız söhbət sahibi bir anda bütün qeydləri silə bilər.")
    else:
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                text="Bütün qeydləri silin", callback_data="notes_rmall")
        ], [InlineKeyboardButton(text="Cancel", callback_data="notes_cancel")]])
        update.effective_message.reply_text(
            f"{chat.title}'da BÜTÜN qeydləri silmək istədiyinizə əminsinizmi? Bu əməliyyat geri qaytarıla bilməz..",
            reply_markup=buttons,
            parse_mode=ParseMode.MARKDOWN)


@run_async
def clearall_btn(update: Update, context: CallbackContext):
    query = update.callback_query
    chat = update.effective_chat
    message = update.effective_message
    member = chat.get_member(query.from_user.id)
    if query.data == 'notes_rmall':
        if member.status == "creator" or query.from_user.id in DRAGONS:
            note_list = sql.get_all_chat_notes(chat.id)
            try:
                for notename in note_list:
                    note = notename.name.lower()
                    sql.rm_note(chat.id, note)
                message.edit_text("Bütün qeydlər silindi.")
            except BadRequest:
                return

        if member.status == "administrator":
            query.answer("Bunu yalnız söhbət sahibi edə bilər.")

        if member.status == "member":
            query.answer("Bunu etmək üçün admin olmalısınız.")
    elif query.data == 'notes_cancel':
        if member.status == "creator" or query.from_user.id in DRAGONS:
            message.edit_text("Bütün qeydlərin silinməsi ləğv edildi.")
            return
        if member.status == "administrator":
            query.answer("Bunu yalnız söhbət sahibi edə bilər.")
        if member.status == "member":
            query.answer("Bunu etmək üçün admin olmalısınız.")


@run_async
@connection_status
def list_notes(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    note_list = sql.get_all_chat_notes(chat_id)
    notes = len(note_list) + 1
    msg = "Get note by `/notenumber` or `#notename` \n\n  *ID*    *Note* \n"
    for note_id, note in zip(range(1, notes), note_list):
        if note_id < 10:
            note_name = f"`{note_id:2}.`  `#{(note.name.lower())}`\n"
        else:
            note_name = f"`{note_id}.`  `#{(note.name.lower())}`\n"
        if len(msg) + len(note_name) > MAX_MESSAGE_LENGTH:
            update.effective_message.reply_text(
                msg, parse_mode=ParseMode.MARKDOWN)
            msg = ""
        msg += note_name

    if not note_list:
        try:
            update.effective_message.reply_text("Bu söhbətdə qeyd yoxdur!")
        except BadRequest:
            update.effective_message.reply_text(
                "Bu söhbətdə qeyd yoxdur!", quote=False)

    elif len(msg) != 0:
        update.effective_message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def __import_data__(chat_id, data):
    failures = []
    for notename, notedata in data.get("extra", {}).items():
        match = FILE_MATCHER.match(notedata)
        matchsticker = STICKER_MATCHER.match(notedata)
        matchbtn = BUTTON_MATCHER.match(notedata)
        matchfile = MYFILE_MATCHER.match(notedata)
        matchphoto = MYPHOTO_MATCHER.match(notedata)
        matchaudio = MYAUDIO_MATCHER.match(notedata)
        matchvoice = MYVOICE_MATCHER.match(notedata)
        matchvideo = MYVIDEO_MATCHER.match(notedata)
        matchvn = MYVIDEONOTE_MATCHER.match(notedata)

        if match:
            failures.append(notename)
            notedata = notedata[match.end():].strip()
            if notedata:
                sql.add_note_to_db(chat_id, notename[1:], notedata,
                                   sql.Types.TEXT)
        elif matchsticker:
            content = notedata[matchsticker.end():].strip()
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.STICKER,
                    file=content)
        elif matchbtn:
            parse = notedata[matchbtn.end():].strip()
            notedata = parse.split("<###button###>")[0]
            buttons = parse.split("<###button###>")[1]
            buttons = ast.literal_eval(buttons)
            if buttons:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.BUTTON_TEXT,
                    buttons=buttons,
                )
        elif matchfile:
            file = notedata[matchfile.end():].strip()
            file = file.split("<###TYPESPLIT###>")
            notedata = file[1]
            content = file[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.DOCUMENT,
                    file=content)
        elif matchphoto:
            photo = notedata[matchphoto.end():].strip()
            photo = photo.split("<###TYPESPLIT###>")
            notedata = photo[1]
            content = photo[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.PHOTO,
                    file=content)
        elif matchaudio:
            audio = notedata[matchaudio.end():].strip()
            audio = audio.split("<###TYPESPLIT###>")
            notedata = audio[1]
            content = audio[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.AUDIO,
                    file=content)
        elif matchvoice:
            voice = notedata[matchvoice.end():].strip()
            voice = voice.split("<###TYPESPLIT###>")
            notedata = voice[1]
            content = voice[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VOICE,
                    file=content)
        elif matchvideo:
            video = notedata[matchvideo.end():].strip()
            video = video.split("<###TYPESPLIT###>")
            notedata = video[1]
            content = video[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VIDEO,
                    file=content)
        elif matchvn:
            video_note = notedata[matchvn.end():].strip()
            video_note = video_note.split("<###TYPESPLIT###>")
            notedata = video_note[1]
            content = video_note[0]
            if content:
                sql.add_note_to_db(
                    chat_id,
                    notename[1:],
                    notedata,
                    sql.Types.VIDEO_NOTE,
                    file=content)
        else:
            sql.add_note_to_db(chat_id, notename[1:], notedata, sql.Types.TEXT)

    if failures:
        with BytesIO(str.encode("\n".join(failures))) as output:
            output.name = "failed_imports.txt"
            dispatcher.bot.send_document(
                chat_id,
                document=output,
                filename="failed_imports.txt",
                caption="Bu fayllar / fotolar mənşəli olduğu üçün idxal edilmədi "
                "başqa bir botdan. Bu telegram API məhdudlaşdırmasıdır və edə bilməz "
                "qarşısını almaq. Narahatçılığa görə üzr istəyirik!",
            )


def __stats__():
    return f"• {sql.num_notes()} notes, across {sql.num_chats()} chats."


def __migrate__(old_chat_id, new_chat_id):
    sql.migrate_chat(old_chat_id, new_chat_id)


def __chat_settings__(chat_id, user_id):
    notes = sql.get_all_chat_notes(chat_id)
    return f"Bu söhbətdə `{len(notes)}` qeydləri var."


__help__ = """
 • /get <qeydadı>:  Yazdığınız qeydi göstərə.
 • #<qeydadı>:   /get ilə eyni
 • /notes or /saved: bu söhbətdə mövcud olunan bütün qeydləri göstərər

Adminər :
 • /save <qeydadı>:  Bir mesaja cavab olaraq yazsanız qeyd olaraq həmin mesajı saxlayar
 • /clear <qeydadı>: Yazdığınız adda olan qeydi silər

"""

__mod_name__ = "Qeydlər"

GET_HANDLER = CommandHandler("get", cmd_get)
HASH_GET_HANDLER = MessageHandler(Filters.regex(r"^#[^\s]+"), hash_get)
SLASH_GET_HANDLER = MessageHandler(Filters.regex(r"^/\d+$"), slash_get)
SAVE_HANDLER = CommandHandler("save", save)
DELETE_HANDLER = CommandHandler("clear", clear)

LIST_HANDLER = DisableAbleCommandHandler(["notes", "saved"],
                                         list_notes,
                                         admin_ok=True)

CLEARALL = DisableAbleCommandHandler("removeallnotes", clearall)
CLEARALL_BTN = CallbackQueryHandler(clearall_btn, pattern=r"notes_.*")

dispatcher.add_handler(GET_HANDLER)
dispatcher.add_handler(SAVE_HANDLER)
dispatcher.add_handler(LIST_HANDLER)
dispatcher.add_handler(DELETE_HANDLER)
dispatcher.add_handler(HASH_GET_HANDLER)
dispatcher.add_handler(SLASH_GET_HANDLER)
dispatcher.add_handler(CLEARALL)
dispatcher.add_handler(CLEARALL_BTN)
