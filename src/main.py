import discord
import config
from discord import app_commands

# import re
import json

intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

path_json = "/app/src/reactions.json"
write_json = False


# bot起動時に発火
@client.event
async def on_ready():
    print("bot is online!")
    global write_json
    # アクティビティを設定
    new_activity = f"出欠席リアクション"
    write_json = False
    await client.change_presence(activity=discord.Game(name=new_activity))
    # スラッシュコマンドを同期
    await tree.sync()


# メッセージの検知
@client.event
async def on_message(message):
    global write_json
    global reaction_num
    global path_json
    # 自身が送信したメッセージには反応しない
    if message.author == client.user:
        return

    # ユーザーからのメンションを受け取った場合、そのメッセージにリアクションをつけ、スレッドを作る
    if client.user in message.mentions:
        with open(path_json, "r") as f_r:
            reaction_dict = json.load(f_r)
        reaction_list = list(reaction_dict)
        channel = message.channel
        thread = await channel.create_thread(
            name=message, type=discord.ChannelType.public_thread
        )
        await thread.send("遅刻・欠席・その他連絡はこちらから！")
        for emoji in reaction_list:
            emoji_id = "<:" + emoji + ":" + reaction_dict[emoji] + ">"
            await message.add_reaction(emoji_id)

    # JSONファイルへの書き込み
    if write_json == True:
        with open(path_json, "r") as f_r:
            reaction_dict = json.load(f_r)
        reaction_list = list(reaction_dict)
        # print(reaction_dict)
        if reaction_num + 2 > len(reaction_list):
            await message.channel.send(
                "/finished コマンドを実行して更新作業を終了してください"
            )
        else:
            await message.channel.send(reaction_list[reaction_num + 1])
        if reaction_num <= len(reaction_list):
            dict_key = reaction_list[reaction_num]
            reaction_dict[dict_key] = message.content
            reaction_num += 1
            with open(path_json, "w") as f_w:
                json.dump(reaction_dict, f_w, indent=4)
        # print(reaction_dict)


@tree.command(
    name="update_reactions-id", description="出欠席リアクションIDを更新します"
)
async def start_update_reaction(interaction: discord.Interaction):
    global write_json
    global reaction_num
    write_json = True
    reaction_num = 0
    await interaction.response.send_message(
        "出欠席リアクションのIDを更新します。リアクションに対応するものを返信してください。\nSoprano_attend"
    )


@tree.command(name="finished", description="出欠席リアクションIDの更新を終了します")
async def finish_update_reaction(interaction: discord.Interaction):
    global write_json
    write_json = False
    await interaction.response.send_message(
        "出欠席リアクションの更新を終了しました。@メンションをして正しく設定されているかを確認してください。"
    )


# Bot起動
client.run(config.DISCORD_TOKEN)
