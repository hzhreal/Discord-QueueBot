import discord
from discord.ext import commands, tasks
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
BOT_CHANNEL_ID = int(os.getenv("BOT_CHANNEL_ID"))
QUEUE_CHANNEL_ID = int(os.getenv("QUEUE_CHANNEL_ID"))
ROLE_NAME = str(os.getenv("ROLE_NAME"))

activity = discord.Activity(type=discord.ActivityType.watching, name="HTO")
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=">", activity=activity, intents=intents)
@bot.event
async def on_ready() -> None:
    print(
        f"Bot is ready, invite link: https://discord.com/api/oauth2/authorize?client_id={bot.user.id}&permissions=8&scope=bot"
    )
@bot.event
async def on_message(message) -> None:
    if message.author.bot:
        return

    if message.content == "hello":
        await message.channel.send("hi")

    await bot.process_commands(message)

embed_missing_role = discord.Embed(title="Missing role",
                      description="Only the owner can use this command.",
                      color=0xFF0000)

embed_missing_role.set_thumbnail(url="https://cdn.discordapp.com/attachments/1133691278001979412/1145824413229522974/85204668-serious-bearded-male-security-guard-says-no-making-x-sign-shape.png")

embed_missing_role.set_footer(text="Made by: hzh.")

queue_list = []
update_role_running = True
first_user_pinged = False

@tasks.loop(seconds=1)
async def idleListener(ctx, bot) -> None:
    global first_user_pinged, queue_list

    if len(queue_list) >= 1:
        target = queue_list[0]

        def check(message):
            if len(queue_list) >= 1: return message.author == target

        try:
            message = await bot.wait_for('message', check=lambda message:check(message), timeout=480) # how many seconds until idle kick
            print(f"Obtained: {message.content}")
        except asyncio.TimeoutError:
            try:
                target_channel = ctx.guild.get_channel(BOT_CHANNEL_ID) # bot channel id 
                await target_channel.purge(limit=200)
                print(f"purged {target_channel}")
                role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME) # role name
                queue_list.remove(target)
                await target.remove_roles(role)
                first_user_pinged = False
                print(f"{target} has idled, now removed\nCurrent queue:\n{queue_list}")
            except Exception as e:
                print(f"Error: {e}")

async def changeperm(ctx) -> None:
    try:
        role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME) # role name
        target_channel = ctx.guild.get_channel(BOT_CHANNEL_ID) # bot channel id
        target_channel2 = ctx.guild.get_channel(QUEUE_CHANNEL_ID) # queue channel id
        await target_channel2.set_permissions(ctx.guild.default_role, send_messages=False) # makes the channel you run the command in read only for @everyone
        await target_channel.set_permissions(ctx.guild.default_role, send_messages=False)
        await target_channel.set_permissions(role, send_messages=True)
        print("changed perms")

        
    except Exception as e:
        # Handle any exceptions that occur during the permission modification
        print(f"Cant change permissions: {e}")

@commands.has_role("Owner")
@bot.slash_command(description="Start the queue.")
async def queue(ctx) -> None:
    global queue_list, update_role_running, first_user_pinged

    update_role_running = True
    first_user_pinged = False
    target_channel2 = ctx.guild.get_channel(QUEUE_CHANNEL_ID) # queue channel id

    await ctx.respond("Starting", ephemeral=True)

    await changeperm(ctx)

    class queuebutton(discord.ui.View):

        def __init__(self):
            super().__init__(timeout=None) # specify the timeout here

        @discord.ui.button(label="Join queue", style=discord.ButtonStyle.success)
        async def callback(self, button, interaction) -> None:
            global first_user_pinged

            author = interaction.user  # Get the author of the interaction (the user who clicked)

            if author in queue_list:
                if author == queue_list[0]:
                    try:
                        target_channel = ctx.guild.get_channel(BOT_CHANNEL_ID) # bot channel id 
                        await target_channel.purge(limit=200)
                        print(f"purged {target_channel}")
                    except Exception as e:
                        print(f"Error purging: {e}")
                    queue_list.remove(author)  # Remove the user from the queue
                    role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME) # role name
                    await author.remove_roles(role)
                    await interaction.response.send_message("Left queue", ephemeral=True)
                    first_user_pinged = False
                else:
                    queue_list.remove(author)  # Remove the user from the queue
                    await interaction.response.send_message("Left queue", ephemeral=True)

            else:
                queue_list.append(author)
                await interaction.response.send_message("Joined queue", ephemeral=True)

    # Create the initial embed with the list of users in the queue
    queue_text = '\n'.join([str(user) for user in queue_list])
    embed = discord.Embed(title="Entry", 
                          description=f"Queue:\n{queue_text}",
                          color=0x22EA0D)
    
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1133691278001979412/1145825848801370203/3d-security-agent-pointing-to-empty-wall.png")

    embed.set_footer(text="Made by: hzh.")

    # Send the initial embed and view
    message = await target_channel2.send(embed=embed, view=queuebutton())

    @tasks.loop(seconds=1)  # Adjust the update interval as needed
    async def update_queue_embed() -> None:
        nonlocal queue_text
        global first_user_pinged

        new_queue_text = '\n'.join([str(user) for user in queue_list])

        if new_queue_text != queue_text:
            queue_text = new_queue_text
            updated_embed = discord.Embed(title="Entry", description=f"Queue:\n{queue_text}", color=0x22EA0D)
            updated_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1133691278001979412/1145825848801370203/3d-security-agent-pointing-to-empty-wall.png")

            updated_embed.set_footer(text="Made by: hzh.")
            await message.edit(embed=updated_embed)  # Use message.edit to update the embed

        if len(queue_list) > 0:
            first_in = queue_list[0]
                  
            # Assuming "HTOS-pass" is a role object, you should add the role, not just a string
            role = discord.utils.get(ctx.guild.roles, name="HTOS-pass") # role name
            await first_in.add_roles(role)
            if not first_user_pinged:
                target_channel = ctx.guild.get_channel(BOT_CHANNEL_ID) # bot channel id
                await asyncio.sleep(2.5)
                await target_channel.send(f"It is your turn {first_in.mention}, please click the join queue button again when you are finished to leave the queue.")
                first_user_pinged = True
                
        if not update_role_running:
            update_queue_embed.stop()
            print("stopped loop")  # Stop the loop
            return

    update_queue_embed.start()
    idleListener.start(ctx, bot)

@queue.error
async def role_error(ctx, error) -> None: 
    if isinstance(error, commands.MissingRole):
        await ctx.respond(embed=embed_missing_role)

@commands.has_role("Owner")
@bot.slash_command(description="End the queue.")
async def end(ctx) -> None:
    global update_role_running, queue_list

    await ctx.respond("Shutting down queue.", ephemeral=True)

    update_role_running = False
    queue_list = []

    role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME) # role name

    await role.delete()
    print("deleted role")

   
    await ctx.guild.create_role(name=ROLE_NAME) # role name
    print("created role")

    try:
        target_channel = ctx.guild.get_channel(BOT_CHANNEL_ID) # bot channel id
        target_channel2 = ctx.guild.get_channel(QUEUE_CHANNEL_ID) # queue channel id
        await target_channel.purge(limit=200)
        print(f"purged {target_channel}")
        await target_channel2.purge(limit=10)
        print(f"purged {target_channel2}")
    except Exception as e:
        print(f"Error purging: {e}")

    await ctx.respond("Shut down queue.", ephemeral=True)
            
@end.error
async def role_error1(ctx, error) -> None:
    if isinstance(error, commands.MissingRole):
        await ctx.respond(embed=embed_missing_role)

@bot.slash_command(description="Removes an user from the queue.")
@commands.has_any_role("Owner", "Admin", "Mod")
async def remove(ctx, user: discord.Member) -> None:
    global first_user_pinged, queue_list

    embedrm = discord.Embed(title="Remove user", description=f"Removed {user} from list.", color=discord.Color.green())
    embedrm.set_thumbnail(url="https://cdn.discordapp.com/attachments/1133691278001979412/1145825848801370203/3d-security-agent-pointing-to-empty-wall.png")
            
    embedrm.set_footer(text="Made by: hzh.")

    if len(queue_list) == 0:
        embederror1 = discord.Embed(title="Error: Empty queue", description="The queue is empty.", color=discord.Color.red())
        embederror1.set_thumbnail(url="https://cdn.discordapp.com/attachments/1133691278001979412/1145825848801370203/3d-security-agent-pointing-to-empty-wall.png")
            
        embederror1.set_footer(text="Made by: hzh.")

        await ctx.respond(embed=embederror1)
       
    elif user == queue_list[0]:
            try:
                target_channel = ctx.guild.get_channel(BOT_CHANNEL_ID) # bot channel id 
                await target_channel.purge(limit=200)
                print(f"purged {target_channel}")
            except Exception as e:
                print(f"Error purging: {e}")
            role = discord.utils.get(ctx.guild.roles, name=ROLE_NAME) # role name
            queue_list.remove(user)
            await user.remove_roles(role)
            first_user_pinged = False
            await ctx.respond(embed=embedrm)
            return
            
    elif user in queue_list:
        queue_list.remove(user)  # Remove the user from the queue
        await ctx.respond(embed=embedrm)

    else:
        embederror = discord.Embed(title="Error: Invalid user", description=f"{user} is not present in the queue.", color=discord.Color.red())
        embederror.set_thumbnail(url="https://cdn.discordapp.com/attachments/1133691278001979412/1145825848801370203/3d-security-agent-pointing-to-empty-wall.png")
            
        embederror.set_footer(text="Made by: hzh.")
        await ctx.respond(embed=embederror)


@remove.error
async def role_error2(ctx, error) -> None:
    if isinstance(error, commands.MissingAnyRole):
        await ctx.respond(embed=embed_missing_role)

@bot.slash_command(description="Pings the bot.")
async def ping(ctx) -> None:
    latency = bot.latency * 1000
    await ctx.respond(f"Pong! {latency: .2f}ms.")     

@bot.command()
@commands.has_role("Owner")
async def echo(ctx, *, message: str) -> None:
    if ctx.message.author.guild_permissions.manage_messages:
        await ctx.channel.purge(limit=1)
    await ctx.send(message) 

bot.run(str(os.getenv("TOKEN"))) # token
