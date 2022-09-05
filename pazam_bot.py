from concurrent.futures import ThreadPoolExecutor, wait
import time
import telegram
import json
import sys, os
from pathlib import Path
from datetime import datetime


#BOT_DIR = f"{Path.home()}\\Downloads"
BOT_DIR = "C:\\CustomCommands"
os.chdir(BOT_DIR)

EMPTY_STRING = ''
TOKEN = ""
DB_FILE = "pazam_db.json"
try:
    with open(DB_FILE, 'r') as db_file:
        try:
            DB = json.load(db_file)
        except json.decoder.JSONDecodeError:
            print(f"Can't decode DB file as JSON")
            sys.exit()
except FileNotFoundError:
    print(f"Can't find DB file under directory {os.getcwd()}")
    sys.exit()


class Command_Methods:
    def join(bot, cmd_args, username, chat_id):
        try:
            args_dict = dict(arg.split('=') for arg in cmd_args)
        except ValueError: # No '=' sign found in command args
            bot.send_message(chat_id=chat_id, text="Invalid format for join command")
            return

        try:
            start = args_dict['start']
            length = args_dict['length']
            hour = args_dict['hour']
        except KeyError as e:
            bot.send_message(chat_id=chat_id, text=f"Invalid args for join command - '{e.args[0]}' argument (or more) is missing")
            return

        with open(DB_FILE, "w") as outfile:
            DB[username] = {'chat_id': chat_id, 'start': start, 'length': length, 'hour': hour}
            json.dump(DB, outfile)
        
        bot.send_message(chat_id=chat_id, text=f"Successfully joined with args {args_dict}")


def daily_pazam_update(bot, username):
    while True:
        now = datetime.today()
        daily_update_dt = datetime.strptime(DB[username]['hour'], "%H:%M").replace(year=now.year, month=now.month, day=now.day)

        if now > daily_update_dt:
            daily_update_dt = daily_update_dt.replace(day=daily_update_dt.day+1)

        time.sleep((daily_update_dt-now).total_seconds())

        total = (calculate_end(username) - datetime.strptime(DB[username]['start'], "%d.%m.%Y")).days
        pazam = calculate_pazam(username)
        
        bot.send_message(chat_id=DB[username]['chat_id'], text=f"Pazam update for {daily_update_dt.date()}: {pazam} days out of {total}, which is {int(pazam/total*100)}%")


def calculate_pazam(username):
    now = datetime.today()
    return (now-datetime.strptime(DB[username]['start'], "%d.%m.%Y")).days


def calculate_end(username):
    start = datetime.strptime(DB[username]['start'], "%d.%m.%Y")
    years, months = map(int, DB[username]['length'].split('.'))
    return start.replace(year=start.year+years if start.month+months<=12 else start.year+years+1, 
                month=start.month+months if start.month+months<=12 else start.month+months%12, 
                                                                            day=start.day-1)

def activate_scheduled_threadpools(bot, futures):
    with ThreadPoolExecutor() as exe:
        for username in DB.keys():
            futures.append(exe.submit(daily_pazam_update, bot, username))


def handle_new_update(bot, last_update):
    print(last_update)
    try:
        message = last_update.message
    except Exception as e:
        print(f"no message exception: {e}")
        return

    author = message.from_user.username
    author_id = message.from_user.id
    text = message.text
    chat = message.chat

    try:
        entities = message.entities[0]
    except IndexError: # No entities - not a bot command
        return
    
    if entities['type'] == 'bot_command' and chat.type == "private": # Bot command
        command_parts = text.split(' ')
        try:
            cmd_to_exe = getattr(Command_Methods, command_parts[0].replace('/', EMPTY_STRING))
        except AttributeError: # Invalid command
            bot.send_message(chat_id=chat.id, text="Invalid command")
            return
        command_parts.remove(command_parts[0])

        cmd_to_exe(bot, command_parts, author, chat.id)


def listen_for_messages(bot):
    last_uid = None
    while True:
        updates = bot.get_updates()
        if len(updates) > 0:
            #print(updates[-1])
            last_update = updates[-1]
            uid = last_update.update_id
            if uid != last_uid:
                last_uid = uid
                handle_new_update(bot, last_update)
        time.sleep(5)


def main():
    futures = []
    bot = telegram.Bot(TOKEN)
    #daily_pazam_update(bot, "LaPingas")
    #listen_for_messages(bot)
    #'''
    with ThreadPoolExecutor() as exe:
        futures.append(exe.submit(listen_for_messages, bot))
        futures.append(exe.submit(activate_scheduled_threadpools, bot, futures))
        wait(futures)
    #'''

    
if __name__ == '__main__':
    main()