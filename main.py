import discord
import config
from discord import app_commands
# import re

intents = discord.Intents.all()
client=discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# bot起動時に発火
@client.event
async def on_ready():
    print("bot is online!")
    # アクティビティを設定 
    new_activity = f"テスト" 
    await client.change_presence(activity=discord.Game(new_activity)) 
    # スラッシュコマンドを同期 
    await tree.sync()

# メッセージの検知
@client.event
async def on_message(message):
    # 自身が送信したメッセージには反応しない
    if message.author == client.user:
        return

    # ユーザーからのメンションを受け取った場合、そのメッセージにリアクションをつける
    if client.user in message.mentions:
        emoji = "<:delay:1224985952393625630>"
        await message.add_reaction(emoji)

# Bot起動
client.run(config.DISCORD_TOKEN)