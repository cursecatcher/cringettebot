# -*- coding: utf-8 -*-

from sqlalchemy import create_engine
from sqlalchemy import (
    and_,
    delete,
    or_
)
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
    def __init__(self, db_name: str):
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

    def __add_user(self, session, user):
        user = session.query(User).filter(User.user_id == user).first()

        if not user: 
            user = User(user_id = user)
            session.add(user)
            session.commit()
        
        return (not user)


    def add_recipe(self, recipe_entity: ent.Recipe):
        """ Add a new recipe and its ingredient list in the database """

        new_recipe_id = None 

        try:
            session = self.__sessionMaker() 

            if self.__add_user(session, recipe_entity.owner):
                logging.info(f"New user ({recipe_entity.owner}) added to the db")

            my_ingredients = list() 

            ### add ingredients in db and keeping trace of their id
            for ingredient in recipe_entity.ingredients:
                curr_ingredient = session.query(Ingredient).filter(Ingredient.name == ingredient.name).first()

                if not curr_ingredient:
                    # insert ingredient if it is not already present 
                    curr_ingredient = Ingredient(name=ingredient.name)
                    session.add(curr_ingredient)
                
                my_ingredients.append(curr_ingredient)
            else:
                session.commit() 

            ### initialize the new recipe 
            recipe = Recipe(
                name=recipe_entity.name, 
                owner=recipe_entity.owner, 
                public_flag=False
            )
            ### adding ingredient ids to the new recipe
            for ingredient in my_ingredients:
                recipe.ingredients.append(
                    IngredientsRecipe(
                        ingredientID=ingredient.id, 
                        quantity="q.b."
                    )
                )
            ### adding the recipe and its composition to the db 
            session.add(recipe)
            session.commit()

            logging.info(f"User {recipe.owner} added recipe '{recipe.name}' having id = {recipe.id}")

            new_recipe_id = recipe.id 

        except:
            logging.info("Error in add_recipe...")
            raise
        finally:
            session.close()

        recipe_entity.id = new_recipe_id
        return new_recipe_id

    def get_recipe_by_id(self, recipe_id: int) -> ent.Recipe:
        """ Retrieve a recipe from the db given its id @recipe_id """

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



    def get_recipes(self, 
            user_id: int, 
            id_only: bool = False, 
            all_recipes: bool = False):
        """ Retrieve the recipes belonging to @user_id from the database 
        if @all_recipes is True. Otherwise it returns all the public recipes.
        If @id_only is True, then only the recipes' id are returned. """

        try:
            session = self.__sessionMaker() 
            recipes_list = list() 
            query = session.query(Recipe)

            query = query.filter(Recipe.public_flag) \
                    if all_recipes else query.filter(Recipe.owner == user_id) 

            if id_only:
                for my_recipe in query.all():
                    recipes_list.append(my_recipe.id)
            else:
                for my_recipe in query.all():
                    curr_recipe = ent.Recipe(recipe_obj = my_recipe)
                    recipes_list.append(curr_recipe)

                    for ingredient in session.query(Ingredient).join(IngredientsRecipe).\
                                    filter(IngredientsRecipe.recipeID == my_recipe.id).all():
                        curr_recipe.add_ingredient(ingredient.name)
            
            logging.info(f"User {user_id} retrieved {len(recipes_list)} -- {'global' if all_recipes else 'local'} search.")

            return recipes_list
        except:
            logging.info(f"Exception raised in DBManager.get_recipes(user_id={user_id}, id_only={id_only}, all_recipes={all_recipes})")
            raise
        finally:
            session.close()

    

    def check_recipe_availability(self, recipe: ent.Recipe) -> bool:
        """ Check if the recipe name is avaiable for the specified user """

        try:
            session = self.__sessionMaker() 
            return (self.__get_recipe(session, recipe.name, recipe.owner) is None)
        finally:
            session.close()
    

    def __get_recipe(self, session, recipe_name: str, user_id: int):
        result = session.query(Recipe).filter(and_(
            Recipe.owner == user_id, 
            Recipe.name == recipe_name
        )).first()
        logging.info(f"Query result of get_id_recipe: {result}")
        return result 


    def toggle_privacy(self, user_id: int, recipe_id: int):
        """ Toggle privacy for a specific recipe owned by @user_id. 
        The function returns the new privacy status (True/False) if it is correctly toggled, None otherwise. """

        try:
            session = self.__sessionMaker()
            my_recipe = session.query(Recipe).filter(Recipe.id == recipe_id).first()

            if my_recipe and my_recipe.owner == user_id:
                my_recipe.public_flag = (not my_recipe.public_flag)
                session.commit()

                logging.info(f"Privacy for recipe {recipe_id} toggled.")

                return my_recipe.public_flag
        except:
            logging.info(f"Esploso: toggle_privacy({user_id}, {recipe_id})")
        finally:
            session.close() 

    
    def delete_recipe(self, user_id: int, by_id: int = None, by_name: str = None):
        """ Delete a recipe given the owner'id @user_id and either
        - the recipe's id @by_id or the recipe's name @by_name """

        if by_id is None and by_name is None:
            return False    #wtf 

        try:
            session = self.__sessionMaker()
            query = session.query(Recipe)
            qresult = None

            if by_id:
                qresult = query.filter(and_(
                    Recipe.id == by_id, 
                    Recipe.owner == user_id)).first() 

            elif by_name:
                qresult = query.filter(and_(
                    Recipe.name == by_name, 
                    Recipe.owner == user_id)).first() 

            if qresult:
                session.delete(qresult)
                session.commit()

                logging.info(f"Recipe named {qresult.name} successfully deleted.")

                return True 
        except:
            raise 
        finally:
            session.close() 


    
    def show_table_content(self):
        #just for debug purposes
        try:
            session = self.__sessionMaker() 

            print("\n\nINGREDIENTS")
            for x in session.query(Ingredient).all():
                print(x)

            print("\n\nRECIPES")
            for x in session.query(Recipe).all():
                print(x)

            print("\n\nIngredients x recipe")
            for x in session.query(IngredientsRecipe).all():
                print(x)
        except:
            raise 
        finally:
            session.close() 

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
    
    def delete_procedure(self, recipe_obj):
        filepath = self.__filename(recipe_obj)

        if os._exists(filepath):
            os.remove(filepath)
            return True 
            
        return False


    
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
    
    def delete_recipe(self, user_id: int, recipe_name: str = None, recipe_id: int = None):
        pass