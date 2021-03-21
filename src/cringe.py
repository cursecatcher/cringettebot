#! /usr/bin/env python3 
# -*- coding: utf-8 -*-

import argparse
import logging
import sys  

from telegram import Update, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler, 
    Defaults
)

from db.managers import DBManager, PersistencyManager
import insert as ins, view, search

import keyboardz as kb 
from statements import Statements as stm 
from states import ChatState, DataEntry as de



# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)



#start a new conversation
def start(update: Update, context: CallbackContext) -> ChatState:   
    """ Reacts to /start command by showing a welcome message and starting a new conversation """

    context.user_data[de.CHAT_ID] = update.message.chat.id

    context.user_data[de.LAST] = update.message.reply_text(
        text = stm.welcome(update.message.from_user.first_name),
        reply_markup = kb.main_keyboard
    )

    logger.info(f"User {update.message.from_user.first_name} presses {update.message.text}")

    return ChatState.SELECTING_ACTION

#start a new conversation
def new_conversation(update: Update, context: CallbackContext) -> ChatState:
    """ Starts a new conversation """

    context.user_data[de.CHAT_ID] = update.message.chat.id

    context.user_data[de.LAST] = update.message.reply_text(
        text = stm.main_message(update.message.from_user.first_name),
        reply_markup = kb.main_keyboard
    )
    
    logger.info(f"User {update.message.from_user.first_name} --  presses {update.message.text}")

    return ChatState.SELECTING_ACTION

#stop nested conversation 
def stop_nested(update: Update, context: CallbackContext) -> None:
    """Completely end conversation from within nested conversation."""
    context.bot.edit_message_reply_markup(
        chat_id = context.user_data[de.CHAT_ID], 
        message_id = context.user_data[de.LAST].message_id)
    update.message.reply_text('Okay, bye.')

    context.user_data.clear() 

    return ChatState.STOPPING

#stop conversation 
def stop(update: Update, context: CallbackContext):
    """End Conversation by command."""
    context.bot.edit_message_reply_markup(
        chat_id = context.user_data[de.CHAT_ID],
        message_id = context.user_data[de.LAST].message_id)
    context.bot.send_message(
        text = "Okay, bye a fairy codday.", 
        chat_id = context.user_data[de.CHAT_ID]
    )

    #clear session
    context.user_data.clear() 

    return ConversationHandler.END 


def error(update: Update, context: CallbackContext):
    """Log Errors caused by Updates."""
    logger.warning(f"An error has occurred!!\nCurrent update: {update}\nError: {context.error}")
    return ConversationHandler.END


def helper(update: Update, context: CallbackContext) -> ChatState:
    try:
        context.bot.edit_message_reply_markup(
            chat_id = context.user_data[de.CHAT_ID],
            message_id = context.user_data[de.LAST].message_id)
    except:
        pass
     
    update.message.reply_text(
        text = stm.helper(),
        reply_markup = kb.main_keyboard
    )
    #NB. currently the helper removes the current action 
    return ChatState.SELECTING_ACTION


def r(state: ChatState = None, states: list = None):
    if state:
        return f"^{str(state)}$"
    elif states:
        strings = "|".join([str(state) for state in states])
        return f"^{strings}$"
    else:
        raise RuntimeError("Cannot use r function without arguments")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("LE CRINGETTE BOT")
    parser.add_argument("--token", action="store", type=str, required=True)
    parser.add_argument("--data", action="store", type=str, default="./my_recipes.db")
    args = parser.parse_args()

    defaults = Defaults(parse_mode=ParseMode.HTML)
    updater = Updater(args.token, use_context=True, defaults = defaults)
    dispatcher = updater.dispatcher

    command_new_recipe = CommandHandler("nuova", ins.request_recipe_name)
    command_view_recipes = CommandHandler("view", view.init_visualization)
    command_search4recipes = CommandHandler("search", search.welcome)
    command_stop_conversation = CommandHandler("stop", stop_nested)

    #ingredient acquisition
    ingredient_conv = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(ins.add_ingredient, pattern = r(ChatState.INGREDIENTS)),
        ], 
        states = {
            ChatState.SELECTING_ACTION: [
                #process text messages  (ingredients)
                MessageHandler(Filters.text & ~Filters.command, ins.save_input),
                #entrypoint ingredient list request 
                CallbackQueryHandler(ins.add_ingredient, pattern = r(ChatState.OBTAINING_DATA)),
                #ingredient list memorization 
                CallbackQueryHandler(ins.save_ingredients, pattern = r(ChatState.SAVE_INGREDIENTS)),
                CallbackQueryHandler(ins.discard_ingredients, pattern = r(ChatState.DELETE_INGREDIENTS))
            ]
        }, 
        fallbacks = [], 
        map_to_parent = {
            ChatState.SELECTING_LEVEL: ChatState.SELECTING_ACTION
        }
    )
    #recipe method & photos acquisition 
    recipe_conv = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(ins.add_recipe_method, pattern = r(ChatState.OBTAINING_RECIPE))
        ], 
        states = {
            ChatState.SELECTING_ACTION: [
                #process text messages (ingredient list and recipe description )
                MessageHandler(Filters.text & ~Filters.command, ins.save_input),
                MessageHandler(Filters.photo, ins.add_photo), 

                CallbackQueryHandler(ins.save_recipe_method, pattern = r(ChatState.SAVE_RECIPE_METHOD)), 
                CallbackQueryHandler(ins.discard_recipe_method, pattern = r(ChatState.DELETE_RECIPE_METHOD))
            ]
        }, 
        fallbacks = [], 
        map_to_parent = {
            ChatState.SELECTING_LEVEL: ChatState.SELECTING_ACTION, 
        }
    )
    #recipe acquisition 
    new_recipe_conv = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(ins.request_recipe_name, pattern=r(ChatState.NEW_RECIPE_REQUEST))
        ], 
        states = { 
            ChatState.SELECTING_ACTION: [
                ingredient_conv, 
                recipe_conv, 
                
                CallbackQueryHandler(ins.cancel_recipe, pattern = r(ChatState.DELETE_RECIPE)),
                CallbackQueryHandler(ins.save_recipe, pattern = r(ChatState.SAVE_RECIPE))
            ],
            ChatState.SELECTING_NAME: [
                #cattura nome ricetta e la inizializza
                MessageHandler(Filters.text & ~Filters.command, ins.init_new_recipe), 
                #annulla inserimento ricetta e torna al menù precedente 
                CallbackQueryHandler(ins.cancel_recipe, pattern = r(ChatState.DELETE_RECIPE))
            ], 
            ChatState.ASK_CONFIRM: [
                CallbackQueryHandler(ins.confirm_operation, pattern = r(states=[
                    ChatState.SAVE_AS_PUBLIC, ChatState.SAVE_AS_PRIVATE,    #save recipe in db as public / private 
                    ChatState.DO_IT])),                                     #confirm recipe cancelation
                CallbackQueryHandler(ins.abort_operation, pattern = r(ChatState.DONT_DO_IT)),
            ], 
            ChatState.MISSING_INFO: [
                MessageHandler(Filters.text & ~Filters.command, ins.save_input), 
                CallbackQueryHandler(ins.save_missing_data, pattern = r(ChatState.SAVE_DATA)),
                CallbackQueryHandler(ins.discard_missing_data, pattern = r(ChatState.DELETE_DATA))   
            ]
        }, 
        fallbacks = [
            command_stop_conversation,
        ], 
        map_to_parent = {
            ChatState.SELECTING_LEVEL: ChatState.SELECTING_ACTION, 
            ChatState.STOPPING: ConversationHandler.END 
        }
    )

    view_actions = [
        #go to prev / next recipe 
        CallbackQueryHandler(view.prev_next, pattern = r(states = [
            ChatState.VIEW_PREV, ChatState.VIEW_NEXT
        ])),
        #edit current recipe 
        CallbackQueryHandler(view.edit, pattern = r(ChatState.EDIT_RECIPE)), 
        #delete current recipe from db 
        CallbackQueryHandler(view.delete, pattern = r(ChatState.DELETE_RECIPE)), 
        #save current recipe in user's bookmarks 
        CallbackQueryHandler(view.bookmark, pattern = r(ChatState.SAVE_BOOKMARK)), 
        #send message containing the current recipe procedure
        CallbackQueryHandler(view.visualize_recipe_method, pattern = r(ChatState.VIEW_RECIPE_METHOD)),
        #send an album containing the photos about the current recipe 
        CallbackQueryHandler(view.visualize_recipe_photos, pattern = r(ChatState.VIEW_RECIPE_PHOTOS)),
        #quit visualization 
        CallbackQueryHandler(view.come_back, pattern = r(ChatState.QUIT_VIZ)), 
    ]

    view_recipes_conv = ConversationHandler(
        entry_points = [
            CallbackQueryHandler(view.init_visualization, pattern = r(ChatState.VIEW_RECIPES))
        ], 
        states = {
            ChatState.INIT_VIZ : [
                CallbackQueryHandler(view.come_back, pattern = r(ChatState.COME_BACK)), 
                CallbackQueryHandler(view.init_view_recipes, pattern = r(states = [
                    ChatState.VIEW_ALL, ChatState.VIEW_MINE
                ]))
            ],
            ChatState.SELECTING_ACTION: [
                *view_actions,
                #back to all / mine recipes menu 
                CallbackQueryHandler(view.init_visualization, pattern = r(ChatState.COME_BACK)), 
            ], 
            ChatState.CONFIRM_DELETE_RECIPE: [
                CallbackQueryHandler(view.perform_delete_operation, pattern = r(states=[
                    ChatState.DO_IT, ChatState.DONT_DO_IT
                ]))
            ], 
            ChatState.WAIT_CONFIRM: [
                CallbackQueryHandler(view.back2visualization, pattern = r(ChatState.OK))
            ]
        }, 
        fallbacks = [
            command_stop_conversation
        ], 
        map_to_parent = {
            ChatState.SELECTING_LEVEL: ChatState.SELECTING_ACTION, 
            ChatState.STOPPING: ConversationHandler.END 
        }
    )
   
    search_recipes_conv = ConversationHandler(entry_points = [
            CallbackQueryHandler(search.welcome, pattern = r(ChatState.SEARCH_FOR_RECIPES))
        ],
        states = {
            ChatState.WHICH_SEARCH: [
                CallbackQueryHandler(search.init_search, pattern = r(states=[
                    ChatState.SEARCH_BY_INGREDIENT, ChatState.SEARCH_BY_HASHTAG])), 
                #back to main menu  
                CallbackQueryHandler(search.quit, pattern = r(ChatState.QUIT_SEARCH)) 
            ], 
            ChatState.INPUT_TIME: [
                MessageHandler(Filters.text & ~Filters.command, search.save_input),
                CallbackQueryHandler(search.do_search, pattern = r(ChatState.SAVE_DATA)), 
                CallbackQueryHandler(search.indecisive_search, pattern = r(ChatState.DELETE_DATA))
            ], 
            ChatState.WAIT_CONFIRM: [
                #start search with given tokens 
                CallbackQueryHandler(search.perform_search, pattern = r(ChatState.DO_IT)), 
                #go back and insert new tokens
                CallbackQueryHandler(search.init_search, pattern = r(ChatState.DONT_DO_IT)), 
                #return to recipe visualization when user has terminated to visualize photos 
                CallbackQueryHandler(view.back2visualization, pattern = r(ChatState.OK)), 
                #
                CallbackQueryHandler(search.quit, pattern = r(ChatState.QUIT_SEARCH))
            ], 
            ChatState.SELECTING_ACTION: [
                *view_actions,
                CallbackQueryHandler(search.indecisive_search, pattern = r(ChatState.COME_BACK)), 
                CallbackQueryHandler(search.quit, pattern = r(ChatState.QUIT_SEARCH)) 
            ]
        },
        fallbacks = [
            command_stop_conversation
        ],
        map_to_parent = {
            ChatState.SELECTING_LEVEL: ChatState.SELECTING_ACTION, 
            ChatState.STOPPING: ConversationHandler.END 
        }
    )

    selection_handlers = [
        new_recipe_conv, 
        view_recipes_conv,
        search_recipes_conv,
        CallbackQueryHandler(stop, pattern = r(ChatState.QUIT_CRINGETTE))
    ]

    conv_handler = ConversationHandler(
        entry_points = [
            CommandHandler('start', start), 
            MessageHandler(Filters.text & ~Filters.command, new_conversation)
        ], 
        states = {
            ChatState.SELECTING_ACTION: selection_handlers, 
        }, 
        fallbacks = [
            CommandHandler('stop', stop),
            CommandHandler("help", helper)
        ]
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_error_handler(error)

    db_manager = DBManager(db_name=args.data) 
    dispatcher.bot_data[de.MANAGER] = PersistencyManager(db_manager)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()