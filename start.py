from flask import Flask, render_template, request
import pickle
import pandas as pd
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import os
import sqlite3

import ssl
ssl._create_default_https_context = ssl._create_unverified_context


app = Flask(__name__)


#координаты центра екатеринбурга
c = (56.83725377741802, 60.597350913273274)


#координаты метро
square_1905 = (56.8362716853893, 60.59968979953426)
dinamo = (56.84782181862475, 60.59947472070306)
uralskaya = (56.857638533270126, 60.60010772203058)
mash = (56.87755339342598, 60.6116150117623)
uralmash = (56.88860434388676, 60.61365789683971)
kosmos = (56.901832944294, 60.613943098293326)
geolog = (56.827545099355305, 60.60260559413865)
chkalov = (56.80774218566658, 60.61050189281998)
botan = (56.79736609518068, 60.63237728844232)
metro_list = (square_1905, dinamo, uralskaya, mash, uralmash, kosmos, geolog, chkalov, botan)


def get_area_list(param, db):
    con = sqlite3.connect(os.path.join(os.getcwd(), 'static/apartments.db'))
    df = pd.read_sql_query(
    "SELECT DISTINCT {} FROM {}".format(param, db), con
    )
    con.close()
    return list(df[param].unique())


def get_distance(address):
    address = "россия екатеринбург " + address
    geolocator = Nominatim(user_agent="housing", timeout=20)
    location = geolocator.geocode(address)
    while hasattr(location, 'latitude') is False:
        address = address[:address.rfind(' ')]
        location = geolocator.geocode(address)
    distance_centre = round(geodesic(c, (location.latitude,location.longitude)).kilometers, 1)
    l = []
    for i in metro_list:
        l.append(round(geodesic(i, (location.latitude, location.longitude)).kilometers, 1))
    distance_metro = min(l)
    area = location.address[location.address[:location.address.find(' район')].rfind(' ')+1:location.address.find(' район')]
    return (distance_centre, distance_metro, area, (location.latitude, location.longitude))


def get_valid_address(coord):
    con = sqlite3.connect(os.path.join(os.getcwd(), 'static/apartments.db'))
    df_valid_address = pd.read_sql_query(
        "select address, latitude, longitude from coords", con
    )
    df_valid_address['distance'] = 0
    for i in range(len(df_valid_address)):
        df_valid_address['distance'][i] = round(geodesic(coord, (float(df_valid_address.latitude[i]), float(df_valid_address.longitude[i]))).kilometers, 1)
    exception_list = tuple(df_valid_address.query("distance <= 0.5")['address'].unique())
    df_analogue = pd.read_sql_query(
        '''
        select address, material, hight, square, kv, price from 
        (select * from total where address in {})
        where hight <= {} and square >= {} and 
        square <= {} and material = '{}'
        
        '''.format(exception_list, int(request.form.get("hight"))+5, int(request.form.get('square'))*0.8,
                   int(request.form.get('square'))*1.2, request.form.get("material")), con
    )
    con.close()
    return df_analogue



features = [['floor', 'square', 'hight', 'first', 'last', 'kv', 'distance_centre',
       'distance_metro', 'material_Бетонные блоки', 'material_Кирпич',
       'material_Монолит', 'material_Панель', 'material_Сборный железобетон',
       'newbuilding_Вторичка', 'rooms_1-к', 'rooms_2-к', 'rooms_3-к',
       'rooms_4-к', 'rooms_5-к', 'area_Академический', 'area_Верх-Исетский',
       'area_Железнодорожный', 'area_Кировский', 'area_Ленинский', 'area_Октябрьский', 'area_Орджоникидзевский',
       'area_Чкаловский'], ['floor', 'square', 'hight', 'first', 'last', 'kv', 'distance_centre',
       'distance_metro', 'material_Бетонные блоки', 'material_Кирпич',
       'material_Монолит', 'material_Панель', 'material_Сборный железобетон',
       'newbuilding_Новостройка', 'rooms_1-к', 'rooms_2-к', 'rooms_3-к',
       'rooms_4-к', 'rooms_5-к', 'area_Академический', 'area_Верх-Исетский',
       'area_Железнодорожный', 'area_Кировский', 'area_Ленинский',
       'area_Октябрьский', 'area_Орджоникидзевский',
       'area_Чкаловский']]


AREA = get_area_list('area', 'coords')
MATERIAL = get_area_list('material', 'total')
NEWBUILD = ['Новостройка', 'Вторичка']
ROOMS = get_area_list('rooms', 'total')




@app.route("/")
def index():
    return render_template("index.html", areas=AREA, materials=MATERIAL,
                           newbuilds=NEWBUILD,
                           rooms=ROOMS,
                           )


@app.route("/start", methods=['POST'])
def start():
    d = {}
    address = request.form.get('address')
    l = get_distance(address)
    d = {}
    if request.form.get('newbuilding') == 'Новостройка':
        list_features = features[1]
        path = os.path.join(os.getcwd(), 'static/dtr_first.pickle')
        with open(path, 'rb') as f:
            dtr = pickle.load(f)
    else:
        list_features = features[0]
        path = os.path.join(os.getcwd(), 'static/gbr_second.pickle')
        with open(path, 'rb') as f:
            dtr = pickle.load(f)
    for i in list_features:
        d[i] = 0

    d['square'] = int(request.form.get('square'))
    d['floor'] = int(request.form.get('floor'))
    d['material_'+request.form.get("material")] = 1
    d['rooms_'+request.form.get("rooms")] = 1
    d['hight'] = int(request.form.get("hight"))
    d['area_'+l[2]] = 1
    d['distance_metro'] = l[1]
    d['distance_centre'] = l[0]
    first = int(request.form.get('floor'))
    last = int(request.form.get('floor'))/int(request.form.get('hight'))
    if first == 1:
        d['first'] = 1
    elif last == 1:
        d['last'] = 1



    data = get_valid_address(l[3])
    model_price = int(dtr.predict(pd.DataFrame(d, index=[0]).drop(columns=['kv']))) * int(request.form.get('square'))
    mean_price = int(data.kv.sum()/len(data) * int(request.form.get('square')))



    con = sqlite3.connect(os.path.join(os.getcwd(), 'static/apartments.db'))
    cur = con.cursor()
    

    data1 = cur.execute('''
     select rooms, count(kv) from 
     (select * from total t left 
     join coords c on t.address == c.address
     where area = '{}' and newbuilding = '{}')
     group by rooms
     '''.format(l[2], request.form.get("newbuilding"))).fetchall()
    labels = [row[0] for row in data1]
    values = [row[1] for row in data1]


    data2 = cur.execute('''
     select rooms, avg(price) from 
     (select * from total t left 
     join coords c on t.address == c.address
     where area = '{}' and newbuilding = '{}')
     group by rooms
     '''.format(l[2], request.form.get("newbuilding"))).fetchall()
    labels2 = [row[0] for row in data2]
    values2 = [row[1] for row in data2]


    data3 = list(cur.execute('''
      select distinct square, kv from 
      (select * from total t left 
      join coords c on t.address == c.address
      where area = '{}' and newbuilding = '{}')
      '''.format(l[2], request.form.get("newbuilding"))).fetchall())
    labels3 = [row[0] for row in data3]
    values3 = [row[1] for row in data3]
    nelist = []
    for i, j in zip(labels3, values3):
        nelist.append({'x':i, 'y':j})
    nelist = str(nelist).replace('\'', '')


    data4 = cur.execute('''
     select rooms, avg(kv) from 
     (select * from total t left 
     join coords c on t.address == c.address
     where area = '{}' and newbuilding = '{}')
     group by rooms
     '''.format(l[2], request.form.get("newbuilding"))).fetchall()
    labels4 = [row[0] for row in data4]
    values4 = [row[1] for row in data4]

    con.close()


    return render_template('table.html', headers=("Адрес", "Материал", "К-во этажей", "Площадь", "Стоимость 1 кв м", "Стоимость квартиры"), data=data.values.tolist(), model_price=model_price,
                           mean_price=mean_price, labels=labels, values=values, labels2=labels2, values2=values2, nelist=nelist, labels4=labels4, values4=values4)






if __name__ == '__main__':
    app.run()


