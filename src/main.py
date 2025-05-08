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
                    f"**🎼 演実**: {'はい' if data['position']['concert'] else 'いいえ'}\n\n"
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
        ),
        color=discord.Color.green(),
    )
    await channel.send(embed=embed_done)

    # 保存と完了メッセージ
    user_settings[user.id] = data
    save_user_settings(user_settings)

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

        # ニックネーム変更
        new_nickname = f"{data['name_kanji']}/{data['term']}{data['part']}"
        try:
            await member.edit(nick=new_nickname)
            await channel.send(f"✅ ニックネームを「{new_nickname}」に変更しました")
        except discord.Forbidden:
            await channel.send(
                "⚠️ ニックネームを変更できませんでした。Botに「ニックネームの変更」権限があるか確認してください"
            )

        await member.add_roles(role)
        await channel.send(f"🎉 `{role.name}` ロールが付与されました！")

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
                await channel.send(f"📌 `{term_role.name}` ロールを付与しました")
            else:
                await channel.send(f"⚠️ `{term_role_name}` ロールが見つかりません")

        # ✅ 新入生ロールの付与（data["is_newcomer"] が True の場合）
        if data.get("is_newcomer"):
            freshman_role = discord.utils.get(guild.roles, name="新入生")
            if freshman_role:
                await member.add_roles(freshman_role)
                await channel.send("🎓 `新入生` ロールを付与しました！")
            else:
                await channel.send("⚠️ `新入生` ロールが見つかりませんでした")

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
            await channel.send(f"🎵 `{part_role_name}` ロールを付与しました")
        else:
            await channel.send(f"⚠️ `{part_role_name}` ロールが見つかりませんでした")

        if gender_role:
            await member.add_roles(gender_role)
            await channel.send(f"🧑 `{gender_role_name}` ロールを付与しました")
        else:
            await channel.send(f"⚠️ `{gender_role_name}` ロールが見つかりませんでした")

        # ✅ 〇責ロールの付与
        if data["position"]["executive"]:
            executive_role = discord.utils.get(guild.roles, name="まるせき")
            if executive_role:
                await member.add_roles(executive_role)
                await channel.send("🎩 `まるせき` ロールを付与しました！")
            else:
                await channel.send("⚠️ `まるせき` ロールが見つかりませんでした")

        # ✅ 〇技ロールの付与
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

        # ✅ 演実ロールの付与
        if data["position"]["concert"]:
            concert_role = discord.utils.get(guild.roles, name="えんじつ")
            if concert_role:
                await member.add_roles(concert_role)
                await channel.send("🎼 `えんじつ` ロールを付与しました！")
            else:
                await channel.send("⚠️ `えんじつ` ロールが見つかりませんでした")

    else:
        await channel.send("⚠️ サーバーメンバーが見つかりませんでした")


def save_user_settings(data, filename="./src/user_settings.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def read_guild_id_from_file(filename="src/guild_id.txt"):
    try:
        with open(filename, "r") as f:
            guild_id = f.read().strip()
            return int(guild_id)  # ファイルから読み込んだIDを整数として返す
    except FileNotFoundError:
        print(f"❌ {filename} が見つかりませんでした")
        return None
    except ValueError:
        print("❌ guild_id.txt に無効なIDが含まれています")
        return None


def read_term_of_execution_from_file(filename="src/term_of_execution.txt"):
    try:
        with open(filename, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def get_execution_term():
    with open("term_of_execution.txt", "r", encoding="utf-8") as f:
        return int(f.read().strip())


def extract_term_from_roles(member):
    for role in member.roles:
        if role.name.endswith("期") and role.name[:-1].isdigit():
            return int(role.name[:-1])
    return None


bot.run(config.DISCORD_TOKEN)
