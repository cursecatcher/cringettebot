#-*- coding: utf-8 -*-

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from emoji import emojize
from states import ChatState


##### Insert recipe keyboards 

main_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(text="Nuova ricetta", callback_data=str(ChatState.NEW_RECIPE_REQUEST)), 
        InlineKeyboardButton(text="Sfoglia ricette", callback_data=str(ChatState.VIEW_RECIPES))
    ], [
        InlineKeyboardButton(text="Cerca!!", callback_data=str(ChatState.SEARCH_FOR_RECIPES)), 
        InlineKeyboardButton(text="Un ghigno", callback_data=str(ChatState.QUIT_CRINGETTE))
    ]
])

insert_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(text="Ingredienti", callback_data=str(ChatState.INGREDIENTS)),
        InlineKeyboardButton(text="Scrivi ricetta", callback_data=str(ChatState.OBTAINING_RECIPE))
    ], 
    [
        InlineKeyboardButton(text="Salva", callback_data=str(ChatState.SAVE_RECIPE)), 
        InlineKeyboardButton(text="Annulla", callback_data=str(ChatState.DELETE_RECIPE))
    ]
])

privacy_keyboard = InlineKeyboardMarkup([
    [
        InlineKeyboardButton(text="Pubblica", callback_data=str(ChatState.SAVE_AS_PUBLIC)), 
        InlineKeyboardButton(text="Privata", callback_data=str(ChatState.SAVE_AS_PRIVATE))
    ], 
    [
        InlineKeyboardButton(text="Indietro", callback_data=str(ChatState.DONT_DO_IT))
    ]
])

def confirm_cancel_keyboard(which_keyboard: ChatState = None):
    keys = {
        ChatState.RECIPE:       (ChatState.SAVE_RECIPE_METHOD, ChatState.DELETE_RECIPE_METHOD), 
        ChatState.INGREDIENTS:  (ChatState.SAVE_INGREDIENTS, ChatState.DELETE_INGREDIENTS), 
        None:                   (ChatState.SAVE_DATA, ChatState.DELETE_DATA)
    }

    if not (cc_kb := keys.get(which_keyboard)):
        raise Exception(
            "which_keyboard argument must be either "
            f"{ChatState.RECIPE} or {ChatState.INGREDIENTS} instead of {which_keyboard}.")

    save, cancel = cc_kb
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(text="Ho finito!", callback_data=str(save)),
            InlineKeyboardButton(text="Annulla!!", callback_data=str(cancel))
        ]
    ])


cancel_keyboard = InlineKeyboardMarkup.from_button(
    InlineKeyboardButton(
        text="Annulla", callback_data=str(ChatState.DELETE_RECIPE))
)

ok_keyboard = InlineKeyboardMarkup.from_button(
    InlineKeyboardButton(
        text = "Ok", callback_data=str(ChatState.OK)
    )
)


def do_it_keyboard(do_it_msg: str, dont_do_it_msg: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(text=do_it_msg, callback_data=str(ChatState.DO_IT)), 
        InlineKeyboardButton(text=dont_do_it_msg, callback_data=str(ChatState.DONT_DO_IT))
    ]])


which_recipes2see = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Tutte!!", callback_data=str(ChatState.VIEW_ALL)), 
        InlineKeyboardButton("Solo le mie!", callback_data=str(ChatState.VIEW_MINE))
    ], 
    [
        InlineKeyboardButton("Indietro", callback_data=str(ChatState.COME_BACK))
    ]
])

search_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton(text="Cerca per nome", callback_data=str(ChatState.SEARCH_BY_INGREDIENT))], 
#     [InlineKeyboardButton(text="Cerca per hashtag", callback_data=str(ChatState.SEARCH_BY_HASHTAG))], 
    [InlineKeyboardButton(text="Torna al menù principale", callback_data=str(ChatState.QUIT_SEARCH))]
])



class VizKB:
    def __init__(self, viz_mode: ChatState, searching=False):
        if viz_mode not in (ChatState.VIEW_MINE, ChatState.VIEW_ALL):
            raise RuntimeError(f"Invalid viz_mode: {viz_mode}")
    
        self.__prev = ("Prev", ChatState.VIEW_PREV)
        self.__next = ("Next", ChatState.VIEW_NEXT)
        self.__actions = [
            #default actions
            ("Mostra ricetta", ChatState.VIEW_RECIPE_METHOD), 
            ("Mostra foto", ChatState.VIEW_RECIPE_PHOTOS)
        ]
        self.__actions.extend([
            #personal actions
        #    ("Modifica", ChatState.EDIT_RECIPE),  ##TODO 
            ("Cancella", ChatState.DELETE_RECIPE)]       
                    if viz_mode is ChatState.VIEW_MINE else [
            #actions for other people's recipes
            ("Preferiti", ChatState.SAVE_BOOKMARK)]
        )
        self.__quit = [
            ("Indietro", ChatState.COME_BACK if searching else ChatState.COME_BACK), 
            ("Chiudi", ChatState.QUIT_SEARCH if searching else ChatState.QUIT_VIZ)
        ]
    
        
    
    def render(self, curr_index, max_index) -> InlineKeyboardMarkup: 
        def render_buttons(keys: list) -> list:
            return [
                InlineKeyboardButton(
                    text=emojize(text, use_aliases=True), callback_data=str(cbd)) 
                for text, cbd in keys
            ]

        if curr_index == max_index == 0:
            moves = list() 
        elif curr_index == 0:
            moves = [self.__next]
        elif curr_index == max_index:
            moves = [self.__prev]
        else:
            moves = [self.__prev, self.__next]

        return InlineKeyboardMarkup([
            render_buttons(moves), 
            render_buttons(self.__actions), 
            render_buttons(self.__quit)
        ])



