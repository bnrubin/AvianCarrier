#!/usr/bin/env python
import cmd
from collections import deque, defaultdict
import logging
import itertools
from random import choice
import re
import sys

from twython import Twython, TwythonStreamer
import tweepy
from tweepy.streaming import StreamListener
from tweepy.utils import import_simplejson
json = import_simplejson()

from twisted.internet import reactor
from twisted.application import service
import urwid
import yaml


log = logging.getLogger('twitter')
log.setLevel(logging.DEBUG)
log.addHandler(logging.FileHandler('avian.log'))

palette = [
    (None, 'light gray', 'black'),
    ('error', 'light red', 'black'),
    ('bold', 'white', 'black'),
    ('meta', 'dark gray', 'black')]

random_palette = list(itertools.permutations(['0', '6', '8', 'a', 'd', 'f'], 3))

def getHashtags(text):
    return re.split(r'(#\w+|@\w+)', text)

class TagMap:
    def __init__(self):
        self.tags = defaultdict(randomColor)


    def get(self, tag):
        return self.tags[tag]


def _format(status, tagmap):
    nick = '@%s' % status.author.screen_name

    when = status.created_at.strftime('%d %b %X')
    meta = ' - %s - %s' % (when, status.source)

    output = [((tagmap.get(nick),nick)), ': ']
    for i in getHashtags(status.text):
        if len(i) > 0 and i[0] == '#':
            output.append((tagmap.get(i), i))
        elif len(i) > 0 and i[0] == '@':
            output.append((tagmap.get(i), i))
        else:
            output.append(i)
    output.append(('meta', meta))
    output.append('\n')

    return urwid.Text(output)

def randomColor():
    attr = urwid.AttrSpec('#%s%s%s' % choice(random_palette),'black',256)
    return attr

class CLIStream(tweepy.Stream):
    def __init__(self, auth, listener, async=True):
        super(CLIStream, self).__init__(auth, listener, async=True)


class CLIListener(TwythonStreamer):
    def __init__(self, view, c_key, c_secret, a_key, a_secret):
        self.view = view
        self.tagmap = TagMap()
        super(CLIListener, self).__init__(c_key, c_secret, a_key, a_secret)

    #def on_data(self, raw_data):
    #    data = json.loads(raw_data)
    #    if type(data) == int:
    #        return
    #    
    #    super(CLIListener, self).on_data(raw_data)

    def on_success(self, data):
        log.info(data)

    def on_status(self, status):
        self._announce(status, self.tagmap)

    def on_error(self, status):
        log.error('error: %s' % status, exc_info=True)

    def _announce(self, status, tagmap):
        widget = _format(status, tagmap)
        walker = self.view.walker
        walker.append(widget)
        size = len(walker)
        walker.set_focus(size-1)
        self.view.loop.draw_screen()
        return


class TweetEditor(urwid.Edit):
    def __init__(self):
        super(TweetEditor, self).__init__('$ ','')

class View(object):
    palette = [
        (None, 'light gray', 'black'),
        ('error', 'light red', 'black'),
        ('bold', 'white', 'black'),
        ('meta', 'dark gray', 'black')]

    random_palette = list(itertools.permutations(['0', '6', '8', 'a', 'd', 'f'], 3))

    def __init__(self):
        self.loop = None
        self.commands = TweetEditor()
        self.div = urwid.Divider()
        self.count = urwid.Text('140')
        self.pile = urwid.Columns([(4, self.count), self.commands])
        self.text = urwid.Text('')
        self.walker = urwid.SimpleFocusListWalker(deque([],2))
        self.listbox = urwid.ListBox(self.walker)
        self.fill = urwid.Frame(self.listbox)
        self.frame = urwid.Frame(self.fill, header=None, footer=self.pile,
                focus_part='footer')

        urwid.connect_signal(self.commands, 'change', self.on_command_change)
        
        self.get_tweets()


    def get_tweets(self):
        with open('avian.yaml') as y:
            config = yaml.load(y)
    
        self. stream = CLIListener(self,
                             config['consumer_key'],
                             config['consumer_secret'],
                             config['access_token'],
                             config['access_token_secret'])
        
        twitter = Twython(config['consumer_key'],
                          config['consumer_secret'],
                          config['access_token'],
                          config['access_token_secret'])
   
        reactor.callInThread(self.stream.statuses.filter, track='poop')
    
        

    def on_command_change(self, edit, new_text):
        limit = 140
        cnt = limit - len(new_text)
        if cnt < 0: 
            attr = 'error'
        else:
            attr = ''
        
        self.count.set_text((attr, str(cnt)))
    

class AvianCarrier(object):
    def __init__(self):
        self.view = View()

    def run(self):
        self.loop = urwid.MainLoop(self.view.frame,
                palette,unhandled_input=self.handle_input,
                event_loop=urwid.TwistedEventLoop())
        self.view.loop = self.loop
        self.loop.run()

    def handle_input(self, key):
        if key == 'enter':
            self.exit()


    

    def exit(self):
        try:
            reactor.callInThread(self.view.stream.disconnect)
        except Exception:
            pass
        raise urwid.ExitMainLoop()

if __name__ == '__main__':
    app = AvianCarrier()
    app.run()
