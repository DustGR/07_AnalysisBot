# Dependencies
import tweepy
import sys
import datetime
import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Import and Initialize Sentiment Analyzer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
analyzer = SentimentIntensityAnalyzer()
# Twitter API Keys
from config import twt_cmr_ak, twt_cmr_ak_s, twt_acc_tkn, twt_acc_tkn_s


# Setup Tweepy API Authentication
auth = tweepy.OAuthHandler(twt_cmr_ak, twt_cmr_ak_s)
auth.set_access_token(twt_acc_tkn, twt_acc_tkn_s)
api = tweepy.API(auth, parser=tweepy.parsers.JSONParser())

my_posts = ['1049024330636509184'] #This is my last tweet id before trying to deploy to Heroku
past_requests = {}  #This dictionary will later store keys as twitter handles for who has been analyzed, with values of the twitter ID where the analysis was posted.
#e.g. '@paizo' : '1049011716934098945'

'''PullTweets gets 500 tweets from target, returns them in a list'''
def PullTweets(target):  #Target should be a string that is a twitter user name
    x=1 #iteration counter - decided to use while instead of for loop because I thought it made exception handling easier
    tw_get = [] #blank list, will get filled with tweet json dictionaries
    while x < 6: #goes through 5 pages
        try:
            raw_get = api.user_timeline(target, page=x, count=100) #Gets a page of 100 tweets
            tw_get += raw_get #appends them to the existing tweets - has its own variable so we can count how many we got back from this page
            print('got page ' + str(x)) #just some flow control to keep track of what page has been pulled successfully
            if len(raw_get) <100 :#If the page had less than the max number of tweets, you can stop trying to pull more - you'll get empty results at best.
                print('ran out of tweets')
                break 
            x+=1 #iterate our loop
            
        except tweepy.RateLimitError: #if we hit rate limit, take a 15 minute break - then continue on the while loop.
            time.sleep(15 * 60) #Could have written 900 seconds, but I saw 15 * 60 in the Tweepy documentation and thought it was clearer
            print('Rate Limit Error')
    print('Pulled ' + str(len(tw_get)) + ' tweets.' )
    return tw_get #Sends the 0-500 tweets back in a list.

'''Runs a VADER analysis on passed tweet data, returns analysis as a dictionary'''
def AnalyzeTweets(data):
    output = {
        'com' : [],
        'id' : []}
    #In the past we've used 4 lists - one for each return by the VADER politary score function.  Our graph only uses one of these metrics.
    for tweet in data: 
        v_analysis = analyzer.polarity_scores(tweet['text'])
        output['com'].append(v_analysis['compound'])
        output['id'].append(tweet['id'])
    return output

'''Sort_Data will sort the passed VADER Dictionary into a dataframe and return a Dataframe sorted by ID'''
def SortData(sent):
    output_pd = pd.DataFrame({
        'Tweet ID' : sent['id'],
        'Compound' : sent['com'],
    })
    output_pd = output_pd.sort_values('Tweet ID') 
    #IDs are assigned chronologically, so sorting from lowest to highest lets us plot from earlier to later
    #We're only required to sort tweets relative to eachother, we don't need the date.
    return output_pd

'''Graph_Tweets takes the passed PD and returns a matplotlib figure of the analysis'''
def GraphTweets(df, target, figtitle):
    date=datetime.datetime.now().strftime('%m/%d, %Y')
    fig = plt.figure()
    x_axis = np.arange(len(df)*-1, 0)
    #Presumably this will usually return 0 to 500, but we'll use arange just in case we got fewer than 500 tweets back.
    plt.plot(x_axis, df['Compound'], color='slateblue', markersize=4, linewidth=0.5, marker = 'o')
    plt.xlabel('Tweets Ago')
    plt.ylabel('Tweet Polarity')
    plt.ylim(-1.1, 1.1)
    plt.xlim(-510, 10)
    plt.grid(alpha=0.5)
    plt.title(f'Sentiment Analysis of {target} on {date}')
    fig.savefig(figtitle)

'''Check_Feed checks my status since the last requests tweet ID and returns all tweets in one JSON'''
def CheckFeed():
    try:
        recent_tweets = api.mentions_timeline(since_id = my_posts[-1])
    except tweepy.RateLimitError:  #Recurses the function 15 minutes from now if I hit the rate limit
        time.sleep(15*60)
        Check_Feed()
    return recent_tweets   #Not sure how this performs with a huge tweet volume within 5 minutes

'''GetReqTag takes a tweet and returns the handle to analyze'''
def GetTargetTag(tweet):
    tag = '@' + tweet['entities']['user_mentions'][1]['screen_name'] 
                #Usually they want you to analyze the second mention, while the first (index 0) mention will be me.
        #add the tag to the list of things to examine
    return tag

'''GetCustTag takes a tweet and returns the handle of the person asking for the analysis'''
def GetCustTag(tweet):
    tag = '@' + tweet['entities']['user_mentions'][0]['screen_name']
    return tag
def GetReqID(tweet):
    reqID = tweet['id']

'''Sends the tweet with the graphic on it'''
def ReplyTweet(graph_path, target, customer, sentiment, request_id):
    tweettext = f'Analysis of {target}, as requested by {customer}.  Mean Compound Sentiment: {sentiment}'
    try:
        out = api.update_with_media(graph_path, tweettext, request_id)
        return str(out['id'])
    except tweepy.RateLimitError:  #Recurses the function 15 minutes from now if I hit the rate limit
        time.sleep(15*60)
        ReplyTweet(graph_path,target,customer,sentiment,request_id)

'''Replies when someone asks for a duplicate analysis.'''
def DirectToPrevious(customer_handle, target, request_id):
    previous_id = str(past_requests[target])
    tweettext = f'Hi, {customer_handle}, this as an old one:    https://twitter.com/DustinGR2/status/{previous_id}'
    try:
        api.update_status(tweettext, request_id)
    except tweepy.RateLimitError:  #Recurses the function 15 minutes from now if I hit the rate limit
        time.sleep(15*60)
        DirectToPrevious(customer_handle,target,request_id)
    except:
        pass

'''Coordinates other functions''' 
def HandleTweets(tweets):
    for tweet in tweets:
        request_id = tweet['id_str']  #Gets the tweet ID for this request
        customer_handle = '@' + tweet['user']['screen_name'] #Find the handle of the person tweeting at me
        if len(tweet['entities']['user_mentions']) > 1 and tweet['text'].lower().find('analyze') >=0: #This will leave the tweet alone if there is not more than one mention in it
            target = '@' + tweet['entities']['user_mentions'][1]['screen_name'] #gets the id of the target account - the second mention
            if target in past_requests:   #Check if this request has been made before
                DirectToPrevious(customer_handle, target, request_id)   #This function will tell the requesting person where the earlier graph is
            else:
                try:
                    tweets_to_analyze = PullTweets(target)    #Downloads tweets
                    analysis_df = SortData(AnalyzeTweets(tweets_to_analyze)) #does vader analysis and returns a dataframe
                    figtitle = datetime.datetime.now().strftime('%B_%Y') + target[1:] + '.png' #Builds a filename for the graph
                    GraphTweets(analysis_df, target, figtitle) #Creates the graph with the filename figtitle
                    sentiment = round(analysis_df['Compound'].mean(), 5) #Gets the mean sentiment to mention in the reply tweet
                    reply_id = ReplyTweet(figtitle, target, customer_handle, sentiment, request_id) # makes the reply tweet, and stores the tweet ID
                    past_requests[target] = reply_id   #This adds the reply's ID to the list of requests so it can be linked to people who request a repeat
                except:
                    print(sys.exc_info()[0]) #prints errors 

#The actual procedural part of the code, an infinite while loop with a 5 minute sleep timer.
while True:
    check = CheckFeed() 
    #Check status for new tweets
    if len(check) > 0:
        #If there are new tweets...
        my_posts.append(check[-1]['id_str'])   #appends the last tweet id to the end of the requests list, which is used on the Check_Feed
        HandleTweets(check)
        #HandleTweets will check for analysis tweets and make necessary replies
    time.sleep(5*60) #Wait 5 minutes and do it again!