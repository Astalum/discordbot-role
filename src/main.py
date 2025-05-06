import discord
from discord.ext import commands
import asyncio
import json
import config

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

user_settings = {}


@bot.event
async def on_ready():
    print(f"✅ ログインしました: {bot.user}")


@bot.event
async def on_member_join(member):
    await asyncio.sleep(1)  # 少し待機（Discord APIの都合で必要な場合がある）

    # サーバーの「はじめに」チャンネルを取得
    intro_channel = discord.utils.get(member.guild.text_channels, name="はじめに")

    if intro_channel is None:
        print("❌『はじめに』チャンネルが見つかりませんでした。")
        return

    # チャンネルでセットアップ案内を送信し、DMでセットアップ開始
    try:
        await intro_channel.send(
            f"🎉 ようこそ {member.mention} さん！\n最初にいくつか設定をお願いします。DMを確認してください。"
        )

        # DMで setup を実行
        dm_channel = await member.create_dm()
        await dm_channel.send(
            "👋 はじめまして！以下のステップで簡単な初期設定を行います。"
        )
        await run_setup_flow(member, dm_channel)
    except Exception as e:
        print(f"⚠️ 初期設定送信中にエラー: {e}")


async def run_setup_flow(user, channel):
    def msg_check(m):
        return m.author == user and m.channel == channel

    data = {}

    # 項目別入力
    async def input_all_fields():
        # 名前（漢字）
        await channel.send(
            embed=discord.Embed(
                title="1️⃣ 名前（漢字）を入力してください", color=discord.Color.blue()
            )
        )
        msg = await bot.wait_for("message", check=msg_check)
        data["name_kanji"] = msg.content.strip()

        # 名前（カナ）
        await channel.send(
            embed=discord.Embed(
                title="2️⃣ 名前（カナ）を入力してください", color=discord.Color.blue()
            )
        )
        msg = await bot.wait_for("message", check=msg_check)
        data["name_kana"] = msg.content.strip()

        # 誕生月
        await channel.send(
            embed=discord.Embed(
                title="3️⃣ 誕生月を入力してください",
                description="例：4月生まれ → `04`",
                color=discord.Color.blue(),
            )
        )
        while True:
            msg = await bot.wait_for("message", check=msg_check)
            if msg.content.strip().isdigit() and 1 <= int(msg.content.strip()) <= 12:
                data["birth_month"] = msg.content.strip().zfill(2)
                break
            else:
                await channel.send("❌ 1〜12の数字を2桁（例: 04）で入力してください。")

        # 誕生日
        await channel.send(
            embed=discord.Embed(
                title="4️⃣ 誕生日を入力してください",
                description="例：2日 → `02`",
                color=discord.Color.blue(),
            )
        )
        while True:
            msg = await bot.wait_for("message", check=msg_check)
            if msg.content.strip().isdigit() and 1 <= int(msg.content.strip()) <= 31:
                data["birth_day"] = msg.content.strip().zfill(2)
                break
            else:
                await channel.send("❌ 1〜31の数字を2桁（例: 02）で入力してください。")

        # 期
        await channel.send(
            embed=discord.Embed(
                title="5️⃣ 期を入力してください", color=discord.Color.blue()
            )
        )
        msg = await bot.wait_for("message", check=msg_check)
        data["term"] = msg.content.strip()

        # パート（リアクション選択）
        embed = discord.Embed(
            title="6️⃣ パートを選択してください",
            description=":regional_indicator_s: ソプラノ\n:regional_indicator_a: アルト\n:regional_indicator_t: テノール\n:regional_indicator_b: バス\n\n該当する絵文字をクリックしてください。",
            color=discord.Color.blue(),
        )
        msg = await channel.send(embed=embed)
        part_emojis = {
            "🇸": "S",
            "🇦": "A",
            "🇹": "T",
            "🇧": "B",
        }
        for emoji in part_emojis:
            await msg.add_reaction(emoji)

        def reaction_check(reaction, user_):
            return (
                user_ == user
                and reaction.message.id == msg.id
                and str(reaction.emoji) in part_emojis
            )

        reaction, _ = await bot.wait_for("reaction_add", check=reaction_check)
        data["part"] = part_emojis[str(reaction.emoji)]

    # 修正付き確認フェーズ
    async def confirm_inputs():
        while True:
            confirm_embed = discord.Embed(
                title="📝 入力内容を確認してください",
                description=(
                    f"1️⃣ **名前（漢字）**: {data['name_kanji']}\n"
                    f"2️⃣ **名前（カナ）**: {data['name_kana']}\n"
                    f"3️⃣ **誕生月**: {data['birth_month']}\n"
                    f"4️⃣ **誕生日**: {data['birth_day']}\n"
                    f"5️⃣ **期**: {data['term']}\n"
                    f"6️⃣ **パート**: {data['part']}\n\n"
                    "✳️ 修正したい項目の絵文字を押してください。\n"
                    "✅ 問題なければ確認完了です。"
                ),
                color=discord.Color.orange(),
            )
            msg = await channel.send(embed=confirm_embed)
            emoji_map = {
                "1️⃣": "name_kanji",
                "2️⃣": "name_kana",
                "3️⃣": "birth_month",
                "4️⃣": "birth_day",
                "5️⃣": "term",
                "6️⃣": "part",
                "✅": "confirm",
            }
            for emoji in emoji_map:
                await msg.add_reaction(emoji)

            def confirm_reaction_check(reaction, user_):
                return (
                    user_ == user
                    and reaction.message.id == msg.id
                    and str(reaction.emoji) in emoji_map
                )

            reaction, _ = await bot.wait_for(
                "reaction_add", check=confirm_reaction_check
            )
            selected = emoji_map[str(reaction.emoji)]

            await msg.delete()

            if selected == "confirm":
                break

            # 再入力処理
            if selected == "name_kanji":
                await channel.send("✏️ 名前（漢字）を再入力してください：")
                msg = await bot.wait_for("message", check=msg_check)
                data["name_kanji"] = msg.content.strip()
            elif selected == "name_kana":
                await channel.send("✏️ 名前（カナ）を再入力してください：")
                msg = await bot.wait_for("message", check=msg_check)
                data["name_kana"] = msg.content.strip()
            elif selected == "birth_month":
                await channel.send("✏️ 誕生月を再入力してください（01〜12）：")
                while True:
                    msg = await bot.wait_for("message", check=msg_check)
                    if (
                        msg.content.strip().isdigit()
                        and 1 <= int(msg.content.strip()) <= 12
                    ):
                        data["birth_month"] = msg.content.strip().zfill(2)
                        break
                    else:
                        await channel.send("❌ 1〜12の数字を2桁で入力してください。")
            elif selected == "birth_day":
                await channel.send("✏️ 誕生日を再入力してください（01〜31）：")
                while True:
                    msg = await bot.wait_for("message", check=msg_check)
                    if (
                        msg.content.strip().isdigit()
                        and 1 <= int(msg.content.strip()) <= 31
                    ):
                        data["birth_day"] = msg.content.strip().zfill(2)
                        break
                    else:
                        await channel.send("❌ 1〜31の数字を2桁で入力してください。")
            elif selected == "term":
                await channel.send("✏️ 期を再入力してください：")
                msg = await bot.wait_for("message", check=msg_check)
                data["term"] = msg.content.strip()
            elif selected == "part":
                await channel.send("✏️ パートを再選択してください：")
                part_msg = await channel.send(
                    ":regional_indicator_s: ソプラノ\n:regional_indicator_a: アルト\n:regional_indicator_t: テノール\n:regional_indicator_b: バス\n\n該当する絵文字をクリックしてください。"
                )
                part_emojis = {
                    "🇸": "S",
                    "🇦": "A",
                    "🇹": "T",
                    "🇧": "B",
                }
                for emoji in part_emojis:
                    await part_msg.add_reaction(emoji)

                def part_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == part_msg.id
                        and str(reaction.emoji) in part_emojis
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=part_check)
                data["part"] = part_emojis[str(reaction.emoji)]

    # 実行フェーズ
    await input_all_fields()
    await confirm_inputs()

    # 保存と完了メッセージ
    user_settings[user.id] = data
    save_user_settings(user_settings)

    embed_done = discord.Embed(
        title="✅ 初期設定が完了しました！",
        description=(
            f"**名前（漢字）**: {data['name_kanji']}\n"
            f"**名前（カナ）**: {data['name_kana']}\n"
            f"**誕生日**: {data['birth_month']}月{data['birth_day']}日\n"
            f"**期**: {data['term']}\n"
            f"**パート**: {data['part']}"
        ),
        color=discord.Color.green(),
    )
    await channel.send(embed=embed_done)

    # ギルドID → ロール付与処理（元コードをそのまま続けて使用）
    guild_id = read_guild_id_from_file()
    if guild_id is None:
        await channel.send(
            "⚠️ サーバーIDが正しく読み込めませんでした。管理者にお問い合わせください。"
        )
        return

    guild = bot.get_guild(guild_id)
    if guild is None:
        await channel.send(
            "⚠️ サーバーが見つかりませんでした。Botが参加しているか確認してください。"
        )
        return

    role = discord.utils.get(guild.roles, name=config.CONFIRMATION_ROLE_NAME)
    if role is None:
        await channel.send(
            "⚠️ ロールが見つかりませんでした。管理者にお問い合わせください。"
        )
        return

    member = guild.get_member(user.id)
    if member:
        await member.add_roles(role)
        await channel.send(f"🎉 `{role.name}` ロールが付与されました！")
    else:
        await channel.send("⚠️ サーバーメンバーが見つかりませんでした。")

    # ニックネーム変更処理
    new_nickname = f"{data['name_kanji']}/{data['term']}{data['part']}"
    try:
        await member.edit(nick=new_nickname)
        await channel.send(f"✅ ニックネームを「{new_nickname}」に変更しました。")
    except discord.Forbidden:
        await channel.send(
            "⚠️ ニックネームを変更できませんでした。Botに「ニックネームの変更」権限があるか確認してください。"
        )


def save_user_settings(data, filename="./src/user_settings.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def read_guild_id_from_file(filename="src/guild_id.txt"):
    try:
        with open(filename, "r") as f:
            guild_id = f.read().strip()
            return int(guild_id)  # ファイルから読み込んだIDを整数として返す
    except FileNotFoundError:
        print(f"❌ {filename} が見つかりませんでした。")
        return None
    except ValueError:
        print("❌ guild_id.txt に無効なIDが含まれています。")
        return None


bot.run(config.DISCORD_TOKEN)
