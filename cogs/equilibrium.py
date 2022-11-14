from typing import Optional

import nextcord
from nextcord.ext import commands

from internal_tools.configuration import CONFIG, JsonDictSaver
from internal_tools.discord import *

# TODO Application Commands (create, cancel, see)
# TODO make a Application System structure


class Equilibrium(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.equilibrium_guilds = JsonDictSaver(
            "equilibrium_guilds",
            default={
                "VERIFIED_guild_idS": [],
                "APPLICATIONS": {},  # TODO clear applications from guilds that kicked the bot or cancel it
            },
        )

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        """
        Everyone can use this.
        """
        return True

    @commands.Cog.listener()
    async def on_ready(self):
        pass

    @nextcord.slash_command(
        "admin-equilibrium",
        dm_permission=False,
        default_member_permissions=nextcord.Permissions(administrator=True),
        guild_ids=[CONFIG["GENERAL"]["HOME_GUILD_ID"]],
    )
    async def admin_top_command(self, interaction: nextcord.Interaction):
        pass

    @admin_top_command.subcommand("server-verfication")
    async def admin_guild_verfication_subcommand(
        self, interaction: nextcord.Interaction
    ):
        pass

    async def autocomplete_guild_verification_guild_id(
        self, interaction: nextcord.Interaction, str_guild_id: Optional[str]
    ):
        if str_guild_id:
            await interaction.response.send_autocomplete(
                [
                    i
                    for i in self.equilibrium_guilds["APPLICATIONS"]
                    if str(i).startswith(str_guild_id)
                ]
            )
        else:
            await interaction.response.send_autocomplete(
                self.equilibrium_guilds["APPLICATIONS"]
            )

    async def guild_info_embed(self, guild_id: int, title: str):
        guild = await GetOrFetch.guild(self.bot, guild_id)
        if not guild:
            return fancy_embed(
                "Guild doesnt exist.", description="Something went wrong here. Weird..."
            )

        return fancy_embed(
            title,
            description="Information about Server is below.",
            fields={
                "Name": guild.name,
                "ID": guild.id,
                "Members": guild.member_count,
                "Exists since": f"<t:{int(guild.created_at.timestamp())}:R>",
                "Role amount": len(guild.roles),
                "Channel amount": len(guild.channels),
                "Flags": "\n".join(guild.features),
            },
        )

    @admin_guild_verfication_subcommand.subcommand(
        "approve", description="Approve a Server for using Equilibrium."
    )
    async def guild_verification_approve(
        self,
        interaction: nextcord.Interaction,
        str_guild_id: str = nextcord.SlashOption(
            "server-id",
            description="ID of the Server that will be granted Equilibrium access.",
            autocomplete_callback=autocomplete_guild_verification_guild_id,
        ),
    ):
        guild_id = int(str_guild_id)
        if guild_id not in self.equilibrium_guilds["APPLICATIONS"]:
            await interaction.send(
                "This Server is not trying to get verified, or maybe doesnt even exist."
            )
            return

        while guild_id in self.equilibrium_guilds["APPLICATIONS"]:
            del self.equilibrium_guilds["APPLICATIONS"][guild_id]

        self.equilibrium_guilds["VERIFIED_guild_idS"].append(guild_id)

        # TODO Send Message back telling the staff they got approved

        self.equilibrium_guilds.save()

        await interaction.send(
            embed=await self.guild_info_embed(guild_id, "Approved Guild")
        )

    @admin_guild_verfication_subcommand.subcommand(
        "reject", description="Reject a Server for using Equilibrium."
    )
    async def guild_verification_reject(
        self,
        interaction: nextcord.Interaction,
        str_guild_id: str = nextcord.SlashOption(
            "server-id",
            description="ID of the Server that will be denied Equilibrium access.",
            autocomplete_callback=autocomplete_guild_verification_guild_id,
        ),
    ):
        guild_id = int(str_guild_id)
        if guild_id not in self.equilibrium_guilds["APPLICATIONS"]:
            await interaction.send(
                "This Server is not trying to get verified, or maybe doesnt even exist."
            )
            return

        while guild_id in self.equilibrium_guilds["APPLICATIONS"]:
            del self.equilibrium_guilds["APPLICATIONS"][guild_id]

        # TODO Send Message back telling the staff they got rejected

        self.equilibrium_guilds.save()

        await interaction.send(
            embed=await self.guild_info_embed(guild_id, "Rejected Guild")
        )


async def setup(bot):
    bot.add_cog(Equilibrium(bot))
