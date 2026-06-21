import math
from typing import Annotated

import discord
from discord.ext import commands

from cogs import map_archive, checks
from cogs.search import SearchArgumentConverter, SearchArguments, build_query
import sqla_db


def odds(wins: int, total: int) -> float:
    return total / wins * 0.95


def winnings(odds: float, bet: int) -> int:
    return math.floor(odds * bet)


def doubloon_str(n: int) -> str:
    return "doubloon" if n == 1 else "doubloons"


def balance_str(balance: sqla_db.Balance) -> str:
    return f"{balance.balance} {doubloon_str(balance.balance)}"


def total_bets_str(balance: sqla_db.Balance) -> str:
    return f"{balance.total_bets} {doubloon_str(balance.total_bets)}"


class GambleCommands(commands.Cog, name="Gambling"):
    """Commands to lose all your money"""
    def __init__(self, bot: discord.Client):
        self.bot = bot

    @checks.is_staff_or_owner()
    @commands.command(hidden=True)
    async def add_balance(self, ctx: commands.Context, user: discord.User, amount: int):
        """Add to balance"""
        
        async with sqla_db.Session() as db:
            balance = await db.add_balance(user.id, amount)

        await ctx.reply(f"{user.name}'s balance is now {balance.balance} doubloons")

    @checks.is_staff_or_owner()
    @commands.command(hidden=True)
    async def reset_balance(self, ctx: commands.Context, user: discord.User | None = None):
        """Reset a user"""

        async with sqla_db.Session() as db:
            balance = await db.reset_gambler(user.id)

        await ctx.reply(f"{user.name}'s balance is now {balance.balance} doubloons")

    @checks.is_in_bot_channel()
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

    @checks.is_in_bot_channel()
    @commands.command()
    async def odds(self, ctx: commands.Context, bet: int | None = 100, *, search_args: Annotated[SearchArguments, SearchArgumentConverter(default_min_size=0, default_order_by="date")]):
        """Check the odds of a search

        Usage: !!odds [bet] search_args

        Parameters
        ----------
        bet : int, optional
            amount of doubloons to bet
        search_args : list, optional
            same search format as !!search
        """

        if bet is None:
            bet = 100

        async with sqla_db.Session() as db:
            query_builder = db.get_query_builder()

            build_query(search_args, query_builder)

            total_count, win_count, _, _ = await db.roll_gamble(query_builder.query)

        if win_count == 0:
            raise commands.BadArgument("can't bet on a search with no results")

        bet_odds = odds(win_count, total_count)
        await ctx.reply(
            "Your chance of winning this bet is {} / {} = {:.2f}%\n".format(win_count, total_count, win_count / total_count * 100) +
            "I will give you odds of {:.2f} : 1, so a bet of {} will win you {} doubloons".format(bet_odds, f"{bet} {doubloon_str(bet)}", winnings(bet_odds, bet))
        )

    @checks.is_in_bot_channel()
    @commands.command(aliases=["claim"])
    @commands.cooldown(1, 24 * 60 * 60, commands.BucketType.user)
    async def work(self, ctx: commands.Context):
        """Claim 200 doubloons every day (+ 50 extra if you boost this server)"""
        is_booster = any(role.is_premium_subscriber() for role in ctx.author.roles)
        reward = 250 if is_booster else 200

        async with sqla_db.Session() as db:
            balance = await db.add_balance(ctx.author.id, reward)

        claim_msg = f"{reward} doubloons claimed"

        if is_booster:
            claim_msg += " (50 bonus for boosting this guild)"

        claim_msg += f", your new balance is {balance_str(balance)}!\nCheck back tomorrow to work again."

        await ctx.reply(claim_msg)

    @checks.is_in_bot_channel()
    @commands.command(aliases=["bet", "gamba"])
    @commands.max_concurrency(1, per=commands.BucketType.user, wait=True)
    async def gamble(self, ctx: commands.Context, bet: int, *, search_args: Annotated[SearchArguments, SearchArgumentConverter(default_min_size=0, default_order_by="date")]):
        """Gamble some money on a random map in the archive

        Usage: !!gamble bet search_args

        Parameters
        ----------
        bet : int, optional
            amount of doubloons to bet
        search_args : list, optional
            same search format as !!search
        """

        if bet <= 0:
            raise commands.BadArgument("can't bet less than 1 doubloon")

        async with sqla_db.Session() as db:
            balance = await db.get_balance(ctx.author.id)

        if bet > balance.balance:
            raise commands.BadArgument("can't bet more than balance")
        
        async with sqla_db.Session() as db:
            query_builder = db.get_query_builder()

            build_query(search_args, query_builder)

            total_count, win_count, won, roll = await db.roll_gamble(query_builder.query)

        if win_count == 0:
            raise commands.BadArgument("can't bet on a search with no results")

        if won:
            bet_odds = odds(win_count, total_count)

            bet_winnings = winnings(bet_odds, bet)
        else:
            bet_winnings = 0

        async with sqla_db.Session() as db:
            balance = await db.update_balance(ctx.author.id, won, bet, bet_winnings)

        message = f"You {"won" if won else "lost"}, your new balance is {balance_str(balance)}!"

        await ctx.send(view=map_archive.get_detail_view(roll, message=message))

    @checks.is_in_bot_channel()
    @commands.command(aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context):
        """Find out who is best at gambling"""
        ranks = {1: "🥇", 2: "🥈", 3: "🥉"}

        def rank_formatter(rank: int, entry: sqla_db.Balance) -> str:
            user = self.bot.get_user(entry.discord_id)

            display_name = discord.utils.escape_markdown(discord.utils.escape_mentions(user.display_name)) if user is not None else "unknown user"
            user_name = "\u202A" + display_name + "\u202C"

            return f"**{ranks.get(rank, f'{rank}:')} {user_name}** - {balance_str(entry)}, {total_bets_str(entry)} bet in total\n"

        async with sqla_db.Session() as db:
            top_bals, top_bets = await db.get_leaderboard(limit=5)

        message = "# Richest Gamblers:\n"

        for rank, gambler in enumerate(top_bals, start=1):
            message += rank_formatter(rank, gambler)

        message += "# Most Addicted Gamblers:\n"

        for rank, gambler in enumerate(top_bets, start=1):
            message += rank_formatter(rank, gambler)
        
        await ctx.send(message)


async def setup(client):
    await client.add_cog(GambleCommands(client))