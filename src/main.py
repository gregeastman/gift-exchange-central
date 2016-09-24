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

#Natively provided by python libraries
import json
import logging

#Natively provided by app engine
import google.appengine.ext.ndb as ndb
import google.appengine.api.users as google_authentication
import google.appengine.api.mail

#Includes specified by the app.yaml
import webapp2
import webapp2_extras.auth

#Included third party libraries distributed with the project
import bleach

#App specific includes
import datamodel
import constants


_DEFAULT_MAX_RESULTS = 200
_DEFAULT_GIFT_EXCHANGE_NAME = datamodel.DEFAULT_GIFT_EXCHANGE_NAME
_MESSAGE_TYPE_TO_TARGET = datamodel.MESSAGE_TYPE_TO_TARGET
_MESSAGE_TYPE_TO_GIVER = datamodel.MESSAGE_TYPE_TO_GIVER

member_required = datamodel.member_required
free_text_to_safe_html_markup = datamodel.free_text_to_safe_html_markup
get_gift_exchange_key = datamodel.get_gift_exchange_key

def participant_required(handler):
    """
        Decorator that checks if there's a participant associated with the current page
        Will look to post and JSON for the participant.
    """
    def check_participant(self, *args, **kwargs):
        gift_exchange_participant = self.get_participant(*args, **kwargs)
        if gift_exchange_participant is None:
            self.redirect(self.uri_for('home'), abort=True)
        elif gift_exchange_participant.is_valid_for_member(self.get_gift_exchange_member()) == False:
            self.redirect(self.uri_for('home'), abort=True)
        else:    
            return handler(self, *args, **kwargs)      
    return check_participant

def send_email_helper(recipient_name, recipient_email, subject, plain_text_content, unsubscribe_link):
    """"Function that will sent an HTML email to a particular recipient with standard headers and footers"""
    plain_text = 'Hello ' + recipient_name + ',\n\n' + plain_text_content
    plain_text = plain_text + '\n\n\n-------------------------------------------------------------------------'
    plain_text = plain_text + '\nThis is an auto-generated email from Gift Exchange Central. Please do not reply to this email.'
    body = free_text_to_safe_html_markup(plain_text, 9999)
    if unsubscribe_link:
        body = body + '<br /><a href="' + unsubscribe_link + '">Unsubscribe from automated updates</a>'
        plain_text = plain_text + '\nUnsubscribe: ' + unsubscribe_link
    
    message = google.appengine.api.mail.EmailMessage(
                sender='anonymous@gift-exchange-central.appspotmail.com',
                subject=subject)
    message.to = recipient_email
    message.body = plain_text
    message.html = '<html><head></head><body>' + body + '</body></html>'
    message.send()


class MainWebAppHandler(datamodel.BaseHandler):
    """A wrapper about webapp2.RequestHandler with customized methods"""
    def get_participant(self, *args, **kwargs):
        """Gets a participant from the get string gift_exchange_participant"""
        gift_exchange_participant = None
        try:
            participant_string = kwargs['participant']
            participant_key = ndb.Key(urlsafe=participant_string)
            gift_exchange_participant = participant_key.get()
        except:
            pass
        return gift_exchange_participant
                           
class LoginHandler(MainWebAppHandler):
    """Class for handling logins"""
    def get(self):
        """Handles the get requests for logins"""
        gift_exchange_member = self.get_gift_exchange_member()
        if gift_exchange_member:
            self.redirect(self.uri_for('home'))
            return
        self.render_template('login.html')

    def post(self):
        """Process the login request as a forms post"""
        username = self.request.get('username')
        password = self.request.get('password')
        failure_message = 'Username/password was not found'
        try:
            self.auth.get_user_by_password(username, password, remember=True, save_session=True)
            self.redirect(self.uri_for('home'))
            return
        except (webapp2_extras.auth.InvalidAuthIdError, webapp2_extras.auth.InvalidPasswordError) as e:
            logging.info('Login failed for user %s because of %s', username, type(e))
        if username.find('@') != -1:
            gift_exchange_key = datamodel.get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
            member = datamodel.GiftExchangeMember.get_member_by_email(gift_exchange_key, username)
            if member is not None and member.verified_email and member.user_key:
                login_string = member.user_key.get().auth_ids[0]
                try:
                    self.auth.get_user_by_password(login_string, password, remember=True, save_session=True)
                    self.redirect(self.uri_for('home'))
                    return
                except (webapp2_extras.auth.InvalidAuthIdError, webapp2_extras.auth.InvalidPasswordError) as e:
                    logging.info('Login failed for user %s because of %s', login_string, type(e))
        self.add_template_values({'username': username, 'failure_message': failure_message})
        self.render_template('login.html')

class GoogleLoginHandler(MainWebAppHandler):
    """Class for handling logins that simply requires google authentication before proceeding"""
    def get(self, *args, **kwargs):
        """Get method for google authentication login. Should be a passthrough, but
             handles the scenario where an account is not yet created"""
        if self.get_gift_exchange_member(*args, **kwargs):
            self.redirect(self.uri_for('home'))
            return
        failure_message = 'Could not find user for ' + google_authentication.get_current_user().email() + '. You must create an account first.'
        self.add_template_values({'failure_message': failure_message, 'google_logout': google_authentication.create_logout_url(self.uri_for('login'))})
        self.render_template('login.html')

class LogoutHandler(MainWebAppHandler):
    """Handles get requests for logging out"""
    def get(self):
        """Logs a user out. Checks if the user is logged in natively and logs them out, otherwise will log
            them out of google"""
        auth = self.auth
        session_user = auth.get_user_by_session()
        user_object = None
        if session_user:
            try:
                user_object = datamodel.User.get_by_id(session_user['user_id'])
            except:
                pass
        if user_object:
            self.auth.unset_session()
        else:
            self.redirect(google_authentication.create_logout_url(self.uri_for('login')))
            return        
        self.redirect(self.uri_for('login'))

class SignupHandler(MainWebAppHandler):
    """Class for processing new user signup"""
    def get(self):
        """Handles get requests for signing up"""
        google_user = google_authentication.get_current_user()
        default_native = True
        if google_user:
            default_native = False
        template_values = {
                'google_user': google_user,
                'default_native': default_native,
                'google_login_url': google_authentication.create_login_url(self.uri_for('signup'))
            }
        self.add_template_values(template_values)
        self.render_template('signup.html')
    
    def post(self):
        """Handles creating new users"""
        data = json.loads(self.request.body)
        
        account_type = data['account_type']
        
        name = data['name']
        lastname = data['lastname']
        if not name:
            self.response.out.write(json.dumps(({'message': 'Name is required.'})))
            return
        if not lastname:
            self.response.out.write(json.dumps(({'message': 'Last name is required.'})))
            return
        gift_exchange_key = get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
    
        if account_type == 'native':
            user_name = data['username']
            email = data['email']
            password = data['password']
            if not user_name:
                self.response.out.write(json.dumps(({'message': 'Username is required.'})))
                return
            if not password:
                self.response.out.write(json.dumps(({'message': 'Password is required.'})))
                return
            if not email:
                self.response.out.write(json.dumps(({'message': 'Email is required.'})))
                return
            email_object = None
            try:
                email_object = datamodel.UserUnique.create_unique_value('email', email)
            except:
                email_object = None
            if not email_object:
                self.response.out.write(json.dumps(({'message': 'Email address already exists'})))
                return
            user_data = self.user_model.create_user(user_name, name=name, password_raw=password)
            if not user_data[0]: #user_data is a tuple
                msg = ''
                if 'auth_id' in user_data[1]:
                    msg = 'Username already exists: ' + user_name
                email_object.key.delete() #clean up object
                self.response.out.write(json.dumps(({'message': msg})))
                return
            
            user = user_data[1]
            user_id = user.get_id()
            
            datamodel.GiftExchangeMember.create_member_by_native_user(gift_exchange_key, user, email_object, name, lastname)
            
            token = self.user_model.create_signup_token(user_id)
        
            verification_url = self.uri_for('verification', type='v', user_id=user_id,
              signup_token=token, _full=True)
        
            message_content = 'You have signed up for a new account at Gift Exchange Central: ' + self.uri_for('root')
            message_content = message_content + 'Verify your account at ' + verification_url
            send_email_helper(name, email, 'Account Verification for Gift Exchange Central', message_content, None)
            self.response.out.write(json.dumps(({'message': ''})))
            return
        elif account_type == 'google':
            google_user = google_authentication.get_current_user()
            if google_user is None:
                self.response.out.write(json.dumps(({'message': 'Cannot create google user when not logged in.'})))
                return
            google_user_object = None
            try:
                google_user_object = datamodel.UserUnique.create_unique_value('google', google_user.user_id())
            except:
                google_user_object = None
            if not google_user_object:
                self.response.out.write(json.dumps(({'message': 'User already exists with this account.'})))
                return
            datamodel.GiftExchangeMember.create_member_by_google_user(gift_exchange_key, google_user_object, name, lastname, google_user.email())
            self.response.out.write(json.dumps(({'message': ''})))
            return
        self.response.out.write(json.dumps(({'message': 'Unknown error'})))
        
        
class VerificationHandler(MainWebAppHandler):
    """Verification handler used for verifiying emails and handling forgotten passwords"""
    def get(self, *args, **kwargs):
        """Handles get requests for verifying emails and forgotten passwords"""
        user = None
        user_id = kwargs['user_id']
        signup_token = kwargs['signup_token']
        verification_type = kwargs['type']
    
        # it should be something more concise like
        # self.auth.get_user_by_token(user_id, signup_token)
        # unfortunately the auth interface does not (yet) allow to manipulate
        # signup tokens concisely 
        my_tuple = self.user_model.get_by_auth_token(int(user_id), signup_token,
          'signup')
        
        if my_tuple:
            user = my_tuple[0]
        if not user:
            logging.info('Could not find any user with id "%s" signup token "%s"',
                         user_id, signup_token)
            self.abort(404)
        
        # store user data in the session
        self.auth.set_session(self.auth.store.user_to_dict(user), remember=True)
    
        if verification_type == 'v':
            # remove signup token, we don't want users to come back with an old link
            self.user_model.delete_signup_token(user.get_id(), signup_token)
            
            gift_exchange_key = get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
            member = datamodel.GiftExchangeMember.get_member_by_user_key(gift_exchange_key, user.key)
            member.verify_email_address()
            self.render_template('verification.html')
            return
        elif verification_type == 'p':
            # remove signup token, we don't want users to come back with an old link
            # this is pretty aggressive to remove it immediately, since it means the user can't refresh the page
            # but it's easy to request a new link
            self.user_model.delete_signup_token(user.get_id(), signup_token)
            
            # supply user to the page
            self.add_template_values({'user': user})
            self.render_template('setpassword.html')
        else:
            logging.info('verification type not supported')
            self.abort(404)

class SetPasswordHandler(MainWebAppHandler):
    """Class for setting a user's password."""
    @member_required
    def get(self):
        # supply user to the page
        self.add_template_values({'user': self.user})
        self.render_template('setpassword.html')
    
    @member_required
    def post(self):
        """Handles the request to set a user's password"""
        data = json.loads(self.request.body)
        password = data['password']
        if not password or password != data['confirm_password']:
            self.response.out.write(json.dumps(({'message': 'Passwords do not match'})))
            return
        user = self.user
        user.set_password(password)
        user.put()
        self.response.out.write(json.dumps(({'message': ''})))


class ForgotPasswordHandler(MainWebAppHandler):
    """Class for handling a forgotten password."""
    def get(self):
        """Handles the front-end for a user requesting a forgotten password."""
        self.render_template('forgot.html')

    def post(self):
        """Handles the request for a user forgetting their password and send an email with verification"""
        data = json.loads(self.request.body)
        username = data['username']
        user = self.user_model.get_by_auth_id(username)
        if not user:
            msg = 'Could not find any user entry for username %s', username
            logging.info(msg)
            self.response.out.write(json.dumps(({'message': msg})))
            return
    
        user_id = user.get_id()
        token = self.user_model.create_signup_token(user_id)
    
        verification_url = self.uri_for('verification', type='p', user_id=user_id,
          signup_token=token, _full=True)
    
        message_content = 'You have signed up for a new account at Gift Exchange Central: ' + self.uri_for('root')
        message_content = message_content + 'Verify your account at ' + verification_url
        gift_exchange_key = get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        member = datamodel.GiftExchangeMember.get_member_by_user_key(gift_exchange_key, user.key)
        send_email_helper(member.first_name, member.get_email_address(), 'Password Reset for Gift Exchange Central', message_content, None)
        self.response.out.write(json.dumps(({'message': ''})))

class HomeHandler(MainWebAppHandler):
    """The home page of the gift exchange app. This finds any events that a member is in"""
    @member_required
    def get(self):
        """The handler for get requests to the home page"""
        gift_exchange_key = get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        member = self.get_gift_exchange_member()
        all_participants = []
        if member is not None:
            query = datamodel.GiftExchangeParticipant.get_participants_by_member_query(gift_exchange_key, member.key)
            all_participants = query.fetch(_DEFAULT_MAX_RESULTS)
        participant_list = []
        for participant in all_participants:
            if participant.get_event().is_active():
                participant_list.append(participant)
        if len(participant_list)==1:
            participant = participant_list[0]
            self.redirect(self.uri_for('main', participant=participant.key.urlsafe()))
        else:
            self.add_template_values({'participant_list': participant_list })
            self.render_template('home.html')
        return

class MainHandler(MainWebAppHandler):
    """The main page for a given event. Requires a specific participant"""
    @member_required
    @participant_required
    def get(self, *args, **kwargs):
        """Handles get requests for the main page of a given event."""
        gift_exchange_participant = self.get_participant(*args, **kwargs)
        gift_exchange_key = get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        target_participant = datamodel.GiftExchangeParticipant.get_participant_by_name(
                                                                            gift_exchange_key, 
                                                                            gift_exchange_participant.target,
                                                                            gift_exchange_participant.event_key)
        target_idea_list = []
        target_messages = []
        giver_messages = []
        if target_participant is not None:
            query = datamodel.GiftExchangeMessage.get_message_exchange_query(gift_exchange_key, gift_exchange_participant, target_participant)
            target_messages = query.fetch(_DEFAULT_MAX_RESULTS)
            for idea in target_participant.idea_list:
                target_idea_list.append(free_text_to_safe_html_markup(idea, 60))           
        giver = gift_exchange_participant.get_giver(True)
        if giver:
            query = datamodel.GiftExchangeMessage.get_message_exchange_query(gift_exchange_key, giver, gift_exchange_participant)
            giver_messages = query.fetch(_DEFAULT_MAX_RESULTS)
        template_values = {
                'page_title': gift_exchange_participant.get_event().display_name + ' Homepage',
                'gift_exchange_participant': gift_exchange_participant,
                'target_participant': target_participant,
                'target_idea_list': target_idea_list,
                'target_messages': target_messages,
                'giver_messages': giver_messages,
                'money_limit': gift_exchange_participant.get_event().money_limit,
            }
        self.add_template_values(template_values)
        self.render_template('main.html')
  
class UpdateHandler(MainWebAppHandler):
    """Class that handles updates to the participant's ideas"""
    @member_required
    @participant_required
    def post(self, *args, **kwargs):
        """This handles post requests. Requires a JSON object"""
        data = json.loads(self.request.body)
        message = 'Ideas could not be updated'
        gift_exchange_participant = self.get_participant(*args, **kwargs)
        if gift_exchange_participant is not None:
            idea_list = data['idea_list'] 
            gift_exchange_participant.idea_list = idea_list
            gift_exchange_participant.put()
            message = 'Ideas successfully updated'
            giver = gift_exchange_participant.get_giver()
            if giver is not None:
                member = giver.get_member()
                if member.get_email_address() and member.subscribed_to_updates:
                    body = gift_exchange_participant.display_name + ' has updated their profile with new ideas for '
                    body = body + gift_exchange_participant.get_event().display_name
                    body = body + '\n\n'
                    for idea in idea_list:
                        body = body + idea + '\n'
                    #Given that ideas are updated on every save, would only want to send message on navigating away from page
                    #email_subject = gift_exchange_participant.get_event().display_name + ' Gift Idea Update'
                    #unsubscribe_link = self.uri_for('unsubscribe') + '?gift_exchange_member=' + member.key.urlsafe()
                    #send_email_helper(giver.display_name, member.get_email_address(), email_subject, body, unsubscribe_link)
        self.response.out.write(json.dumps(({'message': message})))
        
class AssignmentHandler(MainWebAppHandler):
    """The handler for assigning requests."""
    @member_required
    @participant_required
    def post(self, *args, **kwargs):
        """This handles the post request for assigning participants. Requires a JSON object"""
        target = ''
        gift_exchange_participant = self.get_participant(*args, **kwargs)
        if gift_exchange_participant is not None:
            gift_exchange_participant.is_target_known = True
            target = gift_exchange_participant.target
            gift_exchange_participant.put()
        self.response.out.write(json.dumps(({'target': target})))

class PreferencesHandler(MainWebAppHandler):
    """The handler for updating preferences."""
    @member_required
    def get(self):
        """Handles get requests and serves up the preference page."""
        member = self.get_gift_exchange_member()
        template_values = {
                           'page_title': 'User Preferences',
                           'google_user': google_authentication.get_current_user(),
                           'google_login_url': google_authentication.create_login_url(self.uri_for('preferences')),
                           'member': member,
                        }
        self.add_template_values(template_values)
        self.render_template('preferences.html')
    
    @member_required
    def post(self):
        """Handles posts requests for updating preferences. Requires a JSON object."""
        refresh = ''
        data = json.loads(self.request.body)
        member_is_dirty = False
        member = self.get_gift_exchange_member()
        first_name = data['name']
        last_name = data['lastname']
        email = data['email']
        subscribed_string = data['subscribed_string']
        subscribed_to_updates = True
        if subscribed_string == 'no':
            subscribed_to_updates = False
        if not first_name:
            self.response.out.write(json.dumps(({'message': 'First name cannot be blank'})))
            return
        if not last_name:
            self.response.out.write(json.dumps(({'message': 'Last name cannot be blank'})))
            return
        if not email:
            self.response.out.write(json.dumps(({'message': 'Email cannot be blank'})))
            return
        email_object = None
        if (member.get_email_address() != email) or (member.pending_email_key is not None):
            #The UI doesn't allow a change, but if the user is a google user, this can temporarily change the email
            #That doesn't really matter, since it will be reset    
            if member.get_email_address() != email:
                #This is also slightly weird when there's a pending email change, but that should be unlikely, and the behavior is not "wrong"
                #If I keep the existing address, it will clear the pending update
                #If I change to pending address, it will throw an error
                #If I put in a new address, it will work as expected
                try:
                    email_object = datamodel.UserUnique.create_unique_value('email', email)
                except:
                    email_object = None
                if email_object is None:
                    self.response.out.write(json.dumps(({'message': 'Email is already in use'})))
                    return
            else:
                refresh = '1' #if updating with pending email, simply clear out pending key
            #clean up old pending key
            if member.pending_email_key:
                member.pending_email_key.get().key.delete()
                member.pending_email_key = None
                member_is_dirty = True
        if member.subscribed_to_updates != subscribed_to_updates:
            member.subscribed_to_updates = subscribed_to_updates
            member_is_dirty = True
        if member.first_name != first_name:
            member.first_name = first_name
            member_is_dirty = True
            try:
                user_object = member.user_key.get()
                user_object.name = first_name
                user_object.put()
            except:
                pass
        if member.last_name != last_name:
            member.last_name = last_name
            member_is_dirty =True
        if email_object is not None:
            member.pending_email_key = email_object.key
            member_is_dirty = True
            user_id = member.user_key.id()
            refresh = '1'
            token = self.user_model.create_signup_token(user_id)
        
            verification_url = self.uri_for('verification', type='v', user_id=user_id,
              signup_token=token, _full=True)
        
            message_content = 'You have updated your email at Gift Exchange Central: ' + self.uri_for('root')
            message_content = message_content + 'Verify your email address at ' + verification_url
            send_email_helper(member.first_name, email, 'Email Verification for Gift Exchange Central', message_content, None)
            
        if member_is_dirty:
            member.put()
        self.response.out.write(json.dumps(({'message': '', 'refresh': refresh})))

class GoogleLinkHandler(MainWebAppHandler):
    """Class for handling linking and unlinking google accounts"""
    @member_required
    def post(self, *args, **kwargs):
        """Handles the request to link or unlink a google account from a member"""
        data = json.loads(self.request.body)
        change_type = data['type']
        member = self.get_gift_exchange_member(*args, **kwargs)
        if change_type == 'link':
            google_user = google_authentication.get_current_user()
            if not google_user:
                self.response.write(json.dumps(({'message': 'Must be logged into Google to link account.'})))
                return
            google_user_object = None
            try:
                google_user_object = datamodel.UserUnique.create_unique_value('google', google_user.user_id())
            except:
                google_user_object = None
            if not google_user_object:
                self.response.out.write(json.dumps(({'message': 'Cannot link Google account because it is already linked to another user.'})))
                return
            member.link_google_user(google_user_object)
            self.response.write(json.dumps(({'message': ''})))
            return
        elif change_type == 'unlink':
            if member.user_key is None:
                self.response.write(json.dumps(({'message': 'Cannot unlink google account if there is no native user.'})))
                return
            member.unlink_google_user()
            self.response.write(json.dumps(({'message': ''})))
            return
        self.response.write(json.dumps(({'message': 'Unsupported command'})))

class UnsubscribeHandler(MainWebAppHandler):
    """Handles unsubscribing a member"""
    def get(self):
        """Handles get requests for unsubscribing"""
        #Don't require a user to be logged in to unsubcribe.
        #This means that anybody can be unsubscribed with merely a link, but that is better
        #  than being aggressive about disallowing unsubscribes, and the GUID shouldn't
        #  be easy to reproduce
        member = None
        try:
            member_key = ndb.Key(urlsafe=self.request.get('gift_exchange_member'))
            member = member_key.get()
        except:
            pass
        if member:
            if not member.subscribed_to_updates:
                member.subscribed_to_updates = False
                member.put()
            self.add_template_values({'page_title': 'Successfully unsubscribed'})
            self.render_template('unsubscribe.html')
            return
        self.redirect(self.uri_for('home'))

class MessageHandler(MainWebAppHandler):
    """Handler for page to send anonymous messages to your target"""
    @participant_required
    @member_required
    def post(self, *args, **kwargs):
        """Handles posts requests for the message class. Will send an email to the target. Requires a JSON object"""
        data = json.loads(self.request.body)
        display_message = 'Could not send message'
        gift_exchange_participant = self.get_participant(*args, **kwargs)
        participant_key = gift_exchange_participant.key.urlsafe()
        gift_exchange_key = get_gift_exchange_key(_DEFAULT_GIFT_EXCHANGE_NAME)
        message_type = data['message_type']
        email_body = data['email_body']
        message = None
        if not email_body:
            display_message = 'Nothing to send'
        else:
            if message_type == 'target':
                target_participant = datamodel.GiftExchangeParticipant.get_participant_by_name(
                                                                                gift_exchange_key, 
                                                                                gift_exchange_participant.target,
                                                                                gift_exchange_participant.event_key)
                if target_participant.get_member().get_email_address() and target_participant.get_member().verified_email:
                    send_email_helper(target_participant.display_name, target_participant.get_member().get_email_address(), 'Your Secret Santa Has Sent You A Message', email_body, None)
                display_message = ''
                message = datamodel.GiftExchangeMessage.create_message(gift_exchange_key, gift_exchange_participant.key, _MESSAGE_TYPE_TO_TARGET, email_body)
            elif message_type == 'giver':
                giver = gift_exchange_participant.get_giver()
                display_message = ''
                if giver is not None:
                    if giver.get_member().get_email_address() and giver.get_member().verified_email:
                        send_email_helper(giver.display_name, giver.get_member().get_email_address(), gift_exchange_participant.display_name + ' Has Sent You A Message', email_body, None)
                message = datamodel.GiftExchangeMessage.create_message(gift_exchange_key, gift_exchange_participant.key, _MESSAGE_TYPE_TO_GIVER, email_body)
        return_value = {'message': display_message, 'gift_exchange_participant_key': participant_key}
        if message is not None:
            return_value['message_key'] = message.key.urlsafe()
            return_value['message_full'] = message.get_escaped_content()
            return_value['sender'] = bleach.clean(gift_exchange_participant.display_name)
            if message_type == 'target':
                return_value['recipient'] = bleach.clean(target_participant.display_name)
            elif message_type == 'giver':
                return_value['recipient'] = 'Santa'
            return_value['message_type'] = 'Sent'
            return_value['time'] = bleach.clean(message.get_formatted_time_sent())
            return_value['message_truncated'] = bleach.clean(message.content)[0:80]
        self.response.out.write(json.dumps((return_value)))


config = {
  'webapp2_extras.auth': {
    'user_model': 'datamodel.User',
    'user_attributes': ['name']
  },
  'webapp2_extras.sessions': {
    'secret_key': constants.SECRET_KEY
  }
}

app = webapp2.WSGIApplication([
    webapp2.Route('/', handler=LoginHandler, name='root'),
    webapp2.Route('/login', handler=LoginHandler, name='login'),
    webapp2.Route('/googlelogin', GoogleLoginHandler),
    webapp2.Route('/logout', handler=LogoutHandler, name='logout'),
    webapp2.Route('/signup', handler=SignupHandler, name='signup'),
    webapp2.Route('/<type:v|p>/<user_id:\d+>-<signup_token:.+>',
      handler=VerificationHandler, name='verification'),
    webapp2.Route('/password', SetPasswordHandler),
    webapp2.Route('/forgot', handler=ForgotPasswordHandler, name='forgot'),
    webapp2.Route('/link', GoogleLinkHandler),
    webapp2.Route('/main/<participant:.+>', handler=MainHandler, name='main'),
    webapp2.Route('/home', handler=HomeHandler, name='home'),
    webapp2.Route('/preferences', handler=PreferencesHandler, name='preferences'),
    webapp2.Route('/message/<participant:.+>', handler=MessageHandler),
    webapp2.Route('/update/<participant:.+>', handler=UpdateHandler),
    webapp2.Route('/unsubscribe', handler=UnsubscribeHandler, name="unsubscribe"),
    webapp2.Route('/assign/<participant:.+>', handler=AssignmentHandler)
], debug=False, config=config)

logging.getLogger().setLevel(logging.DEBUG)