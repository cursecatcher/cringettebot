#-*- coding: utf-8 -*-

import abc 
import enum, logging
from emoji import emojize

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove
)


class ButtonText(enum.Enum):
    NEW_RECIPE = emojize(":heavy_plus_sign: Nuova", use_aliases=True)
    VIEW_RECIPES = emojize(":book: Lista", use_aliases=True)
    HELP = emojize(":sos: Aiuto", use_aliases=True)

    END_RECIPE = emojize(":ok: Salva!! :ok:", use_aliases=True)
    CANCEL_NEW_RECIPE = emojize(":a::b::o2:RT", use_aliases=True)


class VizKeyboard:
    def __init__(self, global_kb: bool = False):
        self.__all_keys = {
            #actions
            "bookmarks": ":pushpin: Salva!", 
            "bookmarks_back": "Dimentica",
            "edit": "Modifica", 
            "edit_back": "???", 
            "delete": "Elimina",
            "delete_back": "Premimi!!",
            "privacy": "_________",
            "see": "Ricetta", 
            "see_back": "Ingredienti",
            #move actions
            "prev": ":arrow_left: Prev", 
            "next": ":arrow_right: Next", 
            #close kb 
            "end": ":x: Chiudi!!"
        }

        self.__move_status = [True, True]
        self.__move_keys = ["prev", "next"]
        self.__actions = ["see"]
        self.__global_keyboard_mode = global_kb
        #define commands for global and local search
        if global_kb:
            specific_commands = ["bookmarks"]
        else:
            specific_commands = [
#                "edit", 
                "privacy",
                "delete"
            ]
        self.__actions.extend(specific_commands)
        self.__close_key = ["end"]

    def reset(self, privacy_key_string = None):
        """ Reset action keys in the keyboard """
        
        self.__actions = [
            action.rstrip("_back") if action.endswith("_back") 
                else action
                    for action in self.__actions
        ]

        self.set_privacy(privacy_key_string)
        

    def set_privacy(self, privacy_value):
        if not self.__global_keyboard_mode:
            self.__all_keys["privacy"] = "Nascondi!!" if privacy_value else "Pubblica!!"


    def do_action(self, input_action: str):
        """ Update the keyboard's status given the last pressed key """
        if self.__get_key_list(input_action) is self.__actions:
            #get the current base action
            base_action = input_action.partition("_")[0]
            #get the inverse key of @input_action
            new_key = base_action if input_action.endswith("_back") \
                                  else f"{base_action}_back"
            #effective key replacement
            self.__actions[self.__actions.index(input_action)] = new_key
        
        return self 


    def update(self, curr_pos: int, max_pos: int):
        """Update keyboard status given the current recipe position @curr_pos
        and the maximum position value @max_pos """

        #if there is just one recipe, disable both prev and next buttons 
        if curr_pos == max_pos == 1:
            self.__move_status = [False, False]
        else:
            #enable all the keys by default  
            self.__move_status = [True, True]
            #if the last recipe is pointed, disable the next button 
            if curr_pos == max_pos:
                self.__move_status[1] = False
            #if the first recipe is pointed, disable the prev button 
            elif curr_pos == 1:
                self.__move_status[0] = False 
        
        return self

    def get_kb(self):
        """Return an InlineKeyboardMarkup representing the actual state of @self"""
        move = [k for k, s in zip(self.__move_keys, self.__move_status) if s]
        move = self.__get_inline_keys(move)
        actions = self.__get_inline_keys(self.__actions)
        close = self.__get_inline_keys(self.__close_key)

        return InlineKeyboardMarkup([move, actions, close])


    def __get_inline_keys(self, key_list: list):
        """ Return a list of InlineKeyboardButtons given a list of string @key_list"""
        return [
            InlineKeyboardButton(emojize(
                self.__all_keys[key], use_aliases=True), callback_data=key) \
                    for key in key_list
        ]

    def __get_key_list(self, key: str):
        """ Return the attribute list containing the key named as @key """
        if key in ("prev", "next"):
            return self.__move_keys
        elif key in ("see", "edit", "bookmarks") or key.endswith("_back"):
            return self.__actions



class MainKeyboard:
    def __init__(self):
        self.__all_keys = {
            "new": ButtonText.NEW_RECIPE.value, 
            "view": ButtonText.VIEW_RECIPES.value, 
            "help": ButtonText.HELP.value, 
            "end": ButtonText.END_RECIPE.value, 
            "cancel": ButtonText.CANCEL_NEW_RECIPE.value
        }

        self.__keys = ["end", "cancel"]

    def main(self):
        """ Reset keyboard to the main one """

        self.__keys = ["new", "view", "help"]
        return self 
    
    def add_ingredient_mode(self):
        self.__keys = ["end", "cancel"]
        return self 
    
    def add_recipe_mode(self):
        self.__keys = ["cancel"]
        return self 

    def get_kb(self, one_time_keyboard = False):
        keys = [self.__all_keys[key_str] for key_str in self.__keys]
        return ReplyKeyboardMarkup([keys], one_time_keyboard=one_time_keyboard, resize_keyboard=True)
    


def save_recipe_keyboard():
    return InlineKeyboardMarkup([
            [InlineKeyboardButton("Sìììì", callback_data="YES"), InlineKeyboardButton("Noope", callback_data="NO")]
    ])

def view_recipes_which():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Tutte!!", callback_data="all"), 
        InlineKeyboardButton("Solo le mie!", callback_data="mine")
    ]])

