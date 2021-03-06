import os
import re
import sys
import uuid

import redis

from cryptography.fernet import Fernet
from flask import abort, Flask, render_template, request, json, Response
from redis.exceptions import ConnectionError
from werkzeug.urls import url_quote_plus
from werkzeug.urls import url_unquote_plus


SNEAKY_USER_AGENTS = ('Slackbot', 'facebookexternalhit', 'Twitterbot',
                      'Facebot', 'WhatsApp', 'SkypeUriPreview', 'Iframely')
SNEAKY_USER_AGENTS_RE = re.compile('|'.join(SNEAKY_USER_AGENTS))
NO_SSL = os.environ.get('NO_SSL', False)
TOKEN_SEPARATOR = '~'


# Initialize Flask Application
app = Flask(__name__)
if os.environ.get('DEBUG'):
    app.debug = True
app.secret_key = os.environ.get('SECRET_KEY', 'Secret Key')

base_path = os.environ.get('BASE_PATH',"")
listen_ip=os.environ.get('LISTEN_IP','127.0.0.1')
time_list_json=os.environ.get('TIME_LIST','[{"id":"4hours","label":"4 hours","ttl":14400},{"id":"1hour","label":"1 hour","ttl":3600},{"id":"2hours","label":"2 hours","ttl":7200},{"id":"8hours","label": "8 hours","ttl":28800},{"id":"1day","label":"1 day","ttl":86400}]')
api_time_list_json=os.environ.get('API_TIME_LIST','[{"id":"1day","label":"1 day","ttl":86400},{"id":"2days","label":"2 days","ttl":172800},{"id":"4days","label":"4 days","ttl":345600},{"id":"8days","label":"8 days","ttl":691200}]')


app.config.update(dict(BASE_PATH=base_path))
app.config.update(dict(TITLE=os.environ.get('TITLE','Share Password')))
app.config.update(dict(COMPANY_NAME=os.environ.get('COMPANY_NAME','Snappass')))
app.config.update(dict(COMPANY_LOGO_URL=os.environ.get('COMPANY_LOGO_URL','')))
app.config.update(dict(STATIC_URL=os.environ.get('STATIC_URL', '/static')))
app.config.update(dict(HELP_URL=os.environ.get('HELP_URL', '')))

# Initialize Redis
if os.environ.get('MOCK_REDIS'):
    from mockredis import mock_strict_redis_client
    redis_client = mock_strict_redis_client()
elif os.environ.get('REDIS_URL'):
    redis_client = redis.StrictRedis.from_url(os.environ.get('REDIS_URL'))
else:
    redis_host = os.environ.get('REDIS_HOST', 'localhost')
    redis_port = os.environ.get('REDIS_PORT', 6379)
    redis_password = os.environ.get('REDIS_PASSWORD', None)
    redis_db = os.environ.get('SNAPPASS_REDIS_DB', 0)

    redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db, password=redis_password)

REDIS_PREFIX = os.environ.get('REDIS_PREFIX', 'snappass')

#TIME_CONVERSION = {'week': 604800, 'day': 86400, 'hour': 3600}


time_list = json.loads(time_list_json)
api_time_list = json.loads(api_time_list_json)

# [ 
# { 'id' : '4hours', 'label': '4 hours', 'ttl':14400},
# { 'id' : '1hour', 'label': '1 hour', 'ttl':3600},
# { 'id' : '2hours', 'label': '2 hours', 'ttl':7200},
# { 'id' : '8hours', 'label': '8 hours', 'ttl':28800},
# { 'id' : '1day', 'label': '1day', 'ttl':86400}
# ]


#TIME_CONVERSION = {'1hour': 3600, '2hours': 7200, '4hours': 14400, '8hours' : 28800, "1day": 86400}

TIME_CONVERSION={}

for time_info in time_list:
    TIME_CONVERSION[time_info['id']]=time_info['ttl']


API_TIME_CONVERSION={}

for time_info in api_time_list:
    API_TIME_CONVERSION[time_info['id']]=time_info['ttl']


def check_redis_alive(fn):
    def inner(*args, **kwargs):
        try:
            if fn.__name__ == 'main':
                redis_client.ping()
            return fn(*args, **kwargs)
        except ConnectionError as e:
            print('Failed to connect to redis! %s' % e.message)
            if fn.__name__ == 'main':
                sys.exit(0)
            else:
                return abort(500)
    return inner


def encrypt(password):
    """
    Take a password string, encrypt it with Fernet symmetric encryption,
    and return the result (bytes), with the decryption key (bytes)
    """
    encryption_key = Fernet.generate_key()
    fernet = Fernet(encryption_key)
    encrypted_password = fernet.encrypt(password.encode('utf-8'))
    return encrypted_password, encryption_key


def decrypt(password, decryption_key):
    """
    Decrypt a password (bytes) using the provided key (bytes),
    and return the plain-text password (bytes).
    """
    fernet = Fernet(decryption_key)
    return fernet.decrypt(password)


def parse_token(token):
    token_fragments = token.split(TOKEN_SEPARATOR, 1)  # Split once, not more.
    storage_key = token_fragments[0]

    try:
        decryption_key = token_fragments[1].decode('hex')
        #decryption_key = token_fragments[1].encode('utf-8')
    except IndexError:
        decryption_key = None

    return storage_key, decryption_key


@check_redis_alive
def set_password(password, ttl):
    """
    Encrypt and store the password for the specified lifetime.

    Returns a token comprised of the key where the encrypted password
    is stored, and the decryption key.
    """
    storage_key = REDIS_PREFIX + uuid.uuid4().hex
    encrypted_password, encryption_key = encrypt(password)
    redis_client.setex(storage_key, ttl, encrypted_password)
    #encryption_key = encryption_key.decode('utf-8')
    encryption_key = encryption_key.encode('hex')
    token = TOKEN_SEPARATOR.join([storage_key, encryption_key])
    return token





@check_redis_alive
def get_password(token):
    """
    From a given token, return the initial password.

    If the token is tilde-separated, we decrypt the password fetched from Redis.
    If not, the password is simply returned as is.
    """
    storage_key, decryption_key = parse_token(token)
    password = redis_client.get(storage_key)
    redis_client.delete(storage_key)

    if password is not None:

        if decryption_key is not None:
            password = decrypt(password, decryption_key)

        return password.decode('utf-8')



@check_redis_alive
def set_shared_url(ttl):
    """
    """
    storage_key = uuid.uuid4().hex
    redis_client.setex(storage_key, ttl, "")
    return storage_key 


@check_redis_alive
def check_shared_url(storage_key,remove=False):
    """
    """
    password = redis_client.get(storage_key)

    if remove:
        redis_client.delete(storage_key)

    if password is not None:
        return True
    return False


def empty(value):
    if not value:
        return True



@app.errorhandler(400)
def bad_request_page(e):
    return render_template('error.html',error_message="You enter an invalid value like an empty password!"), 400

def clean_input():
    """
    Make sure we're not getting bad data from the front end,
    format data to be machine readable
    """
    if empty(request.form.get('password', '')):
        render_template('error.html',error_message="Password does not have to be empty !")
        abort(400)

    if empty(request.form.get('ttl', '')):
        render_template('error.html',error_message="Surprising! Why the TTL is empty?")
        abort(400)

    time_period = request.form['ttl'].lower()
    if time_period not in TIME_CONVERSION:
        render_template('error.html',error_message="Surprising! This TTL does not exit !")
        abort(400)

    return TIME_CONVERSION[time_period], request.form['password']


def request_is_valid(request):
    """
    Ensure the request validates the following:
        - not made by some specific User-Agents (to avoid chat's preview feature issue)
    """
    return not SNEAKY_USER_AGENTS_RE.search(request.headers.get('User-Agent', ''))


@app.route('/'+base_path, methods=['GET'])
def index():
    return render_template('set_password.html', shareme="yes", time_list=time_list)


@app.route('/'+base_path+"sharepass/"+'<storage_key>', methods=['GET'])
def index_share(storage_key):
    if not request_is_valid(request):
        abort(404)

    if check_shared_url(storage_key,False):
        return render_template('set_password.html', shareme="no",time_list=time_list)
    
    return render_template('nokey.html')
    #abort(404)


# @app.route('/'+base_path+"shareme/", methods=['GET'])
# def share_url():
#     return render_template('share_url.html')


@app.route('/'+base_path+"shareme/", methods=['POST'])
def handle_shared_url():
    time_period = request.form['ttl'].lower()
    if time_period not in TIME_CONVERSION:
        abort(400)
    ttl = TIME_CONVERSION[time_period]
    token = set_shared_url(ttl)

    if NO_SSL:
        base_url = request.url_root
    else:
        base_url = request.url_root.replace("http://", "https://")
    link = base_url + base_path + 'sharepass/' + token
    return render_template('confirm_url.html', password_link=link)


@app.route('/'+base_path, methods=['POST'])
def handle_password():
    return store_password()

@app.route('/'+base_path+"sharepass/<id>", methods=['POST'])
def handle_password_share(id):

    if check_shared_url(id,True):
        return store_password()

    return render_template('nokey.html')

@app.route('/'+base_path+"api/setpassword", methods=['POST'])
def handle_password_api():
    json_data = request.get_json(force=True)
    ttl = API_TIME_CONVERSION[json_data["ttl"].lower()]
    password = json_data["password"]
    result_type = json_data["result_type"].lower()
    token = set_password(password, ttl)

    if NO_SSL:
        base_url = request.url_root
    else:
        base_url = request.url_root.replace("http://", "https://")
    link = base_url + base_path + 'key/' + token

    response_json = json.dumps({"status":"success","token":token,"link":link})
    if result_type == "json":
        return Response(response_json,status=200,mimetype="Application/json")
    else:
        return Response(link,status=200,mimetype="text/plain")


@app.route('/'+base_path+"api/getpassword/<result_type>/<password_key>", methods=['GET'])
def show_password_api(result_type,password_key):
    if not request_is_valid(request):
        if result_type == "json":
            return Response('{"status":"error","message":"invalid request"}',status=400,mimetype="Application/json")
        else:
            return Response("invalid request",status=400,mimetype="text/plain")
    password = get_password(password_key)
    if not password:
        if result_type == "json":
            return Response('{"status":"error","message":"key not found"}',status=404,mimetype="Application/json")
        else:
            return Response("key not found",status=404,mimetype="text/plain")

    if result_type == "json":
        return Response('{"status":"success","password":"%s"}' % password,status=200,mimetype="Application/json")
    else:
        return Response(password,status=200,mimetype="text/plain")


def store_password():
    ttl, password = clean_input()
    token = set_password(password, ttl)

    if NO_SSL:
        base_url = request.url_root
    else:
        base_url = request.url_root.replace("http://", "https://")
    link = base_url + base_path + 'key/' + token

    return render_template('confirm.html', password_link=link)


@app.route('/'+base_path+'key/'+'<password_key>', methods=['GET'])
def show_password(password_key):
    if not request_is_valid(request):
        abort(404)
    password = get_password(password_key)
    if not password:
        #abort(404)
        return render_template('nokey.html')

    return render_template('password.html', password=password)


@check_redis_alive
def main():
    app.run(host=listen_ip)


if __name__ == '__main__':
    main()
