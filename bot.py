import discord
import dotenv
import os

bot = discord.Bot()


@bot.event
async def on_ready() -> None:
    print("The bot is ready!")


for cog in ["cogs.music"]:
    bot.load_extension(cog)


if __name__ == "__main__":
    dotenv.load_dotenv()
    bot.run(os.getenv("TOKEN"))
