import json

from requests import Session
from requests_oauthlib import OAuth1Session


_PROTOCOL = 'application/vnd.physiome.pmr2.json.0'
_UA = 'pmr2.client/0.0'


def default_headers():
    return {
        'Accept': _PROTOCOL,
        'User-Agent': _UA,
        'Content-Type': _UA,
    }


class PMR2OAuth1Session(OAuth1Session):
    """
    This provides some boilerplate to the default one, like setting the
    correct protocol (accept/content-type headers).
    """

    def __init__(self, **kw):
        headers = kw.pop('headers', default_headers())
        super(PMR2OAuth1Session, self).__init__(**kw)
        self.headers.update(headers)


class ClientBase(object):

    endpoints = {}
    site = ''

    def _get_endpoint(self, endpoint):
        return self.endpoints.get(endpoint) % self.site


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
        ):
        self.site = site
        if session is None:
            session = Session()
            session.headers.update(default_headers())
        self.session = session

    def __call__(self, target=None, endpoint='dashboard'):
        if target is None:
            target = self._get_endpoint(endpoint)

        if target is None:
            raise ValueError('unknown target or endpoint specified')

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
        r = self.client.session.post(self.response.url, data=json.dumps(data))
        return State(self.client, r)

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
