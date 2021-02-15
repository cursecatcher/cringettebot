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

from db.entities import Ingredient, Recipe
from db.managers import DBManager, PersistencyManager
import utils

from enums import ChatOperation, ViewAction
import keyboards as kb 
from keyboards import ButtonText


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)





def start(update: Update, context: CallbackContext) -> ChatOperation:     
    update.message.reply_text(emojize(
        f"Ciao, {update.message.from_user.first_name}!\n"
        "Cringette è il bot che ti aiuterà a tenere a portata di tap le tue ricette di cucina! :yum:\n"
        "È in uno stadio di sviluppo <i>alpha</i>, ciò significa che potrebbero verificarsi comportamenti non previsti.\n"
        "Se riscontri un problema, contatta il mio programmatore @Cursecatcher, grazie!\n\n"
        "Per interagire con Cringette, puoi utilizzare la tastiera personalizzata o i comandi.\n"
        "Tappa su /help per visualizzare i comandi supportati!\n\n"
        "Che vuoi fare?", use_aliases=True),
        parse_mode=ParseMode.HTML,
        reply_markup = kb.MainKeyboard().main().get_kb()
    )

    logger.info(f"User {update.message.from_user.first_name} presses {update.message.text}")

    return ConversationHandler.END


def entrypoint(update: Update, context: CallbackContext) -> ChatOperation:
    operation = update.message.text.lower()

    if operation == ButtonText.NEW_RECIPE.value.lower():
        return add_recipe(update, context)
    elif operation == ButtonText.VIEW_RECIPES.value.lower():
        return view_recipes(update, context)
    else:
        return helper(update, context)


def add_recipe(update: Update, context: CallbackContext) -> ChatOperation: 
    user = update.message.from_user
    logger.info(f"User {user.first_name} is adding a new recipe")

    keyboard = kb.MainKeyboard().add_recipe_mode()

    update.message.reply_text("Molto bene! Come si chiama la ricetta?", reply_markup = keyboard.get_kb())
    return ChatOperation.ADD_INGREDIENT

def add_ingredient(update: Update, context: CallbackContext) -> ChatOperation: 
    user = update.message.from_user
    curr_text = update.message.text 

    if curr_text == ButtonText.CANCEL_NEW_RECIPE.value:
        return cancel(update, context)
    elif curr_text == ButtonText.END_RECIPE.value:
        return end_recipe(update, context)

    try:
        #adding a new ingredient to a recipe previously initialized
        user_recipe = context.user_data[utils.OpBot.ADD_RECIPE]
        user_recipe.add_ingredient(curr_text) 
        logger.info(f"User {user.first_name} is adding a new ingredient: {curr_text}")

    except KeyError:
        #initialization new recipe 
        logger.info(f"User {user.first_name} is creating the recipe of {curr_text}")

        new_recipe = Recipe(curr_text, user.id)

        db_manager = context.bot_data["manager"].db_manager
        
        if db_manager.check_recipe_availability(new_recipe):
            user_recipe = utils.RecipeInsertionOperation(context.user_data)
            user_recipe.recipe = new_recipe

        else:
            logger.info(f"Invalid name for recipe '{curr_text}' of user {user.id}")
            update.message.reply_text("Hai già memorizzato una ricetta con lo stesso nome!")
            return ConversationHandler.END

    n_ingredients = len(user_recipe.recipe.ingredients)

    if n_ingredients == 0: 
        update.message.reply_text(
            "Sono pronto! Inviami la lista degli ingredienti!\n\n"
            
            "NB. Puoi inviarmi un ingrediente alla volta, "
            "o se preferisci puoi scrivere più ingredienti in un unico messaggio, "
            "separandoli con delle virgole e/o con delle andate a capo!\n", 
            reply_markup = user_recipe.keyboard.get_kb()
        )

    return ChatOperation.ADD_INGREDIENT


def end_recipe(update: Update, context: CallbackContext) -> int: 
    user = update.message.from_user
    user_recipe = context.user_data[utils.OpBot.ADD_RECIPE]
    text_message = update.message.text
    keyboard = user_recipe.keyboard

    if not user_recipe.recipe.ingredients:
        #back to add ingredient operation 
        update.message.reply_text(emojize(
            "Zio, non mi hai mandato nessun ingrediente!!\n"
            "Non sono ammesse ricette respiriane, quindi dimmi gli ingredienti o vai a fare in culo. :angry:",), 
            reply_markup = keyboard.add_ingredient_mode().get_kb()
        )
        return ChatOperation.ADD_INGREDIENT
    
    if text_message == ButtonText.CANCEL_NEW_RECIPE.value:
        return cancel(update, context)

    elif text_message == ButtonText.END_RECIPE.value and not user_recipe.recipe_method: 
        #send recipe description request
        update.message.reply_text(
            f"{user.first_name}, ci siamo quasi!\n"
            "Se vuoi, mandami qualche foto della tua ricetta e del piatto finale!\n"
            "Infine, inviami il procedimento per cucinare questa deliziosa ricetta!", 
            reply_markup = keyboard.add_recipe_mode().get_kb()
        )
        return ChatOperation.INSERT_RECIPE

    elif not user_recipe.recipe_method: 
        #save recipe description 
        user_recipe.recipe_method = text_message #assuming that this text is the recipe procedure. 
        
        update.message.reply_text(emojize(
        #    f"Oppalà! Ho salvato la tua ricetta denominata '{user_recipe.recipe.name}' nel CringetteDB!\n"
            f"Di seguito un breve riepilogo della tua ricetta '{user_recipe.recipe.name}'\n"
            f"Numero ingredienti: {len(user_recipe.recipe.ingredients)}\n"
            f"Ingredienti: {user_recipe.recipe.ingredients}\n"
            f"Hai caricato {len(user_recipe.photos)} foto.\n", use_aliases=True), 
            reply_markup = keyboard.main().get_kb())
            
    #    logger.info(f"User {user.id} ({user.first_name}) saved recipe {user_recipe.recipe.name} ({user_recipe.recipe.ingredients})")

        update.message.reply_text(
            "Sono pronto a salvare la ricetta nel database!\n"
            "Vuoi renderla visibile anche agli altri utenti del bot?", 
            reply_markup = kb.save_recipe_keyboard()
        )
        return ChatOperation.PRIVACY
        
    return ConversationHandler.END


def add_photo(update: Update, context: CallbackContext) -> ChatOperation:
    new_photo = context.bot.get_file( update.message.photo[-1].file_id )
    context.user_data[utils.OpBot.ADD_RECIPE].add_photo(new_photo)


def set_privacy(update: Update, context: CallbackContext) -> ChatOperation:
    query = update.callback_query
    query.answer() 

    try:
        response = query.data == "YES"
        user_recipe = context.user_data[utils.OpBot.ADD_RECIPE]
        user_recipe.recipe.visibility = response

        context.bot_data["manager"].add_recipe(
            user_recipe.recipe, 
            user_recipe.recipe_method, 
            user_recipe.photos
        )

        message = "Grande spirito di condivisione, complimenti!!" if response else \
                "Ok, tieniti pure i tuoi segreti!"

        query.edit_message_text(message)
        context.user_data.clear() 

        return ConversationHandler.END 
    except KeyError:
        recipe_id = context.user_data[utils.OpBot.VIEW_RECIPES].recipe_id
        logging.info(f"Toggling privacy of recipe #{recipe_id}")

        return context.bot_data["manager"].db_manager.toggle_privacy(
            query.from_user.id, 
            recipe_id
        ) 



def view_recipes(update: Update, context: CallbackContext) -> ChatOperation:
    update.message.reply_text(
        "Procediamo! Quali ricette vuoi vedere?", 
        reply_markup = kb.view_recipes_which()
    )

    return ChatOperation.VIEW_RECIPES


def get_recipe(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    response = query.data
    user = query.from_user 
    data_manager = context.bot_data["manager"]

    if response == "end":
        query.edit_message_text("Cya!")
        del context.user_data[utils.OpBot.VIEW_RECIPES]
        return ConversationHandler.END

    if utils.OpBot.VIEW_RECIPES not in context.user_data:
        if response not in ("all", "mine"):
            raise Exception(f"Unvalid response: {response}")

        context.user_data[utils.OpBot.VIEW_RECIPES] = utils.RecipeViz(data_manager, user.id, response == "mine")
        logging.info(f"RecipeViz({user.id}, {response == 'mine'}) initialized")

    viz = context.user_data[utils.OpBot.VIEW_RECIPES]

    if viz.num_recipes == 0:
        query.edit_message_text("Nessuna ricetta presente. Premi /add per aggiungerne una!")
        del context.user_data[utils.OpBot.VIEW_RECIPES]
        return ConversationHandler.END    
    

    if ViewAction.get(response) != ViewAction.UNKNOWN:
        #just a default message which will be removed sooner or later ... 
        message = (
            "Questa funzionalità non è inclusa nella versione free.\n"
            "Mandami 0.001 bitcoin e te la abilito... Scherzo, ci sto lavorando! :see_no_evil:"
        )
        actual_action, _, inverse_action = response.partition("_")
        actual_action = ViewAction(actual_action)

        if actual_action == ViewAction.VIEW_SEE:
            if inverse_action: #get ingredients 
                message = viz.get(format=True)
            else:
                curr_recipe = viz.get()
                recipe_message = data_manager.fs_manager.get_procedure(curr_recipe)

                if recipe_message:
                    message = f"Procedimento per <b>{curr_recipe.name}</b>\n\n{recipe_message}"
                else:
                    message = f"Impossibile recuperare il procedimento della ricetta <b>{curr_recipe.name}</b>"
                
        elif actual_action == ViewAction.VIEW_EDIT:
            if inverse_action:
                message = viz.get(format=True)

        elif actual_action == ViewAction.VIEW_BMARK:
            if inverse_action:
                message = viz.get(format=True)
        
        elif actual_action == ViewAction.VIEW_DELETE:
            recipe_name = viz.get().name
            viz.delete_recipe()
            message = f"La tua ricetta chiamata '{recipe_name}' è stata cancellata per sempre!\nDovrei aggiungere un tasto di conferma secondo te?"
        
        elif actual_action == ViewAction.VIEW_PRIVACY:
            visible = viz.toggle_privacy(set_privacy(update, context))
            message = viz.get(format=True)
            
            visible_str = "pubblica" if visible else "privata"
            #c'è qualcosa da sistemare [cit. resca]
            value = context.bot.answer_callback_query(
                callback_query_id = query.id, 
                text = f"Da ora la ricetta {viz.get().name} è {visible_str}.",
                show_alert = False,
                cache_time = 3, 
                timeout = 1
            )

        viz.do_action(response)
        query.edit_message_text(
            emojize(message, use_aliases=True), 
            reply_markup=viz.keyboard, 
            parse_mode=ParseMode.HTML
        )

        return ChatOperation.VIEW_RECIPES 
    
    if response == "next":
        viz.next()
    elif response == "prev":
        viz.prev()

  #  logging.info(f"CHAT ID: {update.message.chat.id}")
    logging.info(f"Chat id: {query.message.chat.id}")
    query.edit_message_text(
        text = viz.get(format=True), 
        reply_markup = viz.keyboard, 
        parse_mode=ParseMode.HTML
    )
    return ChatOperation.VIEW_RECIPES 



def helper(update: Update, context: CallbackContext) -> ChatOperation:
    update.message.reply_text(emojize(
        "<b>Comandi supportati:</b>\n\n"
        "• /add - aggiungi una ricetta\n"
        "• /view - scorri le tue ricette o quelle degli altri utenti\n"
        "• /help - visualizza questo messaggio di aiuto\n"
        "• /cancel - annulla il comando in corso\n"
        "\nAltre funzionalità sono in via di sviluppo! :smile:", use_aliases=True), 
        parse_mode=ParseMode.HTML,
        reply_markup = kb.MainKeyboard().main().get_kb()
    )
    #NB. currently the helper removes the current action 
    context.user_data.clear() 
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info(f"User {user.first_name} canceled the conversation.")

    update.message.reply_text(
        "L'operazione corrente è stata annullata. Cosa vuoi fare ora?",
        reply_markup = kb.MainKeyboard().main().get_kb()
    )

    context.user_data.clear() 

    return ConversationHandler.END

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning(f"An error has occurred!!\nCurrent update: {update}\nError: {context.error}")