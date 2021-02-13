#! /usr/bin/env python3 
# -*- coding: utf-8 -*-

import argparse
import logging
import enum
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

    db_manager = op.DBManager(db_name=args.data)

    updater = Updater(args.token, use_context=True)
    dispatcher = updater.dispatcher

    accepted_str = "|".join([x.value for x in op.ButtonText])
    regex_handler = MessageHandler(Filters.regex(f"^({accepted_str})$"), op.entrypoint)

    add_recipe_handler = CommandHandler("add", op.add_recipe)
    view_recipes_handler = CommandHandler("view", op.view_recipes)
    start_handler = CommandHandler("start", op.start)


    conv_handler = ConversationHandler(
        entry_points = [
            start_handler,
            regex_handler, 
            add_recipe_handler, 
            view_recipes_handler
        ], 
        states = {
            op.ChatOperation.ENTRYPOINT: [
                regex_handler,
                start_handler,
                add_recipe_handler, 
                view_recipes_handler
            ], 
            op.ChatOperation.ADD_INGREDIENT: [
                MessageHandler(Filters.text & ~Filters.command, op.add_ingredient)
            ], 
            op.ChatOperation.INSERT_RECIPE: [
                MessageHandler(Filters.text & ~Filters.command, op.end_recipe), 
                MessageHandler(Filters.photo, op.add_photo)
            ],
            op.ChatOperation.VIEW_RECIPES: [
                CallbackQueryHandler(op.get_recipe)
            ], 
            op.ChatOperation.PRIVACY: [
                CallbackQueryHandler(op.set_privacy)
            ]
        }, 
        fallbacks = [
            CommandHandler("cancel", op.cancel), 
            CommandHandler("help", op.helper)
        ]

    )

    #connect the bot to the database 
    dispatcher.bot_data["manager"] = op.PersistencyManager(db_manager)

    dispatcher.add_handler(conv_handler)
    
    dispatcher.add_error_handler(op.error)

    updater.start_polling() 
    updater.idle()
