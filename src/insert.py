#-*- coding: utf-8 -*-

import logging, re
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

from db.entities import Ingredient, Recipe

from statements import RecipeInsertionStatements as stm 
import keyboardz as kb 
from states import ChatState, DataEntry as de, OperationToDo as ToDo


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)



#request name for a fresh new recipe 
def request_recipe_name(update: Update, context: CallbackContext) -> ChatState:
    """ Starts a conversation to create a new recipe by asking the recipe's name """

    args = dict(
        text = stm.request_recipe_name(),
        reply_markup = kb.cancel_keyboard
    )

    try:
        update.callback_query.answer()    
        update.callback_query.edit_message_text(**args)
    except AttributeError:
        context.user_data[de.LAST] = update.message.reply_text(**args)

    return ChatState.SELECTING_NAME

#initialize a new recipe given its name 
def init_new_recipe(update: Update, context: CallbackContext) -> ChatState:
    user = update.message.from_user
    recipe_name = update.message.text
    db_manager = context.bot_data[de.MANAGER].db_manager
    #init magic objects
    context.user_data[de.TODO] = ToDo() 
    context.user_data[de.INGREDIENT_LIST_BUFFER] = set() 
    context.user_data[de.RECIPE_DESCRIPTION_BUFFER] = list() 
    context.user_data[de.PHOTOS] = list()

    logging.info(f"User {user.first_name} -- init new recipe: {update.message.text}")

    #remove keyboard from previous message 
    context.bot.edit_message_reply_markup(
        chat_id = context.user_data[de.CHAT_ID],
        message_id = context.user_data[de.LAST].message_id
    )

    args = dict(recipe_name = recipe_name, recipe_owner = user.id)
    if not db_manager.check_recipe_availability(**args):
        # check recipe'sn name availability. if name isn't available, it ask the user for another name
        logging.info(f"User {update.message.from_user.first_name} -- nome occupato")

        text = (
            "Hai già memorizzato una ricetta con questo nome!\n"
            "Inviami un altro nome!")
        context.user_data[de.LAST] = update.message.reply_text(
            text = text, reply_markup = kb.cancel_keyboard)
        return ChatState.SELECTING_NAME

    recipe = context.user_data[de.RECIPE] = Recipe(name=recipe_name, owner=user.id)
    text = stm.request_more_information(recipe)
    context.user_data[de.LAST] = update.message.reply_text(
        text = text,  
        reply_markup = kb.insert_keyboard)

    return ChatState.SELECTING_ACTION

#ask the user to input the recipe's ingredients 
def add_ingredient(update: Update, context: CallbackContext) -> ChatState:
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = stm.request_ingredients(), 
        reply_markup = kb.confirm_cancel_keyboard(ChatState.INGREDIENTS))
    context.user_data[de.INPUT] = de.INGREDIENT_INPUT

    return ChatState.SELECTING_ACTION

#ask the user to input the recipe's method description
def add_recipe_method(update: Update, context: CallbackContext) -> ChatState:
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text = stm.request_recipe_method(update.callback_query.from_user.first_name), 
        reply_markup = kb.confirm_cancel_keyboard(ChatState.RECIPE))
    context.user_data[de.INPUT] = de.RECIPE_INPUT

    return ChatState.SELECTING_ACTION

#add the new ingredients to the current new recipe
def save_ingredients(update: Update, context: CallbackContext) -> ChatState:
    logger.info("Ingredienti salvati :)")
    chat_id = context.user_data[de.CHAT_ID]

    update.callback_query.answer()
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, 
        message_id = context.user_data[de.LAST].message_id)

    #add acquired ingredients to the current recipe 
    context.user_data[de.RECIPE].add_ingredient_list(
        context.user_data.get(de.INGREDIENT_LIST_BUFFER))
    context.user_data[de.INGREDIENT_LIST_BUFFER].clear() 
    logger.info("Ingredienti salvati :)")

    context.user_data[de.LAST] = context.bot.send_message(
        text = stm.request_more_information(context.user_data.get(de.RECIPE)),
        chat_id = chat_id, 
        reply_markup = kb.insert_keyboard)

    return ChatState.SELECTING_LEVEL

#ad the recipe's description to the current new recipe 
def save_recipe_method(update: Update, context: CallbackContext) -> ChatState:
    update.callback_query.answer()
    chat_id = context.user_data[de.CHAT_ID]

    context.bot.edit_message_reply_markup(
        chat_id = chat_id, 
        message_id = context.user_data[de.LAST].message_id)

    logging.info("Procedimento ricetta e foto salvate :) ")
    recipe_description = "\n".join(context.user_data.get(de.RECIPE_DESCRIPTION_BUFFER))

    context.user_data[de.RECIPE_DESCRIPTION_BUFFER].clear() 
    context.user_data[de.RECIPE_METHOD] = recipe_description

    context.user_data[de.LAST] = context.bot.send_message(
        text = stm.request_more_information(context.user_data.get(de.RECIPE)),
        chat_id = chat_id, 
        reply_markup = kb.insert_keyboard)

    return ChatState.SELECTING_LEVEL

#discard the new ingredients 
def discard_ingredients(update: Update, context: CallbackContext) -> ChatState:
    logging.info("I tuoi ingredienti sono stati buttati al macero")
    chat_id = context.user_data[de.CHAT_ID]

    update.callback_query.answer()
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, 
        message_id = context.user_data[de.LAST].message_id)
    
    context.user_data[de.INGREDIENT_LIST_BUFFER].clear() 

    context.user_data[de.LAST] = context.bot.send_message(
        text = stm.request_more_information(context.user_data.get(de.RECIPE)),
        chat_id = chat_id, 
        reply_markup = kb.insert_keyboard)

    return ChatState.SELECTING_LEVEL

#discard the recipe's description provided by the user 
def discard_recipe_method(update: Update, context: CallbackContext) -> ChatState:
    logging.info("Procedimento ricetta buttato a casino")
    chat_id = context.user_data[de.CHAT_ID]

    update.callback_query.answer()
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, 
        message_id = context.user_data[de.LAST].message_id)    
    
    context.user_data[de.RECIPE_DESCRIPTION_BUFFER].clear() 

    context.user_data[de.LAST] = context.bot.send_message(
        text = stm.discarded_recipe_method_message(context.user_data[de.RECIPE]), 
        chat_id = chat_id, 
        reply_markup = kb.insert_keyboard)

    return ChatState.SELECTING_LEVEL

#save the current recipe in the database 
def save_recipe(update: Update, context: CallbackContext) -> ChatState:
    chat_id = context.user_data[de.CHAT_ID]

    update.callback_query.answer()
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data[de.LAST].message_id)
    
    logging.info("Vediamo se la ricetta è salvabile.")

    recipe = context.user_data.get(de.RECIPE)
    args = dict(
        text = stm.save_recipe_confirm(recipe), 
        chat_id = chat_id, 
        reply_markup = kb.privacy_keyboard
    )

    ##NB. pay attention to walrus operator combined with OR operator!!
    if ((missing_ingredients := not bool(recipe.ingredients)) 
            or not context.user_data.get(de.RECIPE_METHOD)):

        text, todo, what_input = ((
            stm.breatharianism_recipe(), ChatState.INGREDIENTS, de.INGREDIENT_INPUT) if missing_ingredients 
            else (stm.undescribed_recipe(), ChatState.RECIPE, de.RECIPE_INPUT)
        )
        args.update(dict(
            text = text, reply_markup = kb.confirm_cancel_keyboard()
        ))

        logger.info(f"Operation to do: {todo}")

        ### TODO - missing description AND missing ingredients
        # if missing_description and missing_ingredients:
        #     pass #TODO ? 

        context.user_data[de.TODO].todo(todo)
        context.user_data[de.INPUT] = what_input
        context.user_data[de.LAST] = context.bot.send_message(**args)
        logger.info("Moving to MISSING_INFO state")
        return ChatState.MISSING_INFO

    context.user_data[de.LAST] = context.bot.send_message(**args)
    context.user_data[de.OPERATION] = ChatState.SAVE_RECIPE

    return ChatState.ASK_CONFIRM

#saving missing info, either ingredients and/or recipe method
def save_missing_data(update: Update, context: CallbackContext) -> ChatState:
    chat_id = context.user_data[de.CHAT_ID]

    update.callback_query.answer()
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data[de.LAST].message_id)
    
    logging.info("APPOSTO")
    todo_list = context.user_data.get(de.TODO)

    if (todo := todo_list.what_i_have_todo()) is ChatState.INGREDIENTS:
        #save ingredients and clear buffer 
        ingredients = context.user_data.get(de.INGREDIENT_LIST_BUFFER)
        context.user_data[de.RECIPE].add_ingredient_list(ingredients)
        context.user_data[de.INGREDIENT_LIST_BUFFER].clear() 
        todo_list.ingredients_done()
        text = "Tutto a posto, ingredienti ok. E adesso cosa vogliamo fare?"
        
    elif todo is ChatState.RECIPE:
        #save recipe description and clear buffer 
        recipe_description = "\n".join(context.user_data.get(de.RECIPE_DESCRIPTION_BUFFER))
        context.user_data[de.RECIPE_METHOD] = recipe_description
        context.user_data[de.RECIPE_DESCRIPTION_BUFFER].clear()
        todo_list.recipe_done()
        text = "Tutto a posto, procedimento ok. E adesso cosa vogliamo fare?"
    
    else:
        raise RuntimeError("Unexpected todo => {todo}")

    context.user_data[de.LAST] = context.bot.send_message(
        text = text, 
        chat_id = context.user_data[de.CHAT_ID], 
        reply_markup = kb.insert_keyboard
    )

    return ChatState.SELECTING_ACTION

#discarding missing info, either ingredients and/or recipe method
def discard_missing_data(update: Update, context: CallbackContext) -> ChatState:
    logging.info("NON APPOSTO")
    chat_id = context.user_data[de.CHAT_ID]

    update.callback_query.answer()
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data[de.LAST].message_id)
    
    args = dict(chat_id = chat_id, reply_markup = kb.insert_keyboard)
    todo_list = context.user_data.get(de.TODO)

    if (task_todo := todo_list.what_i_have_todo()) is ChatState.INGREDIENTS:
        args["text"] = "Ingredienti eliminati! E mò?"
        todo_list.ingredients_done() 
        context.user_data[de.INGREDIENT_LIST_BUFFER].clear() 
    
    elif task_todo is ChatState.RECIPE:
        args["text"] = "Ricetta lanciata a casino. E ora?"
        todo_list.recipe_done() 
        context.user_data[de.RECIPE_DESCRIPTION_BUFFER].clear() 

    context.user_data[de.LAST] = context.bot.send_message(**args)

    return ChatState.SELECTING_ACTION

#cancel the current recipe from session 
def cancel_recipe(update: Update, context: CallbackContext) -> ChatState:
    logging.info("Sarebbe bello annullare la ricetta....")
    chat_id = context.user_data[de.CHAT_ID]

    update.callback_query.answer()
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data[de.LAST].message_id)

    args = dict(
        text = stm.cancel_recipe_confirm(context.user_data.get(de.RECIPE)), 
        chat_id = chat_id, 
        reply_markup = kb.do_it_keyboard(
            do_it_msg = "Sì, cancella", dont_do_it_msg = "Noo, torna indietro")
    )

    context.user_data[de.LAST] = context.bot.send_message(**args)
    context.user_data[de.OPERATION] = ChatState.DELETE_RECIPE #actually this is cancel, not delete

    return ChatState.ASK_CONFIRM

#confirm salient operations (save recipe / discard recipe)
def confirm_operation(update: Update, context: CallbackContext) -> ChatState:
    chat_id = context.user_data[de.CHAT_ID]
    update.callback_query.answer()
    recipe_obj = context.user_data.get(de.RECIPE)

    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data[de.LAST].message_id)

    operation = context.user_data.get(de.OPERATION)
    if operation not in (ChatState.DELETE_RECIPE, ChatState.SAVE_RECIPE):
        raise RuntimeError(f"Unexpected operation to confirm: {operation}")

    #default message - canceled recipe 
    text = stm.canceled_recipe(recipe_obj)

    if operation == ChatState.SAVE_RECIPE:
        text = stm.saved_recipe(recipe_obj)
        recipe_obj.visibility = (update.callback_query.data == str(ChatState.SAVE_AS_PUBLIC))

        logger.info(f"My recipe is {recipe_obj}")

        context.bot_data.get(de.MANAGER).add_recipe(
            recipe_obj = recipe_obj, 
            recipe_procedure = context.user_data.get(de.RECIPE_METHOD), 
            recipe_photos = context.user_data.get(de.PHOTOS)
        )

        logger.info("New recipe has been saved in the db")

    context.bot.send_message(text=text, chat_id=chat_id)

    #clear session 
    context.user_data.clear() 
    context.user_data[de.CHAT_ID] = chat_id
    context.user_data[de.LAST] = context.bot.send_message(
        text = stm.keep_going(), chat_id = chat_id, reply_markup = kb.main_keyboard)
    
    return ChatState.SELECTING_LEVEL

#cancel salient operations (save recipe / discard recipe)
def abort_operation(update: Update, context: CallbackContext) -> ChatState:
    chat_id = context.user_data[de.CHAT_ID]
    update.callback_query.answer()

    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data[de.LAST].message_id)

    if (recipe := context.user_data.get(de.RECIPE)):
        #the uses presses cancel during recipe creation
        text = stm.request_more_information(recipe)
        keyboard = kb.insert_keyboard
        return_value = ChatState.SELECTING_ACTION
    else:
        #the user presses cancel during recipe name insertion
        text = stm.ask_again_for_recipe_name()
        keyboard = kb.cancel_keyboard
        return_value = ChatState.SELECTING_NAME

    context.user_data[de.LAST] = context.bot.send_message(
        text = text, chat_id = chat_id, reply_markup = keyboard)

    return return_value

#catch input provided by the user 
def save_input(update: Update, context: CallbackContext) -> ChatState:
    """Save input for feature and return to feature selection."""
    input = context.user_data.get(de.INPUT)
    message = update.message.text

    if input == de.INGREDIENT_INPUT:
        splitter = re.compile(r",|\n|;")
        context.user_data[de.INGREDIENT_LIST_BUFFER].update([
            s for x in splitter.split(message) if (s := x.strip())
        ])
        logging.info(f"Ingredienti ricevuti!")
    elif input == de.RECIPE_INPUT:
        context.user_data[de.RECIPE_DESCRIPTION_BUFFER].append(message)
        logging.info(f"Ricetta ricevuta ma tl;dr.")
    else:
        logging.info(f"Unexpected input: {input}")

    return (
        ChatState.SELECTING_ACTION 
        if not context.user_data.get(de.TODO).what_i_have_todo() else None
    )

#catch photos sent by the user 
def add_photo(update: Update, context: CallbackContext) -> ChatState:
    logging.info("che bella foto")
    #update.message.reply_text("Bella foto!!")
    context.user_data[de.PHOTOS].append(
        context.bot.get_file( update.message.photo[-1].file_id )
    )
