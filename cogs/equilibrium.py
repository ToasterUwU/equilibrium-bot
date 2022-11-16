from typing import Optional

import nextcord
from nextcord.ext import commands

from internal_tools.configuration import CONFIG, JsonDictSaver
from internal_tools.discord import *

# TODO Application Commands (create, cancel, see)


class Equilibrium(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.equilibrium_guilds = JsonDictSaver(
            "equilibrium_guilds",
            default={
                "VERIFIED_GUILD_IDS": [],
                "APPLICATIONS": {},
            },
        )

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        """
        These commands can only be used if you verified your Server. Use the help command for this category to learn more.
        """
        top_command = interaction.application_command
        while isinstance(top_command, nextcord.SlashApplicationSubcommand):
            if top_command.parent_cmd == None:
                break

            top_command = top_command.parent_cmd

        if not top_command:
            return False

        if top_command == self.admin_top_command:
            return True

        if interaction.application_command == self.equilibrium_help:
            return True

        if top_command == self.top_command:
            if not interaction.guild_id:
                return False

            return interaction.guild_id in self.equilibrium_guilds["VERIFIED_GUILD_IDS"]

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: nextcord.Guild):
        if guild.id in self.equilibrium_guilds["APPLICATIONS"]:
            ticket_thread = await GetOrFetch.channel(
                self.bot,
                self.equilibrium_guilds["APPLICATIONS"][guild.id]["TICKET_THREAD_ID"],
            )
            if isinstance(ticket_thread, nextcord.Thread):
                await ticket_thread.edit(archived=True, locked=True)

            del self.equilibrium_guilds["APPLICATIONS"][guild.id]

            self.equilibrium_guilds.save()

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

        invites = await guild.invites()

        invite = None
        if "VANITY_URL" in guild.features:
            invite = await guild.vanity_invite()

        if not invite:
            if not self.bot.user:
                return fancy_embed(
                    "You somehow managed to run this while the Bot isnt logged in.. How?",
                    description="Are you god? Or just stupid and lucky?",
                )

            own_member = await GetOrFetch.member(guild, self.bot.user.id)
            if not own_member:
                return fancy_embed(
                    "Bot got kicked while generating.", description="Some people..."
                )

            channel = None
            for c in guild.text_channels:
                if c.permissions_for(own_member).create_instant_invite:
                    channel = c

            if channel:
                invite = await channel.create_invite()

        if invite:
            invite_link = invite.url
        else:
            invite_link = "Couldnt find or make one. Sketchy..."

        return fancy_embed(
            title,
            description="Information about Server is below.",
            fields={
                "Name": guild.name,
                "ID": guild.id,
                "Members": guild.member_count,
                "Considered Large": guild.large,
                "Exists since": f"<t:{int(guild.created_at.timestamp())}:R>",
                "Role amount": len(guild.roles),
                "Channel amount": len(guild.channels),
                "Feature Flags": "\n".join(guild.features),
                "Invite Link": invite_link,
                "Invite Amount": len(invites),
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

        self.equilibrium_guilds["VERIFIED_GUILD_IDS"].append(guild_id)

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

    @nextcord.slash_command(
        "equilibrium",
        dm_permission=False,
        default_member_permissions=nextcord.Permissions(manage_messages=True),
    )
    async def top_command(self, interaction: nextcord.Interaction):
        pass

    @top_command.subcommand(
        "help", description="Shows what this part of the Bot does, and how to use it."
    )
    async def equilibrium_help(self, interaction: nextcord.Interaction):
        pass  # TODO make a good help command


async def setup(bot):
    bot.add_cog(Equilibrium(bot))
