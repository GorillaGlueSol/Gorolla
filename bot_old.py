from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ChatMember
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, \
    ConversationHandler, CallbackContext
from PIL import Image, ImageDraw, ImageFont
import random
import io

# Stany rozmowy
INTRO, CAPTCHA, AIRDROP, JOIN_CHANNEL, VERIFY_CHANNEL, TWITTER, WALLET = range(7)

# Pamięć na dane użytkowników i punkty
user_data = {}
referrals = {}  # Zapisuje polecających dla każdego użytkownika


def generate_captcha_text(length=5):
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
    return ''.join(random.choice(chars) for _ in range(length))


def generate_captcha_image(text):
    width, height = 200, 60
    image = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(image)

    font = ImageFont.load_default()
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    text_x = (width - text_width) // 2
    text_y = (height - text_height) // 2

    draw.text((text_x, text_y), text, fill=(0, 0, 0), font=font)

    # Add some noise
    for _ in range(100):
        x, y = random.randint(0, width - 1), random.randint(0, height - 1)
        draw.point((x, y), fill=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))

    # Convert image to bytes
    buf = io.BytesIO()
    image.save(buf, format='PNG')
    buf.seek(0)

    return buf


async def check_user_in_channel(user_id: int, chat_id: str, bot) -> bool:
    try:
        chat_member = await bot.get_chat_member(chat_id, user_id)
        status = chat_member.status
        return status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        return False


async def start(update: Update, context: CallbackContext) -> int:
    referral_id = context.args[0] if context.args else None

    user = update.message.from_user
    user_data[user.id] = {"username": user.username, "points": 3000, "referrer": referral_id}

    if referral_id and referral_id.isdigit():
        referrer_id = int(referral_id)
        if referrer_id in user_data:
            user_data[referrer_id]['points'] = user_data[referrer_id].get('points', 0) + 500

    captcha_text = generate_captcha_text()
    context.user_data['captcha_text'] = captcha_text

    captcha_image = generate_captcha_image(captcha_text)

    await update.message.reply_photo(
        photo=captcha_image,
        caption="Welcome to our Telegram bot! To proceed, please solve the captcha."
    )
    return CAPTCHA


async def captcha(update: Update, context: CallbackContext) -> int:
    user_answer = update.message.text
    correct_answer = context.user_data.get('captcha_text')

    if user_answer == correct_answer:
        await update.message.reply_text(
            "Welcome to participate in our Airdrop!\n\n"
            "Click the 'Submit Details' button and complete the airdrop tasks to earn 3,000 $SMOKE tokens.\n\n"
            "$GGLUE is a new memecoin on Solana, here to make everyone less stressed.\n\n"
            "Airdrop will end on August 05, 2024 and every valid participant will be rewarded.\n\n"
            "In addition, you can earn an extra 500 $GGLUE tokens for each of your friends who join our airdrop using your referral link which you'll get after completing the airdrop tasks.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Submit Details", callback_data='submit_details')]
            ])
        )
        return AIRDROP
    else:
        await update.message.reply_text("Wrong captcha, please try again.")
        return CAPTCHA


async def airdrop(update: Update, context: CallbackContext) -> int:
    query = update.callback_query

    await query.answer()
    await query.edit_message_text(
        text="You need to join the channel to proceed. Click the button below to join, then click 'Done'.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Channel", url="https://t.me/GorillaGlueSolana")],
            [InlineKeyboardButton("Done", callback_data='done')]
        ])
    )
    return JOIN_CHANNEL


async def done(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user = query.from_user
    chat_id = "@GorillaGlueSolana"

    if await check_user_in_channel(user.id, chat_id, context.bot):
        await query.answer()
        await query.edit_message_text(
            text="🔘 Follow our X (Twitter) profile.\n\nThen submit your X username:\nExample: @username",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Follow Twitter", url="https://twitter.com/GorillaGlueSOL")],
                [InlineKeyboardButton("Submit Twitter Username", callback_data='submit_twitter')]
            ])
        )
        return TWITTER
    else:
        await query.answer("You have not joined the channel yet.")
        return JOIN_CHANNEL


async def twitter(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    user_data[user.id]["username"] = user.username  # Ensure username is set

    await update.message.reply_text(
        "Submit your Solana (SOL) wallet address:\n\nDon't have a wallet?\nCreate one with Phantom or Solflare."
    )
    return WALLET


async def wallet(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    wallet_address = update.message.text
    user_data[user.id]["wallet"] = wallet_address

    # Generate referral link
    referral_link = f"https://t.me/GorillaGlueSOL_Bot?start={user.id}"

    await update.message.reply_text(
        f"Thank you for participating in our airdrop and congratulations you have earned 3,000 $SMOKE tokens airdrop balance. Please do not leave any of our social media platforms until the airdrop distribution is completed.\n\n"
        f"Airdrop will end on August 05, 2024 and every valid participant will be rewarded.\n\n"
        f"In addition, you can earn an extra 500 $SMOKE tokens for each of your friends who join our airdrop using your referral link.\n\n"
        f"Your referral link:\n{referral_link}",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📊 Account"), KeyboardButton("🏆 Leaderboard")]],
            resize_keyboard=True
        )
    )
    return ConversationHandler.END


async def handle_text(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if text == "📊 Account":
        await account(update, context)
    elif text == "🏆 Leaderboard":
        await leaderboard(update, context)


async def account(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    if user.id in user_data:
        points = user_data[user.id].get("points", 0)
        await update.message.reply_text(f"Your current points: {points}")
    else:
        await update.message.reply_text("You have not participated in the airdrop yet.")


async def leaderboard(update: Update, context: CallbackContext) -> None:
    leaderboard = sorted(user_data.items(), key=lambda x: x[1].get("points", 0), reverse=True)[:20]
    leaderboard_text = "\n".join(
        [f"{i + 1}. {user[1].get('username', 'Unknown')} - {user[1].get('points', 0)} points" for i, user in
         enumerate(leaderboard)]
    )
    await update.message.reply_text(f"Leaderboard:\n\n{leaderboard_text}")


def main() -> None:
    application = Application.builder().token("7072742247:AAFjSdB4soVfyHTLfdu5YEgsvkwbF6zDoQ4").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CAPTCHA: [MessageHandler(filters.TEXT & ~filters.COMMAND, captcha)],
            AIRDROP: [CallbackQueryHandler(airdrop, pattern='submit_details')],
            JOIN_CHANNEL: [CallbackQueryHandler(done, pattern='done')],
            TWITTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, twitter)],
            WALLET: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet)],
        },
        fallbacks=[MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
    )

    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling()


if __name__ == '__main__':
    main()
