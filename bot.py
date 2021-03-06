import discord
from discord.ext import commands
import re
import asyncio
from tf_logs import get_player_log_list, get_latest_log_descr, get_log, summarize_log, get_latest_log
from steam_api import get_steam_id_64
from log_user import LogUser
from events import Events


CMD_PREFIX = '!'


class LogBot(commands.Bot):
    __events__ = ('on_subscribe', 'on_unsubscribe')
    def __init__(self, bot_token, steam_api_key):
        super(LogBot, self).__init__(command_prefix=CMD_PREFIX)
        self.bot_token = bot_token
        self.steam_api_key = steam_api_key
        self.subscribed_users = []
        self.events = Events()

        self._apply_commands()


    def run(self):
        super(LogBot, self).run(self.bot_token)


    def get_subscribed_user(self, discord_user_id=None, steam_id_64=None):
        for u in self.subscribed_users:
            if u.contains(discord_user_id, steam_id_64):
                return u
        return None


    def subscribe_user(self, discord_user_id, steam_id_64):
        u = self.get_subscribed_user(discord_user_id, steam_id_64)
        if u != None or discord_user_id == None or steam_id_64 == None:
            return False

        u = LogUser(discord_user_id, steam_id_64)
        self.subscribed_users.append(u)

        self.events.on_subscribe(self, u) #fire on_subscribe event

        return True


    def unsubscribe_user(self, discord_user_id=None, steam_id_64=None):
        u = self.get_subscribed_user(discord_user_id, steam_id_64)

        if u == None:
            return False

        self.subscribed_users.remove(u)

        self.events.on_unsubscribe(self, u) #fire on_unsubscribe event

        return True


    async def fetch_user(self, user):
        return await super(LogBot, self).fetch_user(user.discord_user_id)


    async def log_update_loop(self):
        while True:
            log_dict = {} #contains all logs of current update with log id as key
            for user in self.subscribed_users:
                
                log_list = get_player_log_list(user.steam_id_64)
                log_desc = get_latest_log_descr(log_list)

                if user.latest_log_id == None: #only run in the initial log request of user
                    user.latest_log_id = log_desc["id"]

                elif user.latest_log_id != log_desc["id"]:
                    user.latest_log_id = log_desc["id"]
                    fetch = asyncio.create_task(self.fetch_user(user))

                    if log_desc["id"] in log_dict:
                        log = log_dict[log_desc["id"]]
                    else:
                        log = get_log(log_desc)
                        log_dict[log_desc["id"]] = log

                    summary = summarize_log(log, log_desc)
                    await fetch
                    user_obj = fetch.result()
                    channel = await user_obj.create_dm()
                    await channel.send(summary)

                    print(f"Log[{user.latest_log_id}] sent to {user_obj.name}, {user.steam_id_64}.")

            await asyncio.sleep(30)
            

    async def on_ready(self):
        print('Logged on as {0}!'.format(self.user))

        #start log update loop
        asyncio.create_task(self.log_update_loop())


    async def on_message(self, message):
        if message.author == self.user:
            return

        await self.process_commands(message)

        if message.author.dm_channel != None and message.channel.id == message.author.dm_channel.id and not message.content.startswith(CMD_PREFIX): #only direct message
            print('Message from {0.author}: {0.content}'.format(message))
            #profile = await message.author.profile()
            #print(profile.connected_accounts)

            await message.channel.send("Greetings, to find out how to use me type !help.")
            
    
    def _apply_commands(self):
        @self.command(brief="Needs your steam profile url. Adds you to the subscribed list.")
        async def subscribe(ctx, profile_url):
            steam_id_64 = get_steam_id_64(profile_url, self.steam_api_key)
            succ = self.subscribe_user(ctx.message.author.id, steam_id_64)
            if succ:
                await ctx.send("You are now subscribed and will receive Logs!")
            else:
                await ctx.send("You could not be subscribed.")


        @self.command(brief="Needs your steamID64. Adds you to the subscribed list.")
        async def subscribeid(ctx, steam_id_64):
            succ = self.subscribe_user(ctx.message.author.id, steam_id_64)
            if succ:
                await ctx.send("You are now subscribed and will receive Logs!")
            else:
                await ctx.send("You could not be subscribed.")


        @self.command(brief="Removes you from the subscribed list.")
        async def unsubscribe(ctx):
            succ = self.unsubscribe_user(ctx.message.author.id)
            if succ:
                await ctx.send("You are now unsubscribed and will not receive Logs!")
            else:
                await ctx.send("You could not be unsubscribed.")


        @self.command(brief="Returns you latest log")
        async def latest(ctx, steam_id_64=None):
            if steam_id_64 == None:
                u = self.get_subscribed_user(ctx.message.author.id)
                if(u == None):
                    await ctx.send("You need to be subscribed or add a steamID64 to use this command!")
                    return
                else:
                    steam_id_64 = u.steam_id_64
            
            summary = get_latest_log(steam_id_64)
            await ctx.send(summary)


        @subscribe.error
        async def info_error(ctx, error):
            print(error)
            if isinstance(error, commands.MissingRequiredArgument):
             await ctx.send('You have forgotten your profile url!')

                    

                    



