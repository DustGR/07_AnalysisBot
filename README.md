# 07_AnalysisBot
Twitter Sentiment Analysis bot using VADER and MatPlotLib libraries
Checks Twitter Account @DustinGR2 every 5 minutes.  If a tweet is sent saying Analyze: @TwitterID, it analyzes the twitter ID.
Specifically, it should analyze the second mention on any tweet that contains the word 'analyze'

It generates a graph in MatPlotLib and sends it in a twitter reply.
If a repeat analysis request is sent, it directs the person to the original post in which that account was analyzed.
