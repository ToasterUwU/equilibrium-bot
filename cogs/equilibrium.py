from typing import Optional

import nextcord
from nextcord.ext import commands

from internal_tools.configuration import CONFIG, JsonDictSaver
from internal_tools.discord import *


class Equilibrium(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.equilibrium_servers = JsonDictSaver(
            "equilibrium_servers",
            default={
                "VERIFIED_SERVER_IDS": [],
                "WAITING_FOR_VERIFICATION_SERVER_IDS": [],
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
    async def admin_server_verfication_subcommand(
        self, interaction: nextcord.Interaction
    ):
        pass

    async def autocomplete_server_verification_server_id(
        self, interaction: nextcord.Interaction, server_id: Optional[int]
    ):
        if server_id:
            str_server_id = str(server_id)

            await interaction.response.send_autocomplete(
                [
                    i
                    for i in self.equilibrium_servers[
                        "WAITING_FOR_VERIFICATION_SERVER_IDS"
                    ]
                    if str(i).startswith(str_server_id)
                ]
            )
        else:
            await interaction.response.send_autocomplete(
                self.equilibrium_servers["WAITING_FOR_VERIFICATION_SERVER_IDS"]
            )

    @admin_server_verfication_subcommand.subcommand(
        "approve", description="Approve a Server for using Equilibrium."
    )
    async def server_verification_approve(
        self,
        interaction: nextcord.Interaction,
        server_id: int = nextcord.SlashOption(
            "server-id",
            description="ID of the Server that will be granted Equilibrium access.",
            autocomplete_callback=autocomplete_server_verification_server_id,
        ),
    ):
        pass

    @admin_server_verfication_subcommand.subcommand(
        "reject", description="Reject a Server for using Equilibrium."
    )
    async def server_verification_reject(
        self,
        interaction: nextcord.Interaction,
        server_id: int = nextcord.SlashOption(
            "server-id",
            description="ID of the Server that will be denied Equilibrium access.",
            autocomplete_callback=autocomplete_server_verification_server_id,
        ),
    ):
        pass


async def setup(bot):
    bot.add_cog(Equilibrium(bot))
