#-*- coding: utf-8 -*-

import enum 
from emoji import emojize
from db.entities import Ingredient, Recipe

class Statements:
    @classmethod
    def welcome(cls, user_name):
        message = (
            f"Ciao, {user_name}!\n"
            "Cringette è il bot che ti aiuterà a tenere a portata di tap le tue ricette di cucina! :yum:\n"
            "È in uno stadio di sviluppo <i>alpha</i>, ciò significa che potrebbero verificarsi comportamenti non previsti.\n"
            "Per interagire con Cringette, puoi utilizzare la tastiera personalizzata o i comandi.\n"
            "Tappa su /help per visualizzare i comandi supportati!\n\n"
            "Che vuoi fare?"
        )
        return emojize(message, use_aliases=True)
    
    @classmethod
    def main_message(cls, user_name):
        message = f"Ciao, {user_name}!\nChe vuoi fare?"
        return emojize(message, use_aliases=True)
    
    @classmethod
    def helper(cls):
        message = (
            "<b>Comandi supportati:</b>\n\n"
        #    "• /nuova - aggiungi una ricetta\n"
            # "• /view - scorri le tue ricette o quelle degli altri utenti\n"
            # "• /search - cerca (per parole, hashtag...) tra le tue ricette o quelle degli altri utenti\n"
            "• /help - visualizza questo messaggio di aiuto\n"
            "• /stop - annulla il comando in corso\n"
            "\nAltre funzionalità sono in via di sviluppo! :smile:"
        )
        return emojize(message, use_aliases=True)




class RecipeInsertionStatements:    
    @classmethod
    def request_recipe_name(cls):
        return emojize("Molto bene! Come si chiama la ricetta?", use_aliases=True)

    @classmethod
    def request_ingredients(cls):
        message = (
            "Sono pronto! Inviami la lista degli ingredienti!\n\n"
            "NB. Puoi inviarmi un ingrediente alla volta, "
            "o se preferisci puoi scrivere più ingredienti in un unico messaggio, "
            "separandoli con delle virgole e/o con delle andate a capo!\n")
        return emojize(message, use_aliases=True)
    
    @classmethod
    def request_more_information(cls, recipe: Recipe):
        message = (
            f"{cls.viz_recipe(recipe)}\n"
            "Molto bene! Dimmi di più sulla tua nuova ricetta!"   
        )
        
        return emojize(message, use_aliases=True)

    @classmethod
    def request_recipe_method(cls, username):
        message = (
            f"{username}, ci siamo quasi!\n"
            "Inviami il procedimento per cucinare questa deliziosa ricetta, e anche qualche foto se vuoi!")
        return emojize(message, use_aliases=True)

    @classmethod
    def breatharianism_recipe(cls):
        message = (
            "Zio, non mi hai mandato nessun ingrediente!!\n"
            "Non sono ammesse ricette respiriane, quindi dimmi gli ingredienti o vai a fare in culo. :angry:")
        return emojize(message, use_aliases=True)

    @classmethod
    def undescribed_recipe(cls):
        message = "manca la ricetta, pirla."
        return emojize(message, use_aliases=True)


    @classmethod
    def save_recipe_confirm(cls, recipe):
        message = f"{cls.viz_recipe(recipe)}\n • Sei sicuro sicuro di voler salvare questa merdosissima ricetta?"
        return emojize(message, use_aliases=True)

    @classmethod
    def cancel_recipe_confirm(cls, recipe):
        prefix = str(recipe.name) if recipe else ""
        message = (f"{prefix} • Sei sicuro sicuro di voler cancellare questa merdosissima ricetta?")
        return emojize(message, use_aliases=True)


    @classmethod
    def viz_recipe(cls, recipe):
        ingredients = (
            ", ".join([str(ingr) for ingr in recipe.ingredients])
            if recipe.ingredients else "al momento nessuno."
        )
        message = (
            f"Ricetta: {recipe.name}\n"
            f"Ingredienti: {ingredients}\n"
        )

        return message
    
    @classmethod
    def discarded_recipe_method_message(cls, recipe):
        message = (
            f"{cls.viz_recipe(recipe)}"
            "Molto bene, ho cancellato quello che mi avevi scritto (stronzate)!\nFai qualcosa!")
        return emojize(message, use_aliases=True)
    
    @classmethod
    def canceled_recipe(cls, recipe):
        message = f"Inserimento ricetta {recipe.name if recipe else ''} annullata."
        return emojize(message, use_aliases=True)
    
    @classmethod
    def saved_recipe(cls, recipe):
        message = f"Ricetta {recipe.name} salvata con (in)successo nel database"
        return emojize(message, use_aliases=True)
    
    @classmethod
    def keep_going(cls):
        message = "E ora che intenzioni hai di bello?"
        return emojize(message, use_aliases=True)
    
    @classmethod
    def ask_again_for_recipe_name(cls):
        message = "Riprendiamo da dove eravamo rimasti... Come si chiama la ricetta?"
        return emojize(message, use_aliases=True)
    
    @classmethod
    def canceled_operation_lets_continue(cls):
        message = "Operazione annullata! E ora che intenzioni hai di bello?"
        return emojize(message, use_aliases=True)


class RecipeVisualisationStatements:
    @classmethod
    def view_recipe_in_list(clf, recipe, num_curr_recipe, num_max_recipe):
        ingredients = sorted([i.name.capitalize() for i in recipe.ingredients])
        ingredients = "\n• ".join(ingredients)
        message = (
            f"<b>{recipe.name.capitalize()}</b>\n\n"
            "Ingredienti:\n"
            f"• {ingredients}\n\n"
            f"Ricetta {num_curr_recipe}/{num_max_recipe}"
        )
        return emojize(message, use_aliases=True)