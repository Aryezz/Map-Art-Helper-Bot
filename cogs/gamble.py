import math
from typing import Annotated

import discord
from discord.ext import commands

from cogs import map_archive
import cogs.checks
from cogs.search import SearchArgumentConverter, SearchArguments, search_entries
import sqla_db


def odds(wins: int, losses: int) -> float:
    return losses / wins * 0.95


def winnings(odds: float, bet: int) -> int:
    return math.floor(odds * bet)


def dubloon_str(n: int) -> str:
    return "dubloon" if n == 1 else "dubloons"


def balance_str(balance: sqla_db.Balance) -> str:
    return f"{balance.balance} {dubloon_str(balance.balance)}"


def total_bets_str(balance: sqla_db.Balance) -> str:
    return f"{balance.total_bets} {dubloon_str(balance.total_bets)}"


class GambleCommands(commands.Cog, name="Gambling"):
    """Commands to lose all your money"""
    def __init__(self, bot: discord.Client):
        self.bot = bot
    
    @cogs.checks.is_staff_or_owner()
    @commands.command(hidden=True)
    async def add_balance(self, ctx: commands.Context, user: discord.User, amount: int):
        """Add to balance"""
        
        async with sqla_db.Session() as db:
            balance = await db.add_balance(user.id, amount)

        await ctx.reply(f"{user.name}'s balance is now {balance.balance} dubloons")
    
    @commands.command(aliases=["bal"])
    async def balance(self, ctx: commands.Context, user: discord.User | None = None):
        """Check a balance"""

        if user is None:
            user = ctx.author
        
        async with sqla_db.Session() as db:
            balance = await db.get_balance(user.id)

        if user.id == ctx.author.id:
            await ctx.reply(f"Your balance is {balance_str(balance)} and you have bet a total of {total_bets_str(balance)}")
        else:
            await ctx.reply(f"{user.name}'s balance is {balance_str(balance)} and they have bet a total of {total_bets_str(balance)}")

    @commands.command()
    async def odds(self, ctx: commands.Context, bet: int | None = 100, *, search_args: Annotated[SearchArguments, SearchArgumentConverter(default_min_size=0, default_order_by="date")]):
        """Check the odds of a search"""

        if bet is None:
            bet = 100
        
        search_results = await search_entries(search_args)

        wins = len(search_results.results)
        losses = search_results.total_maps

        if wins == 0:
            raise commands.BadArgument("can't bet on a search with no results")

        bet_odds = odds(wins, losses)
        await ctx.reply(
            "Your chance of winning this bet is {} / {} = {:.2f}%\n".format(wins, losses, wins / losses * 100) +
            "I will give you odds of {:.2f} : 1, so a bet of {} will win you {} dubloons".format(bet_odds, f"{bet} {dubloon_str(bet)}", winnings(bet_odds, bet))
        )
    
    @commands.command(aliases=["claim"])
    @commands.cooldown(1, 24 * 60 * 60, commands.BucketType.user)
    async def work(self, ctx: commands.Context):
        """Claim 200 dubloons every day"""
        async with sqla_db.Session() as db:
            balance = await db.add_balance(ctx.author.id, 200)

        await ctx.reply(f"Your new balance is {balance_str(balance)}!")

    
    @commands.command(aliases=["bet", "gamba"])
    async def gamble(self, ctx: commands.Context, bet: int, *, search_args: Annotated[SearchArguments, SearchArgumentConverter(default_min_size=0, default_order_by="date")]):
        """Gamble some money on a random map in the archive"""

        if bet <= 0:
            raise commands.BadArgument("can't bet less than 1 dubloon")

        async with sqla_db.Session() as db:
            balance = await db.get_balance(ctx.author.id)

        if bet > balance.balance:
            raise commands.BadArgument("can't bet more than balance")

        async with sqla_db.Session() as db:
            roll = await db.get_random_map()
        
        search_results = await search_entries(search_args)

        if len(search_results.results) == 0:
            raise commands.BadArgument("can't bet on a search with no results")

        won = roll in search_results.results

        if won:
            wins = len(search_results.results)
            losses = search_results.total_maps

            bet_odds = odds(wins, losses)

            bet_winnings = winnings(bet_odds, bet)
        else:
            bet_winnings = 0

        async with sqla_db.Session() as db:
            balance = await db.update_balance(ctx.author.id, won, bet, bet_winnings)

        message = f"You {"won" if won else "lost"}, your new balance is {balance_str(balance)}!"

        await ctx.send(view=map_archive.get_detail_view(roll, message=message))
    
    @commands.command(aliases=[])
    async def leaderboard(self, ctx: commands.Context):
        """Find out who is best at gambling"""
        ranks = {1: "🥇", 2: "🥈", 3: "🥉"}

        def rank_formatter(rank: int, entry: sqla_db.Balance) -> str | None:
            user = self.bot.get_user(entry.discord_id)
            if user is None:
                return None

            return f"**{ranks.get(rank, f'{rank}:')} {user.display_name}** - {balance_str(entry)}, {total_bets_str(entry)} bet in total\n"

        async with sqla_db.Session() as db:
            top_gamblers = await db.get_leaderboard()

        message = f"# Top Gamblers:\n"

        for rank, gambler in enumerate(top_gamblers, start=1):
            message += rank_formatter(rank, gambler)
        
        await ctx.send(message)


async def setup(client):
    await client.add_cog(GambleCommands(client))