import re

from time import strftime, localtime
from datetime import datetime, timezone

import logging as logme
from googletransx import Translator
# ref. 
# - https://github.com/x0rzkov/py-googletrans#basic-usage
translator = Translator()


class tweet:
    """Define Tweet class
    """
    type = "tweet"

    def __init__(self):
        pass


def utc_to_local(utc_dt):
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(tz=None)


Tweet_formats = {
    'datetime': '%Y-%m-%d %H:%M:%S %Z',
    'datestamp': '%Y-%m-%d',
    'timestamp': '%H:%M:%S'
}


def _get_mentions(tw):
    """Extract mentions from tweet
    """
    logme.debug(__name__ + ':get_mentions')
    try:
        mentions = [
            {
                'screen_name': _mention['screen_name'],
                'name': _mention['name'],
                'id': _mention['id_str'],
            } for _mention in tw['entities']['user_mentions']
            if tw['display_text_range'][0] < _mention['indices'][0]
        ]
    except KeyError:
        mentions = []
    return mentions


def _get_reply_to(tw):
    try:
        reply_to = [
            {
                'screen_name': _mention['screen_name'],
                'name': _mention['name'],
                'id': _mention['id_str'],
            } for _mention in tw['entities']['user_mentions']
            if tw['display_text_range'][0] > _mention['indices'][1]
        ]
    except KeyError:
        reply_to = []
    return reply_to


def getText(tw):
    """Replace some text
    """
    logme.debug(__name__ + ':getText')
    text = tw['full_text']
    text = text.replace("http", " http")
    text = text.replace("pic.twitter", " pic.twitter")
    text = text.replace("\n", " ")

    return text


def Tweet(tw, config):
    """Create Tweet object
    """
    logme.debug(__name__ + ':Tweet')
    t = tweet()
    t.id = int(tw['id_str'])
    t.id_str = tw["id_str"]
    t.conversation_id = tw["conversation_id_str"]

    # parsing date to user-friendly format
    _dt = tw['created_at']
    _dt = datetime.strptime(_dt, '%a %b %d %H:%M:%S %z %Y')
    _dt = utc_to_local(_dt)
    t.datetime = str(_dt.strftime(Tweet_formats['datetime']))
    # date is of the format year,
    t.datestamp = _dt.strftime(Tweet_formats['datestamp'])
    t.timestamp = _dt.strftime(Tweet_formats['timestamp'])
    
    t.user_id = int(tw["user_id_str"])
    t.user_id_str = tw["user_id_str"]
    t.username = tw["user_data"]['screen_name']
    t.name = tw["user_data"]['name']
    t.user_location = tw["user_data"]['location']
    t.user_description = tw["user_data"]['description']
    t.user_url = f"https://twitter.com/{t.username}"

    try:
        if('name' in tw['place']):
            t.place_type = tw['place']['place_type']
            t.place_name = tw['place']['name']
            t.place_full_name = tw['place']['full_name']
            t.place_country_code = tw['place']['country_code']
            t.place_country = tw['place']['country']
            t.place_bounding_box = tw['place']['bounding_box']

    except:
        t.place_type = ""
        t.place_name = ""
        t.place_full_name = ""
        t.place_country_code = ""
        t.place_country = ""
        t.place_bounding_box = ""

    t.coordinates = tw['coordinates'] if 'coordinates' in tw and tw['coordinates'] else ""
    t.geocode = tw['geo'] if 'geo' in tw and tw['geo'] else ""
    t.source = re.findall('<a[^>]*>([^<]+)<\/a>', tw['source'])[0]

    t.timezone = strftime("%z", localtime())
    t.mentions = _get_mentions(tw)
    t.reply_to = _get_reply_to(tw)
    try:
        t.urls = [_url['expanded_url'] for _url in tw['entities']['urls']]
    except KeyError:
        t.urls = []
    try:
        t.photos = [_img['media_url_https'] for _img in tw['entities']['media'] if _img['type'] == 'photo' and
                    _img['expanded_url'].find('/photo/') != -1]
    except KeyError:
        t.photos = []
    try:
        t.video = 1 if len(tw['extended_entities']['media']) else 0
    except KeyError:
        t.video = 0
    try:
        t.thumbnail = tw['extended_entities']['media'][0]['media_url_https']
    except KeyError:
        t.thumbnail = ''
    t.tweet = getText(tw)
    t.lang = tw['lang']
    try:
        t.hashtags = [hashtag['text'] for hashtag in tw['entities']['hashtags']]
    except KeyError:
        t.hashtags = []
    try:
        t.cashtags = [cashtag['text'] for cashtag in tw['entities']['symbols']]
    except KeyError:
        t.cashtags = []
    t.replies_count = tw['reply_count']
    t.retweets_count = tw['retweet_count']
    t.quote_count = tw['quote_count']
    t.likes_count = tw['favorite_count']
    t.link = f"https://twitter.com/{t.username}/status/{t.id}"
    try:
        if 'user_rt_id' in tw['retweet_data']:
            t.retweet = True
            t.retweet_id = tw['retweet_data']['retweet_id']
            t.retweet_date = tw['retweet_data']['retweet_date']
            t.user_rt = tw['retweet_data']['user_rt']
            t.user_rt_id = tw['retweet_data']['user_rt_id']
    except KeyError:
        t.retweet = False
        t.retweet_id = ''
        t.retweet_date = ''
        t.user_rt = ''
        t.user_rt_id = ''

    
    try:
        t.is_quote_status = tw["is_quote_status"]
        t.quoted_status_id = tw["quoted_status_id_str"]    
        t.quote_url = tw['quoted_status_permalink']['expanded'] if tw['is_quote_status'] else ''
    except:
        t.is_quote_status = False
        t.quoted_status_id = ""
        # means that the quoted tweet have been deleted
        t.quote_url = ""

    t.near = config.Near if config.Near else ""
    t.geo = config.Geo if config.Geo else ""
    
    t.translate = ''
    t.trans_src = ''
    t.trans_dest = ''
    if config.Translate:
        try:
            ts = translator.translate(text=t.tweet, dest=config.TranslateDest)
            t.translate = ts.text
            t.trans_src = ts.src
            t.trans_dest = ts.dest
        # ref. https://github.com/SuniTheFish/ChainTranslator/blob/master/ChainTranslator/__main__.py#L31
        except ValueError as e:
            logme.debug(__name__ + ':Tweet:translator.translate:' + str(e))
            raise Exception("Invalid destination language: {} / Tweet: {}".format(config.TranslateDest, t.tweet))
    return t
