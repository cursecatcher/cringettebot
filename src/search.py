#-*- coding: utf-8 -*-

import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    Update, 
    ParseMode
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext
)
from emoji import emojize

import view 
from statements import Statements as stm 

import keyboardz as kb 
from states import (
    ChatState, 
    DataEntry as de
)
from db.managers import DBManager, PersistencyManager


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

def welcome(update: Update, context: CallbackContext) -> ChatState:
    logger.info("Welcome")
    text = "Che ricerca??" 

    args = dict(
        text=text, 
        reply_markup=kb.search_keyboard)   
    context.user_data[de.BUFFER] = list() 

    try:
        update.callback_query.answer()
        update.callback_query.edit_message_text(
            text=text, 
            reply_markup=kb.search_keyboard)
    except AttributeError:
        context.user_data[de.LAST] = update.message.reply_text(**args)

    return ChatState.WHICH_SEARCH


def init_search(update: Update, context: CallbackContext) -> ChatState:
    logger.info("Che vuoi cercare?")
    update.callback_query.answer() 

    if not (search_type := context.user_data.get(de.SEARCH_TYPE)):
        search_type = update.callback_query.data
        context.user_data[de.SEARCH_TYPE] = search_type #nb. storing str(enum) instead of enum

    text = (
        "Inserisci i nomi degli ingredienti" 
        if search_type == str(ChatState.SEARCH_BY_INGREDIENT) else 
        "Inserisci gli hashtag "
    )

    update.callback_query.edit_message_text(
        text = text, 
        reply_markup = kb.confirm_cancel_keyboard()
    )

    return ChatState.INPUT_TIME


def do_search(update: Update, context: CallbackContext) -> ChatState:
    update.callback_query.answer() 
    update.callback_query.edit_message_reply_markup()
    chat_id = context.user_data.get(de.CHAT_ID)

    if not context.user_data.get(de.BUFFER):
        text = "non hai mandato nessun termine di ricerca...coglione"
        context.user_data[de.LAST] = context.bot.send_message(
            text=text, 
            chat_id = chat_id, 
            reply_markup = kb.confirm_cancel_keyboard()
        )
        return ChatState.INPUT_TIME
        
    #process tokens
    context.user_data[de.SEARCH_TOKENS] = tokens = process_received_tokens(update, context)
    logger.info(f"Received tokens: {tokens}")

    context.user_data[de.LAST] = context.bot.send_message(
        text=f"Effettuo la ricerca con questi termini: {tokens}\nSono corretti?", 
        chat_id = chat_id, 
        reply_markup = kb.do_it_keyboard(do_it_msg="Giusti, vai", dont_do_it_msg="Noo, modifica"))

    return ChatState.WAIT_CONFIRM 



def perform_search(update: Update, context: CallbackContext) -> ChatState:
    data = context.user_data
    chat_id = data.get(de.CHAT_ID)
    logger.info(f"Cerco {data.get(de.SEARCH_TYPE)} usando {data.get(de.SEARCH_TOKENS)}")

    recipe_ids = get_recipes(update, context)

    if not recipe_ids:
        context.bot.edit_message_text(
            text = "Non ci sono ricette :(", 
            chat_id = chat_id, 
            message_id = context.user_data.get(de.LAST).message_id, 
            reply_markup = InlineKeyboardMarkup.from_button(
                InlineKeyboardButton(
                    text = "Ok", callback_data=str(ChatState.QUIT_SEARCH)))
        )
        return ChatState.WAIT_CONFIRM


    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data.get(de.LAST).message_id)

    viz = view.VizManager(
        user_id = chat_id, recipe_ids = list(recipe_ids), 
        manager = context.bot_data.get(de.MANAGER), 
        viz_mode = ChatState.VIEW_ALL, 
        searching = True)
    context.user_data.update({
        de.WHICH_VIEW: ChatState.VIEW_ALL, 
        de.VIZ: viz
    })
    logger.info(f"init {viz}")

    return view.visualize_recipes(update, context)

def indecisive_search(update: Update, context: CallbackContext) -> ChatState:
    logger.info("trying to quit")
    chat_id = context.user_data.get(de.CHAT_ID)
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data.get(de.LAST).message_id)
    context.user_data[de.LAST] = context.bot.send_message(
        chat_id = chat_id, 
        text = "Beh, che vuoi fare?", 
        reply_markup = kb.search_keyboard
    )
    #clear search type 
    del context.user_data[de.SEARCH_TYPE]

    return ChatState.WHICH_SEARCH


def quit(update: Update, context: CallbackContext) -> ChatState:
    logger.info("quit from search")
    chat_id, last = [context.user_data.get(e) for e in (de.CHAT_ID, de.LAST)]

    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text=stm.main_message(update.callback_query.from_user.first_name), 
        reply_markup = kb.main_keyboard
    )
    #clear user data 
    context.user_data.clear() 
    context.user_data.update({
        de.CHAT_ID: chat_id, 
        de.LAST: last
    })

    return ChatState.SELECTING_LEVEL


################################# tasks

def save_input(update: Update, context: CallbackContext) -> None:
    context.user_data[de.BUFFER].append((message := update.message.text))
    logger.info(f"current input: {message}")
    return 

def process_received_tokens(update: Update, context: CallbackContext) -> list:
    data = context.user_data.get(de.BUFFER)
    tokens = list() 

    if (search_type := context.user_data.get(de.SEARCH_TYPE)) == str(ChatState.SEARCH_BY_HASHTAG):
        for message in data:
            tokens.extend(message.split(" "))

    elif search_type == str(ChatState.SEARCH_BY_INGREDIENT):
        for message in data:
            tokens.extend([s.lower() for text in message.split(",") if (s := text.strip())])

    else:
        raise RuntimeError(f"Unknown search type: {search_type}")
    
    data.clear()

    return tokens


def get_recipes(update: Update, context: CallbackContext) -> list:
    logger.info("getting recipes...")
    user_data = context.user_data
    data, recipes_id = user_data.get(de.SEARCH_TOKENS), None     

    if (search_type := user_data.get(de.SEARCH_TYPE)) == str(ChatState.SEARCH_BY_HASHTAG):
        raise NotImplementedError("todo - search by hashtag")

    elif search_type == str(ChatState.SEARCH_BY_INGREDIENT):
        recipes_id = context.bot_data.get(de.MANAGER).db_manager.search_recipes(
            user_data.get(de.SEARCH_TOKENS), 
            user_data.get(de.CHAT_ID),
            True
        )
        logger.info(f"Trovate ricette: {recipes_id}")

    else:
        raise RuntimeError(f"Unknown search type: {search_type}")
    
    data.clear()    #consume tokens 

    return recipes_id
