from unittest import TestCase
import time
import json

from pmr2.client import Client

_data = {
'http://pmr.example.com/pmr2-dashboard': (
    'http://pmr.example.com/pmr2-dashboard', '''{
    "workspace-home": {
        "target":
            "http://pmr.example.com/pmr2-dashboard/workspace-home",
            "label": "Workspace home"
    },
    "workspace-add": {
        "target": "http://pmr.example.com/pmr2-dashboard/workspace-add",
        "label": "Create workspace in workspace home"
    }
}
''', None),

'http://pmr.example.com/pmr2-dashboard/workspace-add': (
    'http://pmr.example.com/workspace/+/addWorkspace', '''{
    "fields": {
        "storage": {"items": [
            {"content": "Mercurial", "selected": false,
                "id": "json-widgets-storage-1", "value": "mercurial"}
            ],
            "error": null,
            "description":
                "The type of storage backend used for this workspace.",
            "value": []
        },
        "description": {
            "items": null, "error": null, "description": "", "value": ""
        },
        "title": {
            "items": null, "error": null, "description": "", "value": ""
        }
    },
    "actions": {
        "add": {"title": "Add"}
    }
}
''', None),

'http://pmr.example.com/workspace/+/addWorkspace': (
    'http://pmr.example.com/workspace/+/addWorkspace', '''{
    "fields": {
        "storage": {"items": [
            {"content": "Mercurial", "selected": false,
                "id": "json-widgets-storage-1", "value": "mercurial"}
            ],
            "error": null,
            "description":
                "The type of storage backend used for this workspace.",
            "value": []
        },
        "description": {
            "items": null, "error": null, "description": "", "value": ""
        },
        "title": {
            "items": null, "error": null, "description": "", "value": ""
        }
    },
    "actions": {
        "add": {"title": "Add"}
    }
}
''', 'http://pmr.example.com/workspace/123'),

'http://pmr.example.com/workspace/123': (
    'http://pmr.example.com/workspace/123', '''{
    "url": "http://pmr.example.com/workspace/123",
    "owner": "admin",
    "storage": "mercurial",
    "id": "123",
    "description": "test workspace"
}
''', None),

}

class DummyResponse(object):
    def __init__(self, url, raw):
        self.url = url
        self.raw = raw

    def json(self):
        return json.loads(self.raw)


class DummySession(object):

    def __init__(self, data=_data):
        self.history = []
        self.data = data

    def get(self, target, *a, **kw):
        self.history.append(target)
        # actual get_url not appended.
        return DummyResponse(*self.data[target][:2])

    def post(self, target, *a, **kw):
        self.history.append(target)
        get_url, data, post_url = self.data[target]
        self.history.append(post_url)
        return DummyResponse(*self.data[post_url][:2])


class ClientTestCase(TestCase):

    def test_client_dashboard(self):
        session = DummySession()
        client = Client('http://pmr.example.com', session)
        result = client()

        self.assertEqual(result.keys(), ['workspace-home', 'workspace-add'])

    def test_client_state(self):
        session = DummySession()
        client = Client('http://pmr.example.com', session)
        result = client()
        state = result.get('workspace-add')

        self.assertEqual(sorted(state.keys()), [u'actions', u'fields'])

    def test_client_state_post(self):
        session = DummySession()
        client = Client('http://pmr.example.com', session)
        result = client()
        state = result.get('workspace-add')
        next_state = state.post(action='add', fields={'storage': 'mercurial',
            'description': 'test workspace', 'title': 'test'})

        self.assertEqual(next_state.value()['description'], 'test workspace')
        self.assertRaises(TypeError, next_state.post, action='test', fields={})
