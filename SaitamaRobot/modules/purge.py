import time
from telethon import events

from SaitamaRobot import telethn
from SaitamaRobot.modules.helper_funcs.telethn.chatstatus import (
    can_delete_messages, user_is_admin)


async def purge_messages(event):
    start = time.perf_counter()
    if event.from_id is None:
        return

    if not await user_is_admin(
            user_id=event.sender_id, message=event) and event.from_id not in [
                1087968824
            ]:
        await event.reply("Bu əmrdən yalnız Adminlərin istifadəsinə icazə verilir")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Mesajı təmizləmək görünmür")
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg:
        await event.reply(
            "Təmizləməyə haradan başlayacağınızı seçmək üçün mesajı cavablandırın.")
        return
    messages = []
    message_id = reply_msg.id
    delete_to = event.message.id

    messages.append(event.reply_to_msg_id)
    for msg_id in range(message_id, delete_to + 1):
        messages.append(msg_id)
        if len(messages) == 100:
            await event.client.delete_messages(event.chat_id, messages)
            messages = []

    try:
        await event.client.delete_messages(event.chat_id, messages)
    except:
        pass
    time_ = time.perf_counter() - start
    text = f"Müvəffəqiyyətlə təmizləndi  {time_:0.2f} Second(s)"
    await event.respond(text, parse_mode='markdown')


async def delete_messages(event):
    if event.from_id is None:
        return

    if not await user_is_admin(
            user_id=event.sender_id, message=event) and event.from_id not in [
                1087968824
            ]:
        await event.reply("Bu əmrdən yalnız Adminlərin istifadəsinə icazə verilir")
        return

    if not await can_delete_messages(message=event):
        await event.reply("Bunu silmək isdiyirsən?")
        return

    message = await event.get_reply_message()
    if not message:
        await event.reply("Whadya silmək istəyirsən?")
        return
    chat = await event.get_input_chat()
    del_message = [message, event.message]
    await event.client.delete_messages(chat, del_message)


__help__ = """
*Admin only:*
 - /del: cavab verdiyiniz mesajı silir
 - /purge: bununla mesajın cavablandırılması arasındakı bütün mesajları silir.
 - /purge <integer X>: cavab verilmiş mesajı və bir mesaja cavab verildiyi təqdirdə onu izləyən X mesajlarını silir. 
"""

PURGE_HANDLER = purge_messages, events.NewMessage(pattern="^[!/]purge$")
DEL_HANDLER = delete_messages, events.NewMessage(pattern="^[!/]del$")

telethn.add_event_handler(*PURGE_HANDLER)
telethn.add_event_handler(*DEL_HANDLER)

__mod_name__ = "Purges/Mesaj Silmək"
__command_list__ = ["del", "purge"]
__handlers__ = [PURGE_HANDLER, DEL_HANDLER]
