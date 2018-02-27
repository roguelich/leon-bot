from discord.ext import commands
import asyncio
import json

class Leon(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg_task = self.loop.create_task(self.save_data())
        
    async def load_data(self):
        try: 
            with open("data.txt", "r") as f:
                self.data = json.load(f)
            print("Data for {} succesfully loaded" .format([guild.name for guild in self.guilds]))
            return self.data
        except Exception as e:
            print(e)
            self.data = {}
            for guild in self.guilds:
                self.data[guild.id] = {}
            print("Data for {} succesfully created" .format([guild.name for guild in self.guilds]))
            return self.data
    
    async def save_data(self):
        await self.wait_until_ready()
        await asyncio.sleep(5)
        with open("data.txt", "w") as f:
            await json.dump(self.data, f)
        await asyncio.sleep(600)


bot = Leon(command_prefix ='!leon ')
bot.remove_command('help')
bot.load_extension('LeonCog') 
bot.run('MzkzMzcxMTk2NDYyMjAyODgw.DSZ26Q.lZCbbLEFEQNHvbFW5J5PuIej-6U')
