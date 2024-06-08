from apscheduler.schedulers.background import BackgroundScheduler
from systemd import journal
import telebot
import mariadb
import uuid
import re
import os
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


dir = os.path.dirname(__file__)
TOKEN = os.environ['Q_TOKEN']
bot = telebot.TeleBot(TOKEN)

variables={}

try:
    conn = mariadb.connect(
        user="wordlerbot",
        password="i4mp455w0rd_",
        host="localhost",
        database="bot_db"

    )
    journal.write(f"Connected well")
    cur = conn.cursor()
except mariadb.Error as e:
    journal.write(f"Error connecting to MariaDB Platform: {e}")
    sys.exit(1)

def set_keyboard(buttons_list):
    w=2
    buttons = [telebot.types.KeyboardButton(i) for i in buttons_list]
    keyboard = telebot.types.ReplyKeyboardMarkup(row_width=w, resize_keyboard=True, one_time_keyboard=True)
    keyboard.add(*buttons)
    
    return keyboard


def present_phrase(chat_id, lng, do_restart=0, phrase_id_logic='ORDER BY RAND() LIMIT 1'):
    journal.write(f"I am presnting {variables}")
    try:
        cur.execute(f"select phrase, source_name, source_author, lang from routelebot_quotes where lang='{lng}' {phrase_id_logic}")
        phrase, source_name, source_author, lang=cur.fetchone()
        
    except mariadb.Error as e:
        journal.write(f"Error in db: {e}")

    if (do_restart == 0):


        sub=''
        match lng:
            case 'en':
                sub='Get quotes daily' if (variables[chat_id]['isScheduled'] == 0) else 'Stop sending me quotes'
            case 'ru':
                sub='Получать цитаты каждый день' if (variables[chat_id]['isScheduled'] == 0) else 'Не хочу больше получать цитаты'
            case _:
                sub=''

        msg=bot.send_message(chat_id, f"{phrase}\n\n{source_author}, <i>{source_name}</i>" , reply_markup=set_keyboard(('Хочу еще одну!' if (lng=='ru') else 'Give me another!', sub)), parse_mode='HTML')

        bot.register_next_step_handler(msg, stateControl)

    if (do_restart == 1):
        msg=bot.send_message(chat_id, f"{phrase}\n\n{source_author}, <i>{source_name}</i>", parse_mode='HTML')
        msg=bot.send_message(chat_id, f"Press /start to go on" if lang=='en' else "Нажмите /start, чтобы продолжить", parse_mode='HTML')


scheduler = BackgroundScheduler({'apscheduler.jobstores.default': {
        'type': 'sqlalchemy',
        'url': 'mysql+pymysql://wordlerbot:i4mp455w0rd_@localhost:3306/bot_db?charset=utf8'
    },
        'apscheduler.executors.default': {
            'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
            'max_workers': '20'
    },
        'apscheduler.executors.processpool': {
        'type': 'processpool',
        'max_workers': '5'
    },
        'apscheduler.job_defaults.coalesce': 'false',
        'apscheduler.job_defaults.max_instances': '3',
        'apscheduler.timezone': 'Europe/Moscow',
    })

scheduler.start()

def schedule_send(message): #time=hh:mm
    chat_id=message.chat.id
    time=message.text
    pattern = re.compile("^[0-2][0-9]:[0-5][0-9]$")
    if (pattern.match(time) == None):
        msg=bot.send_message(chat_id,'Time is incorrect, try again.' if variables[chat_id]['mode']=='en' else 'Некорректный формат времени, попробуйте снова.')
        bot.register_next_step_handler(msg, schedule_send)
        return 
    job_id=str(uuid.uuid4())
    h,m=time.split(':')
    if (h in ('25','26','27','28','29')):
        msg=bot.send_message(chat_id,'Time is incorrect, try again.' if variables[chat_id]['mode']=='en' else 'Некорректный формат времени, попробуйте снова.')
        bot.register_next_step_handler(msg, schedule_send)
        return
    scheduler.add_job(func=present_phrase, trigger='cron', args=[chat_id, variables[chat_id]['mode'], 1], id=job_id, hour=h, minute=m)
    try:
        
        cur.execute(
    "update quotelybot_users set job_id=?", 
    (job_id, ) )
        conn.commit()
    except mariadb.Error as e:
        journal.write(f"Error in db: {e}")
    variables[chat_id]['isScheduled']=1

    sub=''
    match lng:
        case 'en':
            sub='Get quotes daily' if (variables[chat_id]['isScheduled'] == 0) else 'Stop sending me quotes'
        case 'ru':
            sub='Получать цитаты каждый день' if (variables[chat_id]['isScheduled'] == 0) else 'Не хочу больше получать цитаты'
        case _:
            sub=''

    bot.send_message(chat_id,'Request accepted! Press /start to do something else.' if variables[chat_id]['mode']=='en' else 'Принято! Нажмите /start, чтобы продолжить!')
    bot.register_next_step_handler(msg, stateControl)

def unschedule_send(chat_id):
    job_id=''
    try:
        
        cur.execute(
    "select job_id from quotelybot_users where id=?",  
    (chat_id, ))
        job_id=cur.fetchone()[0]
    except mariadb.Error as e:
        journal.write(f"Error in db: {e}")
    if (job_id!=''):
        scheduler.remove_job(job_id)
        try:
        
            cur.execute(
            "update quotelybot_users set job_id=null where id=?", 
            (chat_id, ) )
            conn.commit()
        except mariadb.Error as e:
            journal.write(f"Error in db: {e}")
        variables[chat_id]['isScheduled']=0

    bot.send_message(chat_id,'From now on, we will stop sending you quotes. Press /start, if you want something else!' if variables[chat_id]['mode']=='en' else 'Принято! Нажмите /start, если хотите что-то еще.')
    return



lng = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True, one_time_keyboard=True)
lng_btn1 = telebot.types.KeyboardButton('ENG')
lng_btn2 = telebot.types.KeyboardButton('RUS')
lng.add(lng_btn1, lng_btn2)

# handlers


'''@bot.message_handler(commands=['help'])
def helper(message):
    send_help(message.chat.id)'''

@bot.message_handler(commands=['start', 'go'])

def start_handler(message):
    chat_id = message.chat.id
    name=' '.join(filter(None, (message.chat.first_name, message.chat.last_name)))
    try:
        
        cur.execute(
    "INSERT INTO quotelybot_users (id, name, last_visited, alias) VALUES (?, ?, ?, ?) ON DUPLICATE KEY UPDATE last_visited=?", 
    (chat_id, name, datetime.now(), message.chat.username, datetime.now()) )
        conn.commit()
    except mariadb.Error as e:
        journal.write(f"Error in db: {e}") 

    variables[chat_id] = {'isScheduled':0}

    try:
        
        cur.execute(
    "select case when job_id is not null then 1 else 0 end from quotelybot_users where id=?", 
    (chat_id, ) )
        variables[chat_id]['isScheduled']=cur.fetchone()[0]
        
    except mariadb.Error as e:
        journal.write(f"Error in db: {e}")
    
    msg = bot.send_message(chat_id, 'Выберите язык | Choose your language', reply_markup=lng)

    bot.register_next_step_handler(msg, askLang)

def askLang(message):
    chat_id = message.chat.id
    text = message.text
    if (message.text == '/start'):
        start_handler(message)
        return
    if (text is None or text not in ['ENG', 'RUS']):
        msg=bot.send_message(chat_id, 'Select one of two languages!', reply_markup=lng)
        bot.register_next_step_handler(msg, askLang)
        return
    variables[chat_id]['mode'] = 'ru' if text == 'RUS' else 'en'

    present_phrase(chat_id, variables[chat_id]['mode'])


def stateControl (message):
    chat_id=message.chat.id
    journal.write(f"I am in control of {message.text}")
    match message.text:
        case '/start':
            start_handler(message)
        case 'Хочу еще одну!' | 'Give me another!':
            present_phrase(chat_id, variables[chat_id]['mode'])
        case 'Get quotes daily' | 'Получать цитаты каждый день':
            msg=bot.send_message(chat_id, 'Enter the time when you want to receive quotes. Time must be in hh:mm format.' if variables[chat_id]['mode']=='en' else 'Введите время, в которое хотите получать цитаты, в формате hh:mm')
            bot.register_next_step_handler(msg, schedule_send)
            
        case 'Stop sending me quotes' | 'Не хочу больше получать цитаты':
            unschedule_send(chat_id)
            return
        case _:
            bot.send_message(chat_id, 'Something went wrong, press /start to try again' if variables[chat_id]['mode']=='en' else 'Что-то пошло не так, нажмите /start и попробуйте еще раз')
            return





bot.polling(none_stop=True)


