#-*- coding: utf-8 -*-

class Recipe:
    def __init__(self, name = None, owner = None, recipe_obj = None):
        self.__ingredients = set()
        self.__id = None
        self.__global_visibility = False 

        if recipe_obj is not None: 
            self.__name = recipe_obj.name 
            self.__owner = recipe_obj.owner
            self.__id = recipe_obj.id 
        else: 
            self.__name = name.lower().strip() 
            self.__owner = owner

    @property
    def name(self):
        return self.__name 

    @property
    def owner(self):
        return self.__owner
    
    @property
    def id(self):
        return self.__id
    
    @id.setter 
    def id(self, id_value):
        self.__id = id_value
    
    @property
    def visibility(self):
        return self.__global_visibility
    
    @visibility.setter
    def visibility(self, value):
        self.__global_visibility = value 
    
    @property
    def ingredients(self):
        return list(self.__ingredients)
    
    def add_ingredient(self, ingredient_name: str):
        self.__ingredients.add(Ingredient(ingredient_name))
        return self 
    
    def add_ingredient_list(self, ingredients: list):
        self.__ingredients.update(map(lambda name: Ingredient(name), ingredients))
        return self 
    
    def __repr__(self):
        return (self.name, *self.ingredients)
    
    def __str__(self):
        return f"{self.name} ==> {self.ingredients}"

        

class Ingredient:
    def __init__(self, name):
        self.__name = name.lower().strip()
    
    def __hash__(self):
        return self.__name.__hash__() 
    
    def __eq__(self, other):
        return self.name == other.name

    @property
    def name(self):
        return self.__name
    
    def __repr__(self):
        return f"{self.name}"
