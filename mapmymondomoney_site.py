import cherrypy
import json
import urllib
import uuid
import requests

import secret

class Site:

    @cherrypy.expose
    def index(self):
      if 'state_code' in cherrypy.session:
        raise cherrypy.HTTPRedirect("/map.html")
      else:
        raise cherrypy.HTTPRedirect("/login.html")

    @cherrypy.expose
    def login_redirect(self):
      cherrypy.session['state_code'] = uuid.uuid1().hex;      
      args = urllib.urlencode({
        'client_id' : secret.mondo_client_id,
        'redirect_uri' : "http://www.mapmymondomoney.site/login_complete",
        'response_type' : 'code',
        'state': cherrypy.session['state_code']
      })
      url = "https://auth.getmondo.co.uk/?" + args
      raise cherrypy.HTTPRedirect(url)

    @cherrypy.expose
    def login_complete(self, code, state):
      if state != cherrypy.session['state_code']:
        raise cherrypy.HTTPRedirect('/logout')
      else:
        args = {
          'grant_type' : 'authorization_code',
          'client_id' : secret.mondo_client_id,
          'client_secret' : secret.mondo_client_secret,
          'redirect_uri' : "http://www.mapmymondomoney.site/login_complete",
          'code' : code
        }
        res = requests.post("https://api.getmondo.co.uk/oauth2/token", data=args)
        if res.status_code != 200:
          raise cherrypy.HTTPRedirect('/logout')

        cherrypy.session['access_token'] = res.json()['token_type'] + " " + res.json()['access_token']

        hdrs = { "Authorization": cherrypy.session['access_token'] }
        res = requests.get("https://api.getmondo.co.uk/accounts", headers=hdrs)
        if res.status_code != 200:
          raise cherrypy.HTTPRedirect('/logout')

        cherrypy.session['account_id'] = res.json()['accounts'][0]['id']

        raise cherrypy.HTTPRedirect('/map.html')

    @cherrypy.expose
    def logout(self):
      cherrypy.lib.sessions.expire()
      raise cherrypy.HTTPRedirect('/')

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_transactions(self):
      if 'access_token' in cherrypy.session:
        hdrs = { 'Authorization': cherrypy.session['access_token'] }
        res = requests.get("https://api.getmondo.co.uk/transactions?expand[]=merchant&account_id="+cherrypy.session['account_id'], headers=hdrs)
        if res.status_code == 200:
          merchants = {}
          for t in res.json()['transactions']:
            if t['is_load'] == False:
              id = t['merchant']['id']
              rec = {
                'name' : t['merchant']['name'],
                'amount' : -int(t['amount']),
                'lat': t['merchant']['address']['latitude'],
                'lng': t['merchant']['address']['longitude'],
                'time': t['settled']
              }
              if id in merchants:
                rec['amount'] = rec['amount'] + merchants[id]['amount']
              merchants[id] = rec
          out = []
          for m in merchants:
            out.append( merchants[m] )
          return out
        else:
          raise cherrypy.HTTPRedirect("/login.html")
      else:
        raise cherrypy.HTTPRedirect("/login.html")


