import os
import uuid
import asyncio
import discord
from discord.ext import commands
from aiohttp import web

# Настройки сервера Vakoto
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = 1570943974854623404
PORT = int(os.getenv("PORT", 10000))

# Хранилище статусов заявок в памяти
applications = {}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


class ApplicationView(discord.ui.View):
    def __init__(self, app_id: str, nick: str, discord_tag: str):
        super().__init__(timeout=None)
        self.app_id = app_id
        self.nick = nick
        self.discord_tag = discord_tag

    @discord.ui.button(label="✅ Принять", style=discord.ButtonStyle.success, custom_id="approve_btn")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        applications[self.app_id] = "approved"
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.add_field(name="Статус", value=f"✅ Принята ({interaction.user.mention})", inline=False)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="❌ Отклонить", style=discord.ButtonStyle.danger, custom_id="reject_btn")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        applications[self.app_id] = "rejected"
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.add_field(name="Статус", value=f"❌ Отклонена ({interaction.user.mention})", inline=False)
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(embed=embed, view=self)


# --- Веб-сервер (Aiohttp) ---

async def handle_index(request):
    return web.FileResponse("index.html")


async def handle_submit(request):
    try:
        data = await request.json()
        nick = str(data.get("nick", "")).strip()
        discord_tag = str(data.get("discord", "")).strip()
        age = str(data.get("age", "")).strip()
        about = str(data.get("about", "")).strip()

        if not nick or not discord_tag:
            return web.json_response({"status": "error", "message": "Заполните все поля"}, status=400)

        app_id = str(uuid.uuid4())
        applications[app_id] = "pending"

        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            channel = await bot.fetch_channel(CHANNEL_ID)

        embed = discord.Embed(
            title="❄️ Новая заявка на сервер Vakoto",
            color=discord.Color.blue()
        )
        embed.add_field(name="🎮 Ник в Minecraft", value=f"`{nick}`", inline=True)
        embed.add_field(name="💬 Discord", value=f"`{discord_tag}`", inline=True)
        embed.add_field(name="🎂 Возраст", value=f"`{age}`", inline=True)
        embed.add_field(name="📝 О себе и планах", value=about or "Не указано", inline=False)
        embed.set_footer(text=f"ID заявки: {app_id}")

        view = ApplicationView(app_id, nick, discord_tag)
        await channel.send(embed=embed, view=view)

        return web.json_response({"status": "ok", "app_id": app_id})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)


async def handle_status(request):
    app_id = request.query.get("id", "")
    status = applications.get(app_id, "not_found")
    return web.json_response({"status": status})


@bot.event
async def on_ready():
    print(f"Бот Vakoto запущен как {bot.user}")


async def main():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_post("/submit", handle_submit)
    app.router.add_get("/status", handle_status)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"Веб-сервер запущен на порту {PORT}")

    await bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
