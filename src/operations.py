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
    function = helper 

    if operation == ButtonText.NEW_RECIPE.value.lower():
        function = add_recipe
    elif operation == ButtonText.VIEW_RECIPES.value.lower():
        function = view_recipes
    elif operation == ButtonText.SEARCH_RECIPES.value.lower():
        function = search_recipes_update
    
    context.user_data.clear()
    return function(update, context)

def generic_command_entrypoint(update: Update, context: CallbackContext) -> ChatOperation:
    command = update.message.text.split()[0]
    function = helper 
    
    if command == "/start":
        function = start 
    elif command == "/add":
        function = add_recipe
    elif command == "/view":
        function = view_recipes
    elif command == "/search":
        function = search_recipes_update
    else:
        update.message.reply_text(
            f"Mi dispiace, ma il comando {command} da te usato non è supportato."
        )
    
    return function(update, context)

def add_recipe(update: Update, context: CallbackContext) -> ChatOperation:
    text_message = update.message.text.strip()
    user = update.message.from_user 

    if text_message == ButtonText.CANCEL_NEW_RECIPE.value:
        return cancel(update, context)

    try:
        user_recipe = context.user_data[utils.OpBot.ADD_RECIPE]
        keyboard = user_recipe.keyboard

        ###init recipe name 
        if not user_recipe.recipe:
            logging.info("check name availability")

            db_manager = context.bot_data["manager"].db_manager
            #checking recipe name availability for the user 
            if db_manager.check_recipe_availability(recipe_name = text_message.lower(), recipe_owner = user.id):
                user_recipe.init_recipe(text_message)

                update.message.reply_text(
                    "Sono pronto! Inviami la lista degli ingredienti!\n\n"
                    
                    "NB. Puoi inviarmi un ingrediente alla volta, "
                    "o se preferisci puoi scrivere più ingredienti in un unico messaggio, "
                    "separandoli con delle virgole e/o con delle andate a capo!\n", 
                    reply_markup = keyboard.get_kb()
                )      
            else:
                logger.info(f"Invalid name for recipe '{text_message}' of user {user.id}")
                update.message.reply_text(
                    "Hai già memorizzato una ricetta con lo stesso nome!\n"
                    "Invia un altro nome o premi /cancel per annullare!"
                )
                #TODO - chiedere altro nome 
                #return clear_context(update, context)
                return ChatOperation.INSERT_RECIPE

        elif not user_recipe.recipe.ingredients:
            logging.info("Obtaining ingredients...")
            #add ingredient to list until you received the end message 
            if text_message == ButtonText.END_RECIPE.value:
                if not user_recipe.save_ingredients():
                    update.message.reply_text(emojize(
                        "Zio, non mi hai mandato nessun ingrediente!!\n"
                        "Non sono ammesse ricette respiriane, quindi dimmi gli ingredienti o vai a fare in culo. :angry:", 
                        use_aliases=True), 
                        reply_markup = keyboard.add_ingredient_mode().get_kb()
                    )
                    return ChatOperation.INSERT_RECIPE
                
                update.message.reply_text(
                    f"{user.first_name}, ci siamo quasi!\n"
                    "Se vuoi, mandami qualche foto della tua ricetta e del piatto finale!\n"
                    "Infine, inviami il procedimento per cucinare questa deliziosa ricetta!", 
                    reply_markup = keyboard.add_recipe_mode().get_kb()
                )
            else:
                logging.info(f"Adding ingredient(s): {text_message}")
                user_recipe.add_ingredient(text_message)
        else:
            user_recipe.recipe_method = text_message #assuming that this text is the recipe procedure. 
            #add recipe procedure, photos and so on .... 
            update.message.reply_text(emojize(
        #    f"Oppalà! Ho salvato la tua ricetta denominata '{user_recipe.recipe.name}' nel CringetteDB!\n"
                f"Di seguito un breve riepilogo della tua ricetta '{user_recipe.recipe.name}'\n"
                f"Numero ingredienti: {len(user_recipe.recipe.ingredients)}\n"
                f"Ingredienti: {user_recipe.recipe.ingredients}\n"
                f"Hai caricato {len(user_recipe.photos)} foto.\n", use_aliases=True), 
                reply_markup = keyboard.main().get_kb())
            #TODO - aggiungere tasti "ok continua" / "modifica prima di salvare"

        #    logger.info(f"User {user.id} ({user.first_name}) saved recipe {user_recipe.recipe.name} ({user_recipe.recipe.ingredients})")

            update.message.reply_text(
                "Sono pronto a salvare la ricetta nel database!\n"
                "Vuoi renderla visibile anche agli altri utenti del bot?", 
                reply_markup = kb.save_recipe_keyboard()
            )
            return ChatOperation.PRIVACY
        
    except KeyError:
        logger.info(f"User {user.first_name} is adding a new recipe")
        context.user_data[utils.OpBot.ADD_RECIPE] = utils.RecipeAddNew(user.id)

        keyboard = kb.MainKeyboard().add_recipe_mode()
        update.message.reply_text("Molto bene! Come si chiama la ricetta?", reply_markup = keyboard.get_kb())
    
    return ChatOperation.INSERT_RECIPE


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
        return clear_context(update, context)
    except KeyError:
        recipe_id = context.user_data[utils.OpBot.VIEW_RECIPES].recipe_id
        logging.info(f"Toggling privacy of recipe #{recipe_id}")

        return context.bot_data["manager"].db_manager.toggle_privacy(
            query.from_user.id, 
            recipe_id
        ) 


def view_recipes(update: Update, context: CallbackContext) -> ChatOperation:
    try:
        update.message.reply_text(
            "Procediamo! Quali ricette vuoi vedere?", 
            reply_markup = kb.view_recipes_which()
        )
    except AttributeError:
        return get_recipe(update, context)

    return ChatOperation.VIEW_RECIPES


def get_recipe(update: Update, context: CallbackContext) -> ChatOperation:
    query = update.callback_query
    query.answer()
    response = query.data
    user = query.from_user 
    data_manager = context.bot_data["manager"]

    if response == "end":
        query.edit_message_text("Cya!") 
        return clear_context(update, context)

    if utils.OpBot.VIEW_RECIPES not in context.user_data:
        if response not in ("all", "mine"):
            raise Exception(f"Unvalid response: {response}")

        context.user_data[utils.OpBot.VIEW_RECIPES] = utils.RecipeViz(data_manager, user.id, response == "mine")
        logging.info(f"RecipeViz({user.id}, {response == 'mine'}) initialized")

    viz = context.user_data[utils.OpBot.VIEW_RECIPES]

    if viz.num_recipes == 0:
        query.edit_message_text("Nessuna ricetta presente. Premi /add per aggiungerne una!")
        return clear_context(update, context)
    

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
            context.bot.answer_callback_query(
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

    query.edit_message_text(
        text = viz.get(format=True), 
        reply_markup = viz.keyboard, 
        parse_mode=ParseMode.HTML
    )
    return ChatOperation.VIEW_RECIPES 


def search_recipes_update(update: Update, context: CallbackContext) -> ChatOperation:
    message = update.message.text 
    user = update.message.from_user

    try:
        searcher = context.user_data[utils.OpBot.SEARCH]

        if message == "Ho finito!":
            if len(searcher.all_tokens) == 0:
                update.message.reply_text(emojize(
                    "Non mi hai detto cosa vuoi cercare! :sweat_smile:\n"
                    "Inviami almeno un termine di ricerca!!", use_aliases=True),
                    reply_markup=kb.search_recipes_keyboard()
                )
                return ChatOperation.SEARCH_BY

            searcher.parse()

            update.message.reply_text(
                "Pronti, partenza, via!\nVuoi cercare tra tutte o solo le tue ricette?", 
                reply_markup = kb.view_recipes_which()
            )
        elif message == "Annullaci tutto":
            return cancel(update, context)
        else:
            searcher.add_token(message)

    except KeyError: 
        update.message.reply_text(
            "Inviami i termini con i quali effettuare la ricerca!", 
            reply_markup=kb.search_recipes_keyboard()
        )
        #init context
        context.user_data[utils.OpBot.SEARCH] = utils.Searcher(
            context.bot_data["manager"], 
            user.id
        )
    
    return ChatOperation.SEARCH_BY


def search_recipes_callback(update: Update, context: CallbackContext) -> ChatOperation:
    query = update.callback_query
    query.answer()
    response = query.data

    logging.info(f"RESPONSE is {response}")

    searcher = context.user_data[utils.OpBot.SEARCH]

    if searcher.is_instantiated():
        viz = searcher.visualization

        if response == "end":
            query.edit_message_text("Alla prossima!")
            return clear_context(update, context)

        elif response.startswith("see"):
            viz.do_action(response) #update keyboard 

            if response == "see":
                curr_recipe = viz.get()
                recipe_message = context.bot_data["manager"].fs_manager.get_procedure(curr_recipe)

                if recipe_message:
                    message = f"Procedimento per <b>{curr_recipe.name}</b>\n\n{recipe_message}"
                else:
                    message = f"Impossibile recuperare il procedimento della ricetta <b>{curr_recipe.name}</b>"
                
                query.edit_message_text(
                    text = message, 
                    reply_markup = viz.keyboard, 
                    parse_mode=ParseMode.HTML
                )
                return ChatOperation.SEARCH_BY
        elif response == "next":
            viz.next()
        elif response == "prev":
            viz.prev()
    else:
        global_search = (response == "all")

        if not searcher.instantiate(global_search = global_search):
            query.edit_message_text(
                text = emojize(
                    "Mi dispiace, non ho trovato nessuna ricetta usando i termini da te inseriti. :sweat:", 
                    use_aliases=True), 
                parse_mode=ParseMode.HTML
            )
            return clear_context(update, context)

        viz = searcher.visualization

    query.edit_message_text(
        text = viz.get(format=True), 
        reply_markup = viz.keyboard, 
        parse_mode=ParseMode.HTML
    )

    return ChatOperation.SEARCH_BY


def helper(update: Update, context: CallbackContext) -> ChatOperation:
    update.message.reply_text(emojize(
        "<b>Comandi supportati:</b>\n\n"
        "• /add - aggiungi una ricetta\n"
        "• /view - scorri le tue ricette o quelle degli altri utenti\n"
        "• /search - cerca (per parole, hashtag...) tra le tue ricette o quelle degli altri utenti\n"
        "• /help - visualizza questo messaggio di aiuto\n"
        "• /cancel - annulla il comando in corso\n"
        "\nAltre funzionalità sono in via di sviluppo! :smile:", use_aliases=True), 
        parse_mode=ParseMode.HTML,
        reply_markup = kb.MainKeyboard().main().get_kb()
    )
    #NB. currently the helper removes the current action 
    return clear_context(update, context)


def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info(f"User {user.first_name} canceled the conversation.")

    update.message.reply_text(
        "L'operazione corrente è stata annullata. Cosa vuoi fare ora?",
        reply_markup = kb.MainKeyboard().main().get_kb()
    )
    return clear_context(update, context)


def clear_context(update: Update, context: CallbackContext) -> int:
    logging.info("Deleting user data")
    context.user_data.clear()

    return ConversationHandler.END

def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning(f"An error has occurred!!\nCurrent update: {update}\nError: {context.error}")
    return ConversationHandler.END