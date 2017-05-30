from discord.ext import commands
from discord.ext.commands import errors as commands_errors
from discord import utils as dutils
from utils.dataIO import dataIO
import traceback
import redis
import argparse
import json

with open("config.json") as f:
    config = json.load(f)

redis_host = config.get('AMETHYST_REDIS_HOST') or 'localhost'
redis_pass = config.get('AMETHYST_REDIS_PASSWORD')
redis_port = int(config.get('AMETHYST_REDIS_PORT') or 6379)
redis_db = int(config.get('AMETHYST_REDIS_DB') or 0)
token = config.get('AMETHYST_TOKEN')
prefix = config.get('AMETHYST_PREFIX')

# CMD-L Arguments
parser = argparse.ArgumentParser()
redis_grp = parser.add_argument_group('redis')
redis_grp.add_argument('--host', type=str,
                       help='the Redis host', default=redis_host)
redis_grp.add_argument('--port', type=int,
                       help='the Redis port', default=redis_port)
redis_grp.add_argument('--db', type=int,
                       help='the Redis database', default=redis_db)
redis_grp.add_argument('--password', type=str,
                       help='the Redis password', default=redis_pass)
args = parser.parse_args()

# Redis Connection Attempt... hopefully works.
try:
    redis_conn = redis.StrictRedis(host=args.host,
                                   port=args.port,
                                   db=args.db,
                                   password=args.password)
except:
    print('aaaaaaa unable to redis 404')
    exit(2)


class Amethyst(commands.Bot):
    def __init__(self, command_prefix, args, redis, **options):
        super().__init__(command_prefix, **options)
        self.args = args
        self.redis = redis
        self.owner = None
        self.send_command_help = send_cmd_help
        self.settings = dataIO.load_json('settings')
        self.blacklist_check = self.loop.create_task(self.blacklist_check())

    async def blacklist_check(self):
        if 'blacklist' not in self.settings:
            self.settings['blacklist'] = []
        else:
            pass

    async def on_ready(self):
        self.redis.set(
            '__info__',
            'This database is being used by the Amethyst Framework.')
        app_info = await self.application_info()
        self.invite_url = dutils.oauth_url(app_info.id)
        self.owner = str(app_info.owner.id)
        print('Ready.')
        print(self.invite_url)
        print(self.user.name)

        self.load_extension('modules.core')

    async def on_command_error(self, exception, context):
        if isinstance(exception, commands_errors.MissingRequiredArgument):
            await self.send_command_help(context)
        elif isinstance(exception, commands_errors.CommandInvokeError):
            exception = exception.original
            _traceback = traceback.format_tb(exception.__traceback__)
            _traceback = ''.join(_traceback)
            error = ('`{0}` in command `{1}`: ```py\n'
                     'Traceback (most recent call last):\n{2}{0}: {3}\n```')\
                .format(type(exception).__name__,
                        context.command.qualified_name,
                        _traceback, exception)
            await context.send(error)
        elif isinstance(exception, commands_errors.CommandNotFound):
            pass

    async def on_message(self, message):
        if message.author.bot:
            return
        if message.author.id in self.settings['blacklist']:
            return
        await self.process_commands(message)


async def send_cmd_help(ctx):
    if ctx.invoked_subcommand:
        _help = await ctx.bot.formatter.format_help_for(ctx,
                                                        ctx.invoked_subcommand)
    else:
        _help = await ctx.bot.formatter.format_help_for(ctx, ctx.command)
    for page in _help:
        await ctx.send(page)


amethyst = Amethyst(prefix, args, redis_conn)
amethyst.run(token)
