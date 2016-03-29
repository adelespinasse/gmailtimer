#!/usr/bin/env python

import os

from apiclient import discovery
from google.appengine.api import users
from google.appengine.ext import ndb
from oauth2client.contrib import appengine
import httplib2
import logging
import webapp2

decorator = appengine.OAuth2DecoratorFromClientSecrets(
  os.path.join(os.path.dirname(__file__), 'client_id.json'),
  ['https://www.googleapis.com/auth/gmail.labels',
   'https://www.googleapis.com/auth/gmail.modify'])

service = discovery.build('gmail', 'v1')


class User(ndb.Model):
    credentials = appengine.CredentialsNDBProperty()

# class LabelTimer(ndb.Model):
#     pass


class MainHandler(webapp2.RequestHandler):
    @decorator.oauth_required
    def get(self):
        self.response.write("""
<!DOCTYPE html>
<html>
<head>
<title>gmailtimer</title>
</head>
<body>

<form method="post" action="/initialize">
    Submit to initialize.
    <input type="submit">
</form>

<br>
<a href="{logoutUrl}">Log Out</a>

</body>
</html>
""".format(logoutUrl=users.create_logout_url('/')))


class InitializeHandler(webapp2.RequestHandler):
    @decorator.oauth_required
    def post(self):
        userEntity = User(id=users.get_current_user().email(), credentials=decorator.get_credentials())
        userEntity.put()
        self.response.write('ok')


class CronHandler(webapp2.RequestHandler):
    def get(self):
        for userEntity in User.query():
            doTimerFor(userEntity)
        self.response.write('ok')


def ListThreadsMatchingQuery(service, http, query):
  """List all Threads of the user's mailbox matching the query.

  Args:
    service: Authorized Gmail API service instance.
    http: Httplib2.Http object, authorized for the user.
    query: String used to filter messages returned.
           Eg.- 'label:UNREAD' for unread messages only.

  Returns:
    List of threads that match the criteria of the query. Note that the returned
    list contains Thread IDs, you must use get with the appropriate
    ID to get the details for a Thread.
  """
  list_params = {'userId': 'me', 'q': query, 'fields': 'nextPageToken,threads/id'}
  response = service.users().threads().list(**list_params).execute(http=http)
  threads = []
  if 'threads' in response:
    threads.extend(response['threads'])

  while 'nextPageToken' in response:
    page_token = response['nextPageToken']
    response = service.users().threads().list(pageToken=page_token, **list_params).execute(http=http)
    threads.extend(response['threads'])

  logging.info('Threads: {}'.format(threads))
  return threads


def doTimerFor(userEntity):
    http = httplib2.Http()
    userEntity.credentials.authorize(http)
    threads = ListThreadsMatchingQuery(service, http, 'label:defer -in:inbox is:unread')
    changes = {'addLabelIds': ['INBOX'], 'removeLabelIds': []}
    batch = service.new_batch_http_request()
    length = 0
    for thread in threads:
        mod = service.users().threads().modify(userId='me', id=thread['id'], body=changes)
        # logging.info('executing...')
        # mod.execute(http=http)
        batch.add(mod)
        length += 1
        if length == 1000:
            logging.info('Sending batch request of length {}'.format(length))
            batch.execute(http=http)
            batch = service.new_batch_http_request()
            length = 0
    if length:
        logging.info('Sending batch request of length {}'.format(length))
        batch.execute(http=http)


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/initialize', InitializeHandler),
    ('/q/cron', CronHandler),
    (decorator.callback_path, decorator.callback_handler()),
], debug=os.environ.get('SERVER_SOFTWARE', '').startswith('Dev'))
# run_wsgi_app(app)
