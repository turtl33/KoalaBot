# Built-in/Generic Imports
import math
import time

# Libs
import discord
from discord.ext import commands

# Own modules
import koalabot
from koala.colours import KOALA_GREEN
from koala.db import insert_extension
from koala.utils import extract_id, wait_for_message
from .announce_message import AnnounceMessage
from .db import AnnounceDBManager
from .log import logger
from .utils import ANNOUNCE_SEPARATION_DAYS, SECONDS_IN_A_DAY, MAX_MESSAGE_LENGTH


def announce_is_enabled(ctx):
    """
    A command used to check if the guild has enabled announce
    e.g. @commands.check(announce_is_enabled)

    :param ctx: The context of the message
    :return: True if enabled or test, False otherwise
    """
    try:
        result = koalabot.check_guild_has_ext(ctx, "Announce")
    except PermissionError:
        result = False

    return result or (str(ctx.guild) == koalabot.TEST_USER and koalabot.is_dpytest)


class Announce(commands.Cog):
    """
        Send DM announcements to certain roles and people.
    """

    def __init__(self, bot):
        self.bot = bot
        self.messages = {}
        self.roles = {}
        insert_extension("Announce", 0, True, True)
        self.announce_database_manager = AnnounceDBManager()

    def not_exceeded_limit(self, guild_id):
        """
        Check if enough days have passed for the user to use the announce function
        :return:
        """
        if self.announce_database_manager.get_last_use_date(guild_id):
            return int(time.time()) - self.announce_database_manager.get_last_use_date(
                guild_id) > ANNOUNCE_SEPARATION_DAYS * SECONDS_IN_A_DAY
        return True

    def has_active_msg(self, guild_id):
        """
        Check if a particular id has an active announcement pending announcement
        :param guild_id: The id of the guild of the command
        :return: Boolean of whether there is an active announcement or not
        """
        return guild_id in self.messages.keys()

    def get_role_names(self, guild_id, roles):
        """
        A function to get the names of all the roles the announcement will be sent to
        :param roles: The list of roles in the guild
        :param guild_id: The id of the guild
        :return: All the names of the roles that are tagged
        """
        temp = []
        for role in self.roles[guild_id]:
            temp.append(discord.utils.get(roles, id=role).name)
        return temp

    def get_receivers(self, guild_id, roles):
        """
        A function to get the receivers of a particular announcement
        :param roles: The list of roles in the guild
        :param guild_id: The id of the guild
        :return: All the receivers of the announcement
        """
        temp = []
        for role in self.roles[guild_id]:
            temp += discord.utils.get(roles, id=role).members
        return list(set(temp))

    def receiver_msg(self, guild):
        """
        A function to create a string message about receivers
        :param guild: The guild of the bot
        :return: A string message about receivers
        """
        if not self.roles[guild.id]:
            return f"You are currently sending to Everyone and there are {str(len(guild.members))} receivers"
        return f"You are currently sending to {self.get_role_names(guild.id, guild.roles)} and there are {str(len(self.get_receivers(guild.id, guild.roles)))} receivers "

    def construct_embed(self, guild: discord.Guild):
        """
        Constructing an embedded message from the information stored in the manager
        :param guild: The the guild
        :return: An embedded message for the announcement
        """
        message = self.messages[guild.id]
        embed: discord.Embed = discord.Embed(title=message.title,
                                             description=message.description, colour=KOALA_GREEN)
        embed.set_author(name="Announcement from " + guild.name)
        if message.thumbnail != 'https://cdn.discordapp.com/':
            embed.set_thumbnail(url=message.thumbnail)
        return embed

    @commands.check(announce_is_enabled)
    @commands.group(name="announce")
    async def announce(self, ctx):
        """
        Use k!announce create to create an announcement
        """
        if ctx.invoked_subcommand is None:
            await ctx.send(f"Please use `{koalabot.COMMAND_PREFIX}help announce` for more information")

    @commands.check(announce_is_enabled)
    @announce.command(name="create")
    async def create(self, ctx):
        """
        Create a new message that will be available for sending
        :param ctx: The context of the bot
        :return:
        """
        if not self.not_exceeded_limit(ctx.guild.id):
            remaining_days = math.ceil(
                ANNOUNCE_SEPARATION_DAYS - ((int(time.time()) - self.announce_database_manager.get_last_use_date(
                    ctx.guild.id)) / SECONDS_IN_A_DAY))
            await ctx.send("You have recently sent an announcement and cannot use this function for " + str(
                remaining_days) + " days")
            return
        if self.has_active_msg(ctx.guild.id):
            await ctx.send("There is currently an active announcement being created, you can use 'k!announce cancel' "
                           "or 'k!announce send' to complete it")
        else:
            await ctx.send("Please enter a message, I'll wait for 60 seconds, no rush.")
            message, channel = await wait_for_message(self.bot, ctx)
            if not message:
                await channel.send("Okay, I'll cancel the command.")
                return
            if len(message.content) > MAX_MESSAGE_LENGTH:
                await ctx.send("The content is more than 2000 characters long, and exceeds the limit")
                return
            self.messages[ctx.guild.id] = AnnounceMessage(f"",
                                                          message.content,
                                                          ctx.guild.icon_url)
            self.roles[ctx.guild.id] = []
            await ctx.send(f"An announcement has been created for guild {ctx.guild.name}")
            await ctx.send(embed=self.construct_embed(ctx.guild))
            await ctx.send(self.receiver_msg(ctx.guild))

    @commands.check(announce_is_enabled)
    @announce.command(name="changeTitle")
    async def change_title(self, ctx):
        """
        Change the title of the embedded message
        :param ctx: The context of the bot
        :return:
        """
        if self.has_active_msg(ctx.guild.id):
            await ctx.send("Please enter the new title, I'll wait for 60 seconds, no rush.")
            title, channel = await wait_for_message(self.bot, ctx)
            if not title:
                await channel.send("Okay, I'll cancel the command.")
                return
            self.messages[ctx.guild.id].set_title(title.content)
            await ctx.send(embed=self.construct_embed(ctx.guild))
        else:
            await ctx.send("There is currently no active announcement")

    @commands.check(announce_is_enabled)
    @announce.command(name="changeContent")
    async def change_content(self, ctx):
        """
        Change the content of the embedded message
        :param ctx: The context of the bot
        :return:
        """
        if self.has_active_msg(ctx.guild.id):
            await ctx.send("Please enter the new message, I'll wait for 60 seconds, no rush.")
            message, channel = await wait_for_message(self.bot, ctx)
            if not message:
                await channel.send("Okay, I'll cancel the command.")
                return
            if len(message.content) > MAX_MESSAGE_LENGTH:
                await ctx.send("The content is more than 2000 characters long, and exceeds the limit")
                return
            self.messages[ctx.guild.id].set_description(message.content)
            await ctx.send(embed=self.construct_embed(ctx.guild))
        else:
            await ctx.send("There is currently no active announcement")

    @commands.check(announce_is_enabled)
    @announce.command(name="addRole", aliases=["add"])
    async def add_role(self, ctx):
        """
        Add a role to list of people to send the announcement to
        :param ctx: The context of the bot
        :return:
        """
        if self.has_active_msg(ctx.guild.id):
            await ctx.send("Please enter the roles you want to tag separated by space, I'll wait for 60 seconds, no rush.")
            message, channel = await wait_for_message(self.bot, ctx)
            if not message:
                await channel.send("Okay, I'll cancel the command.")
                return
            for new_role in message.content.split():
                role_id = extract_id(new_role)
                if role_id not in self.roles[ctx.guild.id] and discord.utils.get(ctx.guild.roles,
                                                                                 id=role_id) is not None:
                    self.roles[ctx.guild.id].append(role_id)
            await ctx.send(self.receiver_msg(ctx.guild))
        else:
            await ctx.send("There is currently no active announcement")

    @commands.check(announce_is_enabled)
    @announce.command(name="removeRole", aliases=["remove"])
    async def remove_role(self, ctx):
        """
        Remove a role from a list of people to send the announcement to
        :param ctx: The context of the bot
        :return:
        """
        if self.has_active_msg(ctx.guild.id):
            await ctx.send("Please enter the roles you want to remove separated by space, I'll wait for 60 seconds, no rush.")
            message, channel = await wait_for_message(self.bot, ctx)
            if not message:
                await channel.send("Okay, I'll cancel the command.")
                return
            for new_role in message.content.split():
                role_id = extract_id(new_role)
                if role_id in self.roles[ctx.guild.id]:
                    self.roles[ctx.guild.id].remove(role_id)
            await ctx.send(self.receiver_msg(ctx.guild))
        else:
            await ctx.send("There is currently no active announcement")

    @commands.check(announce_is_enabled)
    @announce.command(name="preview")
    async def preview(self, ctx):
        """
        Post a constructed embedded message to the channel where the command is invoked
        :param ctx: The context of the bot
        :return:
        """
        if self.has_active_msg(ctx.guild.id):
            await ctx.send(embed=self.construct_embed(ctx.guild))
            await ctx.send(self.receiver_msg(ctx.guild))
        else:
            await ctx.send("There is currently no active announcement")

    @commands.check(announce_is_enabled)
    @announce.command(name="send")
    async def send(self, ctx):
        """
        Send a pending announcement
        :param ctx: The context of the bot
        :return:
        """
        if self.has_active_msg(ctx.guild.id):
            embed = self.construct_embed(ctx.guild)
            if self.roles[ctx.guild.id]:
                for receiver in self.get_receivers(ctx.guild.id, ctx.guild.roles):
                    try:
                        await receiver.send(embed=embed)
                    except (discord.Forbidden, AttributeError, discord.HTTPException) as e:
                        logger.error(f'User {receiver.id} cannot recieve dms')
            else:
                for receiver in ctx.guild.members:
                    try:
                        await receiver.send(embed=embed)
                    except (discord.Forbidden, AttributeError, discord.HTTPException) as e:
                        logger.error(f'User {receiver.id} cannot recieve dms')

            self.messages.pop(ctx.guild.id)
            self.roles.pop(ctx.guild.id)
            self.announce_database_manager.set_last_use_date(ctx.guild.id, int(time.time()))
            await ctx.send("The announcement was made successfully")
        else:
            await ctx.send("There is currently no active announcement")

    @commands.check(announce_is_enabled)
    @announce.command(name="cancel")
    async def cancel(self, ctx):
        """
        Cancel a pending announcement
        :param ctx: The context of the bot
        :return:
        """
        if self.has_active_msg(ctx.guild.id):
            self.messages.pop(ctx.guild.id)
            self.roles.pop(ctx.guild.id)
            await ctx.send("The announcement was cancelled successfully")
        else:
            await ctx.send("There is currently no active announcement")


def setup(bot: koalabot) -> None:
    """
    Load this cog to the KoalaBot.
    :param bot: the bot client for KoalaBot
    """
    bot.add_cog(Announce(bot))
    logger.info("announce is ready.")
