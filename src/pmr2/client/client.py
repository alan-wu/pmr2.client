import json

from requests import Session
from requests_oauthlib import OAuth1Session
from oauthlib.common import unicode_type


_PROTOCOL = 'application/vnd.physiome.pmr2.json.0'
_UA = 'pmr2.client/0.0'


def default_headers():
    return {
        'Accept': _PROTOCOL,
        'Content-Type': _PROTOCOL,
        'User-Agent': _UA,
    }


class ClientBase(object):

    endpoints = {}
    site = ''

    def _get_endpoint(self, endpoint):
        return self.endpoints.get(endpoint) % self.site


class DemoAuthClient(ClientBase):

    endpoints = {
        'request': u'%s/OAuthRequestToken',
        'authorize': u'%s/OAuthAuthorizeToken',
        'access': u'%s/OAuthGetAccessToken',
    }

    def __init__(self, site, key, secret, callback='oob'):
        self.site = site
        self.key = key
        self.secret = secret
        self.session = OAuth1Session(
            client_key=self.key,
            client_secret=self.secret,
            callback_uri=callback,
        )

    def fetch_request_token(self, scope=''):
        self.session.fetch_request_token(
            self._get_endpoint('request') + '?scope=' + scope)

    def authorization_url(self):
        return self.session.authorization_url(self._get_endpoint('authorize'))

    def set_verifier(self, verifier):
        self.session._client.client.verifier = unicode_type(verifier)

    def fetch_access_token(self):
        return self.session.fetch_access_token(self._get_endpoint('access'))


class Client(ClientBase):

    site = None
    _auth = None
    lasturl = None

    dashboard = None
    last_response = None

    # just aliases to some default endpoints
    endpoints = {
        'dashboard': '%s/pmr2-dashboard',
        'search': '%s/search',
        'ricordo': '%s/pmr2_ricordo/query',
        # this one is subject to change.
        'mapclient': '%s/map_query',
    }

    def __init__(self,
            site='https://models.physiomeproject.org',
            session=None,
            use_default_headers=False,
        ):
        self.site = site
        if session is None:
            session = Session()
        if use_default_headers:
            session.headers.update(default_headers())
        self.session = session

    def __call__(self, target=None, endpoint='dashboard', data=None):
        if target is None:
            target = self._get_endpoint(endpoint)

        if target is None:
            raise ValueError('unknown target or endpoint specified')

        if data:
            self.last_response = r = self.session.post(target, data=data)
        else:
            self.last_response = r = self.session.get(target)
        return State(self, r)


class State(object):

    def __init__(self, client, response):
        self.client = client
        self.response = response
        self._obj = response.json()

    def get(self, key):
        target = self._obj.get(key, {}).get('target')
        if target:
            return self.client(target=target)

    def post(self, action, fields):
        if not (self.fields() and self.actions()):
            raise TypeError('cannot post here')
        data = {}
        data['actions'] = {action: '1'}
        data['fields'] = fields
        return self.client(self.response.url, data=json.dumps(data))

    def keys(self):
        return self._obj.keys()

    def value(self):
        return self.response.json()

    def actions(self):
        if isinstance(self._obj, dict):
            return self._obj.get('actions', {})
        return {}

    def fields(self):
        if isinstance(self._obj, dict):
            return self._obj.get('fields', {})
        return {}

    def errors(self):
        fields = self.fields()
        errors = []
        for name, field in fields.iteritems():
            error = field.get('error', '')
            if error:
                errors.append((name, error))
        return errors
