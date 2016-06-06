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


_DEFAULT_GIFT_EXCHANGE_NAME = 'playground'

def get_gift_exchange_key(gift_exchange_name):
    """Returns the default key that all data is stored under"""
    return ndb.Key('GiftExchange', gift_exchange_name)

class GiftExchangeEvent(ndb.Model):
    """An event for anonymous giving"""
    display_name = ndb.StringProperty(indexed=True)
    has_started = ndb.BooleanProperty(indexed=False, default=False)
    has_ended = ndb.BooleanProperty(indexed=False, default=False)
    money_limit = ndb.StringProperty(indexed=False, default='$50')
    
    def is_active(self):
        """Returns whether an event is active"""
        return (self.has_started and not self.has_ended)
    

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

class GiftExchangeParticipant(ndb.Model):
    """A particular instantiation of a user in a giving event"""
    user_key = ndb.KeyProperty(indexed=True, kind=GiftExchangeUser)
    display_name = ndb.StringProperty(indexed=True)
    family = ndb.StringProperty(indexed=False)
    ideas = ndb.TextProperty(default='') #TODO: consider making a repeated property
    event_key = ndb.KeyProperty(indexed=True, kind=GiftExchangeEvent)
    target = ndb.StringProperty(indexed=True) #represents display_name of user in same event
    is_target_known = ndb.BooleanProperty(indexed=False)
    #previous_target = ndb.StringProperty(indexed=False) #represents the display name of the user from last year's event
    
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
        

