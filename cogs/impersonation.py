from typing import Callable, List

import aiohttp
import Levenshtein
import nextcord
from nextcord import SlashOption
from nextcord.ext import application_checks, commands
from unidecode import unidecode

from internal_tools.configuration import CONFIG, JsonDictSaver
from internal_tools.discord import *
from internal_tools.general import *

_CHECKS = []


def name_check(func: Callable):
    _CHECKS.append(func)
    return func


class NameIllegalChecker:
    def __init__(self, name: str, illegal_names: List[str]) -> None:
        self.name = unidecode(name).casefold()
        self.illegal_names = [x.casefold() for x in illegal_names]

    @name_check
    def _equal(self):
        for x in self.illegal_names:
            if self.name == x:
                return True

    @name_check
    def _close_enough(self):
        for illegal_name in self.illegal_names:
            if CONFIG["IMPERSONATION"]["LEVENSHTEIN_RATIO"] <= Levenshtein.ratio(
                self.name, illegal_name
            ):
                return True

    def check_all(self):
        """
        Runs all checks and returns True if any of them returned True.
        """
        for func in _CHECKS:
            if func(self):
                return True
        return False


class IllegalNameManager(JsonDictSaver):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__("illegal_name_sources")

        self.bot = bot

        self.illegal_names = {}
        self.known_members = {}

    async def prepare(self):
        self.illegal_names = {}
        self.known_members = {}
        async for g in self.bot.fetch_guilds(limit=None):
            self.add_guild(g.id)

            async for m in g.fetch_members(limit=None):
                if g.id in self:
                    if self.member_is_priveliged(m):
                        self.known_members[g.id].append(m.id)

                        self.illegal_names[g.id].append(m.name)
                        if m.name != m.display_name:
                            self.illegal_names[g.id].append(m.display_name)

            for m_name in self[g.id]["MANUAL_NAMES"]:
                self.illegal_names[g.id].append(m_name)

    def add_guild(self, guild_id: int, save: bool = True):
        if guild_id not in self:
            self[guild_id] = {"ROLE_IDS": [], "USER_IDS": [], "MANUAL_NAMES": []}
            if save:
                self.save()

        if guild_id not in self.illegal_names:
            self.illegal_names[guild_id] = []

        if guild_id not in self.known_members:
            self.known_members[guild_id] = []

    def rm_guild(self, guild_id: int, save: bool = True):
        if guild_id in self:
            del self[guild_id]
            if save:
                self.save()

        if guild_id in self.illegal_names:
            del self.illegal_names[guild_id]

        if guild_id in self.known_members:
            del self.known_members[guild_id]

    def rm_role(self, role: nextcord.Role):
        if role.id in self[role.guild.id]["ROLE_IDS"]:
            self[role.guild.id]["ROLE_IDS"].remove(role.id)
            self.save()

        for m in role.members:
            if not self.member_is_priveliged(m):
                while m.name in self.illegal_names[role.guild.id]:
                    self.illegal_names[role.guild.id].remove(m.name)
                while m.display_name in self.illegal_names[role.guild.id]:
                    self.illegal_names[role.guild.id].remove(m.display_name)

    async def update_user(self, before: nextcord.User, after: nextcord.User):
        if before.name != after.name:
            priveliged_in = []
            async for guild_id in self.user_is_priveliged_in(after):
                priveliged_in.append(guild_id)

                while before.name in self.illegal_names[guild_id]:
                    self.illegal_names[guild_id].remove(before.name)
                self.illegal_names[guild_id].append(after.name)

            for guild_id, illegal_names in self.illegal_names.items():
                if guild_id not in priveliged_in:
                    if NameIllegalChecker(after.name, illegal_names).check_all():
                        guild = await GetOrFetch.guild(self.bot, guild_id)
                        if guild:
                            member = await GetOrFetch.member(guild, after.id)
                            if member:
                                await member.ban(
                                    delete_message_days=7, reason="Used protected Name."
                                )

    async def update_member(self, before: nextcord.Member, after: nextcord.Member):
        if before.display_name != after.display_name:
            if self.member_is_priveliged(before) and not self.member_is_priveliged(
                after
            ):
                while before.display_name in self.illegal_names[before.guild.id]:
                    self.illegal_names[before.guild.id].remove(before.display_name)

            elif not self.member_is_priveliged(before) and self.member_is_priveliged(
                after
            ):
                self.illegal_names[after.guild.id].append(after.display_name)

            elif self.member_is_priveliged(before) and self.member_is_priveliged(after):
                while before.display_name in self.illegal_names[before.guild.id]:
                    self.illegal_names[before.guild.id].remove(before.display_name)
                self.illegal_names[after.guild.id].append(after.display_name)

            else:
                if NameIllegalChecker(
                    after.display_name, self.illegal_names[after.guild.id]
                ).check_all():
                    await after.ban(
                        delete_message_days=7, reason="Used protected Name."
                    )

    async def add_member(self, member: nextcord.Member):
        self.known_members[member.guild.id].append(member.id)

        if (
            NameIllegalChecker(
                member.name, self.illegal_names[member.guild.id]
            ).check_all()
            or NameIllegalChecker(
                member.display_name, self.illegal_names[member.guild.id]
            ).check_all()
        ):
            await member.ban(delete_message_days=7, reason="Used protected Name.")
            self.rm_member(member)

    def rm_member(self, member: nextcord.Member):
        if self.member_is_priveliged(member):
            while member.id in self[str(member.guild.id)]["USER_IDS"]:
                self[str(member.guild.id)]["USER_IDS"].remove(member.id)
                self.save()

            while member.name in self.illegal_names[member.guild.id]:
                self.illegal_names[member.guild.id].remove(member.name)

            while member.display_name in self.illegal_names[member.guild.id]:
                self.illegal_names[member.guild.id].remove(member.display_name)

        while member.id in self.known_members[member.guild.id]:
            self.known_members[member.guild.id].remove(member.id)

    async def get_member_objects(self, user_id: int):
        for guild_id, member_ids in self.known_members.items():
            if user_id in member_ids:
                guild = await GetOrFetch.guild(self.bot, guild_id)
                if guild:
                    member = await GetOrFetch.member(guild, user_id)
                    if member:
                        yield member

    def member_is_priveliged(self, member: nextcord.Member):
        if member.id in self[member.guild.id]["USER_IDS"]:
            return True

        for role in member.roles:
            if role:
                if role.id in self[member.guild.id]["ROLE_IDS"]:
                    return True

        return False

    async def user_is_priveliged_in(self, user: nextcord.User):
        async for m in self.get_member_objects(user.id):
            if self.member_is_priveliged(m):
                yield m.guild.id

    def privelige_member(self, member: nextcord.Member):
        if member.id not in self[member.guild.id]["USER_IDS"]:
            self[member.guild.id]["USER_IDS"].append(member.id)
            self.save()

            self.illegal_names[member.guild.id].append(member.name)
            if member.name != member.display_name:
                self.illegal_names[member.guild.id].append(member.display_name)

    def deprivelige_member(self, member: nextcord.Member):
        while member.id in self[member.guild.id]["USER_IDS"]:
            self[member.guild.id]["USER_IDS"].remove(member.id)
        self.save()

        if not self.member_is_priveliged(member):
            while member.name in self.illegal_names[member.guild.id]:
                self.illegal_names[member.guild.id].remove(member.name)

            while member.display_name in self.illegal_names[member.guild.id]:
                self.illegal_names[member.guild.id].remove(member.display_name)

    def privelige_role(self, role: nextcord.Role):
        if role.id not in self[role.guild.id]["ROLE_IDS"]:
            self[role.guild.id]["ROLE_IDS"].append(role.id)
            self.save()

            for member in role.members:
                self.illegal_names[member.guild.id].append(member.name)
                if member.name != member.display_name:
                    self.illegal_names[member.guild.id].append(member.display_name)

    def deprivelige_role(self, role: nextcord.Role):
        while role.id in self[role.guild.id]["ROLE_IDS"]:
            self[role.guild.id]["ROLE_IDS"].remove(role.id)
        self.save()

        for member in role.members:
            if not self.member_is_priveliged(member):
                while member.name in self.illegal_names[member.guild.id]:
                    self.illegal_names[member.guild.id].remove(member.name)

                while member.display_name in self.illegal_names[member.guild.id]:
                    self.illegal_names[member.guild.id].remove(member.display_name)

    def add_manual_name(self, guild: nextcord.Guild, name: str):
        if name not in self[guild.id]["MANUAL_NAMES"]:
            self.illegal_names[guild.id].append(name)

            self[guild.id]["MANUAL_NAMES"].append(name)
            self.save()

    def list_manual_names(self, guild: nextcord.Guild):
        return self[guild.id]["MANUAL_NAMES"]

    def rm_manual_name(self, guild: nextcord.Guild, name: str):
        if name in self[guild.id]["MANUAL_NAMES"]:
            self.illegal_names[guild.id].remove(name)

            self[guild.id]["MANUAL_NAMES"].remove(name)
            self.save()

    def test_name(self, name: str, guild_id: int):
        return NameIllegalChecker(name, self.illegal_names[guild_id]).check_all()


class Impersonation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.ILM = IllegalNameManager(self.bot)

        self.help_command_assets = load_help_command_assets("assets/IMPERSONATION/HELP")

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        """
        Only Admins can use these commands.
        """
        if not interaction.user:
            return False

        if not isinstance(interaction.user, nextcord.Member):
            return False

        if interaction.user.guild_permissions.administrator:
            return True

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ILM.prepare()

    @commands.Cog.listener()
    async def on_guild_join(self, guild: nextcord.Guild):
        self.ILM.add_guild(guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: nextcord.Guild):
        self.ILM.rm_guild(guild.id)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: nextcord.Role):
        self.ILM.rm_role(role)

    @commands.Cog.listener()
    async def on_user_update(self, before: nextcord.User, after: nextcord.User):
        await self.ILM.update_user(before, after)

    @commands.Cog.listener()
    async def on_member_update(self, before: nextcord.Member, after: nextcord.Member):
        await self.ILM.update_member(before, after)

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        await self.ILM.add_member(member)

    @commands.Cog.listener()
    async def on_member_remove(self, member: nextcord.Member):
        self.ILM.rm_member(member)

    @nextcord.slash_command(
        name="impersonation",
        description="Under this command you can find everything the bot can do against impersonation.",
        dm_permission=False,
        default_member_permissions=nextcord.Permissions(ban_members=True),
    )
    async def top_command(self, interaction: nextcord.Interaction):
        pass

    @top_command.subcommand(
        "help", description="Explains what this does and how to use it."
    )
    async def impersonation_help(self, interaction: nextcord.Interaction):
        pages = generate_help_command_pages(
            self.help_command_assets,
            PROTECT_ROLE_COMMAND_MENTION=self.protect_role.get_mention(),
            DEPROTECT_ROLE_COMMAND_MENTION=self.deprotect_role.get_mention(),
            PROTECT_USER_COMMAND_MENTION=self.protect_user.get_mention(),
            DEPROTECT_USER_COMMAND_MENTION=self.deprotect_user.get_mention(),
            ADD_MANUAL_NAME_COMMAND_MENTION=self.add_manual_name.get_mention(),
            RM_MANUAL_NAME_COMMAND_MENTION=self.rm_manual_name.get_mention(),
            LIST_MANUAL_NAMES_COMMAND_MENTION=self.list_manual_names.get_mention(),
        )

        await CatalogView(pages).start(interaction)

    @top_command.subcommand(
        name="protect-user",
        description="Tell the Bot to protect a User from impersonation.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def protect_user(
        self, interaction: nextcord.Interaction, user: nextcord.Member
    ):
        self.ILM.privelige_member(user)

        await interaction.send(f"{user.mention} is now protected from impersonation.")

    @top_command.subcommand(
        name="dont-protect-user",
        description="Tell the Bot to stop protecting a User from impersonation.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def deprotect_user(
        self, interaction: nextcord.Interaction, user: nextcord.Member
    ):
        self.ILM.deprivelige_member(user)

        await interaction.send(
            f"{user.mention} is not protected from impersonation anymore."
        )

    @top_command.subcommand(
        name="protect-role",
        description="Tell the Bot to protect everybody with a specific Role from impersonation.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def protect_role(
        self, interaction: nextcord.Interaction, role: nextcord.Role
    ):
        self.ILM.privelige_role(role)

        await interaction.send(
            f"Everyone with the role {role.mention} is now protected from impersonation."
        )

    @top_command.subcommand(
        name="dont-protect-role",
        description="Tell the Bot to stop protecting everybody with a specific Role from impersonation.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def deprotect_role(
        self, interaction: nextcord.Interaction, role: nextcord.Role
    ):
        self.ILM.deprivelige_role(role)

        await interaction.send(
            f"Everyone with the role {role.mention} is not protected from impersonation anymore, unless they are also added manually as a user."
        )

    @top_command.subcommand(
        name="add-manual-name",
        description="Lets you manually add a name that will be illegal. This is meant for edge cases.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def add_manual_name(self, interaction: nextcord.Interaction, name: str):
        if not interaction.guild:
            raise application_checks.ApplicationNoPrivateMessage()

        self.ILM.add_manual_name(interaction.guild, name)

        await interaction.send(f"'{name}' is now a illegal name.")

    @top_command.subcommand(
        name="list-manual-names",
        description="Shows all the manually added names.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def list_manual_names(self, interaction: nextcord.Interaction):
        if not interaction.guild:
            raise application_checks.ApplicationNoPrivateMessage()

        names = self.ILM.list_manual_names(interaction.guild)

        await interaction.send(
            embed=fancy_embed(
                "Manually added protected Names", description="\n".join(names)
            )
        )

    @top_command.subcommand(
        name="rm-manual-name",
        description="Lets you remove a name that was manually added. This is meant for edge cases.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def rm_manual_name(self, interaction: nextcord.Interaction, name: str):
        if not interaction.guild:
            raise application_checks.ApplicationNoPrivateMessage()

        self.ILM.rm_manual_name(interaction.guild, name)

        await interaction.send(f"'{name}' is not a illegal name anymore.")

    @top_command.subcommand(
        name="test-name",
        description="Lets you manually check if a user with a specific name would be banned or not.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def test_name(self, interaction: nextcord.Interaction, name: str):
        if not interaction.guild:
            raise application_checks.ApplicationNoPrivateMessage()

        if self.ILM.test_name(name, interaction.guild.id):
            msg = f"Someone with the name '{name}' would be banned."
        else:
            msg = f"Someone with the name '{name}' would NOT be banned."

        await interaction.send(msg)

    @top_command.subcommand(
        name="report-name",
        description="Report a name that slipped past the Bot. So that Aki can find a method to make the bot recognize it.",
    )
    @application_checks.bot_has_permissions(ban_members=True)
    async def report_name(
        self,
        interaction: nextcord.Interaction,
        name: str = SlashOption(
            "name",
            description="The name that the bot didnt recognize as bad, best is you copy paste the name.",
            required=True,
        ),
        member: nextcord.Member = SlashOption(
            name="protected-user",
            description="The person that was impersonated with that name.",
            required=True,
        ),
    ):
        if not interaction.guild:
            raise application_checks.ApplicationNoPrivateMessage()

        embed = fancy_embed(
            "Name slipped past Bouncer",
            description=f"{interaction.user} in {interaction.guild.name}",
            fields={
                "Name": name,
                "Protected Name(s)": member.name + " / " + member.display_name
                if member.name != member.display_name
                else member.name,
            },
        )

        async with aiohttp.ClientSession() as session:
            webhook = nextcord.Webhook.from_url(
                url=CONFIG["IMPERSONATION"]["REPORT_NAME_WEBHOOK"],
                session=session,
            )
            await webhook.send(embed=embed)

        await interaction.send("Thanks for reporting this. ")


def setup(bot):
    bot.add_cog(Impersonation(bot))
