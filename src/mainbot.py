#! /usr/bin/env python3 
# -*- coding: utf-8 -*-

import argparse
import logging
import sys  

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler
)

import operations as op 



# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)



if __name__ == "__main__":
    parser = argparse.ArgumentParser("LE CRINGETTE BOT")
    parser.add_argument("--token", action="store", type=str, required=True)
    parser.add_argument("--data", action="store", type=str, default="./my_recipes.db")
    args = parser.parse_args()

    updater = Updater(args.token, use_context=True)
    dispatcher = updater.dispatcher

    accepted_str = "|".join([x.value for x in op.ButtonText])


    conv_handler = ConversationHandler(
        entry_points = [
            MessageHandler(Filters.regex(f"^({accepted_str})$"), op.entrypoint), 
            CommandHandler("start", op.start),
            CommandHandler("add", op.add_recipe),
            CommandHandler("view", op.view_recipes),
            CommandHandler("search", op.search_recipes_update)
        ], 
        states = {
            op.ChatOperation.INSERT_RECIPE: [
                MessageHandler(Filters.text & ~Filters.command, op.add_recipe),
                MessageHandler(Filters.photo, op.add_photo)
            ],
            op.ChatOperation.VIEW_RECIPES: [
                CallbackQueryHandler(op.view_recipes)
            ], 
            op.ChatOperation.PRIVACY: [
                CallbackQueryHandler(op.set_privacy)
            ],
            op.ChatOperation.SEARCH_BY: [
                MessageHandler(Filters.text & ~Filters.command, op.search_recipes_update),
                CallbackQueryHandler(op.search_recipes_callback)
            ]
        }, 
        fallbacks = [
            CommandHandler("cancel", op.cancel), 
            CommandHandler("help", op.helper), 
            MessageHandler(Filters.command, op.generic_command_entrypoint)
        ]
    )

    #connect the bot to the database
    db_manager = op.DBManager(db_name=args.data) 
    dispatcher.bot_data["manager"] = op.PersistencyManager(db_manager)

    dispatcher.add_handler(conv_handler)
    
    dispatcher.add_error_handler(op.error)

    updater.start_polling() 
    updater.idle()
