#-*- coding: utf-8 -*-

import enum 

#to be completed 
class Operation:
    def __init__(self, operation):
        self.__optype = operation
        

class OpBot(enum.Enum):
    ADD_RECIPE = "add"
    VIEW_RECIPES = "view"


class RecipeInsertionStatus(enum.Enum):
    ADD_INGREDIENT = enum.auto()
    ADD_PROCEDURE = enum.auto()
    ADD_PHOTO = enum.auto()
    SET_PRIVACY = enum.auto()



class ViewAction(enum.Enum):
    VIEW_SEE = "see"
    VIEW_EDIT = "edit"
    VIEW_BMARK = "bookmarks"
    VIEW_DELETE = "delete"
    VIEW_PRIVACY = "privacy"
    UNKNOWN = "unknown"

    @classmethod
    def get(cls, value):
        try:
            if value.endswith("_back"):
                value = value.replace("_back", "")
            return cls(value)
        except ValueError:
            return ViewAction.UNKNOWN


class ChatOperation(enum.Enum):
    INSERT_RECIPE = 1
    VIEW_RECIPES = 2 
    ADD_INGREDIENT = 3 
    ENTRYPOINT = 4
    PRIVACY = 5

