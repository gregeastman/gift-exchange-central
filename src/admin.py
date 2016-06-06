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

import datamodel

import jinja2
import webapp2
import json
from datamodel import get_gift_exchange_key

_JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

_DEFAULT_GIFT_EXCHANGE_NAME = datamodel._DEFAULT_GIFT_EXCHANGE_NAME
_DEFAULT_DISPLAY_NAME = '<ENTER A NAME>'

class HomeHandler(webapp2.RequestHandler):
    """Handles the requests to the admin home page"""
    def get(self):
        """Handles get requests to the admin home page - listing all available events"""
        google_user = users.get_current_user()
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        datamodel.GiftExchangeUser.update_and_retrieve_user(gift_exchange_key, google_user)
        query = datamodel.GiftExchangeEvent.query(ancestor=gift_exchange_key)
        event_list = query.fetch(100) #maybe filter out the  events that have ended
        template_values = {
                'event_list': event_list,
                'page_title': 'Administrative Dashboard',
                'is_admin_user': users.is_current_user_admin(),
                'logout_url': users.create_logout_url(self.request.uri)
            }
        template = _JINJA_ENVIRONMENT.get_template('admin.html')
        self.response.write(template.render(template_values))

class EventHandler(webapp2.RequestHandler):
    """Handles requests for updating a particular event, including the participants"""
    def get(self):
        """Handles get requests to the page that shows an administrative view of an event"""
        event = None
        event_string = self.request.get('event')
        if event_string:
            #consider trapping error - also consider other places doing ndb.Key
            event_key = ndb.Key(urlsafe=event_string)
            event = event_key.get()
        event_display_name = _DEFAULT_DISPLAY_NAME
        money_limit = ''
        participant_list = []
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        query = datamodel.GiftExchangeUser.query(ancestor=gift_exchange_key)
        user_list = query.fetch(200)
        has_started = False
        has_ended = False
        if event is not None:
            event_display_name = event.display_name
            money_limit = event.money_limit
            has_started = event.has_started
            has_ended = event.has_ended
            query = datamodel.GiftExchangeParticipant.query(datamodel.GiftExchangeParticipant.event_key==event.key, ancestor=gift_exchange_key)
            participant_list = query.fetch(100)
        template_values = {
                'event_string': event_string,
                'event_display_name': event_display_name,
                'has_started': has_started,
                'has_ended': has_ended,
                'money_limit': money_limit,
                'participant_list': participant_list,
                'user_list': user_list,
                'page_title': 'Edit an event',
                'is_admin_user': users.is_current_user_admin(),
                'logout_url': users.create_logout_url(self.request.uri)
            }
        template = _JINJA_ENVIRONMENT.get_template('event.html')
        self.response.write(template.render(template_values))
        
    def post(self):
        """Handles updating a particular event, including the users. Expects a JSON object."""
        data = json.loads(self.request.body)
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        message = 'Event Updated Successfully'
        event = None
        needs_saving = False
        event_string = data['event']
        event_display_name = data['event_display_name']
        money_limit = data['money_limit']
        if ((event_display_name is None) or (event_display_name == '') or (event_display_name == _DEFAULT_DISPLAY_NAME)):
            message = 'You must select a valid display name'
        else:
            if event_string:
                event_key = ndb.Key(urlsafe=event_string)
                event = event_key.get()
            if event is None:
                event = datamodel.GiftExchangeEvent(parent=gift_exchange_key)
                needs_saving = True
            if event.display_name != event_display_name:
                event.display_name = event_display_name
                needs_saving = True
            if money_limit:
                if event.money_limit != money_limit:
                    event.money_limit = money_limit
                    needs_saving = True
            if needs_saving:
                event.put()
                event_string = event.key.urlsafe()
                event_key = event.key
            if not event.has_started: #maybe should return a message, but UI handles it
                error_message = EventHandler._save_participants(gift_exchange_key, event_key, data['participant_list'])
                if error_message:
                    message = error_message
        self.response.out.write(json.dumps(({'message': message, 'event_string': event_string})))
    
    @staticmethod
    def _save_participants(gift_exchange_key, event_key, participant_list):
        """Helper method for saving the participants in a particular event, including pruning users"""
        message = None
        #There's likely a better way to check for duplicates, but this shouldn't happen
        name_index = {}
        for participant_object in participant_list:
            temp_name = participant_object['display_name']
            if temp_name in name_index:
                return 'Duplicate name found: ' + temp_name
            name_index[participant_object['display_name']] = (participant_object['email'], participant_object['family'])
        for participant_object in participant_list:
            needs_saving = False
            display_name = participant_object['display_name']
            participant = datamodel.GiftExchangeParticipant.get_participant_by_name(gift_exchange_key, display_name, event_key)
            if participant is None:
                participant = datamodel.GiftExchangeParticipant.create_participant_by_name(gift_exchange_key, display_name, event_key)
                needs_saving = True
            user = datamodel.GiftExchangeUser.get_user_by_email(gift_exchange_key, participant_object['email'])
            if participant.user_key != user.key:
                participant.user_key = user.key
                needs_saving = True
            family = participant_object['family']
            if participant.family != family:
                participant.family = family
                needs_saving = True
            if needs_saving:
                participant.put()
        EventHandler._prune_participants(gift_exchange_key, event_key, name_index)
        return message
    
    @staticmethod
    def _prune_participants(gift_exchange_key, event_key, name_index):
        """Deletes any participants from a given event that aren't in the name_index"""
        query = datamodel.GiftExchangeParticipant.query(datamodel.GiftExchangeParticipant.event_key==event_key, ancestor=gift_exchange_key)
        participant_list = query.fetch(100)
        for participant in participant_list:
            if participant.display_name in name_index:
                if ((participant.get_user().email != name_index[participant.display_name][0]) 
                        or (participant.family != name_index[participant.display_name][1])):
                    participant.key.delete()
            else:
                participant.key.delete()
        return

class DeleteHandler(webapp2.RequestHandler):
    """Handles requests for deleting an event, including all participants associated with the event"""
    def post(self):
        """Takes a JSON request and deletes the event and all users associated with it."""
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        data = json.loads(self.request.body)
        event_string = data['event']
        if event_string:
            event_key = ndb.Key(urlsafe=event_string)
            event = event_key.get()
        if event is not None:
            query = datamodel.GiftExchangeParticipant.query(datamodel.GiftExchangeParticipant.event_key==event.key, ancestor=gift_exchange_key)
            participant_list = query.fetch(100)
            for participant in participant_list:
                participant.key.delete()
            event.key.delete()
        self.response.out.write(json.dumps(({'message': 'Successfully deleted.'})))
    
    
    
class ReportHandler(webapp2.RequestHandler):
    """Handles showing a report for all the data about a particular event."""
    def get(self):
        """Displays a report about a particular event."""
        event = None
        event_string = self.request.get('event')
        if event_string:
            event_key = ndb.Key(urlsafe=event_string)
            event = event_key.get()
        if event is None:
            self.redirect('/admin/')
        else:
            gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
            query = datamodel.GiftExchangeParticipant.query(datamodel.GiftExchangeParticipant.event_key==event.key, ancestor=gift_exchange_key)
            participant_list = query.fetch(100)
            template_values = {
                'event': event,
                'participant_list': participant_list,
                'page_title': 'Event Report',
                'is_admin_user': users.is_current_user_admin(),
                'logout_url': users.create_logout_url(self.request.uri)
            }
            template = _JINJA_ENVIRONMENT.get_template('report.html')
            self.response.write(template.render(template_values))
        return

class StatusChangeHandler(webapp2.RequestHandler):
    """Handler for changing for starting or stopping an event"""
    def post(self):
        """Post handler for starting or stopping an event. Expects a JSON object"""
        data = json.loads(self.request.body)
        event_string = data['event']
        status_change_type = data['status_change_type']
        if event_string:
            event_key = ndb.Key(urlsafe=event_string)
            event = event_key.get()
        if event:
            if status_change_type == 'start':
                StatusChangeHandler._assign_users(get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME), event_key)
                event.has_started = True
                event.put()
            if status_change_type == 'stop':
                event.has_ended = True
                event.put()
        self.response.out.write(json.dumps(({'message': 'Event successfully updated', 'event_string': event_string})))
        
    @staticmethod
    def _assign_users(gift_exchange_key, event_key):
        """Helper method for assigning targets to all users in a given event."""
        query = datamodel.GiftExchangeParticipant.query(datamodel.GiftExchangeParticipant.event_key==event_key, ancestor=gift_exchange_key)
        participant_list = query.fetch(100)
        index = 0
        for participant in participant_list:
            if index == 0:
                participant.target = participant_list[len(participant_list)-1].display_name
            else:
                participant.target = participant_list[index - 1].display_name
            participant.put()
            index = index + 1
        #TODO: implement
        return
        
app = webapp2.WSGIApplication([
    ('/admin/', HomeHandler),
    ('/admin/event', EventHandler),
    ('/admin/statuschange', StatusChangeHandler),
    ('/admin/delete', DeleteHandler),
    ('/admin/report', ReportHandler)
], debug=True)
