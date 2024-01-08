from typing import Union
from fastapi import FastAPI, Query
import hashlib
import re
import json
import math
from datetime import datetime
import mysql.connector
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
title="Gwintoteka_dev",
    summary="Najlepsza aplikacja dla fanów Gwinta!",
    version="0.1.1",
    contact={
        "name": "Aleks M.",
        "email": "aleks.m@gwintoteka.com",
    }
)
app.mount("/cards_images", StaticFiles(directory="app/cards_images"), name="cards_images")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def connect_db():
    conn = mysql.connector.connect(
            host='db',
            user='root',
            password='kochampwr123',
            database='baza',
            port='3306'
    )
    return conn


@app.get('/')
def read_root():
    return {"Serwus, dowoj po Śląsku"}

@app.get('/test_sql')
def test():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute('SELECT VERSION();')
    result = cursor.fetchall()
    conn.close()
    return {'result': result}

# OCHRONA PRZED SQLi
def string_verify(text):
        acceptable_values = re.compile(r'^[a-zA-Z0-9@.]+$')
        if acceptable_values.match(text):
                return True
        else:
                return False

# TWORZENIE NAJMAN_TOKEN
def token_create(passhash):
    conn = connect_db()
    cursor = conn.cursor(buffered=True)
    cursor.execute('SELECT `mail` FROM `users` WHERE `hash` = %s', (passhash,))
    mail = cursor.fetchone()

    print(mail)

    if passhash is not None:
        current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
        combined_string = f'{mail}{passhash}{current_time}'
        hash_object = hashlib.sha256()
        hash_object.update(combined_string.encode('utf-8'))
        najman_hash = hash_object.hexdigest()
        cursor.execute('INSERT INTO `tokens` (`mail`, `token`) VALUES (%s, %s)', (mail[0], najman_hash))
        conn.commit()
        conn.close()
        return najman_hash

    else:
        conn.close()
        # Handle the case where the user with the given passhash is not found
        return False
#            token_create(cursor, passhash)

# SPRAWDZANIE TOKENU
def token_check(token):
    if string_verify(token) == True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT `mail` FROM `tokens` WHERE `token` = %s', (token,))
        result = cursor.fetchone()
        if result is None:
            return False
        else:
            return(result)

# TWORZENIE USERA/CREATE ACC
def create(username, mail, passhash):
    if string_verify(passhash) is True and string_verify(username) is True and string_verify(mail) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO `users` (`username`, `mail`, `hash`, `role`, `created_at`, `decks`, `reputation`, `comments`) VALUES (%s, %s, %s, "user", CURRENT_TIMESTAMP, NULL, "0", NULL)', (username, mail, passhash))
        conn.commit()
        conn.close()
        return True
    else:
        return False

# LOGOWANIE
def login_func(mail, passhash):
    if string_verify(passhash) is True:
        token = token_create(passhash)
        return(token)
    else:
        return False

# ZMIANA HASŁA
def change_hash(mail_b, passhash):
    mail = mail_b[0]
    if string_verify(passhash) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('UPDATE `users` SET `hash` = %s WHERE `users`.`mail` = %s', (passhash, mail))
        conn.commit()
        cursor.execute('DELETE FROM tokens WHERE `tokens`.`mail` = %s', (mail,))
        conn.commit()
        conn.close()
        token = token_create(uid_b[0])
        return(token)
    else:
        return False

def getUid(mail):
    if string_verify is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT `username` FROM `users` WHERE `mail` = %s', (mail,))
        result = cursor.fetchone()
        conn.close()
        if result is not None:
            return(result)
        else:
            return False

def checkMailDuplicate(mail):
    if string_verify(mail) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM `users` WHERE `mail` = %s', (mail,))
        result = cursor.fetchall()
        conn.close()
        print(result)
        if result is not None:
            return True
        else:
            return False


def checkLogged(mail):
    if string_verify(mail) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM `tokens` WHERE `mail` = %s', (mail,))
        token = cursor.fetchall()
        conn.close()
        if token is None:
            return True
        else:
            return False

def logout_now(token):
    if string_verify(token) == True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM `tokens` WHERE `token` = %s', (token,))
        conn.close()
        return
    

class Register(BaseModel):
    username: str
    mail: str
    hash_u: str

class Login(BaseModel):
    mail: str
    hash_u: str

class Change_Pass(BaseModel):
    najman_token: str
    new_hash: str

class Logout(BaseModel):
    mail: str
    najman_token: str


@app.post('/register')
async def register(user: Register):
    """
     Tu mi dajesz username i hash hasła cn mordo
    """
    if checkMailDuplicate(user.mail) is False:
        return {"message":"Mail already registered"}
    if create(user.username, user.mail, user.hash_u):
        return {"message":"Account registered"}
    else:
        return {"Error has been encountered, zobacz czy dobrze tego body mordo zrobiłeś"}

@app.post('/login')
async def login(user: Login):
    """
     Tu dajesz mi mordo to samo co do rejestracji
    """
    if checkLogged(user.mail) is False:
        return {"message":"You can't reach access now"}
    else:
        token = login_func(user.mail, user.hash_u)
        username = getUid(user.mail)
        if token is not False and username is not False:
            return {"username": username[0],
                    "mail": user.mail,
                    "token": token}
        else:
            return {"Error has been encountered"}

@app.post('/changepassword')
async def change_pass(user: Change_Pass):
    """
     Wokurwa zmiana hasla juz dodana ;0000, dobra jak cos to wpierdalasz wsm nie wiem co zobacz body
    """
    mail = token_check(user.najman_token)
    if mail is not False:
        token = change_hash(mail, user.new_hash)
        if token is not False:
             return {"token":token}
        else:
             return {"Error has been encountered"}
    else:
        return {"Error has been encoutered"}

@app.post('/logout')
async def logout(user: Logout):
    if checkLogged(user.mail) is False:
        logout_now(token)
        return {"message": "Succesfull logout"}
    else:
        return {"message": "Wrong data input"}

@app.get('/cards')
def get_cards(
        query_string: str = "",
        page: int = Query(1, ge=1),
        provision: Union[int, None] = None, # Wartosci <1; 14>
        faction: Union[str, None] = None, # Monster, Neutral, Northern Realms, Scoiateal, Nilfgaard, Skellige
        deck_set: Union[str, None] = None, # BaseSet, Unmillable, Thronebreaker, NonOwnable()
        card_type: Union[str, None] = None, # Unit, Special, Artifact, Ability
        color: Union[str, None] = None, # Gold, Bronze, Leader
        rarity: Union[str, None] = None  # Epic, Rare, Legendary, Common
    ):
    """Pozyskaj za pomocą GET Request wszystkie karty lub ich czesc po zastosowaniu filtrow."""
    
    # 1. Otworz polaczenie do bazy danych
    conn = connect_db()

    # 2. Przygotuj paginacje

    # Zdobadz liczbe rekordow z bazy
    # query_cards_total = "SELECT COUNT(*) AS total FROM cards;"
    # cursor.execute(query_cards_total)
    # cards_total = cursor.fetchall()[0][0]
    cards_total = 509 # Usunac, jesli custom karty beda dodane
    cards_per_page = 30
    # total_pages = math.ceil(cards_total / cards_per_page)
    total_pages = 17 # Usunac, jesli custom karty beda dodane
    offset = (page - 1) * cards_per_page # Od ktorej ktorej karty zaczac?

    # 3. Przygotuj trzon query oraz listy

    query = "SELECT * FROM cards JOIN attributes ON cards.name = attributes.name"
    params = []     # Parametry, ktore podstawimy za %s
    filters = []    # Filtry postawione w query po WHERE 

    # 4. Sprawdz, czy sa jakies filtry
    if (not query_string == "") or (provision != None) or (faction != None) or (deck_set != None) or (card_type != None) or (color != None) or (rarity != None):
        # 4.1. Jesli sa, to dodaj klauzure WHERE...
        query += " WHERE "

        # 4.2. ...a nastepnie dodaj do niej zastosowane filtry.
        if not query_string == "":
            filters.append(f"""(cards.name LIKE %s OR cards.category LIKE %s OR cards.ability LIKE %s OR cards.keyword_html LIKE %s)""")
            params += ['%' + query_string + '%'] * 4
        
        if provision != None:
            filters.append(f"attributes.provision=%s")
            params += [provision]

        if faction != None:
            filters.append(f"(attributes.faction=%s OR attributes.factionSecondary=%s)")
            params += [faction, faction]

        if deck_set != None:
            filters.append(f"attributes.deck_set=%s")
            params += [deck_set]

        if card_type != None:
            filters.append(f"attributes.card_type=%s")
            params += [card_type]

        if color != None:
            filters.append(f"attributes.color=%s")
            params += [color]
        
        if rarity != None:
            filters.append(f"attributes.rarity=%s")
            params += [rarity]

        # 4.3 Wszystkie filtry trzeba oddzielic operatorem logicznym AND
        for filter in filters:
            query += filter
            query += " AND "

        # 4.4. Usun ostatniego " AND ", by uniknac bledu skladni
        query = query[:-5]
    
    # 5. Na końcu query dodaj paginacje.
    query += f" ORDER BY attributes.provision DESC LIMIT %s OFFSET %s;"
    params += [cards_per_page, offset]

    # 6. Pobierz rekordy z bazy danych
    if conn and conn.is_connected():
      with conn.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()

    # 7. Zwroc frontend'owi uzyskane rekordy w formacie JSON
    results = []
    for c in data:
            card = {
                "card_id": c[0],
                "name": c[1],
                "category": c[2],
                "ability": c[3],
                "ability_html": c[4],
                "keyword_html": c[5],
                "flavor": c[6],
                "image": c[7],
                "is_custom": c[8],
                "attributes": {
                    "deck_set": c[10],
                    "card_type": c[11],
                    "armor": c[12],
                    "color": c[13],
                    "power": c[14],
                    "reach": c[15],
                    "artist": c[16],
                    "rarity": c[17],
                    "faction": c[18],
                    "related": c[19],
                    "provision":c[20],
                    "factionSecondary": c[21]
                }
            }
            results.append(card)

    return {"response": results}


'''
Pozwolisz, że zakomentuje coś co może rozsadzić nam bazę, jak Bartek będzie łączył API :)

@app.get("/cards/send")
def insert_every_card_and_attr():
    """ Wypelnij baze danych wszystkimi kartami wraz z ich atrybutami znajdujacymi sie w pliku cards.json. """
    
    # 1. Nawiaz polaczenie z baza danych.
    conn = connect_db()
    cursor = conn.cursor()
    
    # 2. Wczytaj dane z pliku JSON
    try:
        with open('./app/cards.json', 'r') as json_file:

            data = json.load(json_file)
            cards_columns = "card_id, name, category, ability, ability_html, keyword_html, flavor, image, is_custom"
            attr_columns = "name, deck_set, card_type, armor, color, power, reach, artist, rarity, faction, related, provision, factionSecondary"
            
            # Shupe: Mage, Shupe: Hunter i Shupe: Knight ma az 6 roznych wersji! 
            # Wybrana zostanie ta ostatnia - liczba porzadkowa 465
            # Unikamy zmiany primary key na card_id?
            i = 0
            duplicates = [459, 460, 461, 462, 463, 465, 466, 467, 468, 469, 471, 472, 473, 474, 475]
            # 2.1 Odczytaj kazdy rekord
            for entry in data['response']:
                if (i not in duplicates):
                    # data['response'][entry] zwraca liczbe porzadkowa karty w pliku json (nie mylic z card_id) - kart jest 523

                    # Dane karty
                    card_id = data['response'][entry]['id']['card'] # Musimy użyć tych samych id, bo jest pole attributes.related
                    name = data['response'][entry]['name']
                    category = data['response'][entry]["category"]
                    ability = data['response'][entry]["ability"]
                    ability_html = data['response'][entry]["ability_html"]
                    keyword_html = data['response'][entry]["keyword_html"]
                    flavor = data['response'][entry]["flavor"]

                    image = f"cards_images/{name}_{card_id}_high.png"
                    # W api.gwent.one niektore karty uzywaja w nazwie znaku ':', podczas gdy nazwy obrazow uzywaja spacji.
                    # Z tego wzgledu trzeba zamienic ':' na spacje.
                    if (":" in image):
                        image = image.replace(":", "")
                    is_custom = 0 # 0 oznacza FALSE, pole potrzebne na customowe karty tworzone przez uzytkownikow.
                    
                    # Przygotowanie query do bazy danych
                    cards_values = (card_id, name, category, ability, ability_html, keyword_html, flavor, image, is_custom,)   
                    cards_query = f"INSERT INTO cards ({cards_columns}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);"
                    
                    # =========================== Attributes ========================================
                    
                    # Dane atrybutów karty
                    deck_set = data['response'][entry]['attributes']["set"]
                    card_type = data['response'][entry]['attributes']["type"]
                    armor = data['response'][entry]['attributes']['armor']
                    color = data['response'][entry]['attributes']["color"]
                    power = data['response'][entry]['attributes']["power"]
                    reach = data['response'][entry]['attributes']["reach"]
                    artist = data['response'][entry]['attributes']["artist"]
                    rarity = data['response'][entry]['attributes']["rarity"]
                    faction = data['response'][entry]['attributes']["faction"]
                    related = data['response'][entry]['attributes']["related"]
                    provision = data['response'][entry]['attributes']["provision"]
                    factionSecondary = data['response'][entry]['attributes']["factionSecondary"]

                    # Przygotowanie query do bazy danych
                    attr_values = (name, deck_set, card_type, armor, color, power, reach, artist, rarity, faction, related, provision, factionSecondary,)
                    attr_query = f"INSERT INTO attributes ({attr_columns}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);"

                    # Wprowadź dane pojedynczego rekordu do bazy danych (powtorz 524 razy)
                    cursor.execute(cards_query, cards_values)
                    conn.commit()
                    cursor.execute(attr_query, attr_values)
                    conn.commit()
                    i += 1
                else:
                    i += 1
                    continue
                

    except Exception as e:
        print(f"\n\nWystąpił błąd podczas wczytywania danych:\n\n{e}")


'''
