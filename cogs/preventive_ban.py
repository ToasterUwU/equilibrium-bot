import os
from typing import Optional

import nextcord
from nextcord.ext import application_checks, commands

from internal_tools.configuration import CONFIG, JsonDictSaver
from internal_tools.discord import *
from internal_tools.general import *

# TODO Application Commands (create, cancel, see)


class PreventiveBan(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.preventive_ban_guilds = JsonDictSaver(
            "preventive_ban_guilds",
            default={
                "VERIFIED_GUILD_IDS": {},
                "APPLICATIONS": {},
            },
        )

        self.help_command_assets = load_help_command_assets(
            "assets/PREVENTIVE_BAN/HELP"
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

        if (
            interaction.application_command == self.preventive_ban_help
            or interaction.application_command == self.apply_for_verification
        ):
            return True

        if top_command == self.top_command:
            if not interaction.guild_id:
                return False

            return (
                interaction.guild_id in self.preventive_ban_guilds["VERIFIED_GUILD_IDS"]
            )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: nextcord.Guild):
        if guild.id in self.preventive_ban_guilds["APPLICATIONS"]:
            ticket_thread = await GetOrFetch.channel(
                self.bot,
                self.preventive_ban_guilds["APPLICATIONS"][guild.id][
                    "TICKET_THREAD_ID"
                ],
            )
            if isinstance(ticket_thread, nextcord.Thread):
                await ticket_thread.edit(archived=True, locked=True)

            del self.preventive_ban_guilds["APPLICATIONS"][guild.id]

            self.preventive_ban_guilds.save()

        if guild.id in self.preventive_ban_guilds["VERIFIED_GUILD_IDS"]:
            del self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][guild.id]

            self.preventive_ban_guilds.save()

    @nextcord.slash_command(
        "admin-preventive-ban",
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
                    for i in self.preventive_ban_guilds["APPLICATIONS"]
                    if str(i).startswith(str_guild_id)
                ]
            )
        else:
            await interaction.response.send_autocomplete(
                self.preventive_ban_guilds["APPLICATIONS"]
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
        "approve", description="Approve a Server for using the preventive ban feature."
    )
    async def guild_verification_approve(
        self,
        interaction: nextcord.Interaction,
        str_guild_id: str = nextcord.SlashOption(
            "server-id",
            description="ID of the Server that will be granted preventive ban feature access.",
            autocomplete_callback=autocomplete_guild_verification_guild_id,
        ),
    ):
        guild_id = int(str_guild_id)
        if guild_id not in self.preventive_ban_guilds["APPLICATIONS"]:
            await interaction.send(
                "This Server is not trying to get verified, or maybe doesnt even exist."
            )
            return

        while guild_id in self.preventive_ban_guilds["APPLICATIONS"]:
            del self.preventive_ban_guilds["APPLICATIONS"][guild_id]

        self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][guild_id] = {"ENABLED": True}

        # TODO Send Message back telling the staff they got approved

        self.preventive_ban_guilds.save()

        await interaction.send(
            embed=await self.guild_info_embed(guild_id, "Approved Guild")
        )

    @admin_guild_verfication_subcommand.subcommand(
        "reject", description="Reject a Server for using the preventive ban feature."
    )
    async def guild_verification_reject(
        self,
        interaction: nextcord.Interaction,
        str_guild_id: str = nextcord.SlashOption(
            "server-id",
            description="ID of the Server that will be denied preventive ban feature access.",
            autocomplete_callback=autocomplete_guild_verification_guild_id,
        ),
    ):
        guild_id = int(str_guild_id)
        if guild_id not in self.preventive_ban_guilds["APPLICATIONS"]:
            await interaction.send(
                "This Server is not trying to get verified, or maybe doesnt even exist."
            )
            return

        while guild_id in self.preventive_ban_guilds["APPLICATIONS"]:
            del self.preventive_ban_guilds["APPLICATIONS"][guild_id]

        # TODO Send Message back telling the staff they got rejected

        self.preventive_ban_guilds.save()

        await interaction.send(
            embed=await self.guild_info_embed(guild_id, "Rejected Guild")
        )

    @nextcord.slash_command(
        "preventive-ban",
        dm_permission=False,
        default_member_permissions=nextcord.Permissions(manage_messages=True),
    )
    async def top_command(self, interaction: nextcord.Interaction):
        pass

    @top_command.subcommand(
        "help", description="Shows what this part of the Bot does, and how to use it."
    )
    async def preventive_ban_help(self, interaction: nextcord.Interaction):
        pages = generate_help_command_pages(
            self.help_command_assets,
            APPLY_FOR_VERIFICATION_COMMAND_MENTION=self.apply_for_verification.get_mention(),  # type: ignore
            ENABLE_OR_DISABLE_PREVENTIVE_BAN_COMMAND_MENTION=self.enable_or_disable.get_mention(),  # type: ignore
        )

        await CatalogView(pages).start(interaction)

    @top_command.subcommand(
        "apply-for-verification",
        description="This is needed to use this part of the Bot.",
    )
    async def apply_for_verification(self, interaction: nextcord.Interaction):
        if not interaction.guild_id:
            raise application_checks.errors.ApplicationNoPrivateMessage()

        if interaction.guild_id in self.preventive_ban_guilds["VERIFIED_GUILD_IDS"]:
            await interaction.send(
                f"Congrats! This server is already verified. Check out {self.preventive_ban_help.get_mention()} to learn about what is next.",
                ephemeral=True,
            )
            return

        if interaction.guild_id in self.preventive_ban_guilds["APPLICATIONS"]:
            await interaction.send(
                "This server already has an Application pending.",  # TODO link to application ticket thing and give invite
                ephemeral=True,
            )
            return

        # TODO ask for website, social media, etc. and make a ticket for the application

    @top_command.subcommand(
        "enable-or-disable",
        description="Toggles the preventive ban feature for this Server.",
    )
    async def enable_or_disable(self, interaction: nextcord.Interaction):
        pass


async def setup(bot):
    bot.add_cog(PreventiveBan(bot))
