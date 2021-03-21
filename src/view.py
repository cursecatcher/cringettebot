#-*- coding: utf-8 -*-

from pathlib import Path 
import logging
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    Update, 
    ParseMode, 
    InputMediaPhoto
)
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext, 
)
from emoji import emojize

from statements import Statements as stm, RecipeVisualisationStatements as viz_stm
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


class VizManager:
    def __init__(self, 
        user_id: int, recipe_ids: list, 
        manager: PersistencyManager, viz_mode: ChatState, searching = False):

        self.__manager = manager
        self.__user = user_id
        # self.__recipes, self.__privacies = zip(*recipe_ids)
        self.__privacies = None
        try:
            self.__recipes, self.__privacies = zip(*recipe_ids)
            self.__recipes = list(self.__recipes)
        except TypeError:
            self.__recipes = recipe_ids

        self.__cache = dict()
        self.__kb = kb.VizKB(viz_mode = viz_mode, searching=searching)

        self.__pointer = 0

    @property
    def current(self):
        if not (rcp := self.__cache.get((i := self.__pointer))):
            #domanda: a che serve avere le privacy delle ricette se poi la recupero da qua?
            self.__cache[i] = rcp = self.__manager.db_manager.get_recipe_by_id(self.__recipes[i])
        return rcp 

    @property 
    def num_recipes(self) -> int:
        return len(self.__recipes)

    def go_next(self) -> int:
        self.__pointer += 1 
        return 0 
    
    def go_previous(self) -> int:
        self.__pointer -= 1 
        return 0 
    
    def delete_recipe(self) -> int:
        args = dict(user_id = self.__user, by_id = self.current.id)
        if (r_id := self.__manager.db_manager.delete_recipe(**args)):
            logger.info(f"User {self.__user} deleted recipe #{r_id}")

            del self.__cache[self.__pointer]
            del self.__recipes[self.__pointer]
            self.__pointer = self.__pointer - 1 if self.__pointer else 0

        return r_id


    def render_kb(self) -> InlineKeyboardMarkup:
        return self.__kb.render(self.__pointer, self.num_recipes - 1) 
    
    def render_recipe(self) -> str:
        return viz_stm.view_recipe_in_list(
            recipe = self.current, 
            num_curr_recipe = self.__pointer + 1, 
            num_max_recipe = self.num_recipes
        )


def init_visualization(update: Update, context: CallbackContext) -> ChatState:
    text = "Procediamo! Quali ricette vuoi vedere?"
    args = dict(text=text, reply_markup=kb.which_recipes2see)    

    try:
        update.callback_query.answer()
        update.callback_query.edit_message_text(**args)
    except AttributeError:
        context.user_data[de.LAST] = update.message.reply_text(**args)

    return ChatState.INIT_VIZ


def come_back(update: Update, context: CallbackContext) -> ChatState:
    logger.info("addios")
    
    update.callback_query.answer()
    update.callback_query.edit_message_text(
        text=stm.main_message(update.callback_query.from_user.first_name), 
        reply_markup = kb.main_keyboard
    )
    return ChatState.SELECTING_LEVEL
    

def init_view_recipes(update: Update, context: CallbackContext) -> ChatState:
    update.callback_query.answer() 
    user_data = context.user_data
    chat_id = user_data.get(de.CHAT_ID)

    which_view = (
        ChatState.VIEW_MINE if update.callback_query.data == str(ChatState.VIEW_MINE)
        else ChatState.VIEW_ALL)

    id_recipes = context.bot_data[de.MANAGER].db_manager.get_recipes(
        user_id = chat_id,  
        id_only = True, 
        all_recipes = which_view is ChatState.VIEW_ALL)

    if not id_recipes:
        context.bot.edit_message_reply_markup(
            chat_id = chat_id, message_id = context.user_data[de.LAST].message_id)
        user_data[de.LAST] = context.bot.send_message(
            text = "Non ho trovato nessuna ricetta coi criteri da te inseriti :( ", 
            chat_id = chat_id, 
            reply_markup = kb.main_keyboard
        )
        return ChatState.SELECTING_LEVEL 

    args = dict(
        user_id = chat_id, recipe_ids = id_recipes, 
        manager = context.bot_data.get(de.MANAGER), 
        viz_mode = which_view)
    user_data.update({
        de.WHICH_VIEW: which_view, 
        de.VIZ: VizManager(**args)})

    return visualize_recipes(update, context)

#visualize stuff 
def visualize_recipes(update: Update, context: CallbackContext) -> ChatState:
    user_data = context.user_data
    chat_id, message, viz = [user_data.get(e) for e in (de.CHAT_ID, de.LAST, de.VIZ)] 
    # context.bot.edit_message_reply_markup(
    #     chat_id = chat_id, message_id = user_data[de.LAST].message_id)
  #  user_data[de.LAST] = context.bot.send_message(

    if viz.num_recipes == 0:
        context.bot.edit_message_text(
            text = "Non c'è più nessuna ricetta da visualizzare! Scegli che fare.", 
            chat_id = chat_id, 
            message_id = message.message_id, 
            reply_markup = kb.main_keyboard
        )
        return ChatState.SELECTING_LEVEL

    context.bot.edit_message_text(
        text = viz.render_recipe(), 
        chat_id = chat_id,
        message_id = message.message_id,
        reply_markup = viz.render_kb())

    return ChatState.SELECTING_ACTION   

def back2visualization(update: Update, context: CallbackContext) -> ChatState:
    chat_id = context.user_data.get(de.CHAT_ID)
    message_id = context.user_data.get(de.LAST).message_id

    try:
        del context.user_data[de.SHOWING_PHOTOS]
        context.bot.delete_message(chat_id = chat_id, message_id = message_id)
    except KeyError:
        context.bot.edit_message_reply_markup(
            chat_id = chat_id, message_id = message_id)
    finally:
        context.user_data[de.LAST] = context.bot.send_message(
            text="loading :)", chat_id = chat_id)
    return visualize_recipes(update, context)


def visualize_recipe_method(update: Update, context: CallbackContext) -> ChatState:
    recipe = context.user_data.get(de.VIZ).current
    text = (
        f"Procedimento per <b>{recipe.name}</b>\n\n"
        f"{context.bot_data.get(de.MANAGER).fs_manager.get_procedure(recipe)}"
    )
    context.bot.edit_message_text(
        text = text,
        chat_id = context.user_data.get(de.CHAT_ID), 
        message_id = context.user_data.get(de.LAST).message_id,
        reply_markup = kb.ok_keyboard
    )
    
    return ChatState.WAIT_CONFIRM

def visualize_recipe_photos(update: Update, context: CallbackContext) -> ChatState:
    user_data = context.user_data
    recipe = user_data.get(de.VIZ).current
    photos = context.bot_data.get(de.MANAGER).fs_manager.get_photos(recipe)
    message_id = user_data.get(de.LAST).message_id
    chat_id = user_data.get(de.CHAT_ID)
    args = dict(
        chat_id = chat_id
    )

    if not photos:
        #no photos: edit previous message 
        function = context.bot.edit_message_text
        args.update(dict(
            text = "Non ci sono foto per questa ricetta :(",
            message_id = message_id,
            reply_markup = kb.ok_keyboard
        ))
    else:
        context.bot.delete_message(
            chat_id = chat_id, message_id = message_id)
        #there is at least one photo: process all photos
        my_media = [open(photo, "rb") for photo in photos[1:]]
        first_photo = open(photos[0], "rb")
        caption = str(recipe.name.capitalize())
        
        if len(photos) == 1:
            #just one photo - send the photo and the ok keyboard 
            function = context.bot.send_photo
            args.update(dict(
                photo = first_photo, 
                caption = caption, 
                reply_markup = kb.ok_keyboard))
        else:
            #multiple photos - send an album, unfortunately with no keyboard
            user_data[de.SHOWING_PHOTOS] = True
            function = context.bot.send_media_group
            media = [InputMediaPhoto(photo) for photo in my_media]
            #the caption must be in the first photo 
            media.insert(0, InputMediaPhoto(first_photo, caption = caption))
            
            args.update(dict(media = media))

    #send photo(s) or edit previous message with no photo(s) :(
    if (result := function(**args)) and len(photos) == 1:
        #save message id if I am sending a photo with reply keyboard
        user_data[de.LAST] = result
    elif user_data.get(de.SHOWING_PHOTOS):
        #show the ok keyboard if I am sending multiple photos
        user_data[de.LAST] = context.bot.send_message(
            chat_id = chat_id, 
            text = "Sono proprio delle belle foto, vero? Dai, torniamo di là?", 
            reply_markup = kb.ok_keyboard)

    return ChatState.WAIT_CONFIRM

### actions
def prev_next(update: Update, context: CallbackContext) -> ChatState: 
    query, viz = update.callback_query, context.user_data.get(de.VIZ)
    query.answer()
    move_function = (
        viz.go_previous if query.data == str(ChatState.VIEW_PREV) else viz.go_next)
    move_function()
    return visualize_recipes(update, context)

def edit(update: Update, context: CallbackContext) -> ChatState:
    return visualize_recipes(update, context)

def delete(update: Update, context: CallbackContext) -> ChatState:
    chat_id = context.user_data.get(de.CHAT_ID)
    context.bot.edit_message_reply_markup(
        chat_id = chat_id, message_id = context.user_data[de.LAST].message_id)
    args = dict(
        text = "Sei sicuro di voler cancellare questa ricetta?", 
        chat_id = chat_id, 
        reply_markup = kb.do_it_keyboard("Sì, cancella", "Noooo, scherzavo")
    )
    context.user_data[de.LAST] = context.bot.send_message(**args)
    return ChatState.CONFIRM_DELETE_RECIPE

def perform_delete_operation(update: Update, context: CallbackContext) -> ChatState:
    update.callback_query.answer() 
    user_data = context.user_data
    chat_id, viz = user_data.get(de.CHAT_ID), user_data.get(de.VIZ)
    text = "Cancellazione annullata. Torniamo a dove eravamo rimasti..."

    if update.callback_query.data == str(ChatState.DO_IT):
        text = f"Ho cancellato la ricetta <b>{viz.current.name}</b> :)"
        viz.delete_recipe()
    
    args = dict(
        text = text, 
        chat_id = chat_id, 
        message_id = context.user_data.get(de.LAST).message_id)
    context.bot.edit_message_text(**args)
    context.user_data[de.LAST] = context.bot.send_message(
        text = ":)", chat_id = chat_id
    )

    return visualize_recipes(update, context)




def bookmark(update: Update, context: CallbackContext) -> ChatState:
    return visualize_recipes(update, context)

