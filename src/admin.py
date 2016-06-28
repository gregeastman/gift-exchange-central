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
import random

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
        event_list = query.fetch(200) #maybe filter out the  events that have ended
        not_started_events = []
        in_progress_events = []
        ended_events = []
        for event in event_list:
            if event.has_ended:
                ended_events.append(event)
            elif event.has_started:
                in_progress_events.append(event)
            else:
                not_started_events.append(event)  
        template_values = {
                'not_started_events': not_started_events,
                'in_progress_events': in_progress_events,
                'ended_events': ended_events,
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
            try:
                event_key = ndb.Key(urlsafe=event_string)
                event = event_key.get()
            except:
                pass
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
                try:
                    event_key = ndb.Key(urlsafe=event_string)
                    event = event_key.get()
                except:
                    pass
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
        self.response.out.write(json.dumps(({'message': message, 'event_string': event_string, 'money_limit': event.money_limit})))
    
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
            try:
                event_key = ndb.Key(urlsafe=event_string)
                event = event_key.get()
            except:
                pass
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
            try:
                event_key = ndb.Key(urlsafe=event_string)
                event = event_key.get()
            except:
                pass
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

class InheritHandler(webapp2.RequestHandler):
    """Handler for a particular event spawning a child event with the same defaults and previous targets filled in"""
    def get(self):
        """Handles the get requests for inheriting an event"""
        parent_event = None
        parent_event_string = self.request.get('parent_event')
        if parent_event_string:
            try:
                parent_event_key = ndb.Key(urlsafe=parent_event_string)
                parent_event = parent_event_key.get()
            except:
                pass
        if parent_event is None:
            self.redirect('/admin/')
        else:
            gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
            event = datamodel.GiftExchangeEvent(parent=gift_exchange_key)
            event.display_name = 'Sequel to ' + parent_event.display_name
            event.money_limit = parent_event.money_limit
            event.put()
            event_key = event.key
            query = datamodel.GiftExchangeParticipant.query(datamodel.GiftExchangeParticipant.event_key==parent_event.key, ancestor=gift_exchange_key)
            participant_list = query.fetch(100)
            for participant in participant_list:
                display_name = participant.display_name
                new_participant = datamodel.GiftExchangeParticipant.create_participant_by_name(gift_exchange_key, display_name, event_key)
                new_participant.user_key = participant.user_key
                new_participant.family = participant.family
                new_participant.previous_target = participant.target
                new_participant.put()
        self.redirect('/admin/event?event=' + event.key.urlsafe())

class StatusChangeHandler(webapp2.RequestHandler):
    """Handler for changing for starting or stopping an event"""
    def post(self):
        """Post handler for starting or stopping an event. Expects a JSON object"""
        data = json.loads(self.request.body)
        event_string = data['event']
        status_change_type = data['status_change_type']
        if event_string:
            try:
                event_key = ndb.Key(urlsafe=event_string)
                event = event_key.get()
            except:
                pass
        if event is not None:
            if status_change_type == 'start':
                StatusChangeHandler._assign_users(datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME), event_key)
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
        if len(participant_list) == 0:
            return
        need_to_give = list(participant_list)
        need_a_giver = list(participant_list)
        #randomize list and then brute force for acceptable assignment
        random.shuffle(need_to_give)
        random.shuffle(need_a_giver)
        source_user = need_to_give[0]
        for target_user in need_a_giver:
            if StatusChangeHandler._is_valid_assignment(source_user, target_user):
                if StatusChangeHandler._can_assign(source_user, target_user, need_to_give, need_a_giver):
                    break
        #Save all participants
        for participant in participant_list:
            participant.put()
        return
        
    @staticmethod
    def _can_assign(source_user, target_user, need_to_give, need_a_giver):
        """Returns where the source_user can give to target_user by checking if there is still a valid assignment scheme for other users"""        
        source_user.target = target_user.display_name
        source_index = need_to_give.index(source_user)
        need_to_give.remove(source_user)
        target_index = need_a_giver.index(target_user)
        need_a_giver.remove(target_user)

        if len(need_to_give) == 0:
            return True
        for giver in need_to_give:
            found_possible_user = False
            for givee in need_a_giver:
                if StatusChangeHandler._is_valid_assignment(giver, givee):
                    found_possible_user = True
                    break
            if not found_possible_user:
                source_user.target = None
                need_to_give.insert(source_index, source_user)
                need_a_giver.insert(target_index, target_user)
                return False
            for givee in need_a_giver:
                if StatusChangeHandler._is_valid_assignment(giver, givee):
                    if StatusChangeHandler._can_assign(giver, givee, need_to_give, need_a_giver):
                        return True
                    else:
                        source_user.target = None
                        need_to_give.insert(source_index, source_user)
                        need_a_giver.insert(target_index, target_user)
        source_user.target = None
        need_to_give.insert(source_index, source_user)
        need_a_giver.insert(target_index, target_user)
        return False
    
    
    @staticmethod
    def _is_valid_assignment(source_user, target_user):
        """Returns whether source_user can give to target_user"""
        #Cannot give to yourself
        if source_user.display_name == target_user.display_name:
            return False
        #Cannot give to the person you gave to last year
        if source_user.previous_target == target_user.display_name:
            return False
        #If you are in a family, cannot give to someone in your own family
        if source_user.family:
            if source_user.family == target_user.family:
                return False
        return True
        

app = webapp2.WSGIApplication([
    ('/admin/', HomeHandler),
    ('/admin/event', EventHandler),
    ('/admin/inherit', InheritHandler),
    ('/admin/statuschange', StatusChangeHandler),
    ('/admin/delete', DeleteHandler),
    ('/admin/report', ReportHandler)
], debug=False)
