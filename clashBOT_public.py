import discord  # used version 1.7.3 (stable); if running this in the future this knowledge will help
from discord.ext import commands
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import random as r
import time

# Initialising sheet access
scope = [
'https://www.googleapis.com/auth/spreadsheets',
'https://www.googleapis.com/auth/drive'
]
creds = ServiceAccountCredentials.from_json_keyfile_name('sheetkey.json', scope)  # sheetkey.json as separate file
client = gspread.authorize(creds)

sheet = client.open("24 Hour Game 2021 Questionnaire (Responses)")  # names of sheets - no need to redact these lol
worksheet_votes = sheet.worksheet("Votes")
worksheet_lootbox = sheet.worksheet("Lootbox Tokens")

sheet2 = client.open("Lootboxes")
worksheet_boxcontents = sheet2.worksheet("Sheet1")  # this sheet points into what is in each lootbox type

# Initialising bot token
TOKEN = 'REDACTED'  # token of bot used for this thing
GUILD = REDACTED  # 24hg discord server id

bot = commands.Bot(command_prefix='!')

bot_actions = REDACTED  # channel id for bot actions, where log of all executed commands are sent

# refs
noah = REDACTED  # discord id for that ref
nick = REDACTED
groves = REDACTED
kit = REDACTED
john = REDACTED

refs = [noah, nick, groves, kit, john]  # list of ref ids

# dictionaries that help to 'bookend' the lists of lootbox objects
# this is just an index
boxconts = {
    "copper": 0,
    "silver": 1,
    "electrum": 2,
    "gold": 3,
    "platinum": 4
}

# this is a bit weirder. gsheets searches 'row-wise' (searches along each row before moving to the next one), rather than
#   'column-wise' (searches each column before moving to the next one). due to item list lengths being different, i manually
#   entered the indexes here, showing that copper has more stuff than silver, which has more stuff than platinum, e.t.c.
#   these are the orders of where the end 'bookend' for each item list shows up when the bookend is searched.
# OPTIMIZATION: have unique names bookends for each box type, e.g. "copper end", and use a dictionary of those.
avgord = {
    "copper": 4,
    "silver": 3,
    "electrum": 0,
    "gold": 1,
    "platinum": 2
}

print("Starting bot")


@bot.event
async def on_ready():  #
    print("on_ready just happened!")
    activity = discord.Activity(name='The CLASH!', type=discord.ActivityType.watching)
    await bot.change_presence(activity=activity)
    channel_ba = bot.get_channel(bot_actions)
    await channel_ba.send("CLASHBOT is now live!")  # tells bot actions channel that bot is live


@bot.command(name='votes', help='Displays the number of votes a character has.')
async def votes(ctx, *sent_text):
    channel_ba = bot.get_channel(bot_actions)  # get bot actions channel
    user = ctx.author  # get user executing command
    user_id = user.id  # get user id of user executing command

    # tell bot channel which user executed this command and any args specified
    # IMPROVEMENT: unpack the list of sent text args, it prints out very uglily
    bot_actions_string = str(user) + " has called the command: !votes " + str(sent_text)
    await channel_ba.send(bot_actions_string)

    # here we see if and how the user hecked up using this command, and if any of these conditions are met
    #   we stop the bot from executing anything further and tell the user that they hecked up
    # OPTIMIZATION: order these from most likely error to least likely error, tiebreak with computing power
    #                   necessary to determine error condition
    if len(sent_text) > 1:  # bot sends error to user if too much text is sent along with command
        await ctx.send("Too much text! Please limit vote search queries to one word if a ref, and no additional text if a player!")
        return
    elif len(sent_text) == 1 and user_id not in refs:  # bot sends error to non-ref if they add any args
        await ctx.send("You don't need to add anything to search queries! Please try again.")
        return
    elif len(sent_text) == 0 and user_id in refs:  # bot sends error to ref if they dont add an arg to specify player
        await ctx.send("Hi ref, I need more information on the player you're trying to get vote numbers on!")
        return

    # now we've established the user executed the command correctly, we actually make calls
    # NOTE: used 'findall' instead of finding one cell to allow for possibility of duplicate cells
    search_tots = worksheet_votes.findall("Total")  # returns list of cells which only contain "Total"
    cell_col = search_tots[0].col  # we only care about the column of this cell, so take that from the first entry in list
    char_cell = worksheet_votes.findall("Character name") # returns list of cells which only contain "Character name"
    char_col = char_cell[0].col  # we only care about the column of this cell, so take that from the first entry in list

    # execute command for ref
    # OPTIMISATION: len(... shouldn't even be here since this condition must be true if a ref and we're here lol
    if len(sent_text) == 1 and user_id in refs:
        sendto = await bot.fetch_user(user_id)
        private_channel = await sendto.create_dm()  # make dm to ref
        arg = sent_text[0]  # this arg will exist on sheet as an identifier of which player is being checked
        search_cell = worksheet_votes.findall(str(arg))
        cell_row = search_cell[0].row  # use reference cell to find correct row
        vote_tot = worksheet_votes.cell(cell_row, cell_col).value  # get vote total
        character = worksheet_votes.cell(cell_row, char_col).value  # get character name
        private_string = str(character) + " has currently been voted for " + str(vote_tot) + " time(s)!"
        public_string = "Hi ref, the vote total of " + str(character) + " has been sent to your dms!"
        await private_channel.send(private_string)  # sends dm to ref of vote total for player
        await ctx.send(public_string)  # tells dm wherever the command was executed that vote total been sent

    # execute command for player
    else:
        search_id = worksheet_votes.findall(str(user_id))  # finds userid of player in sheet
        cell_row = search_id[0].row  # gets correct row
        print(cell_row)  # debug print... i forgot to remove this...
        vote_tot = worksheet_votes.cell(cell_row, cell_col).value  # get vote total
        character = worksheet_votes.cell(cell_row, char_col).value  # get character name
        public_string = str(character) + ", your vote total has been sent to your dms!"
        private_string = str(character) + ", you currently have " + str(vote_tot) + " vote(s)!"
        sendto = await bot.fetch_user(user_id)
        private_channel = await sendto.create_dm()  # make dm to player
        await private_channel.send(private_string)  # send vote total to player dms
        await ctx.send(public_string)  # send confirmation string in channel command wa called in
    bot_actions_string2 = str(user) + " received the private message: \n" + private_string
    await channel_ba.send(bot_actions_string2)  # update bot actions channel on what happened


@bot.command(name='tokenlist', help='Displays the number of lootbox tokens a player has.')
async def tokenlist(ctx, *sent_text):
    channel_ba = bot.get_channel(bot_actions)  # get bot actions channel
    user = ctx.author  # get user calling command
    user_id = user.id  # get user id of user calling command
    bot_actions_string = str(user) + " has called the command: !tokenlist " + str(sent_text)
    await channel_ba.send(bot_actions_string)  # update bot actions

    # error checks
    # OPTIMIZATION: see previous
    if len(sent_text) > 1:
        await ctx.send("Too much text! Please limit token search queries to one word if a ref, and no additional text if a player!")
        return
    if len(sent_text) == 1 and user_id not in refs:
        await ctx.send("You don't need to add anything to search queries! Please try again.")
        return
    if len(sent_text) == 0 and user_id in refs:
        await ctx.send("Hi ref, I need more information on the player you're trying to get token numbers on!")
        return

    # gets all the lootbox columns
    # OPTIMIZATION: this uses a LOT of calls to gsheets. consider:
    #                   1) caching the current sheet to use as reference (perhaps as separate function call?)
    #                   2) download big square in one call instead and use that to determine vals natively
    #                   3) rely on distance between columns being consistent and use one as a reference column
    copper = worksheet_lootbox.findall("Copper")
    cop_col = copper[0].col  # get copper column
    silver = worksheet_lootbox.findall("Silver")
    sil_col = silver[0].col  # get silver column
    electrum = worksheet_lootbox.findall("Electrum")
    elec_col = electrum[0].col  # get electrum column
    gold = worksheet_lootbox.findall("Gold")
    gold_col = gold[0].col  # get gold column
    platinum = worksheet_lootbox.findall("Platinum")
    plat_col = platinum[0].col  # get platinum column
    char_cell = worksheet_lootbox.findall("Character name")
    char_col = char_cell[0].col  # get characters column
    box_cols = [cop_col, sil_col, elec_col, gold_col, plat_col]  # array of columns
    box_vals = ["0", "0", "0", "0", "0"]  # pre initialise array of strings

    # same redundant condition lol, makes call for players
    # OPTIMIZATION: easier to check if a ref than if not a ref, but then again more calls being made by players so...
    if len(sent_text) == 0 and user_id not in refs:
        search_id = worksheet_lootbox.findall(str(user_id))
        cell_row = search_id[0].row  # uses id for reference row
        character = worksheet_lootbox.cell(cell_row, char_col).value  # get character name
        prestring = str(character) + ", you currently have "

    # makes call for ref
    else:
        arg = sent_text[0]  # get player reference arg
        search_cell = worksheet_lootbox.findall(str(arg))
        cell_row = search_cell[0].row  # get reference row from arg
        character = worksheet_lootbox.cell(cell_row, char_col).value  # get character name
        prestring = str(character) + " currently has "

    # iterates through each box, gets correct number of tokens for that player
    for i in range(5):
        box_vals[i] = str(worksheet_lootbox.cell(cell_row, box_cols[i]).value)
    box_vals = box_vals  # what is this for, past noah? left in for posterity

    # constructs the string to be sent to player or ref, prestring dependent
    lootbox_string = prestring + box_vals[0] + " Copper Token(s), " + box_vals[1] + " Silver Token(s), "
    lootbox_string = lootbox_string + box_vals[2] + " Electrum Token(s), " + box_vals[3] + " Gold Token(s), and "
    lootbox_string = lootbox_string + box_vals[4] + " Platinum Token(s)."
    await ctx.send(lootbox_string)  # sends the string to the given location
    bot_actions_string2 = str(user) + " received the message: \n" + lootbox_string
    await channel_ba.send(bot_actions_string2)  # updates bot actions


@bot.command(name='tokenbuy', help='Purchases a type of lootbox token for a player.')
async def tokenbuy(ctx, *sent_text):
    channel_ba = bot.get_channel(bot_actions)  # get bot actions channel
    user = ctx.author  # get user calling command
    user_id = user.id  # get id of user calling command
    bot_actions_string = str(user) + " has called the command: !tokenbuy " + str(sent_text)
    await channel_ba.send(bot_actions_string)  # update bot actions

    # check for user error
    if len(sent_text) > 2:
        await ctx.send("Too much text! Please limit purchases to two terms if a ref, and one term if a player!")
        return
    if len(sent_text) != 1 and user_id not in refs:
        await ctx.send("Only add the lootbox type you intend to purchase! Please try again.")
        return
    if len(sent_text) < 2 and user_id in refs:
        await ctx.send("Hi ref, I need more information on the player you're trying to buy tokens for!")
        return

    # gets box columns. makes lots of calls.
    # OPTIMIZATIONS: see previous for optimizations. Additional: maybe only call the box type the person
    #                   is trying to buy rather than frontloading it?
    copper = worksheet_lootbox.findall("Copper")
    cop_col = copper[0].col  # copper loot box tokens column
    silver = worksheet_lootbox.findall("Silver")
    sil_col = silver[0].col  # silver loot box tokens column
    electrum = worksheet_lootbox.findall("Electrum")
    elec_col = electrum[0].col  # electrum loot box tokens column
    gold = worksheet_lootbox.findall("Gold")
    gold_col = gold[0].col  # gold loot box tokens column
    platinum = worksheet_lootbox.findall("Platinum")
    plat_col = platinum[0].col  # platinum loot box tokens column
    char_cell = worksheet_lootbox.findall("Character name")
    char_col = char_cell[0].col  # character name column

    # dictionary to reference the lootbox type requested. in hindsight frontloading this was definitely a bad idea.
    boxes = {
        "copper": cop_col,
        "silver": sil_col,
        "electrum": elec_col,
        "gold": gold_col,
        "platinum": plat_col
    }

    # player call. more redundant conditions. note: updating the total is done as the LAST CALL so that if we run out
    #  of calls to gsheets we don't end up with weird phantom updates due to running out of calls halfway through
    if len(sent_text) == 1 and user_id not in refs:
        search_id = worksheet_lootbox.findall(str(user_id))  # get row reference cell from user id
        cell_row = search_id[0].row  # get row
        character = worksheet_lootbox.cell(cell_row, char_col).value  # get character name
        boxtype = str(sent_text[0]).lower()  # put lootbox type in all lower case, COPper ==> copper
        box_col = boxes[boxtype]  # use dictionary reference to find correct column
        boxnum_init = worksheet_lootbox.cell(cell_row, box_col).value  # get initial lootbox token total
        boxnum_final = int(boxnum_init) + 1  # add one to get final after purchasing
        worksheet_lootbox.update_cell(cell_row, box_col, str(boxnum_final))  # update lootbox total

        private_string = str(character) + ", you previously had " + str(boxnum_init) + " " + str(sent_text[0])
        private_string = private_string + " lootbox tokens. You now have " + str(boxnum_final) + " tokens."
        await ctx.send(private_string)  # return update confirmation

    # ref call. should have put character call higher to avoid aforementioned hecky wecky with token totals.
    else:
        player = sent_text[0]  # player reference arg
        search_cell = worksheet_lootbox.findall(str(player))  # get row reference cell
        cell_row = search_cell[0].row  # get row
        boxtype = str(sent_text[1]).lower()  # get boxtype
        box_col = boxes[boxtype]  # get column

        boxnum_init = worksheet_lootbox.cell(cell_row, box_col).value  # initial token total
        boxnum_final = int(boxnum_init) + 1  # final token total
        worksheet_lootbox.update_cell(cell_row, box_col, str(boxnum_final))  # update

        character = worksheet_lootbox.cell(cell_row, char_col).value  # get character name
        private_string = str(character) + " had " + str(boxnum_init) + " " + str(sent_text[1])
        private_string = private_string + " lootbox tokens. They now have " + str(boxnum_final) + " tokens."
        await ctx.send(private_string)  # return lootbox token update
    bot_actions_string2 = str(user) + " received the message: \n" + private_string
    await channel_ba.send(bot_actions_string2)  # update bot actions


@bot.command(name='tokenspend', help='Redeems a lootbox token for a player.')
async def tokenspend(ctx, *sent_text):
    channel_ba = bot.get_channel(bot_actions)  # get bot actions channel
    user = ctx.author  # get user calling command
    user_id = user.id  # get id of user calling command
    bot_actions_string = str(user) + " has called the command: !tokenspend " + str(sent_text)
    await channel_ba.send(bot_actions_string)  # update bot actions

    # check for user error
    if len(sent_text) > 2:
        errormsg = "Too much text! Please limit purchases to two terms if a ref, and one term if a player!"
        await ctx.send(errormsg)
        bot_actions_string2 = str(user) + " was told: \n" + errormsg
        await channel_ba.send(bot_actions_string2)
        return
    elif len(sent_text) < 2 and user_id in refs:
        errormsg = "Hi ref, I need more information on the player you're trying to redeem tokens for! Do !tokenspend [player] [boxtype]"
        await ctx.send(errormsg)
        bot_actions_string2 = str(user) + " was told: \n" + errormsg
        await channel_ba.send(bot_actions_string2)
        return
    elif len(sent_text) != 1 and user_id not in refs:
        errormsg = "Only add the lootbox type you intend to spend! Please try again."
        await ctx.send(errormsg)
        bot_actions_string2 = str(user) + " was told: \n" + errormsg
        await channel_ba.send(bot_actions_string2)
        return

    # get all token total columns. see previous function to understand that i regret this design choice.
    copper = worksheet_lootbox.findall("Copper")
    cop_col = copper[0].col
    silver = worksheet_lootbox.findall("Silver")
    sil_col = silver[0].col
    electrum = worksheet_lootbox.findall("Electrum")
    elec_col = electrum[0].col
    gold = worksheet_lootbox.findall("Gold")
    gold_col = gold[0].col
    platinum = worksheet_lootbox.findall("Platinum")
    plat_col = platinum[0].col
    char_cell = worksheet_lootbox.findall("Character name")
    char_col = char_cell[0].col
    boxes = {
        "copper": cop_col,
        "silver": sil_col,
        "electrum": elec_col,
        "gold": gold_col,
        "platinum": plat_col
    }

    # call for refs
    if user_id in refs:
        player = sent_text[0]  # player reference arg
        search_cell = worksheet_lootbox.findall(str(player))  # find reference cell
        cell_row = search_cell[0].row  # find row
        boxtype = str(sent_text[1]).lower()  # get boxtype
        character = worksheet_lootbox.cell(cell_row, char_col).value  # get character name
        box_col = boxes[boxtype]  # get box col
        boxnum_init = worksheet_lootbox.cell(cell_row, box_col).value  # get initial tokens total

        if int(boxnum_init) == 0:  # if player has no tokens, tells them to get one and stops the command
            playerstring = str(character) + " does not have enough lootbox tokens of this type!"
            playerstring = playerstring + " (Try asking them to do !tokenbuy [box type] first!)"
            await ctx.send(playerstring)  # tells the player to acquire capital
            bot_actions_string2 = str(user) + " was told: \n" + playerstring
            await channel_ba.send(bot_actions_string2)  # updates bot actions
            return
        boxnum_final = int(boxnum_init) - 1  # get final number of tokens

        boxnum = boxconts[boxtype]  # finds index of box type for further calls
        itemlists = worksheet_boxcontents.findall("Item")
        itemcell = itemlists[boxnum]  # gets reference cell
        itemcol = itemcell.col  # gets correct column

        itemstrings = worksheet_boxcontents.findall("Order Strings")  # gets reference cell
        stringrow = itemstrings[0].row  # gets row for box content strings

        string = worksheet_boxcontents.cell(stringrow, itemcol).value  # gets string of box contents
        print(string)
        if string == "[]":  # if no more items in list, tells the ref and cancels the command
            await ctx.send("The stockpile of this type of lootbox is empty! Please contact [REDACTED]!")
            return
        string = eval(string)  # turns the string into a list

        # updates number of lootbox tokens. this should be the last call to avoid phantom missing tokens
        worksheet_lootbox.update_cell(cell_row, box_col, str(boxnum_final))

        itemnum = int(string[0])  # finds the reference number for the item
        newstring = string[1::]  # gets the list of items with previous item number removed

        item = worksheet_boxcontents.cell(itemcell.row + itemnum, itemcol).value  # gets item
        quality = worksheet_boxcontents.cell(itemcell.row + itemnum, itemcol + 2).value  # gets item quality
        worksheet_boxcontents.update_cell(stringrow, itemcol, str(newstring))  # updates item string list

        # constructs string to tell player what they got
        publicstring = str(character) + ", you previously had " + str(boxnum_init) + " " + str(sent_text[0])
        publicstring = publicstring + " lootbox token(s). You now have " + str(boxnum_final) + " token(s). "
        publicstring = publicstring + "Within the box you find...\n ```" + item + "!``` \n"
        if quality != None:  # if item has a 'quality' associated with it (e.g. "only says 'oink'"), adds this to string
            publicstring = publicstring + "It has the quality:\n ```" + quality + "```"
        await ctx.send(publicstring)  # sends the string to where command was called

        character = worksheet_lootbox.cell(cell_row, char_col).value  # this is redundant..?
        publicstring = str(character) + " had " + str(boxnum_init) + " " + str(sent_text[1])
        publicstring = publicstring + " lootbox token(s). They now have " + str(boxnum_final) + " token(s)."
        await ctx.send(publicstring)  # updates how many lootbox tokens character has

    # player call
    else:
        search_id = worksheet_lootbox.findall(str(user_id))  # get row reference cell
        cell_row = search_id[0].row  # gets row
        character = worksheet_lootbox.cell(cell_row, char_col).value  # get character name
        boxtype = str(sent_text[0]).lower()  # turn boxtype arg to lowercase
        box_col = boxes[boxtype]  # get column reference
        boxnum_init = worksheet_lootbox.cell(cell_row, box_col).value  # get initial number of lootbox tokens for this type

        if int(boxnum_init) == 0:  # if player has no tokens, tells them to get one and stops the command
            playerstring = str(character) + ", you don't have enough lootbox tokens of this type to redeem this!"
            playerstring = playerstring + " (Try doing !tokenbuy [box type] first!)"
            await ctx.send(playerstring)  # tells player to acquire capital
            bot_actions_string2 = str(user) + " was told: \n" + playerstring
            await channel_ba.send(bot_actions_string2)  # updates bot channel
            return
        boxnum_final = int(boxnum_init) - 1  # get final number of lootbox tokens

        boxnum = boxconts[boxtype]  # get box number
        itemlists = worksheet_boxcontents.findall("Item")  # get cells
        itemcell = itemlists[boxnum]  # get correct column reference cell
        itemcol = itemcell.col  # get column

        itemstrings = worksheet_boxcontents.findall("Order Strings")
        stringrow = itemstrings[0].row  # get row for order strings

        string = worksheet_boxcontents.cell(stringrow, itemcol).value  # get box stockpile string
        print(string)  # debug print left in whoops
        if string == "[]":  # if box stockpile empty,
            await ctx.send("The stockpile of this type of lootbox is empty! Please contact [REDACTED]!")
            return
        string = eval(string)  # turns string into list of item numbers

        itemnum = int(string[0])  # gets item number
        newstring = string[1::]  # gets item list with previous item removed

        worksheet_lootbox.update_cell(cell_row, box_col, str(boxnum_final))  # update player token numbers; should be lower.

        item = worksheet_boxcontents.cell(itemcell.row + itemnum, itemcol).value  # get item
        quality = worksheet_boxcontents.cell(itemcell.row + itemnum, itemcol + 2).value  # get item quality
        worksheet_boxcontents.update_cell(stringrow, itemcol, str(newstring))  # updates

        publicstring = str(character) + ", you previously had " + str(boxnum_init) + " " + str(sent_text[0])
        publicstring = publicstring + " lootbox token(s). You now have " + str(boxnum_final) + " token(s). "
        publicstring = publicstring + "Within the box you find...\n ```" + item + "!``` \n"
        print(quality)  # debug print left in whoops
        if quality != None:  # if item has quality, add this string
            publicstring = publicstring + "It has the quality:\n ```" + quality + "```"
        await ctx.send(publicstring)  # tell player what they got

    bot_actions_string2 = str(user) + " was told: \n" + publicstring
    await channel_ba.send(bot_actions_string2)  # update bot actions
    if newstring == []:  # check if stockpile is empty; if empty, tell the player
        await ctx.send("The stockpile of this type of lootbox is empty! Please contact [REDACTED]!")


@bot.command(name='sequence', help='Generates a random sequence. For ref use only!')
async def sequence(ctx, value):
    channel_ba = bot.get_channel(bot_actions)  # get bot actions channel
    user = ctx.author  # get user executing command
    bot_actions_string = str(user) + " has called the command: !sequence " + str(value)
    await channel_ba.send(bot_actions_string)  # update bot actions
    user_id = user.id  # get id of user executing command
    if user_id not in refs:  # only refs can use command; if not ref using, tell the user and cancel the command
        await ctx.send("Sorry, only refs can use this command!")
        return

    # value is always read in as a string. sometimes it is, e.g. "copper", but it may be number, e.g. "10".
    #   if it is a number, this function will try and convert it into an int without breaking the bot if it's
    #   actually meant to be a string.
    try:
        value = int(value)
    except:
        pass

    if type(value) == int:  # if a number
        numbers = list(range(1, value+1))  # make a list from 1 to [value], inclusive
        r.shuffle(numbers)  # shuffle them into a random order
        await ctx.send(numbers)  # return the shuffled list
    else:  # must be a string

        # check if string is a box type, e.g. "copper", "silver" e.t.c. if it's not, tell the ref and cancel the command.
        if value not in boxconts:
            await ctx.send("Oops, sorry I don't know that one! Try using a lootbox type or a number!")
            return

        # use bookending to pull from sheet. note: this method was done so that stuff could be added to the sheet
        #   without the bot breaking. here, efficiency was traded in for flexibility with other refs being able to
        #   do things.
        itemlists = worksheet_boxcontents.findall("Item")  # get all bookend 1s
        boxnum = boxconts[value]  # find correct bookend for given list
        itemcell = itemlists[boxnum]  # get cell above item list (bookend 1)
        avglists = worksheet_boxcontents.findall("Average")  # this is at the bottom of every list
        ordnum = avgord[value]  # find reference for which item in list is bookend for this box
        stopcell = avglists[ordnum]  # get cell below item list (bookend 2)
        itemnum = stopcell.row - (itemcell.row + 1)  # find total number of items in list

        numbers = list(range(1, itemnum+1))  # make list of numbers from 1 to itemnum inclusive
        r.shuffle(numbers)  # shuffle numbers randomly
        numstring = "List generated! The list is: " + str(numbers) + ". This corresponds to the items: "
        await ctx.send(numstring)  # tell ref the list of numbers
        itemlist = []  # make empty list

        # this is REALLY inefficient. the entire item list should have been imported as a list and calls
        #   should have been made from that.
        for number in numbers:  # for each number in the list
            item = worksheet_boxcontents.cell(itemcell.row + number, itemcell.col).value  # find corresponding item
            itemlist.append(item)  # append item to the list
            time.sleep(0.1)  # manual sleep because hitting 10/sec request limit LMAO
        await ctx.send(itemlist)  # tell the ref the list of items

# bonus command for bot to tell u that it loves u (in reaction emotes)! understanding this function is left as an
#   exercise to the reader.
@bot.command(name='loveu', help=':) <3')
async def loveu(ctx, channel_id, message_id):
    print(channel_id, message_id)
    channel = bot.get_channel(int(channel_id))
    message = await channel.fetch_message(int(message_id))
    emojis = ['\N{SPARKLING HEART}', '\N{REGIONAL INDICATOR SYMBOL LETTER U}', '\N{ROBOT FACE}']
    for emoji in emojis:
        await message.add_reaction(emoji)

# runs the bot
bot.run(TOKEN)


