"""
VOLT - zentrales Branding.

Farben & Assets an einer Stelle, damit alle drei Bots (Setup/Mod/Tickets)
konsistent aussehen. Diese Datei liegt identisch in jedem der drei
Bot-Ordner (volt-setup/, volt-mod/, volt-tickets/), da jeder Ordner ein
eigenständiges Railway-Deployment ist.
"""

import os
import discord

VOLT_RED = discord.Color.from_rgb(224, 17, 17)
VOLT_BLACK = discord.Color.from_rgb(10, 10, 10)

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

ICON = os.path.join(ASSETS_DIR, "volt_icon.png")
MAIN_BANNER = os.path.join(ASSETS_DIR, "volt_main_banner.png")        # nur in volt-setup vorhanden
ADMIN_BANNER = os.path.join(ASSETS_DIR, "volt_admin_banner.png")      # nur in volt-mod vorhanden
TICKETS_BANNER = os.path.join(ASSETS_DIR, "volt_tickets_banner.png")  # nur in volt-tickets vorhanden

ADMIN_FOOTER = "VOLT MOD • Server Protection. Full Control."
TICKETS_FOOTER = "VOLT TICKETS • Tickets. Orders. Done right."
MAIN_FOOTER = "VOLT Discord Solutions"

# ---------------------------------------------------------------------------
# Rollen-Farbschema
#
# Reihenfolge = Hierarchie (oben = höchste Rolle). Jede Rolle bekommt eine
# eigene, klar unterscheidbare Farbe + ein Emoji-Präfix, damit auf einen
# Blick erkennbar ist "wer wie wo" steht. Der volle Rollenname ist
# f"{emoji} {basisname}" (z.B. "👑 Admin").
#
# WICHTIG für VOLT MOD (separates Repo): falls dort Rollen per exaktem
# Namensvergleich gesucht werden ("Admin" statt "👑 Admin"), muss die
# Suche dort auf "endet mit Basisname" umgestellt werden - siehe
# resolve_role_by_base() unten, das kann 1:1 übernommen werden.
# ---------------------------------------------------------------------------
ROLE_CONFIG = [
    # (Basisname,   Emoji, Farbe (RGB),                 hoist=separat in Mitgliederliste anzeigen)
    ("Admin",       "👑",  discord.Color.from_rgb(230, 30, 30),   True),
    ("Moderator",   "🛡️", discord.Color.from_rgb(255, 140, 26),  True),
    ("Supporter",   "🎧",  discord.Color.from_rgb(255, 205, 60),  True),
    ("Kunde",       "🛍️", discord.Color.from_rgb(66, 165, 245),  False),
    ("Verified",    "✅",  discord.Color.from_rgb(87, 242, 135),  False),
]


def full_role_name(base_name: str) -> str:
    for base, emoji, _color, _hoist in ROLE_CONFIG:
        if base == base_name:
            return f"{emoji} {base}"
    return base_name


def resolve_role_by_base(guild: discord.Guild, base_name: str):
    """Findet eine Rolle egal ob sie noch den alten reinen Namen ("Admin")
    oder den neuen Emoji-Namen ("👑 Admin") trägt. So bricht nichts, wenn
    Rollen manuell umbenannt wurden oder noch aus einem alten Setup stammen."""
    exact = discord.utils.get(guild.roles, name=base_name)
    if exact:
        return exact
    return discord.utils.find(
        lambda r: r.name == base_name or r.name.rsplit(" ", 1)[-1] == base_name,
        guild.roles,
    )


def channel_name(emoji: str, name: str) -> str:
    """Einheitliches, gut erkennbares Channel-Namensschema: Emoji + Trenner + Name."""
    return f"{emoji}│{name}"


def category_name(emoji: str, label: str) -> str:
    """Kategorie-Name im Trennstrich-Look (z.B. '───── 📌 INFOS ─────'), damit
    die Kategorien im Kanal-Menü klar abgesetzt und nicht 'nackt' wirken."""
    return f"───── {emoji} {label} ─────"


# ---------------------------------------------------------------------------
# SERVERINFO - gesperrte Voice-Kanäle, deren Name reine Live-Statistik ist
# (niemand kann joinen, sie dienen nur als Anzeige - wie bei bjarne.work).
# Discord erlaubt max. 2 Umbenennungen pro Kanal alle 10 Minuten, deshalb
# aktualisiert der Bot diese Kanäle nur alle 10 Minuten (siehe bot.py).
# ---------------------------------------------------------------------------
SERVERINFO_CATEGORY = category_name("📊", "SERVERINFO")
MEMBERS_LABEL = "👥 Mitglieder"
STATUS_LABEL = "🟢 Status"
RATING_LABEL = "⭐ Bewertungen"
RATING_PLACEHOLDER = "bald verfügbar"


def banner_file(path: str) -> discord.File:
    return discord.File(path, filename=os.path.basename(path))


def with_banner(embed: discord.Embed, path: str, footer: str | None = None) -> tuple[discord.Embed, discord.File]:
    file = banner_file(path)
    embed.set_image(url=f"attachment://{os.path.basename(path)}")
    if footer and not embed.footer:
        embed.set_footer(text=footer)
    return embed, file


def with_icon_thumbnail(embed: discord.Embed) -> tuple[discord.Embed, discord.File]:
    file = banner_file(ICON)
    embed.set_thumbnail(url=f"attachment://{os.path.basename(ICON)}")
    return embed, file


def quiet_discord_logs():
    """Reduziert das Grundrauschen von discord.py in der Railway-Konsole -
    nur eigene INFO-Logs bleiben sichtbar, discord.py selbst nur WARNING+."""
    import logging
    logging.getLogger("discord").setLevel(logging.WARNING)
    logging.getLogger("discord.http").setLevel(logging.WARNING)
    logging.getLogger("discord.gateway").setLevel(logging.WARNING)
