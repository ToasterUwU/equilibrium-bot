import nextcord
from nextcord.ext import commands

from internal_tools.discord import *


class General(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_application_command_check(self, interaction: nextcord.Interaction):
        """
        Everyone can use this.
        """
        return True

    @nextcord.slash_command(
        "help",
        description="Shows information about this Bot and everything that is connected to it.",
        dm_permission=False,
    )
    async def help_command(self, interaction: nextcord.Interaction):
        pages = [
            fancy_embed(
                "Overview",
                description="If you want Information about the Commands and Features of this Bot, please go to the next Page.\n\n"
                "Thanks for inviting Equilibriums Bot.\n\n"
                "Equilibrium started out as an idea of Aki, the Owner and Creator of Equilibrium. (Im writing this, so im gonna talk in the I perspective from now)\n"
                "Since my name starts with A, im often one of the first people to get messages from Scammers and i got frustrated with all these Scammers on Discord. "
                "I started programming little tools that fight against Scammers by attacking their infrastructure. A good example are these Websites that look like the login page of Discord or Steam, but are actually not. "
                "These Websites try to steal login data, so what I did was pretty obvious. I programmed something that spams the Website with fake login data and therefor made the Database of the Scammers practically useless.\n"
                "They even had to take down the Websites multiple times because of things like this. They even upgraded their security in hopes of locking me out. (Didnt work)\n\n"
                "Its not rare that i hear about people loosing their accounts to some Scammer, so i decided to do something. I created Equilibrium, as the opposing force to the Scammers. (Thats the reason for the name)\n\n"
                "Equilibrium is a Discord Server commited to cataloging Scams, warning Discord Users, preventing Scammers from scamming, and also getting Revenge for all those people that got scammed regardless.\n"
                "We have a Announcement channel that you can follow to hear about the newest scams. We will talk about how it works, how to identify it, and also how to waste the most time for those scammers.\n"
                "We are also making tools like the one i made for these websites. Just little tools that people can use to take down scammers websites and other infrastucture.\n"
                "And like you already know, we also have this Discord Bot that bans known bad people even before they can join a Server and try to harm anyone.",
            ),
            fancy_embed(
                "Features and Commands",
                description="So far this Bot has two seperate Features. One is public and can be used by anyone for any Server, the other one requires verification of the Server.\n\n"
                "**1. Impersonation Protection**\n"
                "This part of the Bot lets you protect People from being impersonated.\n"
                "Let me explain why you might want that: Lets assume you have a big Server, with thousands of members. "
                "And this Server is about finances in some way. Something where people talk about money a lot. What a bad guy could do here, is to make an Account that looks just like the Account of a staff member and than send private messages to other memebers, pretending to be part of staff. "
                "They might say that they found a new investment opportunity and convience the victim to give them money, so that they can 'invest it for them'. (This is something i saw happen. And yes, it worked on some people.)\n"
                "By protecting your staff from impersonation, noone will be able to pretend to be them, because this Bot bans everyone who tries.\n"
                f"For a list of commands, please use: {self.bot.cogs['Impersonation'].impersonation_help.get_mention()}\n\n"  # type: ignore
                "**2. Preventive Ban**\n"
                "This is the Part of the Bot that needs verification of the Server you want to use it on. It bans known bad people (people that got banned on multiple servers) on all other servers, even before they join.\n"
                f"To read more about this and find out how to verify your Server and start using this feature, please use: {self.bot.cogs['PreventiveBan'].preventive_ban_help.get_mention()}",  # type: ignore
            ),
        ]

        await CatalogView(pages).start(interaction)


async def setup(bot):
    bot.add_cog(General(bot))
