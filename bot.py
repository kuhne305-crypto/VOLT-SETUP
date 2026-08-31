"""
VOLT SETUP
==========
Baut den kompletten VOLT-Server auf, resettet ihn bei Bedarf komplett neu
(/setup) und bietet schnelle Add-Commands für den laufenden Betrieb, ohne
dass man jedes Mal alles neu aufsetzen muss. Außerdem: das Verify-System
(gehört hierher, weil dieser Bot den Verify-Kanal überhaupt erst anlegt).

Braucht auf dem Server praktisch "Administrator", damit er Kanäle/Rollen
uneingeschränkt anlegen, umbenennen und löschen kann.

Einrichtung:
1. pip install -r requirements.txt
2. .env.example -> .env kopieren und ausfüllen
3. python bot.py
"""

import os
import logging

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import branding
from branding import VOLT_RED

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
branding.quiet_discord_logs()
log = logging.getLogger("volt-setup")

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID", "0") or 0)
STAFF_ROLE_NAMES = [n.strip() for n in os.getenv("STAFF_ROLE_NAMES", "Admin,Moderator,Supporter").split(",") if n.strip()]
HONEYPOT_CHANNEL_NAME = os.getenv("HONEYPOT_CHANNEL_NAME", "nicht-schreiben")

intents = discord.Intents.default()
# Kein "members"-Intent nötig: VOLT SETUP legt nur Rollen/Kanäle an und
# verarbeitet den Verify-Button über interaction.user (kommt schon als
# vollständiges Member-Objekt mit) - das braucht keinen privilegierten Intent
# im Discord Developer Portal.


class VerifyView(discord.ui.View):
    def __init__(self, role_name: str = "Verified"):
        super().__init__(timeout=None)
        self.role_name = role_name

    @discord.ui.button(label="Verifizieren", style=discord.ButtonStyle.success, emoji="✅", custom_id="volt_verify_button")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=self.role_name)
        if role is None:
            role = await interaction.guild.create_role(name=self.role_name, reason="Verify-System")
        if role in interaction.user.roles:
            return await interaction.response.send_message("Du bist bereits verifiziert. ✅", ephemeral=True)
        await interaction.user.add_roles(role, reason="Verify-Button")
        await interaction.response.send_message("✅ Du wurdest erfolgreich verifiziert!", ephemeral=True)


class VoltSetup(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!volt-setup-", intents=intents)

    async def setup_hook(self):
        self.add_view(VerifyView())
        if GUILD_ID:
            guild_obj = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
        else:
            await self.tree.sync()


bot = VoltSetup()


def is_admin():
    return app_commands.checks.has_permissions(administrator=True)


@bot.event
async def on_ready():
    log.info("VOLT SETUP eingeloggt als %s", bot.user)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="über die Serverstruktur ⚡"))


async def ensure_log_channel(guild: discord.Guild) -> discord.TextChannel:
    channel = discord.utils.get(guild.text_channels, name="admin-logs")
    if channel is None:
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
        channel = await guild.create_text_channel("admin-logs", overwrites=overwrites, reason="Setup: Log-Kanal")
    return channel


# ---------------------------------------------------------------------------
# Server-Struktur
#
#   📌 INFOS          -> ankuendigungen, server-status, bewertungen, kosten
#   👋 WILLKOMMEN     -> willkommen, verify, nicht-schreiben (Honeypot-Falle)
#   🛒 SHOP           -> preisliste, bestellen
#   🎫 TICKETS        -> ticket-logs   (Ticket-Kanäle legt VOLT TICKETS selbst an)
#   🛠️ TEAM-INTERN    -> admin-logs, team-chat   (nur Staff sichtbar)
# ---------------------------------------------------------------------------

async def wipe_server(guild: discord.Guild):
    for channel in list(guild.channels):
        try:
            await channel.delete(reason="VOLT /setup: kompletter Neuaufbau")
        except discord.HTTPException:
            log.warning("Konnte Kanal %s nicht löschen", channel.name)
    for role in list(guild.roles):
        if role.is_default() or role.managed:
            continue
        try:
            await role.delete(reason="VOLT /setup: kompletter Neuaufbau")
        except discord.HTTPException:
            log.warning("Konnte Rolle %s nicht löschen", role.name)


async def build_server_structure(guild: discord.Guild) -> discord.TextChannel:
    role_names = ["Admin", "Moderator", "Supporter", "Kunde", "Verified"]
    roles = {}
    for name in role_names:
        existing = discord.utils.get(guild.roles, name=name)
        roles[name] = existing or await guild.create_role(name=name, reason="VOLT Setup")

    staff_roles = [roles["Admin"], roles["Moderator"], roles["Supporter"]]
    staff_only_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        **{r: discord.PermissionOverwrite(view_channel=True, send_messages=True) for r in staff_roles},
    }

    log_channel = await ensure_log_channel(guild)
    await log_channel.edit(overwrites=staff_only_overwrites)

    info_cat = discord.utils.get(guild.categories, name="📌 INFOS") or await guild.create_category("📌 INFOS")
    welcome_cat = discord.utils.get(guild.categories, name="👋 WILLKOMMEN") or await guild.create_category("👋 WILLKOMMEN")
    shop_cat = discord.utils.get(guild.categories, name="🛒 SHOP") or await guild.create_category("🛒 SHOP")
    ticket_cat = discord.utils.get(guild.categories, name="🎫 TICKETS") or await guild.create_category("🎫 TICKETS")
    team_cat = discord.utils.get(guild.categories, name="🛠️ TEAM-INTERN") or await guild.create_category("🛠️ TEAM-INTERN", overwrites=staff_only_overwrites)

    async def ensure_channel(name, category, overwrites=None, topic=None):
        existing = discord.utils.get(guild.text_channels, name=name)
        if existing:
            return existing
        return await guild.create_text_channel(name, category=category, overwrites=overwrites, topic=topic)

    await ensure_channel("ankuendigungen", info_cat)
    await ensure_channel("server-status", info_cat)
    await ensure_channel("bewertungen", info_cat)
    await ensure_channel("kosten-übersicht", info_cat)

    welcome_channel = await ensure_channel("willkommen", welcome_cat)
    verify_channel = await ensure_channel("verify", welcome_cat)

    # Honeypot-Falle: sichtbar & beschreibbar für alle, aber wer hier
    # irgendetwas postet, wird von VOLT MOD sofort gekickt (Spam-/Scam-Bot-Schutz).
    honeypot_overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        **{r: discord.PermissionOverwrite(view_channel=True, send_messages=False) for r in staff_roles},
    }
    await ensure_channel(
        HONEYPOT_CHANNEL_NAME,
        welcome_cat,
        overwrites=honeypot_overwrites,
        topic="⚠️ NICHT SCHREIBEN! Wer hier irgendetwas postet, wird automatisch gekickt (Bot-/Spam-Schutz).",
    )

    await ensure_channel("preisliste", shop_cat)
    await ensure_channel("bestellen", shop_cat)

    await ensure_channel("ticket-logs", ticket_cat, overwrites=staff_only_overwrites)
    await ensure_channel("team-chat", team_cat, overwrites=staff_only_overwrites)

    if welcome_channel.last_message_id is None:
        embed = discord.Embed(
            title="⚡ Willkommen bei VOLT",
            description="Discord Solutions - Server Protection & Full Control.\nSchau bei `#verify` vorbei, um freigeschaltet zu werden.",
            color=VOLT_RED,
        )
        embed, file = branding.with_banner(embed, branding.MAIN_BANNER, branding.MAIN_FOOTER)
        await welcome_channel.send(embed=embed, file=file)

    if verify_channel.last_message_id is None:
        embed = discord.Embed(
            title="✅ Verifizierung",
            description="Klicke auf den Button, um dich zu verifizieren und Zugriff auf den Server zu erhalten.",
            color=VOLT_RED,
        )
        embed, file = branding.with_icon_thumbnail(embed)
        await verify_channel.send(embed=embed, file=file, view=VerifyView("Verified"))

    return log_channel


class WipeConfirmView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=60)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Nur die Person, die `/setup` ausgeführt hat, kann das bestätigen.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Ja, ALLES löschen & neu aufbauen", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content="⏳ Server wird geleert und neu aufgebaut - das kann je nach Größe etwas dauern...",
            embed=None,
            view=self,
        )
        self.stop()

        guild = interaction.guild
        await wipe_server(guild)
        log_channel = await build_server_structure(guild)

        embed = discord.Embed(
            title="✅ VOLT Server-Neuaufbau abgeschlossen",
            description=(
                "Alle vorherigen Kanäle & Rollen wurden gelöscht, die komplette "
                "VOLT-Struktur wurde neu erstellt.\n"
                "Nutze jetzt **VOLT TICKETS** mit `/setup-tickets` im Kanal `#bestellen`."
            ),
            color=VOLT_RED,
        )
        embed, file = branding.with_banner(embed, branding.MAIN_BANNER, branding.MAIN_FOOTER)
        await log_channel.send(embed=embed, file=file)
        await interaction.followup.send("✅ Fertig - Server wurde komplett neu aufgebaut. Details im `#admin-logs` Kanal.", ephemeral=True)

    @discord.ui.button(label="Abbrechen", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="Abgebrochen. Es wurde nichts verändert.", embed=None, view=self)
        self.stop()


@bot.tree.command(name="setup", description="[Admin] ⚠️ Löscht ALLE Kanäle & Rollen und baut den VOLT-Server komplett neu auf")
@is_admin()
async def setup_cmd(interaction: discord.Interaction):
    guild = interaction.guild
    warning = discord.Embed(
        title="⚠️ Kompletter Server-Neuaufbau",
        description=(
            f"Das löscht **wirklich ALLE {len(guild.channels)} Kanäle/Kategorien** "
            f"und **ALLE löschbaren Rollen** auf **{guild.name}** unwiderruflich - "
            "danach wird die komplette VOLT-Struktur neu erstellt.\n\n"
            "**Das kann NICHT rückgängig gemacht werden.** Bist du sicher?"
        ),
        color=discord.Color.red(),
    )
    await interaction.response.send_message(embed=warning, view=WipeConfirmView(interaction.user.id), ephemeral=True)


# ------------------------- Schnelle Add-Commands -------------------------

@bot.tree.command(name="add-category", description="[Admin] Legt schnell eine neue Kategorie an")
@is_admin()
@app_commands.describe(name="Name der Kategorie (Emoji davor ist optional)", staff_only="Nur für Admin/Moderator/Supporter sichtbar?")
async def add_category(interaction: discord.Interaction, name: str, staff_only: bool = False):
    guild = interaction.guild
    overwrites = None
    if staff_only:
        staff_roles = [discord.utils.get(guild.roles, name=n) for n in STAFF_ROLE_NAMES]
        staff_roles = [r for r in staff_roles if r]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            **{r: discord.PermissionOverwrite(view_channel=True, send_messages=True) for r in staff_roles},
        }
    category = await guild.create_category(name, overwrites=overwrites, reason=f"/add-category von {interaction.user}")
    await interaction.response.send_message(f"✅ Kategorie **{category.name}** erstellt{' (nur Staff sichtbar)' if staff_only else ''}.", ephemeral=True)


async def category_autocomplete(interaction: discord.Interaction, current: str):
    cats = interaction.guild.categories if interaction.guild else []
    return [app_commands.Choice(name=c.name, value=c.name) for c in cats if current.lower() in c.name.lower()][:25]


@bot.tree.command(name="add-channel", description="[Admin] Legt schnell einen neuen Text-Kanal an")
@is_admin()
@app_commands.describe(name="Name des Kanals", kategorie="In welche Kategorie?", staff_only="Nur für Admin/Moderator/Supporter sichtbar?")
@app_commands.autocomplete(kategorie=category_autocomplete)
async def add_channel(interaction: discord.Interaction, name: str, kategorie: str = None, staff_only: bool = False):
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name=kategorie) if kategorie else None
    overwrites = None
    if staff_only:
        staff_roles = [discord.utils.get(guild.roles, name=n) for n in STAFF_ROLE_NAMES]
        staff_roles = [r for r in staff_roles if r]
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            **{r: discord.PermissionOverwrite(view_channel=True, send_messages=True) for r in staff_roles},
        }
    channel = await guild.create_text_channel(name, category=category, overwrites=overwrites, reason=f"/add-channel von {interaction.user}")
    await interaction.response.send_message(f"✅ Kanal {channel.mention} erstellt{' (nur Staff sichtbar)' if staff_only else ''}.", ephemeral=True)


@bot.tree.command(name="add-role", description="[Admin] Legt schnell eine neue Rolle an")
@is_admin()
async def add_role(interaction: discord.Interaction, name: str):
    role = await interaction.guild.create_role(name=name, reason=f"/add-role von {interaction.user}")
    await interaction.response.send_message(f"✅ Rolle {role.mention} erstellt.", ephemeral=True)


@bot.tree.command(name="post-verify", description="[Admin] Postet das Verify-Panel erneut in diesen Kanal")
@is_admin()
async def post_verify(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✅ Verifizierung",
        description="Klicke auf den Button, um dich zu verifizieren und Zugriff auf den Server zu erhalten.",
        color=VOLT_RED,
    )
    embed, file = branding.with_icon_thumbnail(embed)
    await interaction.channel.send(embed=embed, file=file, view=VerifyView("Verified"))
    await interaction.response.send_message("✅ Verify-Panel gepostet.", ephemeral=True)


@setup_cmd.error
@add_category.error
@add_channel.error
@add_role.error
@post_verify.error
async def on_admin_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Dieser Command ist nur für Administratoren.", ephemeral=True)
    else:
        log.exception("Fehler in VOLT SETUP-Command", exc_info=error)
        msg = "❌ Es ist ein Fehler aufgetreten."
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("DISCORD_TOKEN fehlt in der .env Datei!")
    bot.run(TOKEN)
