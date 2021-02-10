#-*- coding: utf-8 -*-

import enum, logging
from db.managers import DBManager

from keyboards import VizKeyboard

class OpBot(enum.Enum):
    ADD_RECIPE = "add"
    VIEW_RECIPES = "view"

# TODO 
# class Operation:
#     def __init__(self, operation: OpBot):
#         #TODO
#         pass

class RecipeInsertionStatus(enum.Enum):
    ADD_INGREDIENT = enum.auto()
    ADD_PROCEDURE = enum.auto()
    ADD_PHOTO = enum.auto()
    SET_PRIVACY = enum.auto()



class RecipeInsertionOperation:
    def __init__(self, user_data):
        self.__recipe = None 
        self.__recipe_method = None 
        self.__photos = list()

        #adding this object to context.user_data 
        if OpBot.ADD_RECIPE not in user_data:
            user_data[OpBot.ADD_RECIPE] = self
        else:
            raise RuntimeError("RecipeInsertionOperation object already present in user_data.")
    
    @property
    def recipe(self):
        return self.__recipe

    @property
    def recipe_method(self):
        return self.__recipe_method

    @property
    def photos(self):
        return self.__photos

    @recipe.setter
    def recipe(self, recipe_obj):
        self.__recipe = recipe_obj

    def add_ingredient(self, ingredient_name: str):
        commas = "," in ingredient_name
        new_lines = "\n" in ingredient_name

        if not commas and not new_lines:
            #there are no separators in the given string: assuming is a single ingredient
            logging.info(f"Saving single ingredient: {ingredient_name}")
            self.__recipe.add_ingredient(ingredient_name)
        else:
            #there is at least one accepted separator...

            #if the (satanic) user mixed both commas and \n symbols, just remove one of them
            if commas and new_lines:
                #now there is just one separator (commas)
                ingredient_name = ingredient_name.replace("\n", ",")
            
            sep = "," if commas else "\n"
            logging.info(f"Using separator '{sep}' to split '{ingredient_name}'")
            ingredient_list = [i for i in ingredient_name.split(sep) if len(i.strip()) > 0]
            logging.info(f"Saving the following ingredients: {ingredient_list}")

            for single_ingredient in ingredient_list:
                self.__recipe.add_ingredient(single_ingredient)
    
    def add_photo(self, photo_obj):
        self.__photos.append(photo_obj)
        logging.info(f"Attaching new photo to recipe {self.__recipe.name}")

    def save_photos(self):
        for n, photo in enumerate(self.photos):
            photo.download(f"/data/file_{n}.jpg")

    @recipe_method.setter
    def recipe_method(self, method):
        self.__recipe_method = method 


class RecipeViz:
    def __init__(self, db_manager: DBManager, user_id: int, only_personal_rec: bool = True):
        self.__dbm = db_manager
        self.__user_id = user_id
        self.__personal_flag = only_personal_rec

        self.__recList = list()
        self.__cache = list() 
        self.__index = 0

        is_global_search = not only_personal_rec
        self.__recList = self.__dbm.get_recipes(user_id, id_only=True, all_recipes=is_global_search)
        self.__cache = [None for elem in self.__recList]

        #init keyboard state 
        self.__keyboard = VizKeyboard(global_kb=is_global_search).update(self.recipe_position, self.num_recipes)
        
    
    @property
    def keyboard(self):
        """ Return the InlineKeyboardMarkup object representing the actual kb state """
        return self.__keyboard.get_kb()

    @property
    def personal_recipes_only(self):
        return self.__personal_flag

    @property
    def num_recipes(self):
        return len(self.__recList)
    
    @property
    def recipe_position(self):
        return self.__index + 1

    @property
    def recipe_id(self):
        return self.__recList[self.__index]

    def get(self, format: bool = False):
        index = self.__index
        elem = self.__cache[index]        

        if elem is None:
            elem = self.__dbm.get_recipe_by_id(self.__recList[index])
            self.__cache[index] = elem

        message = elem 

        if format:
            ingredients = [i.name for i in elem.ingredients]
            ingredients = "\n".join(ingredients)
            message = f""" 
Ricetta {self.recipe_position}/{self.num_recipes}: <b>{elem.name}</b>

Ingredienti:
{ingredients}"""

        return message 
        

    def next(self):
        ret = False

        if self.__index < len(self.__recList) - 1:
            self.__index += 1 #increment pointer 
            ret = self.__index != len(self.__recList) - 1

        self.__keyboard.update(self.recipe_position, self.num_recipes)
        return ret

    def prev(self):
        ret = False

        if self.__index > 0:
            self.__index -= 1 #decrease pointer 
            ret = self.__index != 0
        
        self.__keyboard.update(self.recipe_position, self.num_recipes)
        return ret 
    
    def do_action(self, action: str):
        self.__keyboard.do_action(action)