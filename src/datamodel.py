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

from google.appengine.ext import ndb
import re
import bleach
from datetime import timedelta

#constants
message_type_to_target = 1
message_type_to_giver = 2
_DEFAULT_GIFT_EXCHANGE_NAME = 'playground'
_urlfinderregex = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')

def get_gift_exchange_key(gift_exchange_name):
    """Returns the default key that all data is stored under"""
    return ndb.Key('GiftExchange', gift_exchange_name)

def free_text_to_safe_html_markup(text, maxlinklength):
    def replacewithlink(matchobj):
        url = matchobj.group(0)
        text = unicode(url)
        if text.startswith('http://'):
            text = text.replace('http://', '', 1)
        elif text.startswith('https://'):
            text = text.replace('https://', '', 1)

        if text.startswith('www.'):
            text = text.replace('www.', '', 1)

        if len(text) > maxlinklength:
            halflength = maxlinklength / 2
            text = text[0:halflength] + '...' + text[len(text) - halflength:]

        return '<a class="comurl" href="' + url + '" target="_blank" rel="nofollow">' + text + '<img class="imglink" src="/media/images/linkout.png"></a>'

    if text != None and text != '':
        text = bleach.clean(text)
        text = _urlfinderregex.sub(replacewithlink, text)
        return text.replace('\n', '<br />')
    return ''

class GiftExchangeEvent(ndb.Model):
    """An event for anonymous giving"""
    display_name = ndb.StringProperty(indexed=True)
    has_started = ndb.BooleanProperty(indexed=False, default=False)
    has_ended = ndb.BooleanProperty(indexed=False, default=False)
    money_limit = ndb.StringProperty(indexed=False, default='$50')
    
    def is_active(self):
        """Returns whether an event is active"""
        return (self.has_started and not self.has_ended)
    
    @staticmethod
    def get_all_events_query(gift_exchange_key):
        """Returns a query that will return all events"""
        return GiftExchangeEvent.query(ancestor=gift_exchange_key)

class GiftExchangeUser(ndb.Model):
    """A user that could be used in anonymous giving sessions"""
    google_user_id = ndb.StringProperty(indexed=True)
    email = ndb.StringProperty(indexed=True)
    subscribed_to_updates = ndb.BooleanProperty(indexed=False, default=True)

    @staticmethod
    def get_user_by_google_id(gift_exchange_key, google_user_id):
        """Returns a user by their google user id. Will return none if the user doesn't exist"""
        query = GiftExchangeUser.query(GiftExchangeUser.google_user_id==google_user_id, ancestor=gift_exchange_key)
        return query.get()
    
    @staticmethod
    def update_and_retrieve_user(gift_exchange_key, google_user):
        """Gets a user by their google user id. If the user doesn't exist, it will create it. If the cache
            is out of date, it will update it."""
        user = GiftExchangeUser.get_user_by_google_id(gift_exchange_key, google_user.user_id())
        if user is None:
            user = GiftExchangeUser(parent=gift_exchange_key, google_user_id=google_user.user_id(), email=google_user.email())
            user.put()
        else:
            if user.email != google_user.email():
                user.email = google_user.email()
                user.put()
        return user
    
    @staticmethod
    def get_user_by_email(gift_exchange_key, email):
        """Gets a user by their email address. References to emails shouldn't be stored, but are
            useful for display in UIs, so it should only be for using as a user facing intermediary"""
        query = GiftExchangeUser.query(GiftExchangeUser.email==email, ancestor=gift_exchange_key)
        return query.get()
    
    @staticmethod
    def get_all_users_query(gift_exchange_key):
        """Returns a query for getting all possible users of the system"""
        return GiftExchangeUser.query(ancestor=gift_exchange_key)

class GiftExchangeParticipant(ndb.Model):
    """A particular instantiation of a user in a giving event"""
    user_key = ndb.KeyProperty(indexed=True, kind=GiftExchangeUser)
    display_name = ndb.StringProperty(indexed=True)
    family = ndb.StringProperty(indexed=False)
    idea_list = ndb.TextProperty(repeated=True)
    event_key = ndb.KeyProperty(indexed=True, kind=GiftExchangeEvent)
    target = ndb.StringProperty(indexed=True) #represents display_name of user in same event
    is_target_known = ndb.BooleanProperty(indexed=False)
    previous_target = ndb.StringProperty(indexed=False) #represents the display name of the user from last year's event
    
    def get_event(self):
        """Returns the event object that a user is in"""
        return self.event_key.get()
    
    def get_user(self):
        """Returns the user object for this participant"""
        return self.user_key.get()
    
    def is_valid_for_google_id(self, google_user_id):
        """Determines where a user matches a particular google user id"""
        user = self.user_key.get()
        if user is None:
            return False
        return (user.google_user_id == google_user_id)
    
    def get_giver(self):
        """Gets the user who is giving to this participant, if that person knows"""
        query = GiftExchangeParticipant.query(GiftExchangeParticipant.target==self.display_name, GiftExchangeParticipant.event_key==self.event_key)
        giver = query.get()
        if giver.is_target_known:
            return giver
        return None
    
    @staticmethod
    def get_participant_by_name(gift_exchange_key, display_name, event_key):
        """Gets a participant in a gift exchange by their display name"""
        query = GiftExchangeParticipant.query(GiftExchangeParticipant.display_name==display_name, GiftExchangeParticipant.event_key==event_key, ancestor=gift_exchange_key)
        return query.get()
        
    @staticmethod
    def create_participant_by_name(gift_exchange_key, display_name, event_key):
        """Creates a user by their display name. If the user already exists, it will simply return the user"""
        user = GiftExchangeParticipant.get_participant_by_name(gift_exchange_key, display_name, event_key)
        if user is None:
            user = GiftExchangeParticipant(parent=gift_exchange_key, display_name=display_name, event_key=event_key)
            user.put()
        return user
    
    @staticmethod
    def get_participants_in_event_query(gift_exchange_key, event_key):
        """Returns a query for gathering all users in an event"""
        return GiftExchangeParticipant.query(GiftExchangeParticipant.event_key==event_key, ancestor=gift_exchange_key)
    
    @staticmethod
    def get_participants_by_user_query(gift_exchange_key, user_key):
        """Gets the list of participants for a particular user"""
        #Ideally this would query the event's status. Computed properties don't seem to be a perfect fit since
        #they are updated upon put, and not all the users are updated upon the starting/ending of events
        return GiftExchangeParticipant.query(GiftExchangeParticipant.user_key==user_key, ancestor=gift_exchange_key)
        

class GiftExchangeMessage(ndb.Model):
    """A message between two users"""
    sender_key = ndb.KeyProperty(indexed=True, kind=GiftExchangeParticipant)
    """An ndb key representing the sender of the message as a GiftExchangeParticipant"""
    time_sent = ndb.DateTimeProperty(indexed=True, auto_now_add=True)
    """An instant representing when the message was sent/created"""
    message_type = ndb.IntegerProperty(indexed=True)
    """An enumeration representing the type of message
        A value of 1 means it is sent messages to who you're giving to
        A value of 2 means it is messages to your anonymous giver"""
    #consider adding a subject field
    content = ndb.TextProperty(default='')
    """The actual content of the message"""
    
    def get_formatted_time_sent(self):
        """Returns a nicely formatted time sent"""
        central_time = self.time_sent + timedelta(hours=-6)
        return central_time.strftime('%B %d, %Y %I:%M %p')
    
    def get_escaped_content(self):
        """Gets an escaped and minimally linkified version of the content"""
        return free_text_to_safe_html_markup(self.content, 100)
        
    @staticmethod
    def create_message(gift_exchange_key, sender_key, message_type, content):
        """Creates a message and saves it to the database"""
        message = GiftExchangeMessage(parent=gift_exchange_key, sender_key=sender_key, message_type=message_type, content=content)
        message.put()
        return message
    
    @staticmethod
    def get_messages_from_participant_query(gift_exchange_key, gift_exchange_participant):
        return GiftExchangeMessage.query(GiftExchangeMessage.sender_key==gift_exchange_participant.key, ancestor=gift_exchange_key)
    
    @staticmethod
    def get_message_exchange_query(gift_exchange_key, giving_participant, target_participant):
        """Returns a query that returns an ordered list of messages"""
        return GiftExchangeMessage.query(
                            ndb.OR(
                                ndb.AND(
                                    GiftExchangeMessage.sender_key==giving_participant.key,
                                    GiftExchangeMessage.message_type==message_type_to_target
                                    ), 
                                ndb.AND(
                                    GiftExchangeMessage.sender_key==target_participant.key, 
                                    GiftExchangeMessage.message_type==message_type_to_giver
                                    )
                                ),
                            ancestor=gift_exchange_key).order(-GiftExchangeMessage.time_sent)
        
        
        