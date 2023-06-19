from flask import Flask, render_template, jsonify, session, request, redirect, url_for
from configparser import ConfigParser
from flask_talisman import Talisman
from flask_session import Session
from flask_cors import CORS
import qrcode
import requests
import json


app = Flask(__name__)

CORS(app)

talisman = Talisman(app, content_security_policy={
    'default-src': ["'self'", "*", "'unsafe-inline'"]
})

app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_THRESHOLD'] = 500  # Set a threshold for the number of files before cleanup
Session(app)

config = ConfigParser()
config.read('config.ini')
app.secret_key = config.get('DEFAULT', 'SECRET_KEY', )
connection_url = config.get('ENDPOINTS', 'CONNECTION_URL').strip("'")
verifier_url = config.get('ENDPOINTS', 'VERIFIER_URL').strip("'")
cred_def = config.get('CREDENTIAL_DEFINITION', 'CREDENTIAL_DEFINITION').strip("'")
attr1 = config.get('ATTRIBUTES', 'ATTR1').strip("'")
attr2 = config.get('ATTRIBUTES', 'ATTR2').strip("'")

@app.route('/de')
def set_language_de():
    session['lang'] = 'de'
    return redirect(url_for('index'))

@app.route('/fr')
def set_language_fr():
    session['lang'] = 'fr'
    return redirect(url_for('index'))


@app.route('/')
def index():
    if 'lang' not in session:
        session['lang'] = 'de'

    url = connection_url+ '/connection/invitation'
    response = requests.post(url)
    data = json.loads(response.text)
    dynamic_url = data['invitationUrl']
    session['connection'] = data['connectionId']
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=6, border=4)
    qr.add_data(dynamic_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save("static/images/dynamic_url_qr.png")  # Save the QR code image to a file

        # Set the prompt based on the language
    if session['lang'] == 'de':
        prompt = 'Scannen Sie diesen QR-Code mit ihrer elektronischen Brieftasche (Lissie Wallet) und folgen Sie den weiteren Schritten in der App'
        
    elif session['lang'] == 'fr':
        prompt = 'Veuillez scanner le QR code avec votre application de portefeuille'
        

    return render_template('index.html', qr_image='static/images/dynamic_url_qr.png', prompt=prompt)

@app.route('/check_connection/')
def check_connection():
    # Check the connection status by making a GET request to the API endpoint
    url = connection_url+  '/connection/' + session['connection'] 
    response = requests.get(url)
    if response.text == '"established"':
        # Connection has been established
        return jsonify({'status': 'connected'})
    else:
        # Connection has not been established
        return jsonify({'status': 'not connected'})

@app.route('/verify')      
def name():
    url = verifier_url + '/verify/process'
    data = {
        "credentialDefinitionId": cred_def,
        "attributes": [
            attr1,
            attr2
        ],
        "connectionId": session['connection']
    }
    print(data)
    headers = {"Content-Type": "application/json"}
    response = requests.post(
        url,
        json=data,
        headers=headers)
    
    print(response.text)

    if response.status_code == 200:
        data = json.loads(response.text)
        session['processId'] = data['processId']

        if session['lang'] == 'de':
            prompt = 'Bitte beantworten Sie die Informationsanfrage in ihrer elektronischen Brieftasche (Lissi Wallet)'
            
        elif session['lang'] == 'fr':
            prompt = 'Veuillez répondre à la demande d\'informations dans votre portefeuille électronique (Lissi Wallet)'  
            

        return render_template('loading.html', prompt=prompt)
    else:
        return render_template('failure.html')    



@app.route('/loading/')
def loading():
    # Check the Acception status by making a GET request to the API endpoint
    url = verifier_url+ '/verify/process/' + session['processId'] + '/state'
    response = requests.get(url)
    if response.text != '"IN_PROGRESS"':
        # Credential has been accepted
        return jsonify({'status': 'accepted'})
    else:
        # Credential has not been accepted
        return jsonify({'status': 'not accepted'})

@app.route('/success')
def success():
    if session['lang'] == 'de':
        prompt = 'Ihre Anmeldung wurde erfolgreich verifiziert. Herzlich Willkommen!'
    elif session['lang'] == 'fr':
        prompt = 'Votre inscription a été vérifiée avec succès. Bienvenue!'
    return render_template('success.html', prompt=prompt)        
  

if __name__ == "__main__":
    app.run(debug=True)    