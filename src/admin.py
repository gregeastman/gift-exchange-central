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

from google.appengine.api import users
from google.appengine.ext import ndb

import datamodel

import webapp2
import json
import random

_DEFAULT_GIFT_EXCHANGE_NAME = datamodel._DEFAULT_GIFT_EXCHANGE_NAME
_DEFAULT_DISPLAY_NAME = '<ENTER A NAME>'
_DEFAULT_MAX_RESULTS = 200

def event_required(handler):
    """
        Decorator that checks if there's an event associated with the current session.
        Looks for post parameters or JSON object.
        Will also fail if there's no session present.
    """
    def check_event(self, *args, **kwargs):
        event = self.get_event()
        if event is None:
            self.redirect('/admin/', abort=True)
        else:    
            return handler(self, *args, **kwargs)      
    return check_event

class AdminWebAppHandler(datamodel.BaseHandler):
    """A wrapper around webapp2.RequestHandler with a few convenience methods"""
    def get_event(self):
        """Gets an event from the get string event"""
        event = None
        try:
            event_string = ''
            #this is a little hacky, but it seems to work
            if self.request.method == 'GET':
                event_string = self.request.get('event')
            else:
                event_string = json.loads(self.request.body)['event']
            event_key = ndb.Key(urlsafe=event_string)
            event = event_key.get()
        except:
            pass
        return event

class HomeHandler(AdminWebAppHandler):
    """Handles the requests to the admin home page"""
    def get(self):
        """Handles get requests to the admin home page - listing all available events"""
        google_user = users.get_current_user()
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        datamodel.GiftExchangeMember.update_and_retrieve_member(gift_exchange_key, google_user)
        query = datamodel.GiftExchangeEvent.get_all_events_query(gift_exchange_key)
        event_list = query.fetch(_DEFAULT_MAX_RESULTS) #maybe filter out the  events that have ended
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
            }
        self.add_template_values(template_values)
        self.render_template('admin.html')

class EventHandler(AdminWebAppHandler):
    """Handles requests for updating a particular event, including the participants"""
    def get(self):
        """Handles get requests to the page that shows an administrative view of an event"""
        event_string =''
        event = self.get_event()
        event_display_name = _DEFAULT_DISPLAY_NAME
        money_limit = ''
        participant_list = []
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        query = datamodel.GiftExchangeMember.get_all_members_query(gift_exchange_key)
        member_list = query.fetch(_DEFAULT_MAX_RESULTS)
        has_started = False
        has_ended = False
        if event is not None:
            event_string = event.key.urlsafe()
            event_display_name = event.display_name
            money_limit = event.money_limit
            has_started = event.has_started
            has_ended = event.has_ended
            query = datamodel.GiftExchangeParticipant.get_participants_in_event_query(gift_exchange_key, event.key)
            participant_list = query.fetch(_DEFAULT_MAX_RESULTS)
        template_values = {
                'event_string': event_string,
                'event_display_name': event_display_name,
                'has_started': has_started,
                'has_ended': has_ended,
                'money_limit': money_limit,
                'participant_list': participant_list,
                'member_list': member_list,
                'page_title': 'Edit an event',
            }
        self.add_template_values(template_values)
        self.render_template('event.html')
        
    def post(self):
        """Handles updating a particular event, including the participants. Expects a JSON object."""
        def _prune_participants(gift_exchange_key, event_key, name_index):
            """Deletes any participants from a given event that aren't in the name_index"""
            query = datamodel.GiftExchangeParticipant.get_participants_in_event_query(gift_exchange_key, event_key)
            participant_list = query.fetch(_DEFAULT_MAX_RESULTS)
            for participant in participant_list:
                if participant.display_name in name_index:
                    if ((participant.get_member().email != name_index[participant.display_name][0]) 
                            or (participant.family != name_index[participant.display_name][1])):
                        participant.key.delete()
                else:
                    participant.key.delete()
            return
        
        def _save_participants(gift_exchange_key, event_key, participant_list):
            """Helper method for saving the participants in a particular event, including pruning participants"""
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
                member = datamodel.GiftExchangeMember.get_member_by_email(gift_exchange_key, participant_object['email'])
                if participant.member_key != member.key:
                    participant.member_key = member.key
                    needs_saving = True
                family = participant_object['family']
                if participant.family != family:
                    participant.family = family
                    needs_saving = True
                if needs_saving:
                    participant.put()
            _prune_participants(gift_exchange_key, event_key, name_index)
            return message
              
        data = json.loads(self.request.body)
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        message = 'Event Updated Successfully'
        event = self.get_event()
        event_string = data['event']
        needs_saving = False
        event_display_name = data['event_display_name']
        money_limit = data['money_limit']
        if ((event_display_name is None) or (event_display_name == '') or (event_display_name == _DEFAULT_DISPLAY_NAME)):
            message = 'You must select a valid display name'
        else:
            if event is None:
                event = datamodel.GiftExchangeEvent(parent=gift_exchange_key)
                needs_saving = True
            else:
                event_key = event.key
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
                error_message = _save_participants(gift_exchange_key, event_key, data['participant_list'])
                if error_message:
                    message = error_message
        self.response.out.write(json.dumps(({'message': message, 'event_string': event_string, 'money_limit': event.money_limit})))
    
class DeleteHandler(AdminWebAppHandler):
    """Handles requests for deleting an event, including all participants associated with the event"""
    @event_required
    def post(self):
        """Takes a JSON request and deletes the event and all participants associated with it."""
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        event = self.get_event()
        participant_query = datamodel.GiftExchangeParticipant.get_participants_in_event_query(gift_exchange_key, event.key)
        participant_list = participant_query.fetch(_DEFAULT_MAX_RESULTS)
        for participant in participant_list:
            message_query = datamodel.GiftExchangeMessage.get_messages_from_participant_query(gift_exchange_key, participant)
            message_list = message_query.fetch(_DEFAULT_MAX_RESULTS*10)
            for message in message_list:
                message.key.delete()
            participant.key.delete()
        event.key.delete()
        self.response.out.write(json.dumps(({'message': 'Successfully deleted.'})))
       
class ReportHandler(AdminWebAppHandler):
    """Handles showing a report for all the data about a particular event."""
    @event_required
    def get(self):
        """Displays a report about a particular event."""
        event = self.get_event()
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        query = datamodel.GiftExchangeParticipant.get_participants_in_event_query(gift_exchange_key, event.key)
        participant_list = query.fetch(_DEFAULT_MAX_RESULTS)
        template_values = {
            'event': event,
            'participant_list': participant_list,
            'page_title': 'Event Report',
        }
        self.add_template_values(template_values)
        self.render_template('report.html')
        
class InheritHandler(AdminWebAppHandler):
    """Handler for a particular event spawning a child event with the same defaults and previous targets filled in"""
    @event_required
    def get(self):
        """Handles the get requests for inheriting an event"""
        parent_event = self.get_event()
        gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        child_event = datamodel.GiftExchangeEvent(parent=gift_exchange_key)
        child_event.display_name = 'Sequel to ' + parent_event.display_name
        child_event.money_limit = parent_event.money_limit
        child_event.put()
        child_event_key = child_event.key
        query = datamodel.GiftExchangeParticipant.get_participants_in_event_query(gift_exchange_key, parent_event.key)
        participant_list = query.fetch(_DEFAULT_MAX_RESULTS)
        for participant in participant_list:
            display_name = participant.display_name
            new_participant = datamodel.GiftExchangeParticipant.create_participant_by_name(gift_exchange_key, display_name, child_event_key)
            new_participant.member_key = participant.member_key
            new_participant.family = participant.family
            new_participant.previous_target = participant.target
            new_participant.put()
        self.redirect('/admin/event?event=' + child_event.key.urlsafe())

class StatusChangeHandler(AdminWebAppHandler):
    """Handler for changing for starting or stopping an event"""
    @event_required
    def post(self):
        """Post handler for starting or stopping an event. Expects a JSON object"""
        
        def _is_valid_assignment(source_participant, target_participant):
            """Returns whether source_participant can give to target_participant"""
            #Cannot give to yourself
            if source_participant.display_name == target_participant.display_name:
                return False
            #Cannot give to the person you gave to last year
            if source_participant.previous_target == target_participant.display_name:
                return False
            #If you are in a family, cannot give to someone in your own family
            if source_participant.family:
                if source_participant.family == target_participant.family:
                    return False
            return True
        
        def _can_assign(source_participant, target_participant, need_to_give, need_a_giver):
            """Returns where the source_participant can give to target_participant by checking if there is still a valid assignment scheme for other participants"""        
            source_participant.target = target_participant.display_name
            source_index = need_to_give.index(source_participant)
            need_to_give.remove(source_participant)
            target_index = need_a_giver.index(target_participant)
            need_a_giver.remove(target_participant)
    
            if len(need_to_give) == 0:
                return True
            for giver in need_to_give:
                found_possible_participant = False
                for givee in need_a_giver:
                    if _is_valid_assignment(giver, givee):
                        found_possible_participant = True
                        break
                if not found_possible_participant:
                    source_participant.target = None
                    need_to_give.insert(source_index, source_participant)
                    need_a_giver.insert(target_index, target_participant)
                    return False
                for givee in need_a_giver:
                    if _is_valid_assignment(giver, givee):
                        if _can_assign(giver, givee, need_to_give, need_a_giver):
                            return True
                        else:
                            source_participant.target = None
                            need_to_give.insert(source_index, source_participant)
                            need_a_giver.insert(target_index, target_participant)
            source_participant.target = None
            need_to_give.insert(source_index, source_participant)
            need_a_giver.insert(target_index, target_participant)
            return False
        
        def _assign_participants(gift_exchange_key, event_key):
            """Helper method for assigning targets to all participants in a given event."""
            query = datamodel.GiftExchangeParticipant.get_participants_in_event_query(gift_exchange_key, event_key)
            participant_list = query.fetch(_DEFAULT_MAX_RESULTS)
            if len(participant_list) == 0:
                return
            need_to_give = list(participant_list)
            need_a_giver = list(participant_list)
            #randomize list and then brute force for acceptable assignment
            random.shuffle(need_to_give)
            random.shuffle(need_a_giver)
            source_participant = need_to_give[0]
            for target_participant in need_a_giver:
                if _is_valid_assignment(source_participant, target_participant):
                    if _can_assign(source_participant, target_participant, need_to_give, need_a_giver):
                        break
            #Save all participants
            for participant in participant_list:
                participant.put()
            return
    
        data = json.loads(self.request.body)
        status_change_type = data['status_change_type']
        event = self.get_event()
        if status_change_type == 'start':
            _assign_participants(datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME), event.key)
            event.has_started = True
            event.put()
        if status_change_type == 'stop':
            event.has_ended = True
            event.put()
        self.response.out.write(json.dumps(({'message': 'Event successfully updated', 'event_string': event.key.urlsafe()})))

app = webapp2.WSGIApplication([
    ('/admin/', HomeHandler),
    ('/admin/event', EventHandler),
    ('/admin/inherit', InheritHandler),
    ('/admin/statuschange', StatusChangeHandler),
    ('/admin/delete', DeleteHandler),
    ('/admin/report', ReportHandler)
], debug=False)
