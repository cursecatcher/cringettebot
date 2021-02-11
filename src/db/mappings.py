from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import (
    Boolean,
    Column, 
    ForeignKey,
    Integer, 
    PrimaryKeyConstraint,
    Sequence,
    String, 
    UniqueConstraint
)


Base = declarative_base()

class User(Base):
    __tablename__ = "User"

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
    user_id = Column(Integer, unique=True)


    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id})>"


class Ingredient(Base):
    __tablename__ = "Ingredient"

    id = Column(Integer, Sequence("ingredient_id_seq"), primary_key=True)
    name = Column(String, unique=True)


    def __repr__(self):
        return f"<Ingredient(id={self.id}, name='{self.name}')>"


class Recipe(Base):
    __tablename__ = "Recipe"

    id = Column(Integer, Sequence("recipe_id_seq"), primary_key=True)
    owner = Column(Integer, ForeignKey("User.id"), nullable=False)   
    public_flag = Column(Boolean)
    name = Column(String)

    procedure_file = Column(String, nullable=True, default=None)
    # date_add = Column(String, nullable=True)

    UniqueConstraint(owner, name)

    ingredients = relationship("IngredientsRecipe", cascade="all,delete", backref="recipe")


    def __repr__(self):
        return f"<Recipe(id={self.id}, name='{self.name}', owner={self.owner}, public={self.public_flag})>"


class IngredientsRecipe(Base):
    __tablename__ = "IngredientsRecipe"

    recipeID = Column(Integer, ForeignKey("Recipe.id"), nullable=False)
    ingredientID = Column(Integer, ForeignKey("Ingredient.id"), nullable=False)
    quantity = Column(String)
    PrimaryKeyConstraint(recipeID, ingredientID)

    def __repr__(self):
        return f"<IngredientRecipe(id_rec={self.recipeID}, id_ingr={self.ingredientID})>"

