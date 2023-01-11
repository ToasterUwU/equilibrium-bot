import asyncio
from typing import Optional

import aiohttp
import nextcord
from nextcord.ext import application_checks, commands

from cogs.ticket_system import TicketSystem
from internal_tools.configuration import CONFIG, JsonDictSaver
from internal_tools.discord import *
from internal_tools.general import *


class LinkCollector(nextcord.ui.Modal):
    def __init__(self):
        super().__init__(
            "Enter Links below. (Website, Social Media)",
            timeout=600,
        )

        self.input = nextcord.ui.TextInput(
            "Links", style=nextcord.TextInputStyle.paragraph, default_value=""
        )
        self.add_item(self.input)

        self.value = None

    async def callback(self, interaction: nextcord.Interaction):
        self.value = self.input.value

        await interaction.send("Info collected. This might take a Moment...")

        self.stop()


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

        self.preventively_baned_users = JsonDictSaver("preventively_baned_users")
        self.preventive_ban_records = JsonDictSaver("preventive_ban_records")

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

    async def log_ban(
        self, guild_id: int, user_id: int, ban_records: Optional[int] = None
    ):
        if guild_id in self.preventive_ban_guilds["VERIFIED_GUILD_IDS"]:
            if self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][guild_id][
                "LOG_WEBHOOK_URL"
            ]:
                try:
                    async with aiohttp.ClientSession() as session:
                        webhook = nextcord.Webhook.from_url(
                            self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][guild_id][
                                "LOG_WEBHOOK_URL"
                            ],
                            session=session,
                        )
                        await webhook.send(
                            f"Banned User with ID `{user_id}` ( <@{user_id}> ), based on {ban_records or len(self.preventive_ban_records[user_id])} reports."
                        )
                except:
                    pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild: nextcord.Guild, user: nextcord.User):
        if guild.id in self.preventive_ban_guilds["VERIFIED_GUILD_IDS"]:
            if user.id not in self.preventive_ban_records:
                self.preventive_ban_records[user.id] = []

            if guild.id not in self.preventive_ban_records[user.id]:
                self.preventive_ban_records[user.id].append(guild.id)
                self.preventive_ban_records.save()

            if user.id not in self.preventively_baned_users:
                ban_records = len(self.preventive_ban_records[user.id])
                if (
                    ban_records >= CONFIG["PREVENTIVE_BAN"]["BAN_AT_HARD_LIMIT"]
                    or ban_records
                    >= len(self.preventive_ban_guilds["VERIFIED_GUILD_IDS"])
                    * CONFIG["PREVENTIVE_BAN"]["BAN_AT_PERCENT"]
                ):
                    self.preventively_baned_users[user.id] = True
                    self.preventively_baned_users.save()

                    for g in self.bot.guilds:
                        if g.id in self.preventive_ban_guilds["VERIFIED_GUILD_IDS"]:
                            if self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][g.id][
                                "ENABLED"
                            ]:
                                if g.id not in self.preventive_ban_records[user.id]:
                                    try:
                                        await g.ban(
                                            user,
                                            reason=f"Preventive ban, based on {ban_records} reports.",
                                        )
                                        await self.log_ban(
                                            g.id, user.id, ban_records=ban_records
                                        )
                                    except:
                                        continue

    @commands.Cog.listener()
    async def on_member_remove(self, member: nextcord.Member):
        if member.guild.id == CONFIG["GENERAL"]["HOME_GUILD_ID"]:
            application_key = None
            for key, data in self.preventive_ban_guilds["APPLICATIONS"].items():
                if member.id == data["CREATOR_ID"]:
                    application_key = key

                    ticket = await GetOrFetch.channel(
                        member.guild, data["TICKET_CHANNEL_ID"]
                    )
                    if not isinstance(ticket, nextcord.Thread):
                        return

                    await ticket.send(
                        embed=fancy_embed(
                            "Creator of Application left.",
                            description="Application is canceled and Ticket will be archived.",
                        )
                    )

                    await ticket.edit(archived=True)

            if application_key:
                del self.preventive_ban_guilds["APPLICATIONS"][application_key]
                self.preventive_ban_guilds.save()

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        if member.guild.id == CONFIG["GENERAL"]["HOME_GUILD_ID"]:
            for data in self.preventive_ban_guilds["APPLICATIONS"].values():
                if member.id == data["CREATOR_ID"]:
                    verified_role = await GetOrFetch.role(
                        member.guild, CONFIG["GENERAL"]["VERIFIED_MEMBER_ROLE_ID"]
                    )
                    ambassador_role = await GetOrFetch.role(
                        member.guild, CONFIG["GENERAL"]["SERVER_AMBASSADOR_ROLE_ID"]
                    )
                    if not verified_role or not ambassador_role:
                        raise Exception("Well.. thats a Config problem :/")

                    await member.add_roles(verified_role, ambassador_role)

                    await asyncio.sleep(3)

                    ticket = await GetOrFetch.channel(
                        member.guild, data["TICKET_CHANNEL_ID"]
                    )
                    if not isinstance(ticket, nextcord.Thread):
                        return

                    await ticket.send(
                        f"{member.mention} joined the Server. They are the Creator of this Application."
                    )

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: nextcord.Guild):
        if guild.id in self.preventive_ban_guilds["APPLICATIONS"]:
            ticket_thread = await GetOrFetch.channel(
                self.bot,
                self.preventive_ban_guilds["APPLICATIONS"][guild.id][
                    "TICKET_CHANNEL_ID"
                ],
            )
            if isinstance(ticket_thread, nextcord.Thread):
                await ticket_thread.send(
                    embed=fancy_embed(
                        "Guild of Application kicked Bot.",
                        description="Application is canceled and Ticket will be archived.",
                    )
                )

                await ticket_thread.edit(archived=True)

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
                    str(i)
                    for i in self.preventive_ban_guilds["APPLICATIONS"].keys()
                    if str(i).startswith(str_guild_id)
                ]
            )
        else:
            await interaction.response.send_autocomplete(
                [str(i) for i in self.preventive_ban_guilds["APPLICATIONS"].keys()]
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
                invite = await channel.create_invite(max_age=604800)

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
    @application_checks.bot_has_permissions(administrator=True)
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

        home_guild = await GetOrFetch.guild(
            self.bot, CONFIG["GENERAL"]["HOME_GUILD_ID"]
        )
        if not home_guild:
            await interaction.send(
                "There is a Configuration error, please tell the staff about this."
            )
            raise Exception("Couldnt get Home Guild.")

        ticket = await GetOrFetch.channel(
            home_guild,
            self.preventive_ban_guilds["APPLICATIONS"][guild_id]["TICKET_CHANNEL_ID"],
        )
        if isinstance(ticket, nextcord.Thread):
            if not ticket.archived:
                await ticket.send(
                    f"<@{self.preventive_ban_guilds['APPLICATIONS'][guild_id]['CREATOR_ID']}> Your Server has been approved. Enjoy the new Feature.\n"
                    "Make sure the Role of the Bot is above all the roles it should be able to ban on your Server (In the Server Settings, under Roles). If it isnt, it cant ban anyone.\n\n"
                    "This Ticket will be closed in 5 minutes."
                )

        while guild_id in self.preventive_ban_guilds["APPLICATIONS"]:
            del self.preventive_ban_guilds["APPLICATIONS"][guild_id]

        self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][guild_id] = {
            "ENABLED": True,
            "LOG_WEBHOOK_URL": None,
        }
        self.preventive_ban_guilds.save()

        await interaction.send(f"Approved Server. ( {guild_id} )")

        if isinstance(ticket, nextcord.Thread):
            await asyncio.sleep(300)

            await ticket.edit(archived=True)

        guild = await GetOrFetch.guild(self.bot, guild_id)
        if not isinstance(guild, nextcord.Guild):
            return

        for user_id in self.preventively_baned_users.keys():
            try:
                snowflake = nextcord.Object(user_id)
                await guild.ban(snowflake)
                await self.log_ban(guild.id, user_id)
            except:
                continue

    @admin_guild_verfication_subcommand.subcommand(
        "reject", description="Reject a Server for using the preventive ban feature."
    )
    @application_checks.bot_has_permissions(administrator=True)
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

        home_guild = await GetOrFetch.guild(
            self.bot, CONFIG["GENERAL"]["HOME_GUILD_ID"]
        )
        if not home_guild:
            await interaction.send(
                "There is a Configuration error, please tell the staff about this."
            )
            raise Exception("Couldnt get Home Guild.")

        ticket = await GetOrFetch.channel(
            home_guild,
            self.preventive_ban_guilds["APPLICATIONS"][guild_id]["TICKET_CHANNEL_ID"],
        )
        if isinstance(ticket, nextcord.Thread):
            if not ticket.archived:
                await ticket.send(
                    f"<@{self.preventive_ban_guilds['APPLICATIONS'][guild_id]['CREATOR_ID']}> Your Server has been REJECTED. This might be because the Server is too small, or because Staff thought it was sketchy. This Ticket will be closed in 5 minutes."
                )

        self.preventive_ban_guilds.save()

        await interaction.send(f"Rejected Server. ( {guild_id} )")

        if isinstance(ticket, nextcord.Thread):
            await asyncio.sleep(300)

            await ticket.edit(archived=True)

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
            APPLY_FOR_VERIFICATION_COMMAND_MENTION=self.apply_for_verification.get_mention(),
            ENABLE_OR_DISABLE_PREVENTIVE_BAN_COMMAND_MENTION=self.enable_or_disable.get_mention(),
            SET_LOG_WEBHOOK_COMMAND_MENTION=self.set_log_webhook.get_mention(),
        )

        await CatalogView(pages).start(interaction)

    @top_command.subcommand(
        "apply-for-verification",
        description="This is needed to use this part of the Bot.",
    )
    @application_checks.bot_has_permissions(
        manage_guild=True, ban_members=True, embed_links=True
    )
    async def apply_for_verification(self, interaction: nextcord.Interaction):
        if not interaction.guild_id:
            raise application_checks.errors.ApplicationNoPrivateMessage()

        if not interaction.user:
            await interaction.send(
                "Something went wrong on Discords side. Try again.", ephemeral=True
            )
            return

        if interaction.guild_id in self.preventive_ban_guilds["VERIFIED_GUILD_IDS"]:
            await interaction.send(
                f"Congrats! This server is already verified. Check out {self.preventive_ban_help.get_mention()} to learn about what is next.",
                ephemeral=True,
            )
            return

        if interaction.guild_id in self.preventive_ban_guilds["APPLICATIONS"]:
            await interaction.send(
                f"This server already has an Application pending.\nLink to Ticket: {self.preventive_ban_guilds['APPLICATIONS']['TICKET_JUMP_URL']}\n\n{CONFIG['GENERAL']['OFFICAL_INVITE']}",
            )
            return

        link_collector = LinkCollector()
        await interaction.response.send_modal(link_collector)
        if not interaction.response.is_done():
            await interaction.send("Collecting Infos.", ephemeral=True)

        while not link_collector.is_finished():
            await asyncio.sleep(1)

        links = link_collector.value

        home_guild = await GetOrFetch.guild(
            self.bot, CONFIG["GENERAL"]["HOME_GUILD_ID"]
        )
        if not home_guild:
            await interaction.send(
                "There is a Configuration error, please tell the staff about this."
            )
            raise Exception("Couldnt get Home Guild.")

        try:
            member = await home_guild.fetch_member(interaction.user.id)

            verified_role = await GetOrFetch.role(
                home_guild, CONFIG["GENERAL"]["VERIFIED_MEMBER_ROLE_ID"]
            )
            ambassador_role = await GetOrFetch.role(
                home_guild, CONFIG["GENERAL"]["SERVER_AMBASSADOR_ROLE_ID"]
            )

            if not verified_role or not ambassador_role:
                raise Exception("Config Problem, notify staff please.")

            await member.add_roles(verified_role, ambassador_role)

            await asyncio.sleep(3)

        except nextcord.errors.HTTPException:
            member = None

        initial_message = f"{member.mention if member else interaction.user} started the verification process."

        ticket_system: TicketSystem = self.bot.cogs["TicketSystem"]  # type: ignore
        ticket = await ticket_system.create_ticket(
            "Server Verification",
            interaction.user.id,
            initial_message,
            add_ticket_controls=False,
        )

        if not ticket:
            await interaction.send(
                "Couldnt create Ticket. Thats not supposed to happen... Notify staff please."
            )
            raise Exception("Couldnt create Ticket.")

        await ticket.send(
            f"Links:\n\n```\n{links}\n```",
            embed=await self.guild_info_embed(interaction.guild_id, "Server Stats"),
        )

        self.preventive_ban_guilds["APPLICATIONS"][interaction.guild_id] = {
            "LINKS": links,
            "TICKET_JUMP_URL": ticket.jump_url,
            "TICKET_CHANNEL_ID": ticket.id,
            "CREATOR_ID": interaction.user.id,
        }
        self.preventive_ban_guilds.save()

        if member:
            await interaction.send(
                f"Thanks for starting this verification process for your Server."
                "\nPlease check out your ticket with the following link and send a Message there, to let us know you are there."
                f"\n\n{ticket.jump_url}"
            )
        else:
            await interaction.send(
                f"Thanks for starting this verification process for your Server."
                "\nPlease join the offical Server and check out your ticket with the following link and send a Message there, to let us know you are there."
                f"\n\n{ticket.jump_url}\n{CONFIG['GENERAL']['OFFICIAL_INVITE']}"
            )

    @top_command.subcommand(
        "enable-or-disable",
        description="Toggles the preventive ban feature for this Server.",
    )
    @application_checks.bot_has_permissions(
        manage_guild=True, ban_members=True, embed_links=True
    )
    async def enable_or_disable(self, interaction: nextcord.Interaction):
        if not interaction.guild_id:
            raise application_checks.errors.ApplicationNoPrivateMessage()

        self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][interaction.guild_id][
            "ENABLED"
        ] = not self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][interaction.guild_id][
            "ENABLED"
        ]
        self.preventive_ban_guilds.save()

        await interaction.send(
            f"The Preventive ban feature is now: {'Enabled' if self.preventive_ban_guilds['VERIFIED_GUILD_IDS'][interaction.guild_id]['ENABLED'] else 'Disabled'}"
        )

    @top_command.subcommand(
        "set-log-webhook",
        description="Give the Bot a Webhook URL to send log messages about preventive bans to.",
    )
    @application_checks.bot_has_permissions(
        manage_guild=True, ban_members=True, embed_links=True
    )
    async def set_log_webhook(
        self,
        interaction: nextcord.Interaction,
        webhook_url: str = nextcord.SlashOption(
            "webhook-url",
            description="The URL of the Webhook. Can be obtained with the 'Copy Webhook URL' button in the Webhook settings.",
        ),
    ):
        try:
            nextcord.Webhook.from_url(webhook_url, session=aiohttp.ClientSession())
        except nextcord.errors.InvalidArgument:
            await interaction.send("The URL you gave isnt a valid Webhook URL.")
            return

        self.preventive_ban_guilds["VERIFIED_GUILD_IDS"][interaction.guild_id][
            "LOG_WEBHOOK_URL"
        ] = webhook_url
        self.preventive_ban_guilds.save()

        await interaction.send(f"Ok, will send log messages to: {webhook_url}")


async def setup(bot):
    bot.add_cog(PreventiveBan(bot))
