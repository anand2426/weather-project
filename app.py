from flask import Flask, render_template, request, redirect, url_for, flash, session, make_response
from pymongo import MongoClient
import requests
import pandas as pd
import json
from flask import send_file
import os
import time


app = Flask(__name__)
app.secret_key = '1112hewh8283jdjjdwi92392d'

API_KEY = '1aa60b2597eb8a88ae4525f110319f48'

BASE_URL = 'http://api.openweathermap.org/geo/1.0/direct?q={city}&appid={API_KEY}'

def get_weather(city):
    params = {'q': city, 'appid': API_KEY, 'units': 'metric'}
    response = requests.get('http://api.openweathermap.org/data/2.5/weather', params=params)
    
    try:
        data = response.json()
    except json.JSONDecodeError as e:
        print("JSONDecodeError:", e)
        return None
    
    if response.status_code == 200:
        weather_info = {
            'city': data['name'],
            'temperature': data['main']['temp'],
            'description': data['weather'][0]['description']
        }
        return weather_info
    else:
        return None

app.config["MONGO_URI"] = "mongodb://localhost:27017/registration"
client = MongoClient(app.config["MONGO_URI"])
db = client.registration
users_collection = db.users

@app.route("/", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        new_user = {
            "name": name,
            "email": email,
            "password": password
        }

        users_collection.insert_one(new_user)
      
        return redirect(url_for("login"))

    return render_template("reg.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = users_collection.find_one({"email": email,"password": password})
        if not user:
            flash("Invalid email or password. Please try again.")
            return render_template("login.html")

        # Store user information in session
        session['user_email'] = email

        # Redirect to weather page
        return redirect(url_for("weather"))

    return render_template("login.html")

@app.route('/export', methods=['POST'])

def export():
    user_email = session.get('user_email')
    if not user_email:
        # Redirect to login if user is not logged in
        return redirect(url_for("login"))

    user = users_collection.find_one({"email": user_email})
    cities = user.get("cities", []) if user else []

    weather_data = []
    for city in cities:
        # Refresh weather data for each city
        weather_info = get_weather(city)
        if weather_info:
            weather_data.append(weather_info)
            print("weather_data",weather_data)

    df = pd.DataFrame(weather_data)
    timestamp = int(time.time())
    excel_file_path = f"weather_data_{timestamp}.xlsx"  
    df.to_excel(excel_file_path, index=False)
    
    users_collection.update_one({"email": user_email}, {"$set": {"cities": []}})

    return send_file(excel_file_path, as_attachment=True)


@app.route("/logout")
def logout():
    session.pop('user_email', None)
    return redirect(url_for("login"))

@app.route("/weather", methods=["GET", "POST"])
def weather():
    user_email = session.get('user_email')
    if not user_email:
        # Redirect to login if user is not logged in
        return redirect(url_for("login"))

    user = users_collection.find_one({"email": user_email})

    if request.method == "POST":
        city = request.form.get("city")

        weather_info = get_weather(city)

        if weather_info:
            cities = user.get("cities", []) if user else []
            print("Up cities list:", cities)
            cities.append(city)
            print("Updated cities list:", cities)
            users_collection.update_one({"email": user_email}, {"$set": {"cities": cities}})

            return render_template("weather.html", user_email=user_email, user=user, weather_info=weather_info)

        else:
            flash("Error getting weather information.")
            return redirect(url_for("weather"))

    return render_template("weather.html", user_email=user_email, user=user, weather_info=None)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
