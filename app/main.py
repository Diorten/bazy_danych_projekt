import smtplib
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timedelta
from typing import Union, List, Dict, Tuple
from fastapi import FastAPI, Query, Response, Cookie, Request, HTTPException
from fastapi.responses import RedirectResponse
import hashlib
import math
import re
import random
import json
import string
from datetime import datetime
import mysql.connector
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import ssl
import tracemalloc
tracemalloc.start()

app = FastAPI(
title="Gwintoteka_dev",
    summary="Najlepsza aplikacja dla fanów Gwinta!",
    version="0.2",
    contact={
        "name": "Aleks M.",
        "email": "264419@student.pwr.edu.pl",
    }
)
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
ssl_context.load_cert_chain('app/cert.pem', keyfile='app/key.pem', password='cert')

app.mount("/cards_images", StaticFiles(directory="app/cards_images"), name="cards_images")

headers = [
    'Access-Control-Allow-Origin'
    'Access-Control-Allow-Credentials',
    'Access-Control-Allow-Methods',
    'Access-Control-Allow-Headers',
    'Content-Type',
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost", "https://gwintotekaapp.kizumono.cloud","https://gwintoteka.kizumono.cloud","https://ml6j5z6h.up.railway.app"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=headers,
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
    response = RedirectResponse(url='https://gwintotekaapp.kizumono.cloud')
    return response

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
    sus_patterns = [';', '--', '/*', '*/', 'xp_', 'exec', 'sp_', 'delete', 'drop', 'update', 'insert', 'union', 'truncate']
    for pattern in sus_patterns:
        if pattern in text.lower():
            return False

    acceptable_values = re.compile(r'^[a-zA-Z0-9@.!?#$%^&*()-_+=]+$')
    if acceptable_values.match(text):
        return True
    else:
        return False



#KLASY MODELI

class Register(BaseModel):
    username: str
    mail: str
    hash_u: str

class Login(BaseModel):
    mail: str
    hash_u: str

class Change_Pass(BaseModel):
    new_hash: str

class Mail(BaseModel):
    mail: str


def isLogged(najman_token):
    if string_verify(najman_token) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM `tokens` WHERE `token` = %s', (najman_token,))
        result = cursor.fetchone()
        conn.close()
        if result is None:
            return False
        else:
            return result[0]

def send_verify(mail, token):
    link = f'https://gwintoteka.kizumono.cloud/confirm?mail={mail}&verify_token={token}'
    subjectx = 'Confirm your mail at Gwintoteka right now!'
    bodyx = f'Hi, please confirm your mail by opening following link or copy it into browser: {link}'

    port = 587
    smtp_server = "smtp.gmail.com"
    sender_email = "gwintoteka@gmail.com"
    password = "eiomidjnilylgkgq"
    receiver_email = mail
    subject = subjectx
    body = bodyx
    message = 'Subject: {}\n\n{}'.format(subject, body)
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_server, port) as server:
        server.ehlo()  # Can be omitted
        server.starttls(context=context)
        server.ehlo()  # Can be omitted
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, message)
    return {'message':"CHUJ WIE NIE MAM SIŁY"}

def create_token(mail, u_hash):
    conn = connect_db()
    cursor = conn.cursor()
    current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
    combined_string = f'{mail}{u_hash}{current_time}'
    hash_object = hashlib.sha256()
    hash_object.update(combined_string.encode('utf-8'))
    najman_hash = hash_object.hexdigest()
    cursor.execute('INSERT INTO `tokens` (`mail`, `token`) VALUES (%s, %s)', (mail, najman_hash))
    conn.commit()
    conn.close()
    return (najman_hash)


def destroy_token(token):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM `tokens` WHERE `token` = %s', (token,))
    conn.commit()
    conn.close()


### TUTAJ ZACZYNAMY ENDPOINTY
# 480 - Wrong syntax
# 481 - Mail in use
# 491/92 - Wrong password/mail - do not reveal
# 406 - Unauthorized

@app.post('/register')
async def register(user: Register):
    if string_verify(user.mail) is True and string_verify(user.username) is True and string_verify(user.hash_u) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM `users` WHERE `mail` = %s', (user.mail,))
        result = cursor.fetchone()
        if result is None:
            current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
            combined_string = f'{user.mail}{user.hash_u}{current_time}'
            hash_object = hashlib.sha256()
            hash_object.update(combined_string.encode('utf-8'))
            mail_token = hash_object.hexdigest()
            cursor.execute('INSERT INTO `users` (`username`, `mail`, `hash`, `role`, `created_at`, `decks`, `reputation`, `comments`, `verified`) VALUES (%s, %s, %s, "user", CURRENT_TIMESTAMP, NULL, "0", NULL, %s)', (user.username, user.mail, user.hash_u, mail_token))
            conn.commit()
            conn.close()
            send_verify(user.mail, mail_token)
            return {'message': "Account registered, please confirm your mail!"}
        else:
            raise HTTPException(status_code=481, detail="Mail is already registered!")
    else:
        raise HTTPException(status_code=480, detail="Wrong syntax")


@app.post('/login')
async def login(user: Login, response: Response):
    if string_verify(user.mail) is True and string_verify(user.hash_u) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT `hash` FROM `users` WHERE `mail` = %s', (user.mail,))
        result = cursor.fetchone()
        cursor.execute('SELECT `verified` FROM `users` WHERE `mail` = %s', (user.mail,))
        result2 = cursor.fetchone()
        if result is not None and result2 is not None:
            if result[0] == user.hash_u:
                cursor.execute('SELECT `username` FROM `users` WHERE `mail` = %s', (user.mail,))
                username = cursor.fetchone()
                if result2[0] == 'yes':
                    cursor.execute('SELECT `token` FROM `tokens` WHERE `mail` = %s', (user.mail,))
                    result = cursor.fetchone()
                    conn.close()
                    if result is None:
                        token = create_token(user.mail, user.hash_u)
                        response.set_cookie(key="najman_token", value=token, max_age=18000, expires=18000, samesite='none', domain='.kizumono.cloud', secure=True)
                        return {'username': username, 'mail': user.mail, 'verified': 1}
                    else:
                        destroy_token(result[0])
                        token = create_token(user.mail, user.hash_u)
                        response.set_cookie(key="najman_token", value=token, max_age=18000, expires=18000, samesite='none', domain='.kizumono.cloud', secure=True)
                        return {'username': username, 'mail': user.mail, 'verified': 1}
                else:
                    cursor.execute('SELECT `token` FROM `tokens` WHERE `mail` = %s', (user.mail,))
                    result = cursor.fetchone()
                    conn.close()
                    if result is None:
                        #response.set_cookie(key="najman_token", value=najman_hash, max_age=1800, expires=1800, httponly=True, secure=True)
                        token = create_token(user.mail, user.hash_u)
                        response.set_cookie(key="najman_token", value=token, max_age=18000, expires=18000, samesite='none', domain='.kizumono.cloud', secure=True)
                        return {'username': username, 'mail': user.mail, 'verified': 0}
                    else:
                        destroy_token(result[0])
                        token = create_token(user.mail, user.hash_u)
                        response.set_cookie(key="najman_token", value=token, max_age=18000, expires=18000, samesite='none', domain='.kizumono.cloud', secure=True)
                        return {'username': username, 'mail': user.mail, 'verified': 0}
            else:
                conn.close()
                raise HTTPException(status_code=491, detail="Wrong credentials provided")
        else:
            conn.close()
            raise HTTPException(status_code=492, detail="Wrong credentials provided")
    else:
        raise HTTPException(status_code=480, detail="Wrong syntax")


@app.post('/changepassword')
async def change_pass(user: Change_Pass, response: Response, request: Request):
    najman_token = request.cookies.get('najman_token')
    if najman_token is not None:
        if string_verify(najman_token) is True and string_verify(user.new_hash) is True:
            if isLogged(najman_token) is not False:
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute('SELECT `mail` FROM `tokens` WHERE `token` = %s', (najman_token,))
                mail = cursor.fetchone()
                cursor.execute('UPDATE `users` SET `hash` = %s WHERE `users`.`mail` = %s', (user.new_hash, mail[0]))
                conn.commit()
                cursor.execute('DELETE FROM tokens WHERE `tokens`.`mail` = %s', (mail[0],))
                conn.commit()
                #
                current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
                combined_string = f'{mail}{user.new_hash}{current_time}'
                hash_object = hashlib.sha256()
                hash_object.update(combined_string.encode('utf-8'))
                najman_hash = hash_object.hexdigest()
                cursor.execute('INSERT INTO `tokens` (`mail`, `token`) VALUES (%s, %s)', (mail[0], najman_hash))
                conn.commit()
                cursor.execute('SELECT `username` FROM `users` WHERE `mail` = %s', (mail[0],))
                username = cursor.fetchone()
                conn.close()
                expiration_time = datetime.utcnow() + timedelta(minutes=30)
                response.set_cookie(key="najman_token", value=najman_hash, expires=expiration_time, httponly=True, secure=True)
                return {'username': username[0], 'mail': mail[0]}
            else:
                return {'message': "You are not logged in"}
        else:
            return {'message': "There's problem with your syntax :P"}
    else:
        return {'message': "You are not logged in"}

@app.post('/logout')
async def logout(response: Response, request: Request):
    najman_token = request.cookies.get('najman_token')
    if najman_token is not None:
        if string_verify(najman_token) is True:
            if isLogged(najman_token) is not False:
                destroy_token(najman_token)
                response.delete_cookie("najman_token")
                return {'message':"User logout success"}
            else:
                raise HTTPException(status_code=406, detail="Unauthorized")
        else:
            raise HTTPException(status_code=480, detail="Wrong syntax")
    else:
        raise HTTPException(status_code=406, detail="Unathorized")

@app.get('/confirm')
def confirm(mail: str, verify_token: str):
    if string_verify(mail) and string_verify(verify_token):
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT `verified` FROM `users` WHERE `mail` = %s', (mail,))
        temp_verify_token = cursor.fetchone()
        if temp_verify_token[0] is not None:
            if temp_verify_token[0] == verify_token:
                cursor.execute('UPDATE `users` SET `verified` = "yes" WHERE `users`.`mail` = %s', (mail,))
                conn.commit()
                conn.close()
                return {'message':"Mail sucessfully verified!"}
            else:
                raise HTTPException(status_code=483, detail="Wrong auth URI")
        else:
            raise HTTPException(status_code=484, detail="Wrong auth URI")
    else:
        raise HTTPException(status_code=480, detail="Wrong syntax")
    

@app.get('/deleteaccount')
def delteacc(response: Response, request: Request):
    najman_token = request.cookies.get("najman_token")
    if najman_token is not None:
        if string_verify(najman_token) is True:
            mail = isLogged(najman_token)
            if mail is not False:
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM `votes` WHERE `votes`.`mail` = %s', (mail,))
                conn.commit()
                cursor.execute('DELETE FROM `users` WHERE `users`.`mail` = %s', (mail,))
                conn.commit()
                conn.close()
                destroy_token(najman_token)
                return {'message': "Account sucesfully deleted!"}
            else:
                raise HTTPException(status_code=406, detail="Unauthorized")
        else:
            raise HTTPException(status_code=480, detail="Wrong syntax")
    else:
        raise HTTPException(status_code=406, detail="Unauthorized")

################################################
############# KARTY ############################
################################################

def format_card(data):
    """ Sformatuj obiekt karty przed wyslaniem go do frontendu."""
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
                "deck_set": c[9],
                "card_type": c[10],
                "armor": c[11],
                "color": c[12],
                "power": c[13],
                "reach": c[14],
                "artist": c[15],
                "rarity": c[16],
                "faction": c[17],
                "related": c[18],
                "provision":c[19],
                "factionSecondary": c[20]
            }
        }
        results.append(card)
    return results

def format_deck(data):
    """ Sformatuj obiekt deck przed wyslaniem go do frontendu."""
    results = []
    for entry in data:
        deck = {
            "deck_id": entry[0],
            "user": entry[1],
            "skill": entry[2],
            "link": entry[3],
            "title": entry[4],
            "faction": entry[5],
            "rating": entry[6],
            "recruitment": entry[7],
            "card_counter": entry[8]
        }
        results.append(deck)
    return results

def get_deck_details(conn, deck_id, user):
    """ Uzyj buffered cursor do wywolania procedury GetDeckData i pozyskania wszystkich
    danych dotyczacuch wybranej talii. """
    if conn and conn.is_connected():
        # raw=True daje output chyba w binarce - nie wiem NIE TYKAC
        # buffered=True zmienia typ kursora. Teraz kursor wyłapie wszystkie
        # dane przed wywolaniem callproc(). Mam nadzieje, ze wydajnosc nie spadnie
        # Wiecej: https://stackoverflow.com/questions/46682012/what-is-a-mysql-buffered-cursor-w-r-t-python-mysql-connector
        print("Jestem w funkcji get_deck_details przed wywolaniem stored procedure!!!")
        cursor = conn.cursor(raw=True, buffered=True)
        cursor.execute(f"CALL GetDeckData(%s, %s);", (deck_id, user))

        # 2. Zostaje zwrocona tupla z jednym itemem - bytearray.
        byte_data = cursor.fetchone()[0]
        # 3. Tego bytearray trzeba zdeckodowac - frajera pieprzonego.
        decoded_byte = byte_data.decode('utf-8')
        # 4. Na koniec konwertujemy do JSON i essa.
        results = json.loads(decoded_byte)
        cursor.close()
        return results
    else:
        return {"response": "Polaczenie z baza danych nie istnieje."}

def get_deck_id_and_user(conn, link):
    """ Pozyskaj deck_id i wlasciciela talii """
    if conn and conn.is_connected():
        deck_id_query = f"SELECT deck_id, user FROM deck WHERE link=%s;"
        cursor = conn.cursor()
        cursor.execute(deck_id_query, (link,))
        data = cursor.fetchone()
        deck_id = data[0] # Mamy to!
        owner = data[1] # Mamy to!
        cursor.close()
        results = [deck_id, owner]
        print(deck_id, owner)
        return results
    else:
        print("jest problem z polaczeniem, patrz get_deck_id_and_user")
        return False

@app.get('/cards')
def get_cards(
        query_string: str = "",
        page: int = Query(1, ge=1),
        provision: Union[str, None] = None, # Wartosci <1; 14>
        faction: Union[str, None] = None, # Monster, Neutral, Northern Realms, Scoiateal, Nilfgaard, Skellige
        deck_set: Union[str, None] = None, # BaseSet, Unmillable, Thronebreaker, NonOwnable()
        card_type: Union[str, None] = None, # Unit, Special, Artifact, Ability
        color: Union[str, None] = None, # Gold, Bronze, Leader
        rarity: Union[str, None] = None  # Epic, Rare, Legendary, Common
    ):
    """Pozyskaj za pomocą GET Request wszystkie karty lub ich czesc po zastosowaniu filtrow."""

    # 1. Otworz polaczenie do bazy danych
    conn = connect_db()

    # 2. Przygotuj trzon query oraz listy
    params = []     # Parametry, ktore podstawimy za %s
    filters = []    # Filtry postawione w query po WHERE
    deck = 'cards_with_attributes'

    if faction == "Northern Realms":
        deck = 'cards_northern_realms'

    elif faction == "Monster":
        deck = 'cards_monster'

    elif faction == "Scoiatael":
        deck = 'cards_scoiatael'

    elif faction == "Nilfgaard":
        deck = 'cards_nilfgaard'

    elif faction == "Skellige":
        deck = 'cards_skellige'

    query = f"SELECT * FROM {deck}"

    # 3. Przygotuj paginacje
    query_cards_total = f"SELECT COUNT(*) AS total FROM {deck};"
    if conn and conn.is_connected():
        cursor = conn.cursor()
        cursor.execute(query_cards_total)
        cards_total = cursor.fetchall()[0][0]
        cursor.close()
    
    cards_per_page = 30
    total_pages = math.ceil(cards_total / cards_per_page)
    offset = (page - 1) * cards_per_page # Od ktorej ktorej karty zaczac?

    # 4. Sprawdz, czy sa jakies filtry
    if (not query_string == "") or (provision != None) or (deck_set != None) or (card_type != None) or (color != None) or (rarity != None):
        # 4.1. Jesli sa, to dodaj klauzure WHERE...
        query += " WHERE "

        # 4.2. ...a nastepnie dodaj do niej zastosowane filtry.
        if not query_string == "":
            filters.append(f"""(name LIKE %s OR category LIKE %s OR ability LIKE %s OR keyword_html LIKE %s)""")
            params += ['%' + query_string + '%'] * 4

        if provision != None:
            filters.append(f"provision=%s")
            params += [int(provision)]

        if deck_set != None:
            filters.append(f"deck_set=%s")
            params += [deck_set]

        if card_type != None:
            filters.append(f"card_type=%s")
            params += [card_type]

        if color != None:
            filters.append(f"color=%s")
            params += [color]

        if rarity != None:
            filters.append(f"rarity=%s")
            params += [rarity]

        # 4.3 Wszystkie filtry trzeba oddzielic operatorem logicznym AND
        for filter in filters:
            query += filter
            query += " AND "

        # 4.4. Usun ostatniego " AND ", by uniknac bledu skladni
        query = query[:-5]

    # 5. Na końcu query dodaj paginacje.
    query += f" ORDER BY provision DESC LIMIT %s OFFSET %s;"
    params += [cards_per_page, offset]

    # 6. Pobierz rekordy z bazy danych
    if conn and conn.is_connected():
      with conn.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()
        print(data)

    # 7. Zwroc frontend'owi uzyskane rekordy w formacie JSON
    results = [cards_total, total_pages]
    all_cards = []
    for c in format_card(data):
            all_cards.append(c)
    results.append(all_cards)
    return {"response": results}

@app.get('/skills')
def get_skills(
    faction: Union[str, None] = None
):
    """ Pozyskaj skille z bazy danych. Uzyj argumentu faction do uzyskania skilla konkretnej frakcji. """
    # 1. Otworz polaczenie do bazy danych
    conn = connect_db()

    # 2. Pozyskaj skille
    if faction:
        query = f"SELECT * FROM skills WHERE faction=%s;"
        params = (faction,)
        
        if conn and conn.is_connected():
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                data = cursor.fetchall()
    else:
        query = "SELECT * FROM skills;"
        if conn and conn.is_connected():
            with conn.cursor() as cursor:
                cursor.execute(query)
                data = cursor.fetchall()

    skills = []
    for entry in data:
        skill = {
            "skill_name": entry[0],
            "faction": entry[1],
            "description": entry[2],
            "description_html": entry[3],
            "bonus_provisions": entry[4]
        }
        skills.append(skill)

    return skills

@app.get('/decks')
def get_deck_data(
    request: Request,
    action: str = "show_decks",
    deck_id: Union[int, None] = None    
):

    """ Pozyskaj z bazy danych wszystkie decki nalezace do zalogowanego uzytkownika."""
    najman_token = request.cookies.get('najman_token')
    
    if najman_token is not None:
        
        if string_verify(najman_token) is True:
            user = isLogged(najman_token)
            
            if user is not False:
                # 1. Otworz polaczenie do bazy danych
                conn = connect_db()

                # Pokaz tylko ogolne informacje o decku.
                if action == "show_decks":

                    # 2. Pozyskaj wszystkie decki konkretnego użytkownika z bazy danych 
                    query = f"SELECT * FROM deck WHERE user=%s;"
                    params = (user,)

                    if conn and conn.is_connected():
                        with conn.cursor() as cursor:
                            cursor.execute(query, params)
                            data = cursor.fetchall()
                    
                    # 3. Sformatuj dane do JSON.
                    results = []
                    for entry in format_deck(data):
                        results.append(entry)
                
                # Pokaz szczegolowe dane dotyczace wybranego decku
                elif action == "show_details" and (deck_id != None and deck_id > 0):
                    print("Jestem w funkcji get_deck_data!!!")
                    # Sprawdz, czy user ma dostęp do talii.
                    has_access = False

                    # Jesli uzytkownik jest autorem talii, to ma dostep
                    my_own_deck_query = f"SELECT link FROM deck WHERE deck_id=%s AND user=%s;"
                    if conn and conn.is_connected():
                        with conn.cursor() as cursor:
                            cursor.execute(my_own_deck_query, (deck_id,user,))
                            data = cursor.fetchall()
                            print("Czy data jest puste dla tego uzytkownika?\n", data)
                            if data:
                                has_access = True

                    # Jesli uzytkownikowi udostępniono talie, to ma dostep
                    if has_access != True:
                        published_deck_query = f"SELECT link FROM deck WHERE deck_id=%s;"
                        if conn and conn.is_connected():
                            with conn.cursor() as cursor:
                                cursor.execute(published_deck_query, (deck_id,))
                                data = cursor.fetchall()
                                link = data[0][0]
                        if link:
                            # Na tym etapie, wiemy ze talia MOZE byc publiczna, trzeba jeszcze sprawdzic,
                            # czy nie jest udostepniona dla wybrancow i czy obecnie zalogowany uzytkownik
                            # nie jest jednym z tych wybrancow.
                            published_for_choosen_deck_query = f"SELECT user FROM shared_link_users WHERE link=%s;"
                            if conn and conn.is_connected():
                                with conn.cursor() as cursor:
                                    cursor.execute(published_for_choosen_deck_query, (link,))
                                    choosen_ones = cursor.fetchall()
                                    
                                    # Jesli jest jakis wpis w shared_link_users dla tej talii, to talia dla wybrancow
                                    if choosen_ones:
                                        for entry in choosen_ones:
                                            if user in entry:
                                                has_access = True
                                    # Jesli nie ma wpisu, to talia udostepniona dla wszystkich
                                    else:
                                        has_access = True
                                    

                    if has_access == True:
                        # Pobierz autora talii, żeby pobrać całą talię
                        deck_author_query = f"SELECT user FROM deck WHERE deck_id=%s;"
                        if conn and conn.is_connected():
                            with conn.cursor() as cursor:
                                cursor.execute(deck_author_query, (deck_id,))
                                data = cursor.fetchall()
                                author = data[0][0]

                        results = get_deck_details(conn, deck_id, author)
                    else:
                        results = {"response": "Nie masz dostepu do talii!"}
                # Pozyskaj linka do wybranego decku.
                elif action == "link_get" and (deck_id != None and deck_id > 0):
                    if conn and conn.is_connected():
                        link_get_query = f"SELECT link FROM deck WHERE deck_id=%s AND user=%s;"
                        cursor = conn.cursor()
                        cursor.execute(link_get_query, (deck_id, user,))
                        results = cursor.fetchone()[0]
                        cursor.close()
                
                # Wyswietl wszystkie dostepne dla uzytkownika talie (W tym jego wlasne)
                elif action == "show_public_decks":
                    results = []
                    if conn and conn.is_connected():

                        # 2. Pozyskaj wszystkie decki nalezace do obecnie zalogowanego uzytkownika. 
                        my_own_decks_query = f"SELECT * FROM deck WHERE user=%s;"    
                        cursor = conn.cursor()
                        cursor.execute(my_own_decks_query, (user,))
                        my_own_decks = cursor.fetchall()
                        my_own_decks_ids = []
                        # print("\n\nMy Own Decks: ", my_own_decks)
                        for entry in format_deck(my_own_decks):
                            print(entry)
                            results.append(entry)
                            my_own_decks_ids.append(entry["deck_id"])
                        cursor.close()
                        # print("\n\nMy own decks ids: ", my_own_decks_ids)

                        # 3. Pobierz wszystkie decki, dla ktorych pole 'link' nie ma wartosci NULL.
                        public_decks_all_query = "SELECT * FROM deck WHERE link IS NOT NULL;"
                        cursor = conn.cursor()
                        cursor.execute(public_decks_all_query)
                        public_decks_all = cursor.fetchall()
                        cursor.close()
                        # print("\n\nPublic_decks_all: ", public_decks_all)

                        # 4. Pobierz informacje o tym, ktore decki maja widok ograniczony (wybrani uzytkownicy).
                        public_decks_limited_query = f"SELECT * FROM shared_link_users;"
                        cursor = conn.cursor()
                        cursor.execute(public_decks_limited_query)
                        public_decks_limited = cursor.fetchall()
                        cursor.close()
                        # print("\n\nPublic_decks_limited: ", public_decks_limited)
                    
                    
                        # 4.5 Potrzebujemy unikalnych linkow - jesli jest kilka rekordow z tym samym
                        # linkiem, to do listy public_links_limited bierzemy ten link tylko raz.
                        public_links_limited = []
                        for deck in public_decks_limited:
                            if deck[1] not in public_links_limited:
                                public_links_limited.append(deck[1])
                            
                        # 5. Pobierz linki publiczne ograniczone, do ktorych zalogowany uzytkownik ma dostep.
                        public_decks_available_query = f"SELECT link FROM shared_link_users WHERE user=%s;"
                        cursor = conn.cursor()
                        cursor.execute(public_decks_available_query, (user,))
                        public_decks_available = cursor.fetchall()
                        cursor.close()
                        # print("\n\nPublic_decks_available: ", public_decks_available)

                        # 5.5 Umiesc te linki w liscie public_links_available
                        public_links_available = []
                        for l in public_decks_available:
                            public_links_available.append(l[0])
                        # print("\n\nPublic_links_available: ", public_links_available)

                        # 6. Zwroc wszystkie decki, ktore sa dostepne dla wszystkich oraz dla
                        # aktualnie zalogowanego uzytkownika.
                        for entry in format_deck(public_decks_all):
                            # entry["link"] not in public_links_limited = ten link NIE JEST ograniczony
                            # entry["link"] in public_links_available = ten link JEST ograniczony, ale obecnie
                            #   zalogowany uzytkownik ma prawo do jego odczytu.
                            # print(entry["link"])
                            # print(entry["link"] not in public_links_limited)
                            # print(entry["link"] in public_links_available)
                            if ((entry["link"] not in public_links_limited) or (entry["link"] in public_links_available)) and entry["deck_id"] not in my_own_decks_ids:
                                results.append(entry)
                        
                else:
                    results = {"response": "Podano bledne parametry!"}
                conn.close()
            else:
                results = {"response": "You are not logged in"}
        else:
            results = {"response": "There's problem with your syntax."}
    else:
        results = {"response": "You are not logged in."}        
    return results


@app.get('/decks/{public_link}')
def get_deck_by_link(
    request: Request,
    public_link: str
):
    """ Pozyskaj szczegolowe dane dotyczace konkretnej talii, wykorzystujac linka """
    najman_token = request.cookies.get('najman_token')
    print(najman_token is not None)
    if najman_token is not None:
        print(string_verify(najman_token) is True)
        if string_verify(najman_token) is True:
            user = isLogged(najman_token)
            print(user is not False)
            if user is not False:
    
                conn = connect_db()
                results = None
                try:
                    if conn and conn.is_connected():
                        # Sprawdz czy talia jest dostepna dla wszystkich czy wybrancow poprzez sprawdzenie
                        # liczby rekordow w shared_link_users. Jesli nic nie ma, to talia dla wszystkich jest.
                        allowed_users_query = f"SELECT user FROM shared_link_users WHERE link=%s;"
                        cursor = conn.cursor()
                        cursor.execute(allowed_users_query, (public_link,))
                        data = cursor.fetchall()
                        users = []
                        for u in data:
                            users.append(u[0])
                        cursor.close()

                        # Wszyscy moga zobaczyc talie
                        
                        if not users:
                            info = get_deck_id_and_user(conn, public_link)
                            print("Jestem wewnatrz get_deck_by_link. Wartosc users: ", users, "Wartosc info:", info)
                            if info == False:
                                results = {"response": "Polaczenie z baza danych nie istnieje."}
                            else:
                                print("Jestem w funkcji get_deck_by_link, gdzie users jest puste!!!")
                                results = get_deck_details(conn, info[0], info[1])

                        # Konkretne osoby moga zobaczyc talie
                        else:               
                              
                            print("Jestem w funkcj iget_deck_by_link, w warunku else. Wartosc users: ", users, "Wartosc user:", user)
                            if user in users:
                                info = get_deck_id_and_user(conn, public_link)
                                print("Info:", info)
                                if info == False:
                                    results = {"response": "Polaczenie z baza danych nie istnieje."}
                                else:
                                    
                                    print("Jestem w funkcji get_deck_by_link, gdzie users NIE jest puste!!!")
                                    #print(get_deck_details(conn, info[0], info[1]))
                                    results = get_deck_details(conn, info[0], info[1])
                            else:
                                results = {"response": "Z jakiegos powodu link nie dziala, nie powiem jakiego, bo to security link"}
                     
                        print(results)
                except TypeError as e:
                    results = {"response": "Nie ma takiego linku!"}
                conn.close()
            else:
                results = {"response": "You are not logged in"}
        else:
            results = {"response": "There's problem with your syntax."}
    else:
        results = {"response": "You are not logged in."}   
    
    print(results)
    return results

class Deck(BaseModel):
    user: Union[str, None] = None
    skill: Union[str, None] = None
    title: Union[str, None] = None
    faction: Union[str, None] = None
    recruitment: Union[int, None] = None
    card_counter: Union[int, None] = None
    cards: Union[Dict[str, List[str]], None] = None
    """
    deck_example = Deck(
        user="example_user",
        skill="Fruits of Ysgith",
        title="example_title",
        faction="Monster",
        recruitment=4,
        card_counter=30,
        cards={
            "Card1": ("Fiend", '1'),
            "Card2": ("Eredin Br\u00e9acc Glas", '2'),
            "Card3": ("Ge'els", '1')
        }
    )
    """

@app.post('/decks')
def manage_deck(
    request: Request,
    deck: Union[Deck, None] = None,     # Potrzebny do wprowadzenia rekordu
    deck_id: Union[int, None] = None,   # Potrzebny do zmiany/usuniecia rekordu
    users: Union[List[str], None] = None,     # Opcjonalnie potrzebny do stworzenia linka
    action: str = ""

):
    """ Usun wszystkie informacje dotyczace decku o podanym deck_id"""

    # user potrzebny jest wszedzie, zeby miec pewnosc, ze wszystkie akcje podejmuje
    # zalogowany uzytkownik. Moze byc tak, ze bedziemy mieli duplikaty (user oraz deck.user).
    najman_token = request.cookies.get('najman_token')
    if najman_token is not None:
        if string_verify(najman_token) is True:
            user = isLogged(najman_token)
            if user is not False:

                # 1. Otworz polaczenie do bazy danych
                conn = connect_db()
		
                # Wprowadz nowy deck do bazy danych. 
                #   Od frontendu potrzebny jest obiekt Deck.
                print(action)
                print(deck)
                print(deck_id)
                if action == "send" and deck != None and user != None:
                    '''
                    deck = Deck(
                        user="filip@gmail.com",
                        skill="Fruits of Ysgith",
                        title="example_title",
                        faction="Monster",
                        recruitment=4,
                        card_counter=30,
                        cards={
                            "Fiend": ("Fiend", '1'),
                            "Eredin Br\u00e9acc Glas": ("Eredin Br\u00e9acc Glas", '2'),
                            "Ge'els": ("Ge'els", '1')
                        }
                    )
                    '''
                    if conn and conn.is_connected():
                        cursor = conn.cursor()
                        
                        # 2.a) Przygotuj zapytanie do wprowadzenia rekordu do tabeli deck.
                        columns_decks = "user, skill, link, title, faction, rating, recruitment, card_counter"
                        values_decks = (deck.user, deck.skill, None, deck.title, deck.faction, 0, deck.recruitment, deck.card_counter)
                        query_decks = f"INSERT INTO deck ({columns_decks}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"
                        
                        # 2.b) Przygotuj zapytanie do uzyskania deck_id z nowo wprowadzonego rekordu.
                        #       Bedzie ono potrzebne do tego, by w deck_cards bylo takie samo deck_id.
                        deck_id_query = f"SELECT deck_id FROM deck WHERE user=%s ORDER BY deck_id DESC LIMIT 1;"
                        deck_id_params = (deck.user,)

                        # 2.c) Wprowadz rekord do tabeli deck... 
                        cursor.execute(query_decks, values_decks)
                        conn.commit()

                        # 2.d) ...a potem pozyskaj deck_id tego rekordu.
                        cursor.execute(deck_id_query, deck_id_params)
                        deck_id = cursor.fetchone()[0]

                        # 3. Wprowadz karty do deck_cards
                        for card in deck.cards:
                            card_query = f"INSERT INTO deck_cards (deck_id, card_name, quantity) VALUES (%s, %s, %s);"
                            card_name = deck.cards[f"{card}"][0]
                            quantity = deck.cards[f"{card}"][1]
                            card_values = (deck_id, card_name, quantity,)

                            cursor.execute(card_query, card_values)
                            conn.commit()

                        cursor.close()
                    
                    return {"response": "Wprowadzono nowy deck!"}
                
                elif action == "update" and (deck_id != None and deck_id > 0) and deck != None and user != None :

                    fields = [] # nazwy zmienianych pol
                    values = [] # nowe wartosci zmienianych pol

                    # 2. Pobierz dane, ktore sa zmieniane przez usera
                    if deck.skill != None:
                        fields.append("skill")
                        values.append(deck.skill)
                    
                    if deck.title != None:
                        fields.append("title")
                        values.append(deck.title)

                    if deck.faction != None:
                        fields.append("faction")
                        values.append(deck.faction)
                    
                    if deck.recruitment != None:
                        fields.append("recruitment")
                        values.append(deck.recruitment)

                    if deck.card_counter != None:
                        fields.append("card_counter")
                        values.append(deck.card_counter)

                    # 3. Sformatuj odpowiednio zapytanie do bazy danych
                    update_deck_query = "UPDATE deck SET "
                    
                    items = len(fields)
                    for i in range(0, items):
                        update_deck_query += f"{fields[i]} = %s, "
                    
                    update_deck_query = update_deck_query[:-2] # Usun spacje i przecinek
                    update_deck_query += f" WHERE deck_id=%s;"
                    print(update_deck_query)
                    values.append(deck_id)

                    # 4. Zmien informacje o wybranym deck
                    if conn and conn.is_connected():
                        cursor = conn.cursor()
                        cursor.execute(update_deck_query, values)
                        conn.commit()
                        cursor.close()
                    
                    # 5. Przeprowadz transakcje usuwania deck_cards i wprowadzania nowych
                    if deck.cards:
                        try:
                            if conn and conn.is_connected():
                                cursor = conn.cursor()

                                # 5.a. Rozpocznij transakcje
                                cursor.execute("START TRANSACTION;")
                                
                                # 5.b Usun wszystkie karty z tabeli deck_cards o podanym deck_id
                                delete_query = f"DELETE FROM deck_cards WHERE deck_id=%s;"
                                delete_values = (deck_id,)
                                cursor.execute(delete_query, delete_values)
                                
                                # 5.c Dodaj wszystkie nowe karty
                                insert_query = f"INSERT INTO deck_cards (deck_id, card_name, quantity) VALUES (%s, %s, %s);"
                                
                                for card in deck.cards:
                                    insert_values = (deck_id, deck.cards[f"{card}"][0], int(deck.cards[f"{card}"][1]),)
                                    cursor.execute(insert_query, insert_values)
                                
                                # 5.d Zatwierdz transakcje.
                                cursor.execute("COMMIT;")
                                
                                cursor.close()
                            
                        except Exception as e:
                            cursor.execute("ROLLBACK;")
                            cursor.close()
                            conn.close()
                            return {"response": f"Internal Server Error: {e}"}
                    
                    conn.close()
                    return {"response": "Zmiany wprowadzono pomyslnie"}
                
                # Usun istniejacy rekord deck. Od frontendu potrzebny jest deck_id.
                elif action == "delete" and (deck_id != None and deck_id > 0) and user != None:
                    # 2. Usun deck o podanym deck_id. Spowoduje tez usuniecie wszystkich rekordow
                    #       w deck_cards o tym samym deck_id.
                    query = f"DELETE FROM deck WHERE deck_id=%s AND user=%s;"
                    values = (deck_id, user)
                    if conn and conn.is_connected():
                        cursor = conn.cursor()
                        cursor.execute(query, values)
                        conn.commit()
                        cursor.close()
                        conn.close()

                    if cursor.rowcount > 0:
                        return {"response": "Usunieto deck"}
                    else:
                        return {"response": "Deck nie zostal usuniety"}

                # Stworz publiczny link dostepny dla wszystkich lub wybranych uzytkownikow
                elif action == "link_create" and (deck_id != None and deck_id > 0) and user != None:
                    link = generate_public_link(deck_id)
                    if link != '':
                        if conn and conn.is_connected():
                            users_json = json.dumps(users)
                            print(users_json)
                            cursor = conn.cursor()
                            cursor.execute(f"CALL CreateDeckLink(%s, %s, %s, %s)", (link, deck_id, user, users_json,))
                            conn.commit()
                            cursor.close()
                        conn.close()
                        print(link)
                        return {"response": link}
                    
                    else:
                        raise HTTPException(status_code=469, detail="Link exists")

                elif action == "link_delete" and (deck_id != None and deck_id > 0) and user != None:
                    if conn and conn.is_connected():
                        cursor = conn.cursor()
                        cursor.execute(f"CALL DeleteDeckLink(%s, %s);", (deck_id, user,))
                        conn.commit()
                        cursor.close()
                    conn.close()
                    return {"response": "Link usunieto pomyslnie!", "link": link}
                
                else:
                    return {"response": "Bledne parametry!"}
            else:
                return {"response": "You are not logged in"}
        else:
            return {"response": "There's problem with your syntax."}
    else:
        return {"response": "You are not logged in."} 


def generate_public_link(deck_id):
    """ Stworz publicznego linka do decka. Zwraca linka lub pustego stringa, jesli
    link juz istnieje."""

    # 1. Wygeneruj linka
    link = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    link_status = check_if_link_exists(link, deck_id)
    # 2.a Jesli link nie istnieje, to zwroc go.
    if link_status == 0:
        return link
    
    # 2.b. Jesli deck ma juz przypisany link, to zwroc informacje o tym:
    elif link_status == 1:
        return ''
    
    # 2.c Jesli stworzony link jest uzywany przez inny deck, to generuj nowe linki
    #       az do skutku.
    else:
        while (link_status == 2):
            link = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
            link_status = check_if_link_exists(link, deck_id)
    
        return link

def check_if_link_exists(link, deck_id):
    """ Sprawdz, czy link istnieje w bazie danych. Zwraca True, jesli istnieje albo
    False, jesli nie istnieje """
    
    # 0 - nie istnieje
    # 1 - istnieje, wybrany deck juz posiada linka.
    # 2 - istnieje, inny deck go uzywa
    link_status = 0

    conn = connect_db()

    # 1. Sprawdz, czy podany deck ma juz link. 
    if conn and conn.is_connected():
        link_assigned_query = f"SELECT link FROM deck WHERE deck_id=%s;"
        link_assigned_values = (deck_id,)
        cursor = conn.cursor()
        cursor.execute(link_assigned_query, link_assigned_values)
        result = cursor.fetchone()
        
        # Jesli wartosc pola link nie jest None (Albo null w db) to znaczy, ze juz istnieje link.
        if result[0] != None:
            link_status = 1
        cursor.close()
    # 2. Sprawdz, czy taki link juz istnieje.
    if conn and conn.is_connected():
        link_check_query = f"SELECT link FROM deck WHERE link=%s;"
        link_check_values = (link,)
        cursor = conn.cursor()
        cursor.execute(link_check_query, link_check_values)
        # Musimy odczytac wynik, żeby uniknac Unread results found, ale nic z tym nie zrobimy.
        result = cursor.fetchone()

        # Jesli istnieje
        if cursor.rowcount != 0:
            link_status = 2
        cursor.close()
    return link_status

@app.get('/ranking')
def ranking(request: Request):
    najman_token = request.cookies.get("najman_token")
    if najman_token is not None:
        if string_verify(najman_token) is True:
            mail = isLogged(najman_token)
            if mail is not False:
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute('SELECT `user`, `skill`, `title`, `faction`, `rating` FROM `deck` WHERE `link` IS NULL ORDER BY `rating` DESC')
                result = cursor.fetchall()
                print(result)
                ranking = []
                for entry in result:
                    rank = {
                        "author": entry[0],
                        "deck_name": entry[2],
                        "skill": entry[1],
                        "faction": entry[3],
                        "rating": entry[4]
                    }
                    ranking.append(rank)
                return ranking
            else:
                raise HTTPException(status_code=406, detail="Unauthorized")
        else:
            raise HTTPException(status_code=480, detail="Wrong syntax")
    else:
        raise HTTPException(status_code=406, detail="Unauthorized")


def vote_up(mail, deck_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO `votes` (`mail`, `deck_id`, `voted`) VALUES (%s, %s, "1")', (mail, deck_id))
    conn.commit()
    cursor.execute('SELECT `rating` FROM `deck` WHERE `deck_id` = %s', (deck_id,))
    voting = cursor.fetchone()
    voting = voting[0]
    voting = voting + 1
    cursor.execute('UPDATE `deck` SET `rating` = %s WHERE `deck`.`deck_id` = %s', (voting, deck_id))
    conn.commit()
    conn.close()

def vote_down(mail, deck_id):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO `votes` (`mail`, `deck_id`, `voted`) VALUES (%s, %s, "1")', (mail, deck_id))
    conn.commit()
    cursor.execute('SELECT `rating` FROM `deck` WHERE `deck_id` = %s', (deck_id,))
    voting = cursor.fetchone()
    voting = voting[0]
    voting = voting - 1
    cursor.execute('UPDATE `deck` SET `rating` = %s WHERE `deck`.`deck_id` = %s', (voting, deck_id))
    conn.commit()
    conn.close()


###..--------------------..
##|``--------------------''|
##|                        |
##|                        |
##|                        |
##|                        |
##|         KOCHAM         |
##|          PWr           |
##|                        |
##|          5VOL          |
##|         5 /  5         |
##|                        |
##|                        |
##|                        |
##|                        |
##|                        |
##';----..............----;'
####'--------------------'

@app.get('/rate')
def rate(request: Request, deck_id: str, act: str):
    najman_token = request.cookies.get("najman_token")
    if najman_token is not None:
        if string_verify(najman_token) is True:
            mail = isLogged(najman_token)
            if mail is not False:
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute('SELECT `link` FROM `deck` WHERE `deck_id` = %s', (deck_id,))
                owner = cursor.fetchone()
                if owner is None:
                    cursor.execute('SELECT `mail` FROM `votes` WHERE `deck_id` = %s', (deck_id,))
                    result = cursor.fetchone()
                    conn.close()
                    if result is None:
                        if act == "up":
                            vote_up(mail, deck_id)
                            return {'message':"Vote added"}
                        elif act == "down":
                            vote_down(mail, deck_id)
                            return {'message':"Vote added"}
                        else:
                            raise HTTPException(status_code=498, detail="There is problem with your action")
                    else:
                        return {'message':"You already voted!"}
                else:
                    conn = connect_db()
                    cursor = conn.cursor()
                    cursor.execute('SELECT `mail` FROM `votes` WHERE `deck_id` = %s', (deck_id,))
                    result = cursor.fetchone()
                    conn.close()
                    if result is None:
                        if mail == owner[0]:
                            if act == "up":
                                vote_up(mail, deck_id)
                                return {'message':"Vote added"}
                            elif act == "down":
                                vote_down(mail, deck_id)
                                return {'message':"Vote added"}
                            else:
                                raise HTTPException(status_code=498, detail="There is problem with your action")
                        else:
                            conn = connect_db()
                            cursor = conn.cursor()
                            cursor.execute('SELECT * FROM `shared_link_users` WHERE `user` = %s AND deck_id = %s', (mail, deck_id))
                            result = cursor.fetchall()
                            print(result)
                            if result is not None:
                                if act == "up":
                                    vote_up(mail, deck_id)
                                    return {'message':"Vote added"}
                                elif act == "down":
                                    vote_down(mail, deck_id)
                                    return {'message':"Vote added"}
                                else:
                                    raise HTTPException(status_code=498, detail="There is problem with your action")
                            else:
                                raise HTTPException(status_code406, detail="Unauthorized")
                    else:
                        return {'message':"Your already voted!"}
            else:
                raise HTTPException(status_code=406, detail="Unauthorized")
        else:
            raise HTTPException(status_code=480, detail="Wrong syntax")
    else:
        raise HTTPException(status_code=480, detail="Unauthorized")


'''
@app.get('/skills/send')
def insert_skills():
    """ Wypelnij tabelę 'skills' wszystkimi skillami z pliku skills.json. """
    query_columns = "skill_name, faction, description, description_html, bonus_provisions"

    # 1. Otworz polaczenie do bazy danych
    conn = connect_db()
    cursor = conn.cursor()

    # 2. Otwórz plik skills.json
    try:
        with open('./app/skills.json', 'r') as json_file:

            # 3. Odczytaj dane, a nastepnie wprowadz je do bazy danych.
            data = json.load(json_file)
            for entry in data:
                # entry zwraca stringa "1"..."30"
                skill_name = data[entry]["name"]
                faction = data[entry]["faction"]
                description = data[entry]["description"]
                description_html = data[entry]["description_html"]
                bonus_provisions = data[entry]["bonus_provisions"]

                query_values = (skill_name, faction, description, description_html, bonus_provisions,)
                query = f"INSERT INTO skills ({query_columns}) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, query_values)
                conn.commit()
    except Exception as e:
        print(f"\n\nWystąpił błąd podczas wczytywania danych:\n\n{e}")

    conn.close()


# Pozwolisz, że zakomentuje coś co może rozsadzić nam bazę, jak Bartek będzie łączył API :)

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


def get_active_user(
    najman_token: str
):
    """Znajdz uzytkownika na podstawie najman_token.
    Taki uzytkownik jest aktywny + wszelkie operacje beda dotyczyc tylko jego."""
    conn = connect_db()
    cursor = conn.cursor()
    query = f"SELECT mail FROM tokens WHERE tokens=%s"
    values = (najman_token,)

    mail = cursor.execute(query, values)

    # Jezeli znaleziono mail, to go zwroc
    if mail:
        return mail
    else:
        return None

'''
