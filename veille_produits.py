# -*- coding: utf-8 -*-
import os
import json
import time
import requests
import anthropic
from datetime import datetime
from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()

CLE_ANTHROPIC  = os.getenv("ANTHROPIC_API_KEY")
CLE_SERPAPI    = os.getenv("SERPAPI_KEY")
TOKEN_TELEGRAM = os.getenv("TELEGRAM_TOKEN")
CHAT_ID        = os.getenv("TELEGRAM_CHAT_ID")

FICHIER_CACHE = "produits_cache.json"

CATEGORIES_SHOPPING = [
    "beaute soins visage",
    "sport fitness maison",
    "cuisine maison tendance",
    "animaux compagnie accessoires",
    "high tech gadgets",
    "vetements mode tendance",
]

CATEGORIES_ALI = [
    "beauty skincare bestseller",
    "sport fitness equipment",
    "home garden gadget",
    "pet accessories dog cat",
    "electronics gadget trending",
]

def collecter_google_shopping():
    print("Collecte Google Shopping via SerpAPI...")
    produits = []
    for categorie in CATEGORIES_SHOPPING:
        print("  -> " + categorie)
        try:
            params = {
                "engine": "google_shopping",
                "q": categorie,
                "location": "France",
                "hl": "fr",
                "gl": "fr",
                "num": 5,
                "tbs": "p_ord:rv",
                "api_key": CLE_SERPAPI,
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            for item in results.get("shopping_results", [])[:3]:
                titre = item.get("title", "N/A")
                prix  = item.get("price", "N/A")
                lien  = item.get("link", "N/A")
                note  = item.get("rating", "N/A")
                avis  = item.get("reviews", "N/A")
                if titre != "N/A":
                    produits.append({
                        "source":    "Google Shopping",
                        "categorie": categorie,
                        "titre":     titre[:80],
                        "prix":      prix,
                        "note":      note,
                        "avis":      avis,
                        "lien":      lien,
                    })
            time.sleep(2)
        except Exception as e:
            print("  Erreur " + categorie + " : " + str(e))
    print("  " + str(len(produits)) + " produits Google Shopping collectes")
    return produits


def collecter_aliexpress():
    print("Collecte AliExpress via SerpAPI...")
    produits = []
    for categorie in CATEGORIES_ALI:
        print("  -> " + categorie)
        try:
            params = {
                "engine": "aliexpress",
                "query": categorie,
                "locale": "fr_FR",
                "currency": "EUR",
                "api_key": CLE_SERPAPI,
            }
            search = GoogleSearch(params)
            results = search.get_dict()
            for item in results.get("products", [])[:3]:
                titre     = item.get("title", "N/A")
                prix      = item.get("price", {}).get("current_price", "N/A")
                commandes = item.get("orders", "N/A")
                note      = item.get("rating", "N/A")
                lien      = item.get("product_url", "N/A")
                if titre != "N/A":
                    produits.append({
                        "source":    "AliExpress",
                        "categorie": categorie,
                        "titre":     titre[:80],
                        "prix":      str(prix) + " EUR",
                        "commandes": commandes,
                        "note":      note,
                        "lien":      lien,
                    })
            time.sleep(2)
        except Exception as e:
            print("  Erreur " + categorie + " : " + str(e))
    print("  " + str(len(produits)) + " produits AliExpress collectes")
    return produits


def sauvegarder_cache(produits_shopping, produits_ali):
    data = {
        "date_collecte": datetime.now().strftime('%d/%m/%Y %H:%M'),
        "produits_shopping": produits_shopping,
        "produits_ali": produits_ali,
    }
    with open(FICHIER_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Donnees sauvegardees dans " + FICHIER_CACHE)


def charger_cache():
    if not os.path.exists(FICHIER_CACHE):
        print("Aucun cache trouve.")
        return None, None
    with open(FICHIER_CACHE, "r", encoding="utf-8") as f:
        data = json.load(f)
    print("Cache charge du " + data.get("date_collecte", "?"))
    return data.get("produits_shopping", []), data.get("produits_ali", [])


def analyser_avec_claude(produits_shopping, produits_ali):
    print("Analyse avec Claude...")
    client = anthropic.Anthropic(api_key=CLE_ANTHROPIC)
    prompt = """
Tu es un expert en dropshipping et e-commerce.
Voici les produits populaires collectes hier en France.

GOOGLE SHOPPING :
""" + json.dumps(produits_shopping[:15], ensure_ascii=False, indent=2) + """

ALIEXPRESS BESTSELLERS :
""" + json.dumps(produits_ali[:15], ensure_ascii=False, indent=2) + """

Ton travail :
1. Identifie les 5 MEILLEURS produits a lancer en dropshipping aujourd'hui
2. Pour chaque produit donne :
   - Nom du produit
   - Pourquoi c'est une opportunite maintenant
   - Prix de vente recommande
   - Marge estimee (%)
   - Niveau de concurrence : Faible / Moyen / Fort
   - Canal de vente ideal : TikTok Ads / Facebook Ads / Google Shopping / Organique
   - Score opportunite /10

Sois tres concis et direct. Pas de blabla. Format structure.
"""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
    except Exception as e:
        return "Erreur Claude : " + str(e)


def envoyer_telegram(analyse, produits_shopping, produits_ali, date_collecte):
    print("Envoi sur Telegram...")

    message_principal = "PRODUITS GAGNANTS DU JOUR\n"
    message_principal += "Collecte le : " + date_collecte + "\n"
    message_principal += "Envoye le : " + datetime.now().strftime('%d/%m/%Y %H:%M') + "\n\n"
    message_principal += analyse

    message_sources = "SOURCES BRUTES\n\n"
    message_sources += "Google Shopping :\n"
    for p in produits_shopping[:5]:
        message_sources += "- " + p['titre'][:50] + " - " + str(p.get('prix','N/A')) + " (note: " + str(p.get('note','N/A')) + ")\n"
    message_sources += "\nAliExpress :\n"
    for p in produits_ali[:5]:
        message_sources += "- " + p['titre'][:50] + " - " + str(p.get('prix','N/A')) + " (" + str(p.get('commandes','N/A')) + " commandes)\n"

    url = "https://api.telegram.org/bot" + TOKEN_TELEGRAM + "/sendMessage"

    for message in [message_principal, message_sources]:
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for chunk in chunks:
            try:
                r = requests.post(url, json={
                    "chat_id":    CHAT_ID,
                    "text":       chunk,
                    "disable_web_page_preview": True,
                }, timeout=10)
                if r.status_code == 200:
                    print("  Message envoye !")
                else:
                    print("  Erreur Telegram : " + r.text)
            except Exception as e:
                print("  Exception Telegram : " + str(e))
            time.sleep(1)


def collecter_et_sauvegarder():
    print("COLLECTE DU SOIR - " + datetime.now().strftime('%d/%m/%Y %H:%M'))
    produits_shopping = collecter_google_shopping()
    produits_ali      = collecter_aliexpress()
    sauvegarder_cache(produits_shopping, produits_ali)
    print("Collecte terminee !")


def envoyer_rapport_matin():
    print("ENVOI MATIN - " + datetime.now().strftime('%d/%m/%Y %H:%M'))
    produits_shopping, produits_ali = charger_cache()
    if not produits_shopping and not produits_ali:
        print("Pas de donnees a envoyer.")
        return
    with open(FICHIER_CACHE, "r", encoding="utf-8") as f:
        data = json.load(f)
    date_collecte = data.get("date_collecte", "?")
    analyse = analyser_avec_claude(produits_shopping, produits_ali)
    envoyer_telegram(analyse, produits_shopping, produits_ali, date_collecte)
    print("Rapport envoye !")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "collecter":
            collecter_et_sauvegarder()
        elif sys.argv[1] == "envoyer":
            envoyer_rapport_matin()
    else:
        collecter_et_sauvegarder()
        envoyer_rapport_matin()
