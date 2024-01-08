import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Union, List
from fastapi import FastAPI, Query, Response, Cookie, Request
import hashlib
import re
import json
import math
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Access-Contol-Allow-Headers", 'Content-Type', 'Authorization', 'Access-Control-Allow-Origin'],
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
    sus_patterns = [';', '--', '/*', '*/', 'xp_', 'exec', 'sp_', 'delete', 'drop', 'update', 'insert', 'union', 'truncate']
    for pattern in sus_patterns:
        if pattern in text.lower():
            return False

    acceptable_values = re.compile(r'^[a-zA-Z0-9@.!?#$%^&*()-_+=]+$')
    if acceptable_values.match(text):
        return True
    else:
        return False


def isLogged(najman_token):
    if string_verify(najman_token) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM `tokens` WHERE `token` = %s', (najman_token,))
        result = cursor.fetchone()
        conn.close()
        print(result)
        if result is None:
            return False
        else:
            return True

def send_verify(mail, token):
    link = f'https://82.117.230.91:8000/confirm?token={token}&mail={mail}'
    subjectx = 'Confirm your mail at Gwintoteka right now!'
    bodyx = f'Hi, please confirm your mail by copying below address into your browser:{link}'

    port = 587
    smtp_server = "smtp.gmail.com"
    sender_email = "gwintoteka@gmail.com"
    password = "eiomidjnilylgkgq"
    receiver_email = mail
    subject = 'Website registration'
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



class Mail(BaseModel):
    mail: str


'''
def send_mail(mail):
    smtp_server = 'postfix'
    smtp_port = int(os.getenv('POSTFIX_PORT', 1525))
    from_email = os.getenv('FROM_EMAIL', 'no-reply@gwintoteka.kizumono.cloud')

    subject = 'Potwierdź swojego maila!'
    body = 'TWOJ STARY NAJEBANY ELO ELO 320'

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = mail
    msg.attach(MIMEText(body, 'plain'))
    print(mail)
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.ehlo()
        server.login('no-reply@xxx.cloud', 'xxx123')
        server.sendmail(from_email, mail, msg)
        server.quit()
    except Exception as e:
        print(f"Error: {e}")
'''

@app.post('/test-mail')
def test_mail(user: Mail):
    send_verify(user.mail, "cos")
    return {'message':"W sumie to chuj wie czy to zadziałało"}



class Register(BaseModel):
    username: str
    mail: str
    hash_u: str

class Login(BaseModel):
    mail: str
    hash_u: str

class Change_Pass(BaseModel):
    new_hash: str


'''
@app.post('/test_mail')
async def test_mail(mail: str, token:str):
    await send_verify(mail, token)
    return {'message':"Może poszło"}
'''

@app.post('/register')
async def register(user: Register):
    if string_verify(user.mail) is True and string_verify(user.username) is True and string_verify(user.hash_u) is True:    
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM `users` WHERE `mail` = %s', (user.mail,))
        result = cursor.fetchone()
        if result is None:
            #current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
            #combined_string = f'{user.mail}{user.hash_u}{current_time}'
            #hash_object = hashlib.sha256()
            #hash_object.update(combined_string.encode('utf-8'))
            #mail_token = hash_object.hexdigest()
            cursor.execute('INSERT INTO `users` (`username`, `mail`, `hash`, `role`, `created_at`, `decks`, `reputation`, `comments`) VALUES (%s, %s, %s, "user", CURRENT_TIMESTAMP, NULL, "0", NULL)', (user.username, user.mail, user.hash_u))
            conn.commit()
            conn.close()
            #send_verify(user.mail, mail_token)
            return {'message': "Account registered, please confirm your mail!"}
        else:
            return {'message': "Mail is already in use"}
    else:
        return {'message': "There's problem with your syntax :P"}


@app.post('/login')
async def login(user: Login, response: Response):
    if string_verify(user.mail) is True and string_verify(user.hash_u) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT `hash` FROM `users` WHERE `mail` = %s', (user.mail,))
        result = cursor.fetchone()
        #cursor.execute('SELECT `verified` FROM `users` WHERE `mail = %s', (user.mail,))
        #result2 = cursor.fetchone()
        if result is not None:
            if result[0] == user.hash_u:
                cursor.execute('SELECT `token` FROM `tokens` WHERE `mail` = %s', (user.mail,))
                result = cursor.fetchone()
                if result is None:
                    current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
                    combined_string = f'{user.mail}{user.hash_u}{current_time}'
                    hash_object = hashlib.sha256()
                    hash_object.update(combined_string.encode('utf-8'))
                    najman_hash = hash_object.hexdigest()
                    cursor.execute('INSERT INTO `tokens` (`mail`, `token`) VALUES (%s, %s)', (user.mail, najman_hash))
                    conn.commit()
                    cursor.execute('SELECT `username` FROM `users` WHERE `mail` = %s', (user.mail,))
                    username = cursor.fetchone()
                    conn.close()
                    response.set_cookie(key="najman_token", value=najman_hash, max_age=1800, expires=1800, httponly=True, secure=True)
                    return {'username': username[0], 'mail': user.mail}
                else:
                    cursor.execute('DELETE FROM `tokens` WHERE `token` = %s', (result[0],))
                    conn.commit()
                    current_time = datetime.now().strftime('%Y-%m-%d %H-%M-%S')
                    combined_string = f'{user.mail}{user.hash_u}{current_time}'
                    hash_object = hashlib.sha256()
                    hash_object.update(combined_string.encode('utf-8'))
                    najman_hash = hash_object.hexdigest()
                    cursor.execute('INSERT INTO `tokens` (`mail`, `token`) VALUES (%s, %s)', (user.mail, najman_hash))
                    conn.commit()
                    cursor.execute('SELECT `username` FROM `users` WHERE `mail` = %s', (user.mail,))
                    username = cursor.fetchone()
                    conn.close()

                    response.set_cookie(key="najman_token", value=najman_hash, max_age=1800, expires=1800, httponly=True, secure=True)
                    return {'username': username[0], 'mail': user.mail}
            else:
                conn.close()
                return {'message':"I'm not sure if anyone with this data exists in our base :)1"}
        else:
            conn.close()
            return {'message':"I'm not sure if anyone with this data exists in our base :)2"}
    else:
        return {'message': "There's problem with your syntax :P"}

@app.post('/changepassword')
async def change_pass(user: Change_Pass, response: Response, request: Request):
    najman_token = request.cookies.get('najman_token')
    if najman_token is not None:
        if string_verify(najman_token) is True and string_verify(user.new_hash) is True:
            if isLogged(najman_token) is True:
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
            if isLogged(najman_token) is True:
                conn = connect_db()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM `tokens` WHERE `token` = %s', (najman_token,))
                conn.commit()
                conn.close()
                response.delete_cookie("najman_token")
                return {'message':"User logout success"}
            else:
                return {'message':"Unauthorized"}
        else:
            return {'message': "There's problem with your sytanx :P"}
    else:
        return {'message': "You are not logged in"}

'''
@app.get('/verify')
async def verify(token: str, mail: str):
    if string_verify(token) is True:
        conn = connect_db()
        cursor = conn.cursor()
        cursor.execute('SELECT `mail` FROM `users` WHERE `verify` = %s', (token,))
        result = cursor.fetchone()
        if result[0] == mail:
            cursor.execute('UPDATE `users` SET `verified` = "yes" WHERE `users`.`mail` = %s', (mail,))
            conn.commit()
            conn.close()
            return {'message':"Mail sucesfully confirmed"}
        else:
            return {'message':"Confirmation link is not valid"}
    else:
        return {'message':"There's problem with your syntax :P"}
'''

@app.get('/cards')
def get_cards(
        query_string: str = "",
        page: int = Query(1, ge=1),
        provision: Union[int, None] = None, # Wartosci <1; 14>
        faction: Union[str, None] = None, # Monster, Neutral, Northern Realms, Scoiateal, Nilfgaard, Skellige
        deck_set: Union[str, None] = None, # BaseSet, Unmillable, Thronebreaker, NonOwnable()
        card_type: Union[str, None] = None, # Unit, Special, Artifact, Ability
        color: Union[str, None] = None, # Gold, Bronze, Leader
        rarity: Union[str, None] = None,  # Epic, Rare, Legendary, Common
        cookie: Union[str, None] = Cookie(None)
    ):
    """Pozyskaj za pomocą GET Request wszystkie karty lub ich czesc po zastosowaniu filtrow."""
    print(cookie)
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

    query = "SELECT * FROM cards_with_attributes"
    params = []     # Parametry, ktore podstawimy za %s
    filters = []    # Filtry postawione w query po WHERE

    # 4. Sprawdz, czy sa jakies filtry
    if (not query_string == "") or (provision != None) or (faction != None) or (deck_set != None) or (card_type != None) or (color != None) or (rarity != None):
        # 4.1. Jesli sa, to dodaj klauzure WHERE...
        query += " WHERE "

        # 4.2. ...a nastepnie dodaj do niej zastosowane filtry.
        if not query_string == "":
            filters.append(f"""(name LIKE %s OR category LIKE %s OR ability LIKE %s OR keyword_html LIKE %s)""")
            params += ['%' + query_string + '%'] * 4

        if provision != None:
            filters.append(f"provision=%s")
            params += [provision]

        if faction != None:
            filters.append(f"(faction=%s OR factionSecondary=%s)")
            params += [faction, faction]

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

    return {"response": results}

@app.get('/decks')
def get_decks():
    """ Pozyskaj z bazy danych wszystkie decki nalezace do zalogowanego uzytkownika."""
    user = "najman.robert@wp.pl"
    # 1. Otworz polaczenie do bazy danych
    conn = connect_db()

    # 2. Pozyskaj wszystkie decki konkretnego użytkownika z bazy danych 
    query = f"SELECT * FROM deck WHERE user=%s;"
    params = (user,)

    if conn and conn.is_connected():
      with conn.cursor() as cursor:
        cursor.execute(query, params)
        data = cursor.fetchall()
    
    # 3. Sformatuj dane do JSON.
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

class Deck(BaseModel):
    user: str
    skill: str
    title: str
    faction: str
    recruitment: int
    card_counter: int
    cards: List[str]

@app.post('/decks/send')
def insert_deck(deck: Deck):
    """ Wypelnij tabele danymi w celach testowych."""

    probne_karty = Deck.cards

    # 1. Otworz polaczenie do bazy danych
    conn = connect_db()

    # 2. Wprowadź rekord do deck

    # 2.a) Przygotuj zapytanie do wprowadzenia rekordu do tabeli deck.
    columns_decks = "user, skill, link, title, faction, rating, recruitment, card_counter"
    values_decks = (Deck.user, Deck.skill, None, Deck.title, Deck.faction, 0, Deck.recruitment, Deck.card_counter)
    query_decks = f"INSERT INTO deck ({columns_decks}) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);"

    # 2.b) Przygotuj zapytanie do uzyskania deck_id z nowo wprowadzonego rekordu.
    # Bedzie ono potrzebne do tego, by w deck_cards bylo to samo deck_id.
    deck_id_query = f"SELECT deck_id FROM deck WHERE user=%s ORDER BY deck_id DESC LIMIT 1;"
    deck_id_params = (user,)

    # 2.c) Wykonaj obydwa zapytania
    if conn and conn.is_connected():
      with conn.cursor() as cursor:
        cursor.execute(query_decks, values_decks)
        conn.commit()
        cursor.execute(deck_id_query, deck_id_params)
        deck_id = cursor.fetchone()

    # 3. Wprowadz rekord do deck_cards
    for card in Deck.cards:
        card_query = f"INSERT INTO deck_cards (deck_id, card_name) VALUES (%s, %s);"
        card_values = (deck_id, card)

        if conn and conn.is_connected():
            with conn.cursor() as cursor:
                cursor.execute(card_query, card_values)
                conn.commit()

    conn.close()

@app.get('/decks/{deck_id}')
def get_specific_deck(
    deck_id: int,
    user_mail: Union[str, None] = None
):
    user_mail = "najman.robert@wp.pl"
    # 1. Otworz polaczenie do bazy danych
    conn = connect_db()
    
    if conn and conn.is_connected():
        # raw=True daje output chyba w binarce - nie wiem NIE TYKAC
        # buffered=True zmienia typ kursora. Teraz kursor wyłapie wszystkie
        # dane przed wywolaniem callproc(). Mam nadzieje, ze wydajnosc nie spadnie
        # Wiecej: https://stackoverflow.com/questions/46682012/what-is-a-mysql-buffered-cursor-w-r-t-python-mysql-connector
        cursor = conn.cursor(raw=True, buffered=True)
        cursor.callproc("GetDeckData", args=(deck_id, user_mail,))
        for result in cursor.stored_results():
            # Zostaje zwrocona tupla z jednym itemem - bytearray.
            byte_data = result.fetchone()[0]
            # Tego bytearray trzeba zdeckodowac - frajera pieprzonego.
            decoded_data = byte_data.decode('utf-8')
            # Na koniec konwertujemy do JSON i essa.
            deck_data = json.loads(decoded_data)
        cursor.close()
    
    conn.close()
    return deck_data

@app.delete('/decks/{deck_id}/delete')
def remove_deck(
    deck_id: int,
    user_mail: Union[str, None] = None
):
    """ Usun wszystkie informacje dotyczace decku o podanym deck_id"""
    user_mail = "filip@gmail.com"
    # 1. Otworz polaczenie do bazy danych
    conn = connect_db()
    if conn and conn.is_connected():
        cursor = conn.cursor()
        print(deck_id)
        print(user_mail)

        # 2. Usun deck o podanym deck_id. Spowoduje tez usuniecie wszystkich rekordow
        # w deck_cards o tym samym deck_id.
        query = f"DELETE FROM deck WHERE deck_id=%s AND user=%s;"
        values = (deck_id, user_mail)
        cursor.execute(query, values)
        conn.commit()
        cursor.close()
    conn.close()
    if cursor.rowcount > 0:
        return {"response": "Usunieto deck"}
    else:
        return {"response": "Deck nie zostal usuniety"}

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
