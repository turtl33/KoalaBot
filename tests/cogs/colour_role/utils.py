#!/usr/bin/env python

"""
Testing KoalaBot BaseCog

Commented using reStructuredText (reST)
"""
# Futures

import random
import re
# Built-in/Generic Imports
from typing import List

import discord
# Libs
import discord.ext.test as dpytest
import mock
import pytest
from discord.ext import commands
from sqlalchemy import delete, select

# Own modules
import koalabot
from koala.db import session_manager
from koala.cogs import ColourRole
from koala.cogs import colour_role
from koala.cogs.colour_role.utils import COLOUR_ROLE_NAMING
from koala.cogs.colour_role.db import ColourRoleDBManager
from koala.cogs.colour_role.models import GuildColourChangePermissions, GuildInvalidCustomColourRoles
from tests.tests_utils import last_ctx_cog

# Constants

# Variables
DBManager = ColourRoleDBManager()


async def make_list_of_roles(guild: discord.Guild, length: int) -> List[discord.Role]:
    arr: List[discord.Role] = []
    for i in range(length):
        role = await guild.create_role(name=f"TestRole{i}")
        arr.append(role)
        await arr[i].edit(position=i + 1)
    return arr


def random_colour_str():
    import random
    return hex(random.randint(0, 16777216))


def random_colour() -> discord.Colour:
    import random
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return discord.Colour.from_rgb(r, g, b)


def make_list_of_colours(num: int) -> List[discord.Colour]:
    arr: List[discord.Colour] = []
    for i in range(num):
        arr.append(random_colour())
    return arr


async def make_list_of_custom_colour_roles(guild: discord.Guild, length: int) -> List[discord.Role]:
    arr = []
    for i in range(length):
        role = await guild.create_role(name=f"KoalaBot[{random_colour_str().upper()}]", colour=random_colour())
        arr.append(role)
        await arr[i].edit(position=i + 1)
    return arr


async def make_list_of_protected_colour_roles(guild: discord.Guild, length: int) -> List[discord.Role]:
    arr = []
    for i in range(length):
        role = await guild.create_role(name=f"TestProtectedRole{i}", colour=random_colour())
        arr.append(role)
        await arr[i].edit(position=i + 1)
        DBManager.add_guild_protected_colour_role(guild.id, role.id)
    return arr


def independent_get_protected_colours(guild_id):
    with session_manager() as session:
        rows = session.execute(select(GuildInvalidCustomColourRoles.role_id).filter_by(guild_id=guild_id)).all()
        return [row.role_id for row in rows]


def independent_get_colour_change_roles(guild_id):
    with session_manager() as session:
        rows = session.execute(select(GuildColourChangePermissions.role_id).filter_by(guild_id=guild_id)).all()
        return [row.role_id for row in rows]
