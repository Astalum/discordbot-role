import discord
import config
from discord import app_commands
# import re
import json

intents = discord.Intents.all()
client=discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

write_json=False

# bot起動時に発火
@client.event
async def on_ready():
    print("bot is online!")
    # アクティビティを設定 
    new_activity = f"出欠席リアクション" 
    write_json = False
    await client.change_presence(activity=discord.Game(new_activity)) 
    # スラッシュコマンドを同期 
    await tree.sync()

# メッセージの検知
@client.event
async def on_message(message, write_json):
    # 自身が送信したメッセージには反応しない
    if message.author == client.user:
        return

    # ユーザーからのメンションを受け取った場合、そのメッセージにリアクションをつける
    if client.user in message.mentions:
        emoji_list = ["<:delay:1224985952393625630>","<:mozuku:1252115584624099370>","<:naetoru:1252115727599538279>"]
        for emoji in emoji_list:
            await message.add_reaction(emoji)
    
    # JSONファイルへの書き込み
    if write_json == True:
        with open('/home/astalum/discordbot/konsei/discordbot-attend/reactions.json','r') as f:
            d_update = json.load(f)
            # print(d_update)
        for reaction in d_update.key():
            if reaction == "Soprano_attend":
                continue
            else:
                message.channel.send(reaction)
        await message.channel.send("/finished コマンドを実行して更新作業を終了してください")


@tree.command(name="update_reactions-id", description="出欠席リアクションIDを更新します") 
async def start_update_reaction(interaction: discord.Interaction): 
    write_json = True
    await interaction.response.send_message("出欠席リアクションのIDを更新します。リアクションに対応するものを返信してください。\nSoprano_attend")


@tree.command(name="finished", description="出欠席リアクションIDの更新を終了します") 
async def finish_update_reaction(interaction: discord.Interaction): 
    write_json = False
    await interaction.response.send_message("出欠席リアクションの更新を終了しました。@メンションをして正しく設定されているかを確認してください。")


# Bot起動
client.run(config.DISCORD_TOKEN)