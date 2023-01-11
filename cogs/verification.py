import asyncio
import random
from typing import List, Tuple

import nextcord
from nextcord.ext import commands

from internal_tools.configuration import CONFIG
from internal_tools.discord import *


class VerificationRequired(nextcord.ui.View):
    def __init__(self, cog: "Verification"):
        super().__init__(timeout=None)

        self.cog = cog

    @nextcord.ui.button(
        label="Verify",
        emoji="🔓",
        style=nextcord.ButtonStyle.green,
        custom_id="VerificationRequired:Verify",
    )
    async def start_puzzle(
        self, button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        if not interaction.user:
            await interaction.send(
                "Something went wrong on Discords side. Try again.", ephemeral=True
            )
            return

        if interaction.user.id not in self.cog.verifying_users:
            self.cog.verifying_users.append(interaction.user.id)

        CHOSEN_PHRASE, CHOSEN_EMOJI, WRONG_OPTIONS = self.cog.get_random_puzzle_data()

        await interaction.send(
            embed=fancy_embed(
                "Puzzle",
                description=f"Select the Emoji in the Dropdown that can be described with the following Phrase: '{CHOSEN_PHRASE}'",
            ),
            view=VerificationPuzzle(self.cog, CHOSEN_EMOJI, WRONG_OPTIONS),
            ephemeral=True,
        )


class VerificationPuzzle(nextcord.ui.View):
    def __init__(
        self, cog: "Verification", chosen_emoji: str, wrong_options: List[str]
    ):
        super().__init__(timeout=600)

        self.active = True

        self.cog = cog
        self.CHOSEN_EMOJI = chosen_emoji
        self.WRONG_OPTIONS = wrong_options

        self.OPTIONS = []
        self.OPTIONS.extend(self.WRONG_OPTIONS)
        self.OPTIONS.append(self.CHOSEN_EMOJI)

        random.shuffle(self.OPTIONS)

        select_options = []
        for i, emoji in zip(range(len(self.OPTIONS)), self.OPTIONS):
            select_options.append(
                nextcord.SelectOption(label=str(i + 1), value=emoji, emoji=emoji)
            )

        self.select = nextcord.ui.Select(
            placeholder="Select the right Emoji", options=select_options, row=0
        )
        self.add_item(self.select)

    @nextcord.ui.button(label="Confirm", style=nextcord.ButtonStyle.green, row=1)
    async def confirm(
        self, button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        if not isinstance(interaction.user, nextcord.Member):
            await interaction.send(
                "Something went wrong on Discords side. Try again.", ephemeral=True
            )
            return

        if not self.active:
            await interaction.send(
                "This Menu is not active anymore. Either because you requested a new one, or because you solved the Puzzle.",
                ephemeral=True,
            )
            return

        if len(self.select.values) < 1:
            await interaction.send("You need to select a Emoji", ephemeral=True)
            return

        selected = self.select.values[0]
        if selected == self.CHOSEN_EMOJI:
            home_guild = await GetOrFetch.guild(
                self.cog.bot, CONFIG["GENERAL"]["HOME_GUILD_ID"]
            )
            if not home_guild:
                await interaction.send(
                    "Couldnt find home_guild. Contact staff and show this this Error.",
                    ephemeral=True,
                )
                return

            role = await GetOrFetch.role(
                home_guild, CONFIG["VERIFICATION"]["VERIFIED_ROLE_ID"]
            )
            if not role:
                await interaction.send(
                    "Couldnt find verfied role. Contact staff and show this this Error.",
                    ephemeral=True,
                )
                return

            await interaction.user.add_roles(role)

            if interaction.user.id in self.cog.verifying_users:
                self.cog.verifying_users.remove(interaction.user.id)

            await interaction.send("You are now verified.", ephemeral=True)
        else:
            (
                CHOSEN_PHRASE,
                CHOSEN_EMOJI,
                WRONG_OPTIONS,
            ) = self.cog.get_random_puzzle_data()

            await interaction.send(
                "That was wrong. Try again.",
                ephemeral=True,
                embed=fancy_embed(
                    "Puzzle",
                    description=f"Select the Emoji in the Dropdown that can be described with the following Phrase: '{CHOSEN_PHRASE}'",
                ),
                view=VerificationPuzzle(self.cog, CHOSEN_EMOJI, WRONG_OPTIONS),
            )

        self.active = False

    @nextcord.ui.button(label="Next Puzzle", style=nextcord.ButtonStyle.blurple, row=1)
    async def next_puzzle(
        self, button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        if not self.active:
            await interaction.send(
                "This Menu is not active anymore. Either because you requested a new one, or because you solved the Puzzle.",
                ephemeral=True,
            )
            return

        CHOSEN_PHRASE, CHOSEN_EMOJI, WRONG_OPTIONS = self.cog.get_random_puzzle_data()

        await interaction.send(
            "Ok, have a different one. Try again.",
            ephemeral=True,
            embed=fancy_embed(
                "Puzzle",
                description=f"Select the Emoji in the Dropdown that can be described with the following Phrase: '{CHOSEN_PHRASE}'",
            ),
            view=VerificationPuzzle(self.cog, CHOSEN_EMOJI, WRONG_OPTIONS),
        )

        self.active = False


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

        self.verifying_users = []

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        return True

    def get_random_puzzle_data(self) -> Tuple[str, str, List[str]]:
        """
        returns: CHOSEN_PHRASE, CHOSEN_EMOJI, wrong_options
        """
        puzzle_options = CONFIG["VERIFICATION"]["PUZZLE_OPTIONS"].copy()

        CHOSEN_PHRASE = random.choice(list(puzzle_options.keys()))
        CHOSEN_EMOJI = random.choice(puzzle_options[CHOSEN_PHRASE])

        del puzzle_options[CHOSEN_PHRASE]
        other_emojis = []
        for _, emojis in puzzle_options.items():
            other_emojis.extend(emojis)

        wrong_options = random.sample(other_emojis, k=4)

        return CHOSEN_PHRASE, CHOSEN_EMOJI, wrong_options

    @commands.Cog.listener()
    async def on_ready(self):
        if CONFIG["VERIFICATION"]["VERIFICATION_MESSAGE_ID"] == None:
            channel = await GetOrFetch.channel(
                self.bot, CONFIG["VERIFICATION"]["VERIFICATION_CHANNEL_ID"]
            )
            if not isinstance(channel, nextcord.TextChannel):
                raise Exception(
                    "Couldnt get verification channel (or its not a TextChannel). Check config."
                )

            msg = await channel.send(
                embed=fancy_embed(
                    "Verification Required",
                    "In order to get access to the Server you must click the button below and solve a little puzzle.",
                ),
                view=VerificationRequired(self),
            )

            CONFIG["VERIFICATION"]["VERIFICATION_MESSAGE_ID"] = msg.id
            CONFIG.save()

        self.bot.add_view(VerificationRequired(self))

    @commands.Cog.listener()
    async def on_member_join(self, member: nextcord.Member):
        if member.guild.id == CONFIG["GENERAL"]["HOME_GUILD_ID"]:
            return

        if member.bot:
            return

        await asyncio.sleep(120)

        if member.id not in self.verifying_users:
            fetched_member = await GetOrFetch.member(member.guild, member.id)
            if fetched_member:
                role_ids = [r.id for r in fetched_member.roles]
            else:
                role_ids = [r.id for r in member.roles]

            if CONFIG["VERIFICATION"]["VERIFIED_ROLE_ID"] not in role_ids:
                await member.kick(reason="Failed to verify.")

        await asyncio.sleep(120)

        fetched_member = await GetOrFetch.member(member.guild, member.id)
        if fetched_member:
            role_ids = [r.id for r in fetched_member.roles]
        else:
            role_ids = [r.id for r in member.roles]

        if CONFIG["VERIFICATION"]["VERIFIED_ROLE_ID"] not in role_ids:
            await member.kick(reason="Failed to verify.")

    @commands.Cog.listener()
    async def on_member_remove(self, member: nextcord.Member):
        while member.id in self.verifying_users:
            self.verifying_users.remove(member.id)

    @nextcord.slash_command(
        "verification",
        default_member_permissions=nextcord.Permissions(administrator=True),
        dm_permission=False,
        guild_ids=[CONFIG["GENERAL"]["HOME_GUILD_ID"]],
    )
    async def verication_top_command(self, interaction: nextcord.Interaction):
        pass

    @verication_top_command.subcommand(
        "add-puzzle", description="Add a verification Puzzle"
    )
    async def add_puzzle(
        self,
        interaction: nextcord.Interaction,
        phrase: str = nextcord.SlashOption(
            "phrase", description="The phrase that describes the emoji you give"
        ),
        emoji: str = nextcord.SlashOption(
            "emoji", description="The emoji that is described by the phrase"
        ),
    ):
        phrase = phrase.casefold().strip().replace("  ", " ")

        if phrase not in CONFIG["VERIFICATION"]["PUZZLE_OPTIONS"]:
            CONFIG["VERIFICATION"]["PUZZLE_OPTIONS"][phrase] = []

        if emoji not in CONFIG["VERIFICATION"]["PUZZLE_OPTIONS"][phrase]:
            CONFIG["VERIFICATION"]["PUZZLE_OPTIONS"][phrase].append(emoji)
            CONFIG.save()

        await interaction.send(
            f"Done.\n'{phrase}' → {emoji} + {len(CONFIG['VERIFICATION']['PUZZLE_OPTIONS'][phrase])-1} more"
        )

    @add_puzzle.on_autocomplete("phrase")
    async def autocomplete_phrase(self, interaction: nextcord.Interaction, phrase: str):
        if not phrase:
            return list(CONFIG["VERIFICATION"]["PUZZLE_OPTIONS"])[:20]

        return [
            x
            for x in CONFIG["VERIFICATION"]["PUZZLE_OPTIONS"]
            if x.startswith(phrase.casefold())
        ][:20]


def setup(bot):
    bot.add_cog(Verification(bot))
