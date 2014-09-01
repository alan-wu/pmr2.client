import os.path
import traceback
import json
import code
import pdb
import webbrowser

from urllib import quote_plus
from requests_oauthlib.oauth1_session import TokenRequestDenied

try:
    import readline
except ImportError:
    pass

from pmr2.client import Client
from pmr2.client import DemoAuthClient

HOME = os.path.expanduser('~')
CONFIG_FILENAME = os.path.join(HOME, '.pmr2clirc')

PMR2ROOT = 'http://staging.physiomeproject.org'
CONSUMER_KEY = 'ovYoqjlJLrpCcEWcIFyxtqRS'
CONSUMER_SECRET = 'fHssEYMWZzgo6JWUBh4l1bhd'
DEFAULT_SCOPE = quote_plus(
    'http://staging.physiomeproject.org/oauth_scope/collection,'
    'http://staging.physiomeproject.org/oauth_scope/search,'
    'http://staging.physiomeproject.org/oauth_scope/workspace_tempauth,'
    'http://staging.physiomeproject.org/oauth_scope/workspace_full'
)


class Cli(object):

    token_key = ''
    token_secret = ''
    active = False
    state = None
    _debug = 0
    last_response = None

    def __init__(self, 
            site=PMR2ROOT,
            consumer_key=CONSUMER_KEY, 
            consumer_secret=CONSUMER_SECRET,
            scope=DEFAULT_SCOPE,
        ):

        self.auth_client = DemoAuthClient(site, consumer_key, consumer_secret)

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, value):
        if isinstance(value, int):
            self._debug = value

        if isinstance(value, basestring):
            if value.lower() in ('false', 'no', '0',):
                self._debug = 0
            else:
                self._debug = 1

    def build_config(self):
        return  {
            'token_key':
                self.auth_client.session._client.client.resource_owner_key,
            'token_secret':
                self.auth_client.session._client.client.resource_owner_secret,
            'debug': self.debug,
            'scope': DEFAULT_SCOPE,
        }

    def load_config(self, filename=CONFIG_FILENAME):
        try:
            with open(filename, 'r') as fd:
                config = json.load(fd)
        except IOError:
            print("Fail to open configuration file.")
            config = self.build_config()
        except ValueError:
            print("Fail to decode JSON configuration.  Using default values.")
            config = self.build_config()

        token = config.get('token_key', '')
        secret = config.get('token_secret', '')
        self.auth_client.session._client.client.resource_owner_key = token
        self.auth_client.session._client.client.resource_owner_secret = secret
        self.debug = config.get('debug', 0)
        self.scope = config.get('scope', DEFAULT_SCOPE)
        return token and secret

    def save_config(self, filename=CONFIG_FILENAME):
        try:
            with open(filename, 'wb') as fd:
                json.dump(self.build_config(), fd)
        except IOError:
            print("Error saving configuration")

    def get_access(self):
        # get user to generate one.
        try:
            self.auth_client.fetch_request_token(scope=self.scope)
        except Exception as e:
            print('Fail to request temporary credentials.')
            return
        target = self.auth_client.authorization_url()
        webbrowser.open(target)
        verifier = raw_input('Please enter the verifier: ')
        self.auth_client.set_verifier(verifier=verifier)
        token = self.auth_client.fetch_access_token()
        return True

    def do_help(self, arg=''):
        """
        Print this message.
        """

        print('Basic demo commands:')
        print('')
        for name in sorted(dir(self)):
            if not name.startswith('do_'):
                continue
            obj = getattr(self, name)
            if not callable(obj):
                continue
            print(name[3:])
            print(obj.__doc__)

    def do_console(self, arg=''):
        """
        Start the interactive python console.
        """

        console = code.InteractiveConsole(locals=locals())
        result = console.interact('')

    def do_dashboard(self, arg=''):
        """
        List out the features available on the dashboard.
        """

        dashboard = self.client(endpoint='dashboard')
        if not arg:
            for k, v in dashboard.value().items():
                print('%s\t%s\t%s' % (k, v['label'], v['target']))
            return

        self.state = dashboard.get(arg)
        print('Acquired state "%s"; use console to interact.') % arg

    def do_list_workspace(self, arg=''):
        """
        Returns a list of workspaces within your private workspace
        container.
        """

        dashboard = self.client(endpoint='dashboard')
        state = dashboard.get('workspace-home')
        for i in state.value():
            print('"%s"\t%s' % (i['title'], i['target']))

    def do_raw(self, arg=''):
        """
        Open a target URL to receive raw API output.
        """

        a = arg.split(None, 1)
        url = ''.join(a[:1])
        data = ''.join(a[1:])
        if not url:
            print("URL is required.")
            return

        if not data:
            self.state = self.client(url)
        else:
            self.state = self.client(url, data=data)
        print(self.client.last_response.json())

    def do_property(self, arg=''):
        """
        Set property for this object.
        """

        permitted = ['debug']

        a = arg.split()
        if len(a) < 1:
            print("need both key and values.")
            return

        args = list(arg.split())
        prop = args.pop(0)

        if len(a) < 2:
            print('%s = %s') % (prop, getattr(self, prop))
            return

        if prop not in permitted:
            print("'%s' cannot be set") % prop
            return

        setattr(self, prop, ' '.join(args))

    def shell(self):
        while self.active:
            try:
                raw = raw_input('pmr2cli> ')
                if not raw:
                    continue
                rawargs = raw.split(None, 1)
                command = rawargs.pop(0)
                obj = getattr(self, 'do_' + command, None)
                if callable(obj):
                    obj(*rawargs)
                else:
                    print("Invalid command, try 'help'.")
            except EOFError:
                self.active = False
                print('')
            except KeyboardInterrupt:
                print('\nGot interrupt signal.')
                self.active = False
            except ValueError:
                print("Couldn't decode json.")
                # print("Status was %d") % self.last_response.status_code
                print("Use console to check `self.last_response` for details.")
            except:
                print(traceback.format_exc())
                if self.debug:
                    pdb.post_mortem()

    def run(self):
        access = self.load_config()
        if not access:
            try:
                access = self.get_access()
            except TokenRequestDenied as e:
                print('Fail to validate the verifier.')

        if not access:
            self.save_config()
            return

        self.client = Client(PMR2ROOT,
            session=self.auth_client.session, use_default_headers=True)

        try:
            self.client()
        except ValueError as e:
            # JSON decoding error
            print('Credentials are invalid and are purged.  Quitting')
            self.auth_client.session._client.client.resource_owner_key = ''
            self.auth_client.session._client.client.resource_owner_secret = ''
            self.scope = DEFAULT_SCOPE
            self.save_config()
            return

        self.active = True
        print('Starting PMR2 Demo Shell...')
        self.save_config()
        self.shell()


if __name__ == '__main__':
    cli = Cli()
    cli.run()
