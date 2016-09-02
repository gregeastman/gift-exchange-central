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
from google.appengine.api import users

from webapp2_extras import auth
from webapp2_extras import sessions

from datetime import timedelta
import os
import time

import re
import bleach

import webapp2
import jinja2

#from webapp2_extras import auth
#from webapp2_extras import sessions
import webapp2_extras.appengine.auth.models
from webapp2_extras import security

#constants
message_type_to_target = 1
message_type_to_giver = 2
member_type_native_user = 1
member_type_google_user = 2
_DEFAULT_GIFT_EXCHANGE_NAME = 'playground'
_urlfinderregex = re.compile(r'http([^\.\s]+\.[^\.\s]*)+[^\.\s]{2,}')

_JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__),'templates')),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

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

class BaseHandler(webapp2.RequestHandler):
    """A wrapper about webapp2.RequestHandler with customized methods"""
    def __init__(self, *args, **kwargs):
        super(BaseHandler, self).__init__(*args, **kwargs)
        self._my_templates = {}
        self._my_templates['page_title'] =  'Gift Exchange Central' #set default page title
        self._my_templates['is_admin_user'] = users.is_current_user_admin()
        self._my_templates['logout_url'] = '/logout'
        self._my_templates['logged_in_member'] = self.get_gift_exchange_member()
    
    def add_template_values(self, template_values):
        """Adds a list of templates to the array"""
        for key in template_values:
            self._my_templates[key] = template_values[key]
        return
    
    def render_template(self, template):
        """Renders a remplate with the built up list of values"""
        self.response.write(_JINJA_ENVIRONMENT.get_template(template).render(self._my_templates))
        
    @webapp2.cached_property
    def auth(self):
        """Shortcut to access the auth instance as a property."""
        return auth.get_auth()
    
    @webapp2.cached_property
    def user_info(self):
        """Shortcut to access a subset of the user attributes that are stored
        in the session.

        The list of attributes to store in the session is specified in
          config['webapp2_extras.auth']['user_attributes'].
        :returns
          A dictionary with most user information
        """
        return self.auth.get_user_by_session()

    @webapp2.cached_property
    def user(self):
        """Shortcut to access the current logged in user.

        Unlike user_info, it fetches information from the persistence layer and
        returns an instance of the underlying model.

        :returns
          The instance of the user model associated to the logged in user.
        """
        u = self.user_info
        return self.user_model.get_by_id(u['user_id']) if u else None

    @webapp2.cached_property
    def user_model(self):
        """Returns the implementation of the user model.

        It is consistent with config['webapp2_extras.auth']['user_model'], if set.
        """    
        return self.auth.store.user_model

    @webapp2.cached_property
    def session(self):
        """Shortcut to access the current session."""
        return self.session_store.get_session(backend="datastore")
    
    # this is needed for webapp2 sessions to work
    def dispatch(self):
        # Get a session store for this request.
        self.session_store = sessions.get_store(request=self.request)

        try:
            # Dispatch the request.
            webapp2.RequestHandler.dispatch(self)
        finally:
            # Save all sessions.
            self.session_store.save_sessions(self.response)

    def get_gift_exchange_member(self):
        """Gets the member object associated with a particular session"""
        gift_exchange_member = None
        gift_exchange_key = get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        #first see if the user is in the DB
        auth = self.auth
        session_user = auth.get_user_by_session()
        if session_user:
            try:
                user_object = User.get_by_id(session_user['user_id'])
                gift_exchange_member = GiftExchangeMember.get_member_by_user_key(gift_exchange_key, user_object.key)
            except:
                pass
        if gift_exchange_member is None:
            try:
                google_user = users.get_current_user()      
                gift_exchange_member = GiftExchangeMember.update_and_retrieve_member_by_google_user(gift_exchange_key, google_user)
            except:
                pass
        return gift_exchange_member

class User(webapp2_extras.appengine.auth.models.User):
    def set_password(self, raw_password):
        """Sets the password for the current user

        :param raw_password:
            The raw password which will be hashed and stored
        """
        self.password = security.generate_password_hash(raw_password, length=12)

    @classmethod
    def get_by_auth_token(cls, user_id, token, subject='auth'):
        """Returns a user object based on a user ID and token.

        :param user_id:
            The user_id of the requesting user.
        :param token:
            The token string to be verified.
        :returns:
            A tuple ``(User, timestamp)``, with a user object and
            the token timestamp, or ``(None, None)`` if both were not found.
        """
        token_key = cls.token_model.get_key(user_id, subject, token)
        user_key = ndb.Key(cls, user_id)
        # Use get_multi() to save a RPC call.
        valid_token, user = ndb.get_multi([token_key, user_key])
        if valid_token and user:
            timestamp = int(time.mktime(valid_token.created.timetuple()))
            return user, timestamp
        return None, None

class GiftExchangeMember(ndb.Model):
    """A person that could be used in anonymous giving sessions"""
    member_type = ndb.IntegerProperty(indexed=False)
    """An enumeration representing the type of member
        A value of 1 means it is a native user
        A value of 2 means it is a user from app engine's google integration"""
    google_user_id = ndb.StringProperty(indexed=True)
    first_name = ndb.StringProperty(indexed=False)
    last_name = ndb.StringProperty(indexed=False)
    user_key = ndb.KeyProperty(indexed=True, kind=User)
    email = ndb.StringProperty(indexed=True)
    subscribed_to_updates = ndb.BooleanProperty(indexed=False, default=True)
    
    @staticmethod
    def get_member_by_user_key(gift_exchange_key, user_key):      
        query = GiftExchangeMember.query(GiftExchangeMember.user_key==user_key, ancestor=gift_exchange_key)
        return query.get()
    
    @staticmethod
    def get_member_by_google_id(gift_exchange_key, google_user_id):
        """Returns a user by their google user id. Will return none if the user doesn't exist"""
        query = GiftExchangeMember.query(GiftExchangeMember.google_user_id==google_user_id, ancestor=gift_exchange_key)
        return query.get()
    
    @staticmethod
    def create_member_by_native_user(gift_exchange_key, user, email):
        member = GiftExchangeMember.get_member_by_user_key(gift_exchange_key, user.key)
        if member is None:
            member = GiftExchangeMember(parent=gift_exchange_key, 
                                        user_key=user.key,
                                        first_name=user.name,
                                        last_name=user.last_name, 
                                        email=email, 
                                        member_type=member_type_native_user)
            member.put()
        return member
    
    @staticmethod
    def create_member_by_google_user(gift_exchange_key, google_user, first_name, last_name):
        member = GiftExchangeMember.get_member_by_google_id(gift_exchange_key, google_user.user_id())
        if member is None:
            member = GiftExchangeMember(parent=gift_exchange_key, 
                                        google_user_id=google_user.user_id(),
                                        first_name=first_name,
                                        last_name=last_name, 
                                        email=google_user.email(), 
                                        member_type=member_type_google_user)
            member.put()
        return member
    
    @staticmethod
    def update_and_retrieve_member_by_google_user(gift_exchange_key, google_user):
        """Gets a member by their google user id. If the cache is out of date, it will update it.
                It will not create any users"""
        member = GiftExchangeMember.get_member_by_google_id(gift_exchange_key, google_user.user_id())
        if member is not None:
            if member.email != google_user.email():
                member.email = google_user.email()
                member.put()
        return member
    
    @staticmethod
    def get_member_by_email(gift_exchange_key, email):
        """Gets a member by their email address. References to emails shouldn't be stored, but are
            useful for display in UIs, so it should only be for using as a public facing intermediary"""
        query = GiftExchangeMember.query(GiftExchangeMember.email==email, ancestor=gift_exchange_key)
        return query.get()
    
    @staticmethod
    def get_all_members_query(gift_exchange_key):
        """Returns a query for getting all possible members of the system"""
        return GiftExchangeMember.query(ancestor=gift_exchange_key)

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

class GiftExchangeParticipant(ndb.Model):
    """A particular instantiation of a member in a giving event"""
    member_key = ndb.KeyProperty(indexed=True, kind=GiftExchangeMember)
    display_name = ndb.StringProperty(indexed=True)
    family = ndb.StringProperty(indexed=False)
    idea_list = ndb.TextProperty(repeated=True)
    event_key = ndb.KeyProperty(indexed=True, kind=GiftExchangeEvent)
    target = ndb.StringProperty(indexed=True) #represents display_name of member in same event
    is_target_known = ndb.BooleanProperty(indexed=False)
    previous_target = ndb.StringProperty(indexed=False) #represents the display name of the member from last year's event
    
    def get_event(self):
        """Returns the event object that a member is in"""
        return self.event_key.get()
    
    def get_member(self):
        """Returns the member object for this participant"""
        return self.member_key.get()
    
    def is_valid_for_member(self, gift_exchange_member):
        """Determines where a participant matches a particular member"""
        participant_member = self.member_key.get()
        return (participant_member.key == gift_exchange_member.key)
    
    def get_giver(self):
        """Gets the participant name who is giving to this participant, if that person knows"""
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
        """Creates a participant by their display name. If the participant already exists, it will simply return the participant"""
        participant = GiftExchangeParticipant.get_participant_by_name(gift_exchange_key, display_name, event_key)
        if participant is None:
            participant = GiftExchangeParticipant(parent=gift_exchange_key, display_name=display_name, event_key=event_key)
            participant.put()
        return participant
    
    @staticmethod
    def get_participants_in_event_query(gift_exchange_key, event_key):
        """Returns a query for gathering all participants in an event"""
        return GiftExchangeParticipant.query(GiftExchangeParticipant.event_key==event_key, ancestor=gift_exchange_key)
    
    @staticmethod
    def get_participants_by_member_query(gift_exchange_key, member_key):
        """Gets the list of participants for a particular member"""
        #Ideally this would query the event's status. Computed properties don't seem to be a perfect fit since
        #they are updated upon put, and not all the participants are updated upon the starting/ending of events
        return GiftExchangeParticipant.query(GiftExchangeParticipant.member_key==member_key, ancestor=gift_exchange_key)
        

class GiftExchangeMessage(ndb.Model):
    """A message between two participants"""
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
        