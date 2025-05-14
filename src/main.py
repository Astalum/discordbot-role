import os
import discord
from discord.ext import commands
import asyncio
import json
import config
from discord.ext import tasks
from datetime import datetime, time

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.messages = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

user_settings = {}
PATH_SERVER_VERSION = "./src/server_version.txt"
# dockercontainer用
PATH_TERM_OF_EXECUTION = "/shared_data/term_of_execution.txt"
PATH_GUILD_JSON = "/shared_data/guild_id.json"
PATH_USER_SETTINGS = "/shared_data/user_settings.json"
# local用
# PATH_GUILD_JSON = "guild_id.json"
# PATH_USER_SETTINGS = "user_settings.json"
# PATH_TERM_OF_EXECUTION = "./src/term_of_execution.txt"


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ ログインしました: {bot.user}")


@bot.event
async def on_member_join(member):
    await asyncio.sleep(1)  # 少し待機（Discord APIの都合で必要な場合がある）

    # サーバーの「はじめに」チャンネルを取得
    intro_channel = discord.utils.get(member.guild.text_channels, name="ようこそ")

    if intro_channel is None:
        print("❌『はじめに』チャンネルが見つかりませんでした")
        return

    # チャンネルでセットアップ案内を送信し、DMでセットアップ開始
    try:
        await intro_channel.send(
            f"🎉 ようこそ {member.mention} さん！\n最初にいくつか設定をお願いします。DMを確認してください。"
        )

        # DMで setup を実行
        dm_channel = await member.create_dm()
        await dm_channel.send(
            "👋 はじめまして！初期設定を行います、必要事項を入力してください。"
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
                await channel.send("❌ 1〜12の数字を2桁（例: 04）で入力してください")

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
                await channel.send("❌ 1〜31の数字を2桁（例: 02）で入力してください")

        # 期
        await channel.send(
            embed=discord.Embed(
                title="5️⃣ 期を入力してください",
                description="数字のみ入力してください",
                color=discord.Color.blue(),
            )
        )
        msg = await bot.wait_for("message", check=msg_check)
        data["term"] = msg.content.strip()

        # パート（リアクション選択）
        embed = discord.Embed(
            title="6️⃣ パートを選択してください",
            description=":regional_indicator_s: ソプラノ\n:regional_indicator_a: アルト\n:regional_indicator_t: テノール\n:regional_indicator_b: バス\n\n該当する絵文字をクリックしてください",
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

        # 新入団員確認
        embed = discord.Embed(
            title="7️⃣ あなたは新入団員ですか？",
            description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
            color=discord.Color.blue(),
        )
        msg = await channel.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❎")

        def newcomer_check(reaction, user_):
            return (
                user_ == user
                and reaction.message.id == msg.id
                and str(reaction.emoji) in ["✅", "❎"]
            )

        reaction, _ = await bot.wait_for("reaction_add", check=newcomer_check)
        data["is_newcomer"] = str(reaction.emoji) == "✅"

    # 修正付き確認フェーズ
    async def confirm_inputs_information():
        while True:
            confirm_embed = discord.Embed(
                title="📝 入力内容を確認してください",
                description=(
                    f"1️⃣ **名前（漢字）**: {data['name_kanji']}\n"
                    f"2️⃣ **名前（カナ）**: {data['name_kana']}\n"
                    f"3️⃣ **誕生月**: {data['birth_month']}\n"
                    f"4️⃣ **誕生日**: {data['birth_day']}\n"
                    f"5️⃣ **期**: {data['term']}\n"
                    f"6️⃣ **パート**: {data['part']}\n"
                    f"7️⃣ **新入生**: {'はい' if data['is_newcomer'] else 'いいえ'}\n\n"
                    "❗️ 修正したい項目の絵文字を押してください\n"
                    "✅ 問題なければ確認完了です"
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
                "7️⃣": "is_newcomer",
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
                        await channel.send("❌ 1〜12の数字を2桁で入力してください")
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
                        await channel.send("❌ 1〜31の数字を2桁で入力してください")
            elif selected == "term":
                await channel.send("✏️ 期を再入力してください：")
                msg = await bot.wait_for("message", check=msg_check)
                data["term"] = msg.content.strip()
            elif selected == "part":
                await channel.send("✏️ パートを再選択してください：")
                part_msg = await channel.send(
                    ":regional_indicator_s: ソプラノ\n:regional_indicator_a: アルト\n:regional_indicator_t: テノール\n:regional_indicator_b: バス\n\n該当する絵文字をクリックしてください"
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
            elif selected == "is_newcomer":
                embed = discord.Embed(
                    title="✏️ 新入団員かどうかを再選択してください：",
                    description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def newcomer_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=newcomer_check)
                data["is_newcomer"] = str(reaction.emoji) == "✅"

    async def prompt_reaction_position():
        execution_term = read_term_of_execution_from_file()
        print(execution_term)
        if (int(data["term"]) not in [execution_term, execution_term + 1]) or data[
            "is_newcomer"
        ]:
            return
        else:
            # 役職の確認フロー（リアクション応答）
            positions = {
                "executive": False,
                "technique": False,
                "concert": False,
            }

            questions = [
                ("あなたは〇責に所属していますか？", "executive"),
                ("あなたは〇技に所属していますか？", "technique"),
                ("あなたは演実に所属していますか？", "concert"),
                ("あなたは第三者に所属していますか？", "third_party"),
            ]

            # 質問を順番に送信し、リアクションで返答を受け取る
            await channel.send("続いて組織情報の入力に移ります")
            for question, role in questions:
                embed = discord.Embed(
                    title=question,
                    description="✅：はい\n❎：いいえ",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def reaction_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=reaction_check)

                if str(reaction.emoji) == "✅":
                    positions[role] = True
                elif str(reaction.emoji) == "❎":
                    positions[role] = False

            # 最終的に `data["position"]` に保存
            data["position"] = positions

    # 修正付き確認フェーズ
    async def confirm_inputs_position():
        while True:
            confirm_embed = discord.Embed(
                title="📝 入力内容を確認してください",
                description=(
                    f"**🎩 〇責**: {'はい' if data['position']['executive'] else 'いいえ'}\n"
                    f"**🛠️ 〇技**: {'はい' if data['position']['technique'] else 'いいえ'}\n"
                    f"**🎼 演実**: {'はい' if data['position']['concert'] else 'いいえ'}\n"
                    f"**⚖️ 第三者**: {'はい' if data['position']['third_party'] else 'いいえ'}\n\n"
                    "❗️ 修正したい項目の絵文字を押してください\n"
                    "✅ 問題なければ確認完了です"
                ),
                color=discord.Color.orange(),
            )
            msg = await channel.send(embed=confirm_embed)
            emoji_map = {
                "🎩": "executive",
                "🛠️": "technique",
                "🎼": "concert",
                "⚖️": "third_party",
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
            if selected == "executive":
                embed = discord.Embed(
                    title="✏️ 〇責かどうかを再選択してください：",
                    description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def executive_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=executive_check)
                data["position"]["executive"] = str(reaction.emoji) == "✅"

            elif selected == "technique":
                embed = discord.Embed(
                    title="✏️ 〇技かどうかを再選択してください：",
                    description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def technique_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=technique_check)
                data["position"]["technique"] = str(reaction.emoji) == "✅"

            elif selected == "concert":
                embed = discord.Embed(
                    title="✏️ 演実かどうかを再選択してください：",
                    description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def concert_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=concert_check)
                data["position"]["concert"] = str(reaction.emoji) == "✅"

            elif selected == "third_party":
                embed = discord.Embed(
                    title="✏️ 第三者かどうかを再選択してください：",
                    description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def third_party_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for(
                    "reaction_add", check=third_party_check
                )
                data["position"]["third_party"] = str(reaction.emoji) == "✅"

    async def prompt_reaction_job():
        execution_term = read_term_of_execution_from_file()
        if (int(data["term"]) not in [execution_term, execution_term + 1]) or data[
            "is_newcomer"
        ]:
            return
        else:
            # 役職の確認フロー（リアクション応答）
            jobs = {
                "vice": False,
                "publicity": False,
            }

            questions = [
                ("あなたは副団長ですか？", "vice"),
                ("あなたは〇運広報ですか？", "publicity"),
            ]

            # 質問を順番に送信し、リアクションで返答を受け取る
            await channel.send("続いて役職情報の入力に移ります")
            for question, role in questions:
                embed = discord.Embed(
                    title=question,
                    description="✅：はい\n❎：いいえ",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def reaction_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=reaction_check)

                if str(reaction.emoji) == "✅":
                    jobs[role] = True
                elif str(reaction.emoji) == "❎":
                    jobs[role] = False

            # 最終的に `data["position"]` に保存
            data["job"] = jobs

    # 修正付き確認フェーズ
    async def confirm_inputs_job():
        while True:
            confirm_embed = discord.Embed(
                title="📝 入力内容を確認してください",
                description=(
                    f"**🛡️ 副団長**: {'はい' if data['job']['vice'] else 'いいえ'}\n"
                    f"**📣 〇運広報**: {'はい' if data['job']['publicity'] else 'いいえ'}\n\n"
                    "❗️ 修正したい項目の絵文字を押してください\n"
                    "✅ 問題なければ確認完了です"
                ),
                color=discord.Color.orange(),
            )
            msg = await channel.send(embed=confirm_embed)
            emoji_map = {
                "🛡️": "vice",
                "📣": "publicity",
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
            if selected == "vice":
                embed = discord.Embed(
                    title="✏️ 副団長かどうかを再選択してください：",
                    description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def vice_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=vice_check)
                data["job"]["vice"] = str(reaction.emoji) == "✅"

            elif selected == "publicity":
                embed = discord.Embed(
                    title="✏️ 〇運広報かどうかを再選択してください：",
                    description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                    color=discord.Color.blue(),
                )
                msg = await channel.send(embed=embed)
                await msg.add_reaction("✅")
                await msg.add_reaction("❎")

                def publicity_check(reaction, user_):
                    return (
                        user_ == user
                        and reaction.message.id == msg.id
                        and str(reaction.emoji) in ["✅", "❎"]
                    )

                reaction, _ = await bot.wait_for("reaction_add", check=publicity_check)
                data["job"]["publicity"] = str(reaction.emoji) == "✅"

    async def activity_investigation(user, channel, data):
        stages = {
            "first": "副指揮ステージ",
            "second": "正指揮ステージ",
            "german": "ドイツリートステージ",
            "takata": "髙田曲ステージ",
        }

        for key, label in stages.items():
            embed = discord.Embed(
                title=f"あなたは{label}にオンステしますか？",
                description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                color=discord.Color.blue(),
            )
            msg = await channel.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❎")

            def check(reaction, u):
                return (
                    u == user
                    and reaction.message.id == msg.id
                    and str(reaction.emoji) in ["✅", "❎"]
                )

            reaction, _ = await bot.wait_for("reaction_add", check=check)
            data["stage"][key] = str(reaction.emoji) == "✅"

    async def confirm_activity_investigation(user, channel, data):
        emoji_map = {
            "1️⃣": "first",
            "2️⃣": "second",
            "3️⃣": "german",
            "4️⃣": "takata",
            "✅": "confirm",
        }

        labels = {
            "first": "副指揮",
            "second": "正指揮",
            "german": "ドイツリート",
            "takata": "髙田曲",
        }

        while True:
            confirm_embed = discord.Embed(
                title="📝 入力内容を確認してください",
                description="\n".join(
                    f"**{labels[key]}**: {'乗る' if data['stage'][key] else '乗らない'}"
                    for key in ["first", "second", "german", "takata"]
                )
                + "\n\n❗️ 修正したい項目の絵文字を押してください\n✅ 問題なければ確認完了です",
                color=discord.Color.orange(),
            )

            msg = await channel.send(embed=confirm_embed)
            for emoji in emoji_map:
                await msg.add_reaction(emoji)

            def check(reaction, u):
                return (
                    u == user
                    and reaction.message.id == msg.id
                    and str(reaction.emoji) in emoji_map
                )

            reaction, _ = await bot.wait_for("reaction_add", check=check)
            selected = emoji_map[str(reaction.emoji)]
            await msg.delete()

            if selected == "confirm":
                break

            label = labels[selected]
            embed = discord.Embed(
                title=f"✏️ {label}に乗るかどうかを再選択してください：",
                description="✅：はい\n❎：いいえ\n\n該当するリアクションをクリックしてください",
                color=discord.Color.blue(),
            )
            msg = await channel.send(embed=embed)
            await msg.add_reaction("✅")
            await msg.add_reaction("❎")

            def stage_check(reaction, u):
                return (
                    u == user
                    and reaction.message.id == msg.id
                    and str(reaction.emoji) in ["✅", "❎"]
                )

            reaction, _ = await bot.wait_for("reaction_add", check=stage_check)
            data["stage"][selected] = str(reaction.emoji) == "✅"

    # 実行フェーズ
    await input_all_fields()
    await confirm_inputs_information()

    embed_done = discord.Embed(
        title="✅ 初期設定が完了しました！",
        description=(
            f"**名前（漢字）**: {data['name_kanji']}\n"
            f"**名前（カナ）**: {data['name_kana']}\n"
            f"**誕生日**: {data['birth_month']}月{data['birth_day']}日\n"
            f"**期**: {data['term']}\n"
            f"**パート**: {data['part']}\n"
            f"**新入生**: {'はい' if data['is_newcomer'] else 'いいえ'}"
        ),
        color=discord.Color.green(),
    )
    await channel.send(embed=embed_done)

    await prompt_reaction_position()
    await confirm_inputs_position()

    embed_done = discord.Embed(
        title="✅ 組織情報の設定が完了しました！",
        description=(
            f"**〇責**: {'はい' if data['position']['executive'] else 'いいえ'}\n"
            f"**〇技**: {'はい' if data['position']['technique'] else 'いいえ'}\n"
            f"**演実**: {'はい' if data['position']['concert'] else 'いいえ'}"
            f"**第三者**: {'はい' if data['position']['third_party'] else 'いいえ'}"
        ),
        color=discord.Color.green(),
    )
    await channel.send(embed=embed_done)

    await prompt_reaction_job()
    await confirm_inputs_job()

    embed_done = discord.Embed(
        title="✅ 役職情報の設定が完了しました！",
        description=(
            f"**副団長**: {'はい' if data['job']['vice'] else 'いいえ'}\n"
            f"**広報**: {'はい' if data['job']['publicity'] else 'いいえ'}\n"
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

    member = guild.get_member(user.id)
    if member:

        # ニックネーム変更
        new_nickname = f"{data['name_kanji']}/{data['term']}{data['part']}"
        try:
            await member.edit(nick=new_nickname)
            await channel.send(f"✅ ニックネームを「{new_nickname}」に変更しました")
        except discord.Forbidden:
            await channel.send(
                "⚠️ ニックネームを変更できませんでした。Botに「ニックネームの変更」権限があるか確認してください"
            )

        # ✅ 団員/新入生ロールの付与
        if data.get("is_newcomer"):
            freshman_role = discord.utils.get(guild.roles, name="新入生")
            if freshman_role:
                await member.add_roles(freshman_role)
                await channel.send("🎓 `新入生` ロールを付与しました！")
            else:
                await channel.send("⚠️ `新入生` ロールが見つかりませんでした")
        else:
            group_member = discord.utils.get(guild.roles, name="団員")
            if group_member:
                await member.add_roles(group_member)
                await channel.send("🎓 `団員` ロールを付与しました！")
            else:
                await channel.send("⚠️ `団員` ロールが見つかりませんでした")

        execution_term = read_term_of_execution_from_file()
        if execution_term is None:
            await channel.send("⚠️ term_of_execution.txt が読み込めませんでした。")
            return

        try:
            user_term = int(data["term"])
        except ValueError:
            await channel.send("⚠️ 入力された期が整数ではありません。")
            return

        min_role_term = execution_term - 1
        max_role_term = execution_term + 2

        if user_term <= min_role_term:
            term_role_name = f"{min_role_term}期以上"
        elif user_term <= max_role_term:
            term_role_name = f"{user_term}期"
        else:
            await channel.send(f"⚠️ `{user_term}期` は有効な期ロールの範囲外です。")
            term_role_name = None

        if term_role_name:
            term_role = discord.utils.get(guild.roles, name=term_role_name)
            if term_role:
                await member.add_roles(term_role)
                await channel.send(f"📌 `{term_role.name}` ロールを付与しました！")
            else:
                await channel.send(f"⚠️ `{term_role_name}` ロールが見つかりません")

        # ✅ ← ネストの外に移動：パートロールと性別ロールは常に実行
        part_role_map = {
            "S": ("ソプラノ", "女声"),
            "A": ("アルト", "女声"),
            "T": ("テナー", "男声"),
            "B": ("ベース", "男声"),
        }

        part_role_name, gender_role_name = part_role_map[data["part"]]
        part_role = discord.utils.get(guild.roles, name=part_role_name)
        gender_role = discord.utils.get(guild.roles, name=gender_role_name)

        if part_role:
            await member.add_roles(part_role)
            await channel.send(f"🎵 `{part_role_name}` ロールを付与しました！")
        else:
            await channel.send(f"⚠️ `{part_role_name}` ロールが見つかりませんでした")

        if gender_role:
            await member.add_roles(gender_role)
            await channel.send(f"🎶 `{gender_role_name}` ロールを付与しました！")
        else:
            await channel.send(f"⚠️ `{gender_role_name}` ロールが見つかりませんでした")

        # 〇責ロールの付与
        if data["position"]["executive"]:
            executive_role = discord.utils.get(guild.roles, name="まるせき")
            if executive_role:
                await member.add_roles(executive_role)
                await channel.send("🎩 `まるせき` ロールを付与しました！")
            else:
                await channel.send("⚠️ `まるせき` ロールが見つかりませんでした")

        # 〇技ロールの付与
        if data["position"]["technique"]:
            technique_role = discord.utils.get(guild.roles, name="まるぎ")
            parent_role = discord.utils.get(guild.roles, name="おやまる")
            child_role = discord.utils.get(guild.roles, name="こまる")
            if technique_role:
                await member.add_roles(technique_role)
                await channel.send("🛠️ `まるぎ` ロールを付与しました！")
                if data["term"] == execution_term:
                    await member.add_roles(parent_role)
                    await channel.send("🛠️ `おやまる` ロールを付与しました！")
                else:
                    await member.add_roles(child_role)
                    await channel.send("🛠️ `こまる` ロールを付与しました！")
            else:
                await channel.send("⚠️ `まるぎ` ロールが見つかりませんでした")

        # 演実ロールの付与
        if data["position"]["concert"]:
            concert_role = discord.utils.get(guild.roles, name="えんじつ")
            if concert_role:
                await member.add_roles(concert_role)
                await channel.send("🎼 `えんじつ` ロールを付与しました！")
            else:
                await channel.send("⚠️ `えんじつ` ロールが見つかりませんでした")

        # 第三者ロールの付与
        if data["position"]["third_party"]:
            concert_role = discord.utils.get(guild.roles, name="第三者")
            if concert_role:
                await member.add_roles(concert_role)
                await channel.send("⚖️ `第三者` ロールを付与しました！")
            else:
                await channel.send("⚠️ `第三者` ロールが見つかりませんでした")

        # 副団長ロールの付与
        if data["job"]["vice"]:
            concert_role = discord.utils.get(guild.roles, name="副団長")
            if concert_role:
                await member.add_roles(concert_role)
                await channel.send("🛡️ `副団長` ロールを付与しました！")
            else:
                await channel.send("⚠️ `副団長` ロールが見つかりませんでした")

        # 広報ロールの付与
        if data["job"]["publicity"]:
            concert_role = discord.utils.get(guild.roles, name="広報")
            if concert_role:
                await member.add_roles(concert_role)
                await channel.send("📣 `広報` ロールを付与しました！")
            else:
                await channel.send("⚠️ `広報` ロールが見つかりませんでした")

        await activity_investigation()
        await confirm_activity_investigation()

        embed_done = discord.Embed(
            title="✅ オンステ情報の入力が完了しました！",
            description=(
                f"**副指揮**: {'乗る' if data['stage']['first'] else '乗らない'}\n"
                f"**正指揮**: {'乗る' if data['stage']['second'] else '乗らない'}\n"
                f"**ドイツリート**: {'乗る' if data['stage']['german'] else '乗らない'}"
                f"**髙田曲**: {'乗る' if data['stage']['takata'] else '乗らない'}"
            ),
            color=discord.Color.green(),
        )

        await channel.send(embed=embed_done)

        # 副指揮ロールの付与
        if data["stage"]["first"]:
            first_role = discord.utils.get(guild.roles, name="副指揮")
            if first_role:
                await member.add_roles(first_role)
                await channel.send("🛡️ `副指揮` ロールを付与しました！")
            else:
                await channel.send("⚠️ `副指揮` ロールが見つかりませんでした")

        # 正指揮ロールの付与
        if data["stage"]["second"]:
            second_role = discord.utils.get(guild.roles, name="正指揮")
            if second_role:
                await member.add_roles(second_role)
                await channel.send("🛡️ `正指揮` ロールを付与しました！")
            else:
                await channel.send("⚠️ `正指揮` ロールが見つかりませんでした")

        # 3ステロールの付与
        if data["stage"]["german"]:
            german_role = discord.utils.get(guild.roles, name="ドイツリート")
            if german_role:
                await member.add_roles(german_role)
                await channel.send("🛡️ `ドイツリート` ロールを付与しました！")
            else:
                await channel.send("⚠️ `ドイツリート` ロールが見つかりませんでした")

        # 4ステロールの付与
        if data["stage"]["takata"]:
            takata_role = discord.utils.get(guild.roles, name="髙田曲")
            if takata_role:
                await member.add_roles(takata_role)
                await channel.send("🛡️ `髙田曲` ロールを付与しました！")
            else:
                await channel.send("⚠️ `髙田曲` ロールが見つかりませんでした")
    else:
        await channel.send("⚠️ サーバーメンバーが見つかりませんでした")

    # 保存と完了メッセージ
    user_settings[user.id] = data
    save_user_settings(user_settings)


def save_user_settings(data, filename=PATH_USER_SETTINGS):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def read_guild_id_from_file(
    json_path=PATH_GUILD_JSON, version_path=PATH_SERVER_VERSION
):
    try:
        with open(version_path, "r") as vf:
            version_str = vf.read().strip()
            version = int(version_str)
    except FileNotFoundError:
        print(f"❌ {version_path} が見つかりませんでした")
        return None
    except ValueError:
        print("❌ server_version.txt に無効な整数が含まれています")
        return None

    try:
        with open(json_path, "r") as jf:
            guilds = json.load(jf)
            guild_id = guilds.get(str(version))  # キーは文字列である必要がある
            if guild_id is None:
                print(
                    f"❌ バージョン {version} に対応する guild_id が見つかりませんでした"
                )
                return None
            return int(guild_id)
    except FileNotFoundError:
        print(f"❌ {json_path} が見つかりませんでした")
        return None
    except json.JSONDecodeError:
        print("❌ guilds.json の読み込み中にエラーが発生しました")
        return None


def read_term_of_execution_from_file(filename=PATH_TERM_OF_EXECUTION):
    try:
        with open(filename, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def get_execution_term():
    with open(PATH_TERM_OF_EXECUTION, "r", encoding="utf-8") as f:
        return int(f.read().strip())


def extract_term_from_roles(member):
    for role in member.roles:
        if role.name.endswith("期") and role.name[:-1].isdigit():
            return int(role.name[:-1])
    return None


@bot.tree.command(name="set_server-id", description="サーバーIDを記録します")
async def set_server_id(interaction: discord.Interaction):
    await interaction.response.send_message(
        "🗝️ まず、このサーバーのバージョン番号（整数）を送信してください。"
    )

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        # バージョン番号を受信
        version_msg = await bot.wait_for("message", check=check, timeout=60.0)
        version_key = int(version_msg.content.strip())
    except asyncio.TimeoutError:
        await interaction.followup.send(
            "⚠️ 時間切れです。もう一度 `/set_server-id` を実行してください。",
            ephemeral=True,
        )
        return
    except ValueError:
        await interaction.followup.send(
            "❌ 整数のバージョン番号を入力してください。", ephemeral=True
        )
        return

    await interaction.followup.send("📥 次に、サーバーID（数値）を送信してください。")

    try:
        # サーバーIDを受信
        id_msg = await bot.wait_for("message", check=check, timeout=60.0)
        guild_id = int(id_msg.content.strip())
    except asyncio.TimeoutError:
        await interaction.followup.send(
            "⚠️ 時間切れです。もう一度 `/set_server-id` を実行してください。",
            ephemeral=True,
        )
        return
    except ValueError:
        await interaction.followup.send(
            "❌ 数値のサーバーIDを入力してください。", ephemeral=True
        )
        return

    # guilds.json 読み込み
    file_path = os.path.join(os.path.dirname(__file__), PATH_GUILD_JSON)
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                guilds = json.load(f)
        except json.JSONDecodeError:
            await interaction.followup.send(
                "❌ JSONファイルの読み込みに失敗しました。", ephemeral=True
            )
            return
    else:
        guilds = {}

    # 上書きまたは追加
    guilds[str(version_key)] = guild_id

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(guilds, f, indent=4, ensure_ascii=False)
    except Exception as e:
        await interaction.followup.send(f"❌ 書き込みエラー: {e}", ephemeral=True)
        return

    await interaction.followup.send(
        f"✅ サーバーID `{guild_id}` をバージョン `{version_key}` に保存しました。"
    )


@bot.tree.command(
    name="set_term-of-execution",
    description="執行代を記録します",
)
async def set_term_of_execution(interaction: discord.Interaction):
    await interaction.response.send_message(
        "執行代の期を数字のみでこのチャンネルで送ってください。"
    )

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for(
            "message", check=check, timeout=60.0
        )  # 60秒のタイムアウト
    except asyncio.TimeoutError:
        await interaction.followup.send(
            "⚠️ 時間切れです。もう一度 `/set_term-of-execution` を実行してください。"
        )
        return

    if not msg.content.isdigit():
        await interaction.followup.send(
            "⚠️ 入力は数字のみでお願いします。もう一度 `/set_term-of-execution` を実行してください。"
        )
        return

    file_path = os.path.join(os.path.dirname(__file__), PATH_TERM_OF_EXECUTION)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{msg.content}\n")

    await interaction.followup.send("✅ 執行代を書き込みました。")


@bot.tree.command(
    name="set_admin-server-version",
    description="サーバのバージョンを記録します",
)
async def set_server_version(interaction: discord.Interaction):
    await interaction.response.send_message(
        "使用するサーバの年度を数字のみでこのチャンネルで送ってください。"
    )

    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    try:
        msg = await bot.wait_for("message", check=check, timeout=60.0)
    except asyncio.TimeoutError:
        await interaction.followup.send(
            "⚠️ 時間切れです。もう一度 `/set_server_version` を実行してください。"
        )
        return

    if not msg.content.isdigit():
        await interaction.followup.send(
            "⚠️ 入力は数字のみでお願いします。もう一度 `/set_server_version` を実行してください。"
        )
        return

    # ファイルパスを安全な場所に設定
    file_path = os.path.join(os.path.dirname(__file__), PATH_SERVER_VERSION)

    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"{msg.content}\n")
        await interaction.followup.send("✅ サーバのバージョンを書き込みました。")
    except PermissionError:
        await interaction.followup.send(
            "⚠️ ファイルへの書き込みに失敗しました。パーミッションを確認してください。"
        )


@bot.tree.command(
    name="set_my-status", description="ギルドオーナーの初期設定を行います"
)
async def set_my_status(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        embed = discord.Embed(
            title="🚫 権限がありません",
            description="このコマンドはサーバーの作成者（オーナー）のみが実行できます。",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    else:
        # チャンネルでセットアップ案内を送信し、DMでセットアップ開始
        await interaction.response.send_message("DMを確認してください")
        try:
            # member情報を取得
            member = interaction.user
            # DMで setup を実行
            dm_channel = await member.create_dm()
            await dm_channel.send(
                "👋 はじめまして！初期設定を行います、必要事項を入力してください。"
            )
            await run_setup_flow(member, dm_channel)
        except Exception as e:
            print(f"⚠️ 初期設定送信中にエラー: {e}")


@bot.tree.command(
    name="help_initialization", description="サーバの初期設定のヘルプを表示します"
)
async def set_my_status(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        embed = discord.Embed(
            title="🚫 権限がありません",
            description="このコマンドはサーバーの作成者（オーナー）のみが実行できます。",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    else:
        # チャンネルでセットアップ案内を送信し、DMでセットアップ開始
        await interaction.response.send_message("/set_server-id を実行してください")
        await interaction.response.send_message(
            "/set_term-of-execution を実行してください"
        )
        await interaction.response.send_message("/update_bot-id を実行してください")
        await interaction.response.send_message(
            "/update_reactions-id を実行してください"
        )
        await interaction.response.send_message(
            "これらのコマンドを実行することで、サーバーの初期設定が完了します。"
        )
        await interaction.response.send_message(
            "その後、/set_my-status を実行して、自分の初期設定を行ってください"
        )


bot.run(config.DISCORD_TOKEN)
