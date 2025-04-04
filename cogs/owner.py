import asyncio
import os
from typing import Optional

import nextcord
from nextcord.ext import commands

from internal_tools.configuration import CONFIG, JsonDictSaver
from internal_tools.discord import *


class QandACollector(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            "Enter Q and A data below.",
            timeout=1800,
        )

        self.question_input = nextcord.ui.TextInput(
            "Question", style=nextcord.TextInputStyle.paragraph, min_length=10
        )
        self.add_item(self.question_input)

        self.answer_input = nextcord.ui.TextInput(
            "Answer", style=nextcord.TextInputStyle.paragraph, min_length=10
        )
        self.add_item(self.answer_input)

    async def callback(self, interaction: nextcord.Interaction):
        self.question = self.question_input.value
        self.answer = self.answer_input.value

        await interaction.send(
            "Info collected. This might take a Moment...", ephemeral=True
        )

        self.stop()


class Owner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.rejected_servers = JsonDictSaver(
            "rejected_servers", default={"SERVER_IDS": []}
        )

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        """
        You need to be the Owner of the Bot to use this.
        """
        if interaction.user == None:
            return False

        return await self.bot.is_owner(interaction.user)  # type: ignore

    @nextcord.slash_command(
        name="play",
        description="Sets a 'playing' Status",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def play_status(
        self,
        interaction: nextcord.Interaction,
        status: str = nextcord.SlashOption(
            name="status", description="The status text to use", required=True
        ),
    ):
        """
        Sets a 'playing' Status
        """
        await self.bot.change_presence(activity=nextcord.Game(status))
        await interaction.send("Done", ephemeral=True)

    @nextcord.slash_command(
        name="watch",
        description="Sets a 'watching' Status",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def watch_status(
        self,
        interaction: nextcord.Interaction,
        status: str = nextcord.SlashOption(
            name="status", description="The status text to use", required=True
        ),
    ):
        """
        Sets a 'watching' Status
        """
        await self.bot.change_presence(
            activity=nextcord.Activity(type=nextcord.ActivityType.watching, name=status)
        )
        await interaction.send("Done", ephemeral=True)

    @nextcord.slash_command(
        name="listen",
        description="Sets a 'listening' Status",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def listen_status(
        self,
        interaction: nextcord.Interaction,
        status: str = nextcord.SlashOption(
            name="status", description="The status text to use", required=True
        ),
    ):
        """
        Sets a 'listening' Status
        """
        await self.bot.change_presence(
            activity=nextcord.Activity(
                type=nextcord.ActivityType.listening, name=status
            )
        )
        await interaction.send("Done", ephemeral=True)

    async def cog_autocomplete(self, interaction: nextcord.Interaction, cog: str):
        all_cogs = [
            x.name.replace(".py", "")
            for x in os.scandir("cogs/")
            if x.is_file() and not x.name.startswith("_")
        ]

        if cog:
            await interaction.response.send_autocomplete(
                [x for x in all_cogs if x.startswith(cog)]
            )
        else:
            await interaction.response.send_autocomplete(all_cogs)

    @nextcord.slash_command(
        name="load",
        description="Loads a Cog",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def load_cog(
        self,
        interaction: nextcord.Interaction,
        cog: str = nextcord.SlashOption(
            name="cog",
            description="Name of the Cog you want to load",
            required=True,
            autocomplete_callback=cog_autocomplete,
        ),
    ):
        """
        Loads a Module.
        """
        try:
            self.bot.load_extension("cogs." + cog)
        except Exception as e:
            await interaction.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await interaction.send("Done", ephemeral=True)

    @nextcord.slash_command(
        name="unload",
        description="Loads a Cog",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def unload_cog(
        self,
        interaction: nextcord.Interaction,
        cog: str = nextcord.SlashOption(
            name="cog",
            description="Name of the Cog you want to unload",
            required=True,
            autocomplete_callback=cog_autocomplete,
        ),
    ):
        """
        Unloads a Module.
        """
        try:
            self.bot.unload_extension("cogs." + cog)
        except Exception as e:
            await interaction.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await interaction.send("Done", ephemeral=True)

    @nextcord.slash_command(
        name="reload",
        description="Reloads a Cog",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def reload_cog(
        self,
        interaction: nextcord.Interaction,
        cog: str = nextcord.SlashOption(
            name="cog",
            description="Name of the Cog you want to reload",
            required=True,
            autocomplete_callback=cog_autocomplete,
        ),
    ):
        """
        Reloads a Module.
        """
        try:
            self.bot.unload_extension("cogs." + cog)
            self.bot.load_extension("cogs." + cog)
        except Exception as e:
            await interaction.send(f"**`ERROR:`** {type(e).__name__} - {e}")
        else:
            await interaction.send("Done", ephemeral=True)

    @nextcord.slash_command(
        "q-and-a",
        description="Create a Q and A Message here.",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def q_and_a(
        self,
        interaction: nextcord.Interaction,
        screenshot: Optional[nextcord.Attachment] = None,
    ):
        if not isinstance(interaction.channel, nextcord.abc.Messageable):
            await interaction.send(
                "Cant do that here"
            )  # cant do this either, but its not possible to get here anyways.. unless it shouldnt be
            return

        qanda_collector = QandACollector()
        await interaction.response.send_modal(qanda_collector)
        if not interaction.response.is_done():
            await interaction.send("Collecting Infos.", ephemeral=True)

        while not qanda_collector.is_finished():
            await asyncio.sleep(1)

        await interaction.channel.send(
            embed=fancy_embed(
                f"Q: {qanda_collector.question}",
                f"**A:** {qanda_collector.answer}",
                image_url=screenshot.url if screenshot else None,
            )
        )

    @nextcord.slash_command(
        "stats",
        description="Show Stats of the Bot.",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def stats(
        self,
        interaction: nextcord.Interaction,
    ):
        preventive_ban_cog = self.bot.get_cog("PreventiveBan")
        preventive_ban_guilds = preventive_ban_cog.preventive_ban_guilds  # type: ignore
        preventively_baned_users = preventive_ban_cog.preventively_baned_users  # type: ignore
        preventive_ban_records = preventive_ban_cog.preventive_ban_records  # type: ignore

        illegal_name_manager = self.bot.get_cog("Impersonation").ILM  # type: ignore

        impersonation_protection_servers = []
        for guild_id, config in illegal_name_manager.items():
            for sublist in config.values():
                if len(sublist) != 0:
                    break
            else:
                continue

            impersonation_protection_servers.append(guild_id)

        fields = {
            "Servers": len(self.bot.guilds),
            "Preventive Ban Servers": len(
                [
                    i
                    for i in preventive_ban_guilds["VERIFIED_GUILD_IDS"]
                    if preventive_ban_guilds["VERIFIED_GUILD_IDS"][i]["ENABLED"]
                ]
            ),
            "Preventively banned Users": len(preventively_baned_users),
            "Preventive Ban reported Users": len(preventive_ban_records),
            "Preventive Ban reports": len(
                [
                    item
                    for sublist in preventive_ban_records.values()
                    for item in sublist
                ]
            ),
            "Impersonation Protection Servers": len(impersonation_protection_servers),
        }

        await interaction.send(
            embed=fancy_embed(
                "Stats",
                fields=fields,
                inline=False,
                thumbnail_url=self.bot.user.avatar.url,  # type: ignore
            )
        )

    @nextcord.slash_command(
        "refuse-service-to-server",
        description="Leave a Server and refuse joining it ever again.",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def refuse_service(self, interaction: nextcord.Interaction, server_id: str):
        if not server_id.isnumeric():
            await interaction.send("Server ID is not a number")
            return
        else:
            guild_id = int(server_id)

        server = nextcord.utils.get(self.bot.guilds, id=guild_id)
        if server is None:
            await interaction.send("Bot isnt on the Server")
            return

        await server.leave()

        self.rejected_servers["SERVER_IDS"].append(server.id)
        self.rejected_servers.save()

        await interaction.send(f"Refusing Service to {server.name}")

    @nextcord.slash_command(
        "stop-refusing-server",
        description="Takes a Server of the refusal list.",
        guild_ids=CONFIG["GENERAL"]["OWNER_COG_GUILD_IDS"],
        contexts=[nextcord.InteractionContextType.guild],
        default_member_permissions=nextcord.Permissions(administrator=True),
    )
    async def setop_refusing(self, interaction: nextcord.Interaction, server_id: str):
        if not server_id.isnumeric():
            await interaction.send("Server ID is not a number")
            return
        else:
            guild_id = int(server_id)

        server = nextcord.utils.get(self.bot.guilds, id=guild_id)
        if server is None:
            await interaction.send("Bot isnt on the Server")
            return

        while server.id in self.rejected_servers["SERVER_IDS"]:
            self.rejected_servers["SERVER_IDS"].remove(server.id)

        self.rejected_servers.save()

        await interaction.send(f"No longer refusing Service to {server.name}")

    @commands.Cog.listener()
    async def on_guild_join(self, guild: nextcord.Guild):
        if guild.id in self.rejected_servers["SERVER_IDS"]:
            await guild.leave()


async def setup(bot):
    bot.add_cog(Owner(bot))
