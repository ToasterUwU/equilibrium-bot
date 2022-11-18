import hashlib
import io
import random

import nextcord
from nextcord.ext import commands

from internal_tools.configuration import CONFIG, JsonDictSaver
from internal_tools.discord import *


class TicketControls(nextcord.ui.View):
    def __init__(self, cog: "TicketSystem"):
        super().__init__(timeout=None)

        self.cog = cog

    @nextcord.ui.button(
        label="Close", custom_id="TicketControls:Close", style=nextcord.ButtonStyle.red
    )
    async def close_ticket(
        self, button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        if not interaction.guild:
            await interaction.send(
                "Something went wrong on Discords side. Try again.", ephemeral=True
            )
            return

        if isinstance(interaction.user, nextcord.User):
            member = await GetOrFetch.member(interaction.guild, interaction.user.id)
        else:
            member = interaction.user

        if not member:
            await interaction.send("Member left while closing Ticket. Thats weird...")
            return

        if interaction.channel_id == None:
            try:
                await interaction.send(
                    "Couldnt get Channel ID, please try again.", ephemeral=True
                )
            except:
                pass
            return

        if not isinstance(interaction.channel, nextcord.Thread):
            interaction_channel = await GetOrFetch.channel(
                self.cog.bot, interaction.channel_id
            )
        else:
            interaction_channel = interaction.channel

        if not isinstance(interaction_channel, nextcord.Thread):
            await interaction.send(
                "This only works with Thread channels as Tickets.", ephemeral=True
            )
            return

        if interaction_channel.archived:
            await interaction.response.pong()
            return

        try:
            ticket_data = self.cog.tickets[interaction.channel_id]
        except:
            await interaction.send(
                "This Ticket doesnt seem to be known by the Bot. Please close it manually by archiving this channel."
            )
            return

        if (
            ticket_data["CREATOR_ID"] != member.id
            and member.guild_permissions.manage_messages == False
        ):
            ticket_category_channel_id = interaction_channel.parent_id
            for category_name, data in CONFIG["TICKET_SYSTEM"]["CATEGORIES"].items():
                if data["CHANNEL_ID"] == ticket_category_channel_id:
                    if data["FIRST_RESPONDER_ROLE_ID"] not in [
                        r.id for r in member.roles
                    ]:
                        try:
                            await interaction.send(
                                "You are not permitted to close this Ticket. Only Moderators, First Responders of this Category, and the Ticket Creator are.",
                                ephemeral=True,
                            )
                        except:
                            pass
                        return

        try:
            if interaction.user:
                await interaction.send(
                    embed=fancy_embed(
                        "Ticket has been closed.",
                        description=f"{interaction.user.mention} has closed this Ticket.\nIf the problem didnt get solved, open a new Ticket.",
                    )
                )
        except:
            pass

        await interaction_channel.edit(archived=True)

    @nextcord.ui.button(
        label="(Un)Claim Ticket",
        custom_id="TicketControls:Claim",
        style=nextcord.ButtonStyle.blurple,
    )
    async def claim_ticket(
        self, button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        if not interaction.guild:
            await interaction.send(
                "Something went wrong on Discords side. Try again.", ephemeral=True
            )
            return

        if isinstance(interaction.user, nextcord.User):
            member = await GetOrFetch.member(interaction.guild, interaction.user.id)
        else:
            member = interaction.user

        if not member:
            await interaction.send("Member left while closing Ticket. Thats weird...")
            return

        if interaction.channel_id == None:
            try:
                await interaction.send("Couldnt get Channel ID, please try again.")
            except:
                pass
            return

        if not isinstance(interaction.channel, nextcord.Thread):
            interaction_channel = await GetOrFetch.channel(
                self.cog.bot, interaction.channel_id
            )
        else:
            interaction_channel = interaction.channel

        if not isinstance(interaction_channel, nextcord.Thread):
            await interaction.send(
                "This only works with Thread channels as Tickets.", ephemeral=True
            )
            return

        if interaction_channel.archived:
            await interaction.response.pong()
            return

        try:
            ticket_data = self.cog.tickets[interaction.channel_id]
        except:
            await interaction.send(
                "This Ticket doesnt seem to be known by the Bot. Please finish it manually close it by archiving this channel."
            )
            return

        if member.guild_permissions.manage_messages == False:
            ticket_category_channel_id = interaction_channel.parent_id
            for category_name, data in CONFIG["TICKET_SYSTEM"]["CATEGORIES"].items():
                if data["CHANNEL_ID"] == ticket_category_channel_id:
                    if data["FIRST_RESPONDER_ROLE_ID"] not in [
                        r.id for r in member.roles
                    ]:
                        try:
                            await interaction.send(
                                "You are not permitted to claim this Ticket. Only Moderators and First Responders of this Category are.",
                                ephemeral=True,
                            )
                        except:
                            pass
                        return

        if ticket_data["CLAIMER_ID"] != member.id:
            new_name = f"{member.display_name}-{self.cog.get_ticket_id(interaction.channel_id)}"

            self.cog.tickets[interaction.channel_id]["CLAIMER_ID"] = member.id
            self.cog.tickets.save()

            try:
                await interaction.send(
                    embed=fancy_embed(
                        f"Ticket has been claimed.",
                        description=f"{member.mention} has claimed this Ticket.\n\nChannel name will be changed as soon as Discords ratelimiting allows it, might be instant, might take a few minutes.",
                    )
                )
            except:
                pass

            await interaction_channel.edit(name=new_name)
        else:
            new_name = f"Ticket-{self.cog.get_ticket_id(interaction.channel_id)}"

            self.cog.tickets[interaction.channel_id]["CLAIMER_ID"] = None
            self.cog.tickets.save()

            try:
                await interaction.send(
                    embed=fancy_embed(
                        f"Ticket has been unclaimed.",
                        description=f"{member.mention} has unclaimed this Ticket.\n\nChannel name will be changed as soon as Discords ratelimiting allows it, might be instant, might take a few minutes.",
                    )
                )
            except:
                pass

            await interaction_channel.edit(name=new_name)


class NewTicket(nextcord.ui.View):
    def __init__(self, cog: "TicketSystem"):
        super().__init__(timeout=None)

        self.cog = cog

        options = [
            nextcord.SelectOption(
                label=key, description=data["DESCRIPTION"], emoji=data["EMOJI"]
            )
            for key, data in CONFIG["TICKET_SYSTEM"]["CATEGORIES"].items()
            if data["SYSTEM_CATEGORY"] == False
        ]

        self.select = nextcord.ui.Select(
            custom_id="NewTicket:CategorySelect",
            placeholder="Please select a Topic",
            row=0,
            options=options,
        )
        self.add_item(self.select)

    @nextcord.ui.button(
        label="Create Ticket",
        custom_id="NewTicket:Create",
        style=nextcord.ButtonStyle.green,
        row=1,
    )
    async def create_ticket(
        self, button: nextcord.ui.Button, interaction: nextcord.Interaction
    ):
        if not interaction.user:
            await interaction.send(
                "Something went wrong on Discords side.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        if len(self.select.values) == 0:
            await interaction.send(
                "You need to select a Topic before creating the Ticket.", ephemeral=True
            )
            return

        ticket = await self.cog.create_ticket(
            category=self.select.values[0],
            creator_id=interaction.user.id,
            initial_message=f"{interaction.user.mention} Here is your Ticket.\n\nPlease describe your issue/question/inquery in full.\nAs soon as you send a message explaining your issue/question/inquery, staff will be notified and will be ready to help you.",
        )

        if ticket:
            await interaction.send(
                f"Ticket created, you can find it here: {ticket.jump_url}",
                ephemeral=True,
            )
        else:
            await interaction.send("Couldnt create a Ticket.", ephemeral=True)


class AutoResponseModal(nextcord.ui.Modal):
    def __init__(self, category_name: str):
        super().__init__(f"Auto Response for Category '{category_name}'", timeout=900)

        self.category_name = category_name

        self.input = nextcord.ui.TextInput(
            "Text",
            style=nextcord.TextInputStyle.paragraph,
            min_length=10,
            max_length=2000,
            required=True,
        )
        self.add_item(self.input)

    async def callback(self, interaction: nextcord.Interaction):
        CONFIG["TICKET_SYSTEM"]["CATEGORIES"][self.category_name][
            "AUTO_RESPOND_TEXT"
        ] = self.input.value
        CONFIG.save()

        await interaction.send("Done.")


class TicketSystem(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.tickets = JsonDictSaver("tickets")

        self.seven_day_archive = None
        self.three_day_archive = None
        self.private_threads = None

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        return True

    async def create_ticket(
        self,
        category: str,
        creator_id: int,
        initial_message: str,
        add_ticket_controls: bool = True,
    ):
        category_data = CONFIG["TICKET_SYSTEM"]["CATEGORIES"][category]
        category_text_channel = await GetOrFetch.channel(
            self.bot, category_data["CHANNEL_ID"]
        )

        if not isinstance(category_text_channel, nextcord.TextChannel):
            return None

        temp_name = f"temp-{random.randint(100, 999)}"
        if self.private_threads:
            thread = await category_text_channel.create_thread(name=temp_name)
        else:
            msg = await category_text_channel.send(temp_name)
            thread = await msg.create_thread(name=temp_name)

            await msg.delete()

        if self.seven_day_archive:
            archive_duration = 10080
        elif self.three_day_archive:
            archive_duration = 4320
        else:
            archive_duration = 1440

        await thread.edit(
            name=f"Ticket-{self.get_ticket_id(thread.id)}",
            locked=True,
            invitable=True if self.private_threads else nextcord.utils.MISSING,
            auto_archive_duration=archive_duration,
        )

        self.tickets[thread.id] = {
            "STARTED": False,
            "CREATOR_ID": creator_id,
            "CLAIMER_ID": None,
        }
        self.tickets.save()

        if add_ticket_controls:
            await thread.send(
                initial_message,
                view=TicketControls(self),
            )
        else:
            await thread.send(initial_message)

        if category_data["AUTO_RESPOND_TEXT"]:
            await thread.send(
                embed=fancy_embed(
                    "Automatic Message", description=category_data["AUTO_RESPOND_TEXT"]
                )
            )

        return thread

    async def autocomplete_category_name(
        self, interaction: nextcord.Interaction, category_name: str
    ):
        if not category_name:
            await interaction.response.send_autocomplete(
                list(CONFIG["TICKET_SYSTEM"]["CATEGORIES"])[:20]
            )
            return

        near_name = [
            c_name
            for c_name in CONFIG["TICKET_SYSTEM"]["CATEGORIES"]
            if c_name.casefold().startswith(category_name.casefold())
        ]
        await interaction.response.send_autocomplete(near_name[:20])

    def get_ticket_id(self, thread_id: int):
        return hashlib.shake_256(str(thread_id).encode()).hexdigest(5)

    def _update_flags(self, home_guild: nextcord.Guild):
        features = [str(x) for x in home_guild.features]

        self.seven_day_archive = "SEVEN_DAY_THREAD_ARCHIVE" in features
        self.three_day_archive = "THREE_DAY_THREAD_ARCHIVE" in features
        self.private_threads = "PRIVATE_THREADS" in features

    async def update_create_ticket_message(self):
        channel = await GetOrFetch.channel(
            self.bot, CONFIG["TICKET_SYSTEM"]["OPEN_TICKET_CHANNEL_ID"]
        )

        if not isinstance(channel, nextcord.TextChannel):
            return

        if CONFIG["TICKET_SYSTEM"]["OPEN_TICKET_MESSAGE_ID"] == None:
            msg = await channel.send(embed=fancy_embed("Placeholder"))
            CONFIG["TICKET_SYSTEM"]["OPEN_TICKET_MESSAGE_ID"] = msg.id
            CONFIG.save()
        else:
            msg = await channel.fetch_message(
                CONFIG["TICKET_SYSTEM"]["OPEN_TICKET_MESSAGE_ID"]
            )

        if len(CONFIG["TICKET_SYSTEM"]["CATEGORIES"]) > 0:
            await msg.edit(
                embed=fancy_embed(
                    "Create a Ticket",
                    description="1. Select a Topic for the Ticket\n2. Click the Button below to create a Ticket with the selected Topic",
                ),
                view=NewTicket(self),
            )
        else:
            await msg.edit(
                embed=fancy_embed(
                    "Ticket System has not been setup yet.",
                    description="There are no Ticket Categories set yet. Use the command to add at least one category.",
                ),
                view=None,
            )

    @commands.Cog.listener()
    async def on_ready(self):
        home_guild = await GetOrFetch.guild(
            self.bot, CONFIG["GENERAL"]["HOME_GUILD_ID"]
        )
        if not home_guild:
            raise Exception("Couldnt get home_guild")

        self._update_flags(home_guild)

        await self.update_create_ticket_message()

        self.bot.add_view(TicketControls(self))

    @commands.Cog.listener()
    async def on_guild_update(self, before: nextcord.Guild, after: nextcord.Guild):
        if before.id == CONFIG["GENERAL"]["HOME_GUILD_ID"]:
            if before.features != after.features:
                self._update_flags(after)

    @commands.Cog.listener()
    async def on_thread_update(self, before: nextcord.Thread, after: nextcord.Thread):
        if before.guild.id == CONFIG["GENERAL"]["HOME_GUILD_ID"]:
            if not before.archived and after.archived:
                if after.id in self.tickets:
                    creator = await GetOrFetch.member(
                        after.guild, self.tickets[after.id]["CREATOR_ID"]
                    )
                    if creator:
                        try:
                            await creator.send(
                                embed=fancy_embed(
                                    "A Ticket you created was closed.",
                                    description=f"Ticket-{self.get_ticket_id(after.id)} has been closed"
                                    f"{' automatically, following the lasting inactivity' if not after.archiver_id else ''}."
                                    "\nClick the following link to see the closed Ticket and all of its contents: {after.jump_url}",
                                )
                            )
                        except:
                            pass

                    del self.tickets[after.id]
                    self.tickets.save()

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: nextcord.Role):
        if role.guild.id == CONFIG["GENERAL"]["HOME_GUILD_ID"]:
            delete_key = None

            for name, data in CONFIG["TICKET_SYSTEM"]["CATEGORIES"].items():
                if data["FIRST_RESPONDER_ROLE_ID"] == role.id:
                    delete_key = name

            if delete_key:
                del CONFIG["TICKET_SYSTEM"]["CATEGORIES"][delete_key]
                CONFIG.save()

                await self.update_create_ticket_message()

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: nextcord.abc.GuildChannel):
        if channel.guild.id == CONFIG["GENERAL"]["HOME_GUILD_ID"]:
            if isinstance(channel, nextcord.TextChannel):
                delete_key = None

                for name, data in CONFIG["TICKET_SYSTEM"]["CATEGORIES"].items():
                    if data["CHANNEL_ID"] == channel.id:
                        delete_key = name

                if delete_key:
                    del CONFIG["TICKET_SYSTEM"]["CATEGORIES"][delete_key]
                    CONFIG.save()

                    await self.update_create_ticket_message()

    @commands.Cog.listener()
    async def on_message(self, msg: nextcord.Message):
        if msg.guild:
            if msg.guild.id == CONFIG["GENERAL"]["HOME_GUILD_ID"]:
                if isinstance(msg.channel, nextcord.Thread):
                    if msg.channel.id in self.tickets:
                        if self.tickets[msg.channel.id]["STARTED"] == False:
                            first_responder_role_id = None
                            system_category = None
                            for name, data in CONFIG["TICKET_SYSTEM"][
                                "CATEGORIES"
                            ].items():
                                if data["CHANNEL_ID"] == msg.channel.parent_id:
                                    first_responder_role_id = data[
                                        "FIRST_RESPONDER_ROLE_ID"
                                    ]
                                    system_category = data["SYSTEM_CATEGORY"]

                            if not msg.author.bot or system_category:
                                self.tickets[msg.channel.id]["STARTED"] = True
                                self.tickets.save()
                                if not isinstance(first_responder_role_id, int):
                                    return

                                first_responder_role = await GetOrFetch.role(
                                    msg.guild, first_responder_role_id
                                )
                                if first_responder_role:
                                    await msg.channel.send(
                                        f"{first_responder_role.mention} A new Ticket has been created."
                                    )

    @nextcord.slash_command(
        "ticket-system",
        default_member_permissions=nextcord.Permissions(administrator=True),
        dm_permission=False,
        guild_ids=[CONFIG["GENERAL"]["HOME_GUILD_ID"]],
    )
    async def top_command(self, interaction: nextcord.Interaction):
        pass

    @top_command.subcommand(
        "add-category",
        description="Add a new Category for Tickets, or edit an existing one (use same name for this).",
    )
    async def add_category(
        self,
        interaction: nextcord.Interaction,
        name: str = nextcord.SlashOption(
            "name",
            description="The name of the Category. Example: 'Discord Issues'",
            required=True,
            max_length=100,
        ),
        description: str = nextcord.SlashOption(
            "description",
            description="Description of the Category. Example: 'Problems with the Discord Server and its channels.'",
            required=True,
            max_length=100,
        ),
        channel: nextcord.TextChannel = nextcord.SlashOption(
            "channel",
            description="The Channel in which the Threads will be created.",
            required=True,
        ),
        first_responder_role: nextcord.Role = nextcord.SlashOption(
            name="first-responder-role",
            description="The Role of the people who are the first to get added to a Ticket in this Category.",
            required=True,
        ),
        emoji: str = nextcord.SlashOption(
            "emoji",
            description="An optional Emoji to display along with the name and description of the Category.",
            required=False,
            default=None,
        ),
        system_category: bool = nextcord.SlashOption(
            "system-category",
            description="If this is True, this category wont be shown to users, and is for Bot use only.",
            required=False,
            default=False,
        ),
    ):
        CONFIG["TICKET_SYSTEM"]["CATEGORIES"][name] = {
            "SYSTEM_CATEGORY": system_category,
            "DESCRIPTION": description,
            "EMOJI": emoji,
            "CHANNEL_ID": channel.id,
            "FIRST_RESPONDER_ROLE_ID": first_responder_role.id,
            "AUTO_RESPOND_TEXT": None,
        }
        CONFIG.save()

        await self.update_create_ticket_message()

        await interaction.send("Done.")

    @top_command.subcommand(
        "rm-category", description="Remove an already existing Category."
    )
    async def rm_category(
        self,
        interaction: nextcord.Interaction,
        category_name: str = nextcord.SlashOption(
            "category-name",
            description="The name of the Category, this is case-sensitive. Example: 'Discord Issues'",
            required=True,
            max_length=100,
            autocomplete_callback=autocomplete_category_name,
        ),
    ):
        if category_name not in CONFIG["TICKET_SYSTEM"]["CATEGORIES"]:
            await interaction.send("This Category doesnt exist.")
            return

        del CONFIG["TICKET_SYSTEM"]["CATEGORIES"][category_name]
        CONFIG.save()

        await self.update_create_ticket_message()

        await interaction.send(
            f"Category '{category_name}' has been deleted.\nThe Channel and the Tickets in it are not being deleted. If you want these to be deleted as well, manually delete the channel which contains the Tickets."
        )

    @top_command.subcommand(
        "set-auto-respond",
        description="Set a Message that gets send automatically when a new Ticket in a specific Category gets created.",
    )
    async def set_auto_respond(
        self,
        interaction: nextcord.Interaction,
        category_name: str = nextcord.SlashOption(
            "category-name",
            description="The name of the Category, this is case-sensitive. Example: 'Discord Issues'",
            required=True,
            max_length=100,
            autocomplete_callback=autocomplete_category_name,
        ),
    ):
        if category_name not in CONFIG["TICKET_SYSTEM"]["CATEGORIES"]:
            await interaction.send("This Category doesnt exist.")
            return

        await interaction.response.send_modal(AutoResponseModal(category_name))

    @top_command.subcommand(
        "clear-auto-respond",
        description="Remove the Auto-Respond message for a specific Category.",
    )
    async def clear_auto_respond(
        self,
        interaction: nextcord.Interaction,
        category_name: str = nextcord.SlashOption(
            "category-name",
            description="The name of the Category, this is case-sensitive. Example: 'Discord Issues'",
            required=True,
            max_length=100,
            autocomplete_callback=autocomplete_category_name,
        ),
    ):
        if category_name not in CONFIG["TICKET_SYSTEM"]["CATEGORIES"]:
            await interaction.send("This Category doesnt exist.")
            return

        CONFIG["TICKET_SYSTEM"]["CATEGORIES"][category_name]["AUTO_RESPOND_TEXT"] = None
        CONFIG.save()

        await interaction.send("Done.")

    @top_command.subcommand(
        "show-categories",
        description="Shows an overview of all Ticket Categories and their settings.",
    )
    async def show_categories(self, interaction: nextcord.Interaction):
        home_guild = await GetOrFetch.guild(
            self.bot, CONFIG["GENERAL"]["HOME_GUILD_ID"]
        )
        if not home_guild:
            await interaction.send(
                "Could not get home_guild. Check the config.", ephemeral=True
            )
            return

        for name, settings in CONFIG["TICKET_SYSTEM"]["CATEGORIES"].items():
            channel = await GetOrFetch.channel(self.bot, settings["CHANNEL_ID"])
            if not isinstance(channel, nextcord.TextChannel):
                await interaction.send(
                    f"Ticket-Channel is missing for {name}", ephemeral=True
                )
                return

            first_responder_role = await GetOrFetch.role(
                home_guild, settings["FIRST_RESPONDER_ROLE_ID"]
            )
            if not first_responder_role:
                await interaction.send(
                    f"First responder role is missing for {name}", ephemeral=True
                )
                return

            fields = {
                "Emoji": "Not set" if settings["EMOJI"] == None else settings["EMOJI"],
                "Folder Channel": channel.mention,
                "First Responder Role": first_responder_role.mention,
                "Auto Reponse Message": "Not set"
                if settings["AUTO_RESPOND_TEXT"] == None
                else "Attached as message.txt",
            }

            embed = fancy_embed(name, settings["DESCRIPTION"], fields=fields)

            file = nextcord.utils.MISSING
            if settings["AUTO_RESPOND_TEXT"]:
                file = nextcord.File(
                    io.StringIO(settings["AUTO_RESPOND_TEXT"]), "message.txt"  # type: ignore
                )

            await interaction.send(embed=embed, file=file)

    @top_command.subcommand(
        "reorder-categories",
        description="Move one specific Category to one specific place in the list.",
    )
    async def reorder_categories(
        self,
        interaction: nextcord.Interaction,
        category_name: str = nextcord.SlashOption(
            "category-name",
            description="The name of the Category, this is case-sensitive. Example: 'Discord Issues'",
            required=True,
            max_length=100,
            autocomplete_callback=autocomplete_category_name,
        ),
        place: int = nextcord.SlashOption(
            "place",
            description="The new place of the Category. 1 is the very top of the list.",
            required=True,
            min_value=1,
        ),
    ):
        if category_name not in CONFIG["TICKET_SYSTEM"]["CATEGORIES"]:
            await interaction.send("This Category doesnt exist.")
            return

        if place > len(CONFIG["TICKET_SYSTEM"]["CATEGORIES"]):
            await interaction.send(
                f"Place {place} is too high, the maximum is {len(CONFIG['TICKET_SYSTEM']['CATEGORIES'])}"
            )
            return

        i = 1
        new_categories = {}
        for name, settings in CONFIG["TICKET_SYSTEM"]["CATEGORIES"].copy().items():
            if i == place:
                new_categories[category_name] = CONFIG["TICKET_SYSTEM"]["CATEGORIES"][
                    category_name
                ].copy()
                i += 1

            if name == category_name:
                continue

            new_categories[name] = settings

            i += 1

        CONFIG["TICKET_SYSTEM"]["CATEGORIES"] = new_categories
        CONFIG.save()

        await self.update_create_ticket_message()

        await interaction.send("Done.")


def setup(bot):
    bot.add_cog(TicketSystem(bot))
