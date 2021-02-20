#-*- coding: utf-8 -*-

import logging
import re 
from db.managers import PersistencyManager
import db.entities as entities

import keyboards
from enums import OpBot


class RecipeAddNew:
    def __init__(self, user_id):
        self.__user_id = user_id
        self.__recipe = None 
        self.__recipe_method = None 
        self.__ingredients = list()
        self.__photos = list() 

        self.__splitter = re.compile(r",|\n|;")
        self.__keyboard = keyboards.MainKeyboard()


    @property
    def keyboard(self):
        return self.__keyboard

    @property
    def recipe_name(self):
        return self.__recipe.name if self.__recipe else None 
    
    @property
    def recipe(self):
        return self.__recipe

    @property
    def photos(self):
        return self.__photos
    
    @property
    def recipe_method(self):
        return self.__recipe_method
    
    @recipe_method.setter
    def recipe_method(self, text):
        self.__recipe_method = text 

    def init_recipe(self, recipe_name):
        logging.info(f"Recipe name is {recipe_name} belonging to user {self.__user_id}")
        self.__recipe = entities.Recipe(name = recipe_name, owner = self.__user_id)
    
    def save_ingredients(self):
        for ingredient in self.__ingredients:
            self.__recipe.add_ingredient(ingredient)
        return bool(self.__ingredients)

    def add_ingredient(self, ingredient_name: str):
        ingredient_list = [name.strip() for name in self.__splitter.split(ingredient_name)]
        self.__ingredients.extend([name for name in ingredient_list if len(name) > 0])

        logging.info(f"Adding the following ingredients: {ingredient_list}")


    def add_photo(self, photo_obj):
        self.__photos.append(photo_obj)
        logging.info(f"Attaching new photo to recipe {self.__recipe.name}")

    def save_photos(self):
        for n, photo in enumerate(self.__photos):
            photo.download(f"/data/file_{n}.jpg")

 
class RecipeViz:
    def __init__(self, 
        data_manager: PersistencyManager, 
        user_id: int, 
        only_personal_rec: bool = True, 
        recipe_id_list: list = None, 
        disable_kb_actions: bool = False
    ):
        self.__data_manager = data_manager  
        self.__user_id = user_id
        self.__personal_flag = only_personal_rec
        is_global_search = not only_personal_rec

        #init keyboard state 
        self.__keyboard = keyboards.VizKeyboard(global_kb=is_global_search, disable_actions=disable_kb_actions)
        self.__index = 0
        self.__recList, self.__privList = list(), list()
        self.__cache = list()

        if recipe_id_list:
            #TODO - fix privacy values 
            recList = [(recipe_id, True) for recipe_id in recipe_id_list] 
        else:
            # obtain a list of pairs (id_recipe, recipe_privacy)
            recList = self.__data_manager.db_manager.get_recipes(
                user_id, 
                id_only=True, 
                all_recipes=is_global_search
            )
        
        #obtain two lists: the former for recipe's id, the latter for recipe's privacy
        if recList:
            self.__recList, self.__privList = [list(x) for x in zip(*recList)]
            self.__cache = [None for elem in self.__recList]

            self.__keyboard.update(self.recipe_position, self.num_recipes)
            self.__keyboard.reset(privacy_key_string = self.recipe_visibility)
        
    
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
    
    @property
    def recipe_visibility(self):
        return self.__privList[self.__index]
        
    def next(self):
        ret = False

        if self.__index < len(self.__recList) - 1:
            self.__index += 1 #update pointer 
            ret = self.__index != len(self.__recList) - 1

        self.__keyboard.update(self.recipe_position, self.num_recipes)
        self.__keyboard.reset(privacy_key_string = self.recipe_visibility)
        return ret

    def prev(self):
        ret = False

        if self.__index > 0:
            self.__index -= 1 #update pointer 
            ret = self.__index != 0
        
        self.__keyboard.update(self.recipe_position, self.num_recipes)
        self.__keyboard.reset(privacy_key_string = self.recipe_visibility)
        return ret 
    
    def do_action(self, action: str):
        self.__keyboard.do_action(action)


    def toggle_privacy(self, new_privacy_value):
        self.__keyboard.set_privacy(new_privacy_value) 
        self.__privList[self.__index] = new_privacy_value
        return new_privacy_value

    def delete_recipe(self):
        """ Delete from the database the current recipe and update the viz state """

        recipe_id = self.__recList[self.__index]

        logging.info(f"Trying to delete recipe #{recipe_id} owned by user {self.__user_id}")

        #remove the recipe from local buffers if the it has been correctly removed from db
        if self.__data_manager.delete_recipe(user_id = self.__user_id, recipe_id = recipe_id):
            del self.__recList[self.__index]
            del self.__cache[self.__index]

            logging.info(f"Recipe #{recipe_id} owned by user {self.__user_id} successfully deleted.")


    def get(self, format: bool = False):
        index = self.__index
        elem = self.__cache[index]        

        if elem is None:
            elem = self.__data_manager.db_manager.get_recipe_by_id(self.__recList[index])
            self.__cache[index] = elem

        message = elem 

        if format:
            ingredients = sorted([i.name.capitalize() for i in elem.ingredients])
            ingredients = "\n• ".join(ingredients)
            message = f""" 
<b>{elem.name.capitalize()}</b>

Ingredienti:
• {ingredients}

Ricetta {self.recipe_position}/{self.num_recipes}"""

        return message 


class Searcher:
    def __init__(self, data_manager: PersistencyManager, user_id: int):
        self.__data_manager = data_manager
        self.__user = user_id
        self.__all_tokens = list() #all tokens here 
        self.__tokens = list()     #word token here 
        self.__hashtags = list()   #hashtags here 
        self.__viz = None 

        self.__splitter = re.compile(r",|\n|\s|;")
    
    @property
    def visualization(self) -> RecipeViz:
        return self.__viz

    @property
    def all_tokens(self) -> list:
        return self.__all_tokens

    def add_token(self, message):
        self.__all_tokens.extend(self.__splitter.split(message))

    def parse(self):         
        for token in self.__all_tokens:
            target_list = self.__hashtags if token.startswith("#") else self.__tokens
            target_list.extend(token.split())

        logging.info(f"Tokens: {self.__tokens}\nHashtags: {self.__hashtags}")

    def is_instantiated(self) -> bool:
        return (self.__viz is not None)
    
    def instantiate(self, global_search) -> bool:
        """Initialize the visualization manager """

        recipes_id = self.__data_manager.db_manager.search_recipes(
            self.__tokens, self.__user, global_search
        )
        if recipes_id:
            self.__viz = RecipeViz(
                self.__data_manager, 
                self.__user, 
                only_personal_rec=(not global_search), 
                recipe_id_list=recipes_id, 
                disable_kb_actions=True
            )
            return True

        return False 

