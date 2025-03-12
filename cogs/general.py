import nextcord
from nextcord.ext import commands

from internal_tools.discord import *
from internal_tools.general import *


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.help_command_assets = load_help_command_assets("assets/GENERAL/HELP")

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        """
        Everyone can use this.
        """
        return True

    @nextcord.slash_command(
        "help",
        description="Shows information about this Bot and everything that is connected to it.",
        contexts=[nextcord.InteractionContextType.guild],
    )
    async def help_command(self, interaction: nextcord.Interaction):
        pages = generate_help_command_pages(
            self.help_command_assets,
            IMPERSONATION_HELP_COMMAND_MENTION=self.bot.cogs[
                "Impersonation"
            ].impersonation_help.get_mention(),  # type: ignore
            PREVENTIVE_BAN_HELP_COMMAND_MENTION=self.bot.cogs[
                "PreventiveBan"
            ].preventive_ban_help.get_mention(),  # type: ignore
        )

        await CatalogView(pages).start(interaction)


async def setup(bot):
    bot.add_cog(General(bot))
