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
import os, shutil

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
                public_flag=recipe_entity.visibility
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
        If @id_only is True, then a pair containing the recipe id and the recipe privacy is returned. """

        try:
            session = self.__sessionMaker() 
            recipes_list = list() 
            query = session.query(Recipe)

            query = query.filter(Recipe.public_flag) \
                    if all_recipes else query.filter(Recipe.owner == user_id) 

            if id_only:
                for my_recipe in query.all():
                    recipes_list.append((my_recipe.id, my_recipe.public_flag))
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

    

    def check_recipe_availability(self, 
        recipe_name: str = None, 
        recipe_owner: int = None,  
        recipe: ent.Recipe = None
    ) -> bool:
        """ Check if the recipe name is avaiable for the specified user """

        try:
            session = self.__sessionMaker() 
            if recipe: 
                recipe_name, recipe_owner = recipe.name, recipe.owner
            return (self.get_recipe_pro(session, user_id=recipe_owner, by_what=recipe_name) is None)
        finally:
            session.close()


    def toggle_privacy(self, user_id: int, recipe_id: int):
        """ Toggle privacy for a specific recipe owned by @user_id. 
        The function returns the new privacy status (True/False) if it is correctly toggled, None otherwise. """

        try:
            session = self.__sessionMaker()

            my_recipe = self.get_recipe_pro(session, user_id, recipe_id)
            if my_recipe:
                my_recipe.public_flag = (not my_recipe.public_flag)
                session.commit()

                logging.info(f"Privacy for recipe {recipe_id} toggled.")
                return my_recipe.public_flag
        except:
            logging.info(f"Esploso: toggle_privacy({user_id}, {recipe_id})")
        finally:
            session.close() 


    def get_recipe_pro(self, session, user_id: int, by_what) -> Recipe:
        """ @by_what can be either int or string """
        query = session.query(Recipe)

        if isinstance(by_what, int):
            return query.filter(and_(
                Recipe.id == by_what, Recipe.owner == user_id)).first() 

        elif isinstance(by_what, str):
            return query.filter(and_(
                Recipe.name == by_what, Recipe.owner == user_id)).first() 

        else:
            raise RuntimeError("By what argument must be either str or int.")



    def delete_recipe(self, user_id: int, by_id: int = None, by_name: str = None) -> int:
        """ Delete a recipe given the owner'id @user_id and either
        - the recipe's id @by_id or the recipe's name @by_name.
        Returns the deleted recipe's id, None otherwise. """
   
        try:
            session = self.__sessionMaker()
            qresult = self.get_recipe_pro(session, user_id, 
                by_id if by_id and isinstance(by_id, int) else str(by_name)
            )

            if qresult:
                recipe_id = qresult.id 
                session.delete(qresult)
                session.commit()

                logging.info(f"Recipe named {qresult.name} successfully deleted.")
                return recipe_id
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
    

    def search_recipes(self, tokens: list, user_id: int, all_recipes: bool) -> list:
        #TODO - sort by score 
        """ Returns the list of recipe's id matching 1+ tokens """
        try:
            session = self.__sessionMaker()
            all_results = set()

            logging.info(f"User {user_id} is searching in {'public' if all_recipes else 'mine'} recipes")
            partial_query = session.query(Recipe).filter(Recipe.public_flag == True) \
                            if all_recipes else \
                            session.query(Recipe).filter(Recipe.owner == user_id)
            
            for token in tokens:
                results = partial_query.filter(Recipe.name.like(f"%{token}%")).all()
                all_results.update([recipe.id for recipe in results])
                logging.info(f"Results for user {user_id} for token {token}: {results}")
            
            logging.info(f"All search results for user {user_id}: {all_results}")
            return all_results

        except:
            raise 
        finally:
            session.close() 


    def search_by_hashtag(self, hashtag_list: list):
        return list()


class FSManager:
    def __init__(self, procedure_folder: str, photo_folder: str):
        self.__procedure_folder = procedure_folder
        self.__photo_folder = photo_folder 

        for dest_folder in (procedure_folder, photo_folder):
            if not os.path.exists(dest_folder):
                os.mkdir(dest_folder)
    
    def persist_procedure(self, recipe_obj: ent.Recipe, recipe_procedure: str):
        filepath = self.__filename(recipe_obj)

        with open(filepath, "w") as fo:
            fo.write(recipe_procedure)

    def persist_photos(self, recipe_obj: ent.Recipe, photo_list: list):
        if photo_list:
            photo_folder = self.__foldername(recipe_obj = recipe_obj)

            if not os.path.exists(photo_folder):
                os.mkdir(photo_folder)

            for index, photo in enumerate(photo_list, 1):
                filename = f"photo_{index}.jpg"
                photo.download(os.path.join(photo_folder, filename))


    def get_procedure(self, recipe_obj: ent.Recipe) -> str:
        """ Try to retrieve the procedure of @recipe_obj recipe from file. """

        filepath = self.__filename(recipe_obj)
        fcontent = None 

        try:
            with open(filepath) as fi:
                fcontent = fi.read()
        except FileNotFoundError:
            pass
        
        return fcontent

    
    def delete_procedure(self, recipe_obj: ent.Recipe = None, user_id: int = None, recipe_id: int = None):
        """ Delete the procedure file associated to the recipe passed as parameter.  """
        filepath = self.__filename(recipe_obj = recipe_obj, user_id = user_id, recipe_id = recipe_id)

        if os.path.exists(filepath):
            logging.info("File found")
            os.remove(filepath)
            return True 
    
    def delete_photos(self, recipe_obj: ent.Recipe = None, user_id: int = None, recipe_id: int = None):
        """ Delete all the photos associated to the recipe passed as parameter. """

        foldername = self.__foldername(recipe_obj, user_id, recipe_id)

        if os.path.exists(foldername):
            shutil.rmtree(foldername)

    def __foldername(self, recipe_obj: ent.Recipe = None, user_id: int = None, recipe_id: int = None) -> str: 
        """ Return the foldername where to save photos belonging to a specific recipe of a specific user """

        univocal_id = self.__identifier(recipe_obj, user_id, recipe_id)
        return os.path.join(self.__photo_folder, univocal_id)

    def __filename(self, recipe_obj: ent.Recipe = None, user_id: int = None, recipe_id: int = None) -> str: 
        """ Return the filename where to save the procedure of a specific recipe of a specific user """

        univocal_id = self.__identifier(recipe_obj, user_id, recipe_id)
        return os.path.join(self.__procedure_folder, f"{univocal_id}.txt")

    def __identifier(self, recipe_obj: ent.Recipe = None, user_id: int = None, recipe_id: int = None) -> str: 
        """ Return a string representing in a univocal way a certain recipe of a specific user.
        That string is simply @user_id <underscore> @recipe_id  """

        if recipe_obj:
            user_id = recipe_obj.owner
            recipe_id = recipe_obj.id 
        
        if user_id and recipe_id:
            return f"{user_id}_{recipe_id}"

        raise RuntimeError("Cannot obtain univocal identifier: missing data (user_id or recipe_id)")

class PersistencyManager:
    def __init__(self, db_manager: DBManager):
        self.__base_folder = os.path.dirname(db_manager.database_name)
        self.__dbmanager = db_manager

        procedure_folder = os.path.join(self.__base_folder, "procedures")
        photo_folder = os.path.join(self.__base_folder, "img")

        self.__fsmanager = FSManager(procedure_folder, photo_folder)
    
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
            self.fs_manager.persist_photos(recipe_obj, recipe_photos)

        return new_recipe_id
    
    def get_recipe(self, user_id: int, recipe_name: str = None, recipe_id: int = None):
        #recipe_obj = self.__dbmanager.
        pass 
    
    def delete_recipe(self, user_id: int, recipe_name: str = None, recipe_id: int = None):
        #try to delete recipe from db 
        id_rec = self.__dbmanager.delete_recipe(user_id = user_id, by_id = recipe_id, by_name = recipe_name)

        if id_rec:
            logging.info(f"Recipe #{id_rec} successfully deleted.")
            self.__fsmanager.delete_procedure(user_id = user_id, recipe_id = id_rec)
            self.__fsmanager.delete_photos(user_id = user_id, recipe_id = id_rec)

            return True 
        