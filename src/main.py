#!/usr/bin/env python
#
# Copyright 2016 Greg Eastman
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os

from google.appengine.api import users
from google.appengine.ext import ndb
#from google.appengine.api import mail

import datamodel

import jinja2
import webapp2
import json

_JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

_DEFAULT_GIFT_EXCHANGE_NAME = datamodel._DEFAULT_GIFT_EXCHANGE_NAME


def is_key_valid_for_user(participant_string):
    participant_key = ndb.Key(urlsafe=participant_string)
    gift_exchange_participant = participant_key.get()
    if gift_exchange_participant is None:
        return (False, None)
    elif gift_exchange_participant.is_valid_for_google_id(users.get_current_user().user_id()) == False:
        return (False, None)
    else:
        return (True, gift_exchange_participant)
    return (False, None)

class LoginHandler(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.redirect('/home')
        else:
            template_values = {
                    'page_title': 'Secret Santa Login',
                    'login_url': users.create_login_url(self.request.uri)
                }
            template = _JINJA_ENVIRONMENT.get_template('login.html')
            self.response.write(template.render(template_values))

class HomeHandler(webapp2.RequestHandler):
    def get(self):
        google_user = users.get_current_user()
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        user = datamodel.GiftExchangeUser.update_and_retrieve_user(gift_exchange_key, google_user)
        all_participants = []
        if user is not None:
            query = datamodel.GiftExchangeParticipant.query(datamodel.GiftExchangeParticipant.user_key==user.key, ancestor=gift_exchange_key)
            all_participants = query.fetch(100)
        participant_list = []
        for participant in all_participants:
            event = participant.get_event()
            if event.is_active:
                participant_list.append(participant)
        if len(participant_list)==1:
            participant = participant_list[0]
            self.redirect('/main?gift_exchange_participant=' + participant.key.urlsafe())
        else:
            template_values = {
                    'participant_list': participant_list,
                    'page_title': 'Secret Santa Homepage',
                    'is_admin_user': users.is_current_user_admin(),
                    'logout_url': users.create_logout_url(self.request.uri)
                }
            template = _JINJA_ENVIRONMENT.get_template('home.html')
            self.response.write(template.render(template_values))
        return

class MainHandler(webapp2.RequestHandler):
    def get(self):
        ret = is_key_valid_for_user(self.request.get('gift_exchange_participant'))
        if ret[0]:
            gift_exchange_participant = ret[1]
            gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
            target_participant = datamodel.GiftExchangeParticipant.get_participant_by_name(
                                                                                gift_exchange_key, 
                                                                                gift_exchange_participant.target,
                                                                                gift_exchange_participant.event_key)
            template_values = {
                    'page_title': gift_exchange_participant.get_event().display_name + ' Homepage',
                    'gift_exchange_participant': gift_exchange_participant,
                    'targe_participant': target_participant,
                    'money_limit': gift_exchange_participant.get_event().money_limit,
                    'is_admin_user': users.is_current_user_admin(),
                    'logout_url': users.create_logout_url(self.request.uri)
                }
            template = _JINJA_ENVIRONMENT.get_template('main.html')
            self.response.write(template.render(template_values))
            return
        self.redirect('/home')

class UpdateHandler(webapp2.RequestHandler):
    def post(self):
        ret = is_key_valid_for_user(self.request.get('gift_exchange_participant'))
        if ret[0]:
            gift_exchange_participant = ret[1]
            url_params = ''
            if gift_exchange_participant is not None:
                ideas = self.request.get('ideas')
                #emailSubject = self.request.get('emailSubject')
                gift_exchange_participant.ideas = ideas
                gift_exchange_participant.put()
                url_params = '?gift_exchange_participant=' + gift_exchange_participant.key.urlsafe()
                #TODO: send update email
            self.redirect('/main' + url_params)
            return
        self.redirect('/home')
        

class AssignmentHandler(webapp2.RequestHandler):
    def post(self):
        ret = is_key_valid_for_user(self.request.get('gift_exchange_participant'))
        if ret[0]:
            gift_exchange_participant = ret[1]
            url_params = ''
            if gift_exchange_participant is not None:
                gift_exchange_participant.is_target_known = True
                gift_exchange_participant.put()
                url_params = '?gift_exchange_participant=' + gift_exchange_participant.key.urlsafe()
            self.redirect('/main' + url_params)
            return
        self.redirect('/home')

class PreferencesHandler(webapp2.RequestHandler):
    def get(self):
        google_user = users.get_current_user()
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        user = datamodel.GiftExchangeUser.get_user_by_google_id(gift_exchange_key, google_user.user_id())
        template_values = {
                           'page_title': 'User Preferences',
                           'user': user,
                           'is_admin_user': users.is_current_user_admin(),
                           'logout_url': users.create_logout_url(self.request.uri)
                        }
        template = _JINJA_ENVIRONMENT.get_template('preferences.html')
        self.response.write(template.render(template_values))
    
    def post(self):
        data = json.loads(self.request.body)
        subscribed_string = data['subscribed_string']
        subscribed_to_updates = True
        if subscribed_string == 'no':
            subscribed_to_updates = False
        google_user = users.get_current_user()
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        user = datamodel.GiftExchangeUser.get_user_by_google_id(gift_exchange_key, google_user.user_id())
        if user is None:
            user = datamodel.GiftExchangeUser.update_and_retrieve_user(gift_exchange_key, google_user)
        if user.subscribed_to_updates != subscribed_to_updates:
            user.subscribed_to_updates = subscribed_to_updates
            user.put()
        self.response.out.write(json.dumps(({'message': 'Preferences Updated Successfully'})))

class MessageHandler(webapp2.RequestHandler):
    def get(self):
        ret = is_key_valid_for_user(self.request.get('gift_exchange_participant'))
        if ret[0]:
            gift_exchange_participant = ret[1]
            gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
            target_participant = datamodel.GiftExchangeParticipant.get_participant_by_name(
                                                                                gift_exchange_key, 
                                                                                gift_exchange_participant.target,
                                                                                gift_exchange_participant.event_key)
            target_has_email = False
            if target_participant.email:
                target_has_email = True
            template_values = {
                               'target_participant': target_participant,
                               'target_has_email': target_has_email,
                               'page_title': 'Send A Message',
                               'is_admin_user': users.is_current_user_admin(),
                               'logout_url': users.create_logout_url(self.request.uri)
                            }
            template = _JINJA_ENVIRONMENT.get_template('message.html')
            self.response.write(template.render(template_values))
            return
        self.redirect('/home')
    
    def post(self):
        #TODO: implement
        self.redirect('/home')

app = webapp2.WSGIApplication([
    ('/', LoginHandler),
    ('/login', LoginHandler),
    ('/main', MainHandler),
    ('/home', HomeHandler),
    ('/preferences', PreferencesHandler),
    ('/message', MessageHandler),
    ('/update', UpdateHandler),
    ('/assign', AssignmentHandler)
], debug=True)