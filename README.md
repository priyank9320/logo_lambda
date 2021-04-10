# logo_lambda
Find companies' twitter and facebook page, scrape logos and store in S3 bucket. Also provides the ability to query the logos using domain names or a prefix.

Serverless Framework was used to deploy the AWS Lambda functions and AWS API Gateway was used to build a REST API using the deployed Lambda function.

# Files provided : 

`handler.py` : Contains all the code required to run this. Used in AWS Lambda function.

`serverless.yml` : Contains the yaml file used in Serverless Framework, which was used to deploy the AWS Lambda function.

`requirements.txt`: Contains all the dependencies that needs to be installed. The Serverless Framework uses this file along with the plugin  "serverless-python-requirements"  to automatically handle the installation.

In the API gateway set two "URL Query String Parameters" : `url` and `social` . These are passed in the `event` that the Lambda receives and will contain the input provided  by the user for these two fields.

# Problem Statement:

There are several companies like Crunchbase, Beauhurst, Craft.co, etc which maintain profiles of companies and collect information from several resources and consolidate it in their profile page. 

Such information also includes company logo, and social media links like Facebook and Twitter link. 

Identifying the logo image from the company website is a difficult problem and therefore sources like social media account seems to be the most suitable place to pick the company logos. But scraping social media websites is very difficult because the websites start blocking the requests if you hit it multiple times in a short period of time.

Another problem is to find the Facebook and Twitter links automatically. This is also an important information and also without these links you cannot scrape the logo. Some companies attach their social media account links on their websites but some companies don't, even when they have an account. Finding the social media accounts on the basis of just name of the companies is very difficult as this companies might use some variations of their names (like short forms). 

There are thousands of companies/websites for which this needs to be done and so we need to do scraping for the companies parallely. 

Since there can be a huge number of companies in the platform and doing web scraping for all of them might waste a lot of computation and time as many of those companies user will not be visiting. An on-demand solution was required to scrape only for those companies which the users are visiting.



# Proposed Solution:

I built a serverless API, using AWS Lambda and AWS API Gateway to this problem.

Each AWS Lambda function gets a different Public IP address assigned, so scraping social media websites using Lambda becomes much easier as now you will not be using the same IP address to perform the scraping. The only problem remains is to avoid using the same instance again and again, and for this the code maintains a global variable `lambda_counter` and records the number of times the function has been executed, once the count reaches a set values (in my code set to 5), the code makes a configuration change in the Lambda code which forces a `cold-start` of the Lambda instance. As a result you get a new public IP address after every 'n' executions. In my code I am changing the timeout, doesn't have any bad effect as the function only runs for the amount of time it requires to complete its execution and the timeout is set to large enough to let the entire code run.

Services like AWS Fargate could also be used, but Lambda Functions are faster in terms of initialization and thus a better choice for this (AWS EC2 instances are the slowest option, and would be very slow to discard and provision after every 'n' executions).

Since the IP address related problem is now resolved we can proceed with the scraping of social media websites. 

For finding the social media links, we can try scraping the company websites and also try googling it through code. But the problem is that by using just names we cannot say for sure if a particular social media link belongs to a particular company. To tackle this problem, the code tries to check if the website link is attached on the social media profile for which the link was found. If the company website link is present on the profile we can be confident that it belongs to the company. 

Since we are using just `requests` and `BeautifulSoup` libraries for scraping, pages which need a browser (Javascript engine) to perform web scraping becomes problematic. For example, scraping Twitter requires a headless browser with Selenium or Scrapy with Splash. To tackle the problem of scraping Twitter I have used the Googles webcache to get the Twitter data. These caches are loaded as static HTML and therefore doesn't require a browser to load. Since logo and social media links are the type of information which doesn't change with time very frequently, we can easily get the information from the caches. 

To visit the Google's webcache of any twitter profile, just add the prefix " http://webcache.googleusercontent.com/search?q=cache:" to your full twitter link.

Facebook loads enough information statically if you just want the logo and website url from the profile, and therefore we don't need a cache in this case.

Once the logo is scraped it is stored in an S3 bucket (which you can make public if required), and the object link is returned as a response to the API call. Once the logo is in your bucket you can retrieve it as many times as you want. The code is built such that when the user provides a company domain name, the code first tries to fetch it in the bucket and only if it is not found then it tries to scrape. This avoids unnecessary hitting of the social media servers and reduces the latency if the logo is already present in the bucket.

The social media links that were scraped are stored in the metadata of the logo (S3 Object's metadata ). So when when the logo is retrieved from the bucket the social media links are also returned with it and we avoid maintaining a separate database just for storing the social media links corresponding to the logo.

The logos saved use the website name as their name, for example : www.example.com , this websites logo will be saved as `example.com.logo` . This was done to avoid ambiguity because some websites have the same domain name and differ only in the Top Level Domain name (TLD).



# Short description of the algorithm:

The API endpoint looks something like this:

https:xxxxxxxxx.execute-api.eu-west-2.amazonaws.com/development/logo?url=https://example.com

Alternately you can force the API to skip the social media links finding part of the code and by directly providing the social media link along with the website url (website url is then just used to for deciding the name of the logo). The API endpoint looks like this in this scenario:

https:xxxxxxxxx.execute-api.eu-west-2.amazonaws.com/development/logo?url=https://example.com&social=https://twitter.com/example

Below is short description of the flow of the code:

1. The user provides either the full url of a company website or just a starting prefix.
2. The code tries to fetch the logo in the S3 bucket. If it is not found then the web scraping will be done to retrieve the logo.
3. if only the domain name is provided the code tries to fix the Top Level Domain (TLD) by googling the domain and finding the best match available.
4. Once the TLD is fixed, the code tries to scrape the social media links from the company website if possible. 
5. If the social media links are not found on the website, the code tries to fetch it on google (picks just the top result of googling)
6. Once the links are found, the code tries to find the website link on the profile page.
7. If the website links are found, we can say the we have accurately located the profile and the logo is scraped from the profile. For logo scraping first Twitter profile is tried if that is not present, then Facebook profile is tried.
8. Logo is then saved in the S3 bucket and the social media links are saved in its metadata.
9. Next time if the user tries to retrieve the logo of the same company again, it is retrieved from the bucket instead of web scraping and is returned in a fraction of a second (web scraping can take around 10 seconds to complete the full process)
10. Alternately if the `social` parameter is provided with the social media link, the code directly tries to pick the logo from that profile and save it in the bucket.



The output of the API is a json response with list a of S3 object links for the logos that were found for the users request along with the social media links that were stored in their metadata.

Example of the output :

{"public_ip_address": "18.133.193.82", "time_taken_seconds": 0.6703431606292725, "lambda_counter": 1, "list_of_logos": [{"url": "https://example.com/", "facebook": "", "twitter": "https://twitter.com/examplecompany", "object_link": "https://xxxxx.s3.eu-west-2.amazonaws.com/example.com.logo"}]}



# Existing issues:

1. The code can somehow still get blocked if you over-do scraping.
2. I have used a free Google SERP scraping library and this is problematic because it starts throwing `too many requests` error after a while or if you start hitting their servers too many times in a short interval. In one scenario the requests started getting blocked even though the code was changing the IP addresses after every 5 requests. Try using the paid programmatic access to the search engine.
3. Speed issues are there, it can sometimes take around 10+ seconds to perform the entire scraping. This happens because the code is sending several requests to different servers, and it depends on the servers how much time they take to respond back (some websites don't give back the response once they detect the bot and thus I have used 4 second timeouts for those scenarios, which still wastes a lot of time). Solution is to modify the code to perform the scraping of twitter and facebook parallely using multiple threads (but in this scenario you will have to use paid programmatic access to google search engine, because the free version might start throwing the 429 error if the two threads send request to google servers simultaneously.)

