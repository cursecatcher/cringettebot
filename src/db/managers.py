# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy import or_, and_
from sqlalchemy.orm import sessionmaker
from db.mappings import (
    Base,  
    Ingredient, 
    IngredientsRecipe, 
    Recipe, 
    User
)

from collections import defaultdict
import logging  
import os 

import db.entities as ent


class DBManager:
    def __init__(self, db_name: str = "/data/my_recipes.db"):
        self.__db_name = db_name
        self.__engine = create_engine(f"sqlite:///{db_name}")
        Base.metadata.create_all(self.__engine)

        self.__sessionMaker = sessionmaker()
        self.__sessionMaker.configure(bind=self.__engine)

    @property
    def database_name(self) -> str:
        return self.__db_name

    def set_recipe_privacy(self, recipe_id: int, public_recipe: bool):
        logging.info(f"setting  privacy of recipe {recipe_id} to {public_recipe}")

        try:
            session = self.__sessionMaker()
            session.query(Recipe).filter(Recipe.id == recipe_id).update({
                "public_flag": public_recipe
            })
            session.commit()
        except:
            logging.info(f"Esploso: set_recipe_privacy({recipe_id}, {public_recipe})")
        finally:
            session.close()

    def add_recipe(self, recipe_entity: ent.Recipe): 
        new_recipe_id = None

        try:
            session = self.__sessionMaker() 
            user = session.query(User).filter(User.user_id == recipe_entity.owner).first()

            if not user: 
                user = User(user_id = recipe_entity.owner)
                session.add(user)
                session.commit()
                logging.info(f"New user ({user}) added to the db")


            my_recipe = Recipe(name = recipe_entity.name, owner = recipe_entity.owner, public_flag = False)
            my_ingredients = list() 
            session.add(my_recipe)
        
            for ingredient in recipe_entity.ingredients:
                #search for an ingredient in the db
                curr_ingredient = session.query(Ingredient).filter(Ingredient.name == ingredient.name).first()

                if not curr_ingredient:
                    # insert ingredient if it is not already present 
                    curr_ingredient = Ingredient(name=ingredient.name)
                    session.add(curr_ingredient)
                
                my_ingredients.append(curr_ingredient)
            else: 
                # commit  recipe and ingredient insertions 
                session.commit()
                new_recipe_id = my_recipe.id 

            recipe_ingredients = [
                IngredientsRecipe(recipeID = my_recipe.id, ingredientID = ingredient.id) \
                    for ingredient in my_ingredients
            ]
            session.bulk_save_objects(recipe_ingredients)

            #commit ingredients for the current recipe 
            session.commit()

            logging.info(f"Recipe {my_recipe} successfully inserted in the db.")
        except:
            logging.warning("add_recipe triggers an exception => rollback")
            session.rollback()
            raise 
        finally: 
            session.close()
        
        recipe_entity.id = new_recipe_id
        return new_recipe_id

    def get_recipe_by_id(self, recipe_id: int):
        my_recipe = None 
        try:
            session = self.__sessionMaker() 
            that_recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()
            my_recipe = ent.Recipe(recipe_obj = that_recipe)

            for ingredient in session.query(Ingredient).join(IngredientsRecipe).\
                              filter(IngredientsRecipe.recipeID == that_recipe.id).all():
                my_recipe.add_ingredient(ingredient.name)
        except:
            logging.info(f"esploso in get_recipe_by_id({recipe_id}")
        finally:
            session.close() 
        
        return my_recipe

    def get_recipes(self, user_id: int, id_only: bool = False, all_recipes: bool = False):
        """ Retrieve the recipes belonging to @user_id from the database if @all_recipes is True. 
        Otherwise it returns all the public recipes.
        If @id_only is True, then only the recipes' id are returned. """

        recipes_list = list() 

        try:
            session = self.__sessionMaker() 

            query = session.query(Recipe).filter(Recipe.public_flag) \
                    if all_recipes else session.query(Recipe).filter(Recipe.owner == user_id) 

            for my_recipe in query.all():
                if id_only:
                    recipes_list.append(my_recipe.id)
                else:
                    curr_recipe = ent.Recipe(recipe_obj = my_recipe)
                    recipes_list.append(curr_recipe)

                    for ingredient in session.query(Ingredient).join(IngredientsRecipe).\
                                    filter(IngredientsRecipe.recipeID == my_recipe.id).all():
                        curr_recipe.add_ingredient(ingredient.name)
            
            logging.info(f"User {user_id} retrieved {len(recipes_list)} -- {'global' if all_recipes else 'local'} search.")
        except:
            logging.info(f"Exception raised in DBManager.get_recipes(user_id={user_id}, id_only={id_only}, all_recipes={all_recipes})")
            raise
        finally:
            session.close()

        return recipes_list
    

    def check_recipe_availability(self, recipe: ent.Recipe) -> bool:
        """ Check if the recipe name is avaiable for the specified user """

        session = self.__sessionMaker() 
        return (self.__get_recipe(session, recipe.name, recipe.owner) is None)
    

    def __get_recipe(self, session, recipe_name: str, user_id: int):
        result = session.query(Recipe).filter(and_(
            Recipe.owner == user_id, 
            Recipe.name == recipe_name
        )).first()
        logging.info(f"Query result of get_id_recipe: {result}")
        return result 


class FSManager:
    def __init__(self, dest_folder: str = "/data/recipes_folder"):
        self.__folder = dest_folder

        if not os.path.exists(dest_folder):
            os.mkdir(dest_folder)
    
    def persist_procedure(self, recipe_obj: ent.Recipe, recipe_procedure: str):
        filepath = self.__filename(recipe_obj)

        with open(filepath, "w") as fo:
            fo.write(recipe_procedure)

    def get_procedure(self, recipe_obj: ent.Recipe) -> str:
        filepath = self.__filename(recipe_obj)
        fcontent = None 

        with open(filepath) as fi:
            fcontent = fi.read()
        
        return fcontent
    
    def __filename(self, recipe_obj) -> str: 
        filename = f"{recipe_obj.owner}_{recipe_obj.id}.txt"
        return os.path.join(self.__folder, filename)


class PersistencyManager:
    def __init__(self, db_manager: DBManager):
        self.__base_folder = os.path.dirname(db_manager.database_name)
        self.__dbmanager = db_manager
        self.__fsmanager = FSManager(dest_folder = os.path.join(self.__base_folder, "procedures"))
    
    @property
    def db_manager(self):
        return self.__dbmanager

    @property
    def fs_manager(self):
        return self.__fsmanager
    

    def add_recipe(self, recipe_obj: ent.Recipe, recipe_procedure: str, recipe_photos: list = list()):
        new_recipe_id = self.db_manager.add_recipe(recipe_obj)

        if new_recipe_id is not None: 
            self.fs_manager.persist_procedure(recipe_obj, recipe_procedure)

        return new_recipe_id
    
    def delete_recipe(self, recipe_obj: ent.Recipe):
        pass 