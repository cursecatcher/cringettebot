#-*- coding: utf-8 -*-

import enum 
from telegram.ext import ConversationHandler

class ChatState(enum.Enum):
    #main operations
    NEW_RECIPE_REQUEST = enum.auto()
    VIEW_RECIPES = enum.auto()
    SEARCH_FOR_RECIPES = enum.auto()

    #add recipe states 
    INGREDIENTS = enum.auto()
    RECIPE = enum.auto()
    RECIPE_ACQUISITION = enum.auto()
    SELECTING_NAME = enum.auto() 
    OBTAINING_DATA = enum.auto()
    OBTAINING_PHOTO = enum.auto()
    OBTAINING_RECIPE = enum.auto()
    OBTAINING_INGREDIENTS = enum.auto() 
    SAVE_INGREDIENTS = enum.auto()
    EDIT_INGREDIENTS = enum.auto()
    DELETE_INGREDIENTS = enum.auto() 
    DELETE_RECIPE = enum.auto() 
    SAVE_RECIPE = enum.auto()
    SAVE_RECIPE_METHOD = enum.auto()
    DELETE_RECIPE_METHOD = enum.auto()

    MISSING_INFO = enum.auto()      #missing required data to save the recipe 
    SAVE_DATA = enum.auto()         #save missing data (ingredients or recipe method)
    DELETE_DATA = enum.auto()       #delete missing ingredients or recipe method

    ASK_CONFIRM = enum.auto()
    CONFIRM_YES = enum.auto()
    DO_IT = enum.auto()
    DONT_DO_IT = enum.auto()
    SAVE_AS_PRIVATE = enum.auto()
    SAVE_AS_PUBLIC = enum.auto()


    #visualization states 
    INIT_VIZ = enum.auto()
    VIEW_MINE = enum.auto()
    VIEW_ALL = enum.auto() 

    VIEW_NEXT = enum.auto()
    VIEW_PREV = enum.auto()
    EDIT_RECIPE = enum.auto()
    SAVE_BOOKMARK = enum.auto() 
    VIEW_RECIPE_METHOD = enum.auto()
    VIEW_RECIPE_PHOTOS = enum.auto()

    CONFIRM_DELETE_RECIPE = enum.auto()

    #search states 
    WHICH_SEARCH = enum.auto()
    SEARCH_BY_HASHTAG = enum.auto()
    SEARCH_BY_INGREDIENT = enum.auto()
    INPUT_TIME = enum.auto()

    
    #generic states 
    OK = enum.auto()
    WAIT_CONFIRM = enum.auto()
    STOPPING = enum.auto() 

    COME_BACK = enum.auto()
    QUIT_VIZ = enum.auto()
    QUIT_SEARCH = enum.auto()
    SELECTING_ACTION = enum.auto()
    SELECTING_LEVEL = enum.auto()
    QUIT_CRINGETTE = ConversationHandler.END 


class OperationToDo:
    def __init__(self):
        self.__ingredient = False
        self.__recipe = False 

    def todo(self, stuff: ChatState):
        if stuff is ChatState.INGREDIENTS:
            self.__ingredient = True 
        elif stuff is ChatState.RECIPE:
            self.__recipe = True
        else:
            raise Exception(f"You can't do {stuff}")

    def what_i_have_todo(self) -> ChatState:
        return (ChatState.INGREDIENTS if self.__ingredient else (
            ChatState.RECIPE if self.__recipe else None)
        )

    def ingredients_done(self):
        if self.__ingredient:
            self.__ingredient = False
            return
        raise Exception("you do not have to do ingredients")

    def recipe_done(self):
        if self.__recipe:
            self.__recipe = False
            return
        raise Exception("you do not have to do ingredients")
        

class DataEntry(enum.Enum):
    LAST = enum.auto()          #last message id 
    CHAT_ID = enum.auto()       #current chat id 
    MANAGER = enum.auto()       #persistency manager 
    RECIPE = enum.auto()        #current recipe during creation phase 
    INPUT = enum.auto()         #
    INGREDIENT_INPUT = enum.auto() 
    RECIPE_INPUT = enum.auto() 
    RECIPE_METHOD = enum.auto() 
    OPERATION = enum.auto() 
    PHOTOS = enum.auto() 

    SEARCH_TYPE = enum.auto() 
    SEARCH_TOKENS = enum.auto() 
    SHOWING_PHOTOS = enum.auto()


    WHICH_VIEW = enum.auto()
    VIZ = enum.auto()           #viz manager
    KB = enum.auto()            #viz keyboard
    TODO = enum.auto()

    #some buffers for different purposes
    BUFFER = enum.auto()
    INGREDIENT_LIST_BUFFER = enum.auto() 
    RECIPE_DESCRIPTION_BUFFER = enum.auto()

    @classmethod
    def from_string(cls, string: str):
        return cls[string.split(".")[1]]



    
