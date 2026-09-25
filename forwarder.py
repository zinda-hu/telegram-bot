import asyncio
import re
from telethon import TelegramClient, events
from telethon.tl.types import MessageService

# 🔑 Your Telegram API Credentials
API_ID = 35581326
API_HASH = "6cf93b0b1fabeea4364979450c8173c1"

# 📋 Group and Topic Configurations
SOURCE_CHAT_ID = -1002422791506  
DEST_CHAT_ID = -1004465182450    
DEST_TOPIC_ID = 668              

# Initialize Telethon Client
client = TelegramClient("final_fixed_session", API_ID, API_HASH)


def clean_text_completely(original_text):
  """Removes third-party links, advertisements, and handles cleanly as pure text."""
  if not original_text:
    return ""

  text = original_text

  # Protect your target channel link from being accidentally scrubbed
  text = re.sub(r"t\.me\/UPSC_LECTURE_DUMP", "___MY_LINK___", text, flags=re.IGNORECASE)
  
  # Strip out external Telegram links
  text = re.sub(
      r"(https?:\/\/)?(www\.)?(t\.me|telegram\.me)\/[a-zA-Z0-9_\+\/]+",
      "",
      text,
  )

  # Strip out handles and restore yours
  text = re.sub(r"@[a-zA-Z0-9_]+", "", text)
  text = text.replace("___MY_LINK___", "t.me/UPSC_LECTURE_DUMP")

  cleanup_phrases = [
      "forward on channel",
      "backup channel",
      "extracted by",
      "downloaded by",
      "join channel",
      "credit:",
  ]

  lines = text.split("\n")
  cleaned_lines = []

  for line in lines:
    line_clean = line.replace("-", "").replace(":", "").strip().lower()
    if any(phrase in line_clean for phrase in cleanup_phrases):
      continue
    cleaned_lines.append(line)

  text = "\n".join(cleaned_lines).strip()
  text = re.sub(r"\n{3,}", "\n\n", text)
  return text


def is_valid_lecture_content(message):
  """Filters out chat noise, greeting spams, and student chatting."""
  if isinstance(message, MessageService):
    return False

  if message.media and not message.photo:
    return True
  
  raw_text = message.message if hasattr(message, 'message') and message.message else ""
  text_clean = raw_text.strip().lower()

  if not text_clean or text_clean in [".", "..", "...", "hello", "hi", "sir", "ok", "okay"]:
    return False

  block_chatter_triggers = [
      "anyone have", "anybody has", "please send", "de do", "kaha hai", 
      "send me", "provide", "share link", "give lecture", "sir lecture"
  ]
  if any(trigger in text_clean for trigger in block_chatter_triggers):
    return False

  if message.media:
    return True

  has_lecture_markers = any(
      kw in text_clean 
      for kw in ["lecture", "ch-", "chapter", "class", "drive.google", "mega.nz", "pdf", "notes"]
  )
  return has_lecture_markers


async def process_and_send(message):
  """Sanitizes text and appends the working group link shortcut cleanly."""
  if not is_valid_lecture_content(message):
    return None

  raw_text = message.message if hasattr(message, 'message') and message.message else ""
  cleaned_body = clean_text_completely(raw_text)

  footer = "\n\n👉 **for more lecture join my group:** https://t.me/UPSC_LECTURE_DUMP"
  final_text = f"{cleaned_body}{footer}" if cleaned_body else footer.strip()

  sent_msg = None
  if message.media:
    sent_msg = await client.send_message(
        DEST_CHAT_ID, message=final_text, file=message.media, reply_to=DEST_TOPIC_ID
    )
  else:
    sent_msg = await client.send_message(
        DEST_CHAT_ID, message=final_text, reply_to=DEST_TOPIC_ID
    )
  return sent_msg


# 📡 Live Monitoring Hook
@client.on(events.NewMessage(chats=SOURCE_CHAT_ID))
async def live_handler(event):
  try:
    sent_msg = await process_and_send(event.message)
    if sent_msg and event.message.pinned:
      await client.pin_message(DEST_CHAT_ID, sent_msg.id, notify=False)
      print(f"[Live] Forwarded and pinned new message ID: {event.message.id}")
    elif sent_msg:
      print(f"[Live] Forwarded new message ID: {event.message.id}")
  except Exception:
    pass


# 🕒 Chunked History Synchronizer
async def sync_historical_data():
  print("[History] Resuming database sync precisely from message ID 2826...")
  count = 0
  
  # 📍 FORCE START: This ensures it starts picking up blocks at ID 2826
  last_processed_id = 7062  

  while True:
    try:
      messages = await client.get_messages(
          SOURCE_CHAT_ID, 
          limit=100, 
          offset_id=last_processed_id, 
          reverse=True
      )
      
      if not messages:
        print("[History] Reached the end of available history logs.")
        break

      print(f"[Scanning] Processing block of {len(messages)} messages starting from ID {last_processed_id}...")

      for message in messages:
        # Keep moving the tracker forward
        last_processed_id = message.id
        
        if is_valid_lecture_content(message):
          sent_msg = await process_and_send(message)
          if sent_msg:
            count += 1
            print(f"[History] 👉 SUCCESS: Transferred lecture ID {message.id}")
            
            if message.pinned:
              try:
                await client.pin_message(DEST_CHAT_ID, sent_msg.id, notify=False)
                print(f"[History Pin] 📌 Pinned message copy for ID: {message.id}")
              except Exception:
                pass
                
            await asyncio.sleep(1.5)  # Slightly increased delay to remain safe from rate limits
            
      await asyncio.sleep(2.5)

    except Exception as e:
      if "FloodWaitError" in str(type(e)) or "Wait" in str(e):
        wait_time = int(re.search(r'\d+', str(e)).group()) if re.search(r'\d+', str(e)) else 60
        print(f"[System Warning] Telegram rate limit active. Cooling down for {wait_time} seconds...")
        await asyncio.sleep(wait_time)
      else:
        await asyncio.sleep(5)
        continue

  print(f"\n[History] Complete! {count} valid materials imported in absolute order.")
  print("[System] Standing by for incoming live updates...")


async def main():
  print("[System] Initializing chronological timeline connection...")
  await client.start()
  asyncio.create_task(sync_historical_data())
  await client.run_until_disconnected()


if __name__ == "__main__":
  asyncio.run(main())
