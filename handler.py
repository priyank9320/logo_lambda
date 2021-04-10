import json
#import requests
import boto3
from boto3.dynamodb.conditions import Key
import random
import tldextract
from bs4 import BeautifulSoup
from googlesearch import search
import time
import re
from requests import Session # trying to create a session, might provide some improvement
requests = Session()
headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) '\
                         'AppleWebKit/537.36 (KHTML, like Gecko) '\
                         'Chrome/75.0.3770.80 Safari/537.36'}
# Add headers
requests.headers.update(headers)

lambda_counter=0 # GLOBAL VARIABLE TO DECIDE WHEN TO DISCARD THE LAMBDA INSTANCE

# google
def get_urls(tag, n, language,pause=2.0):
    urls = [url for url in search(tag, stop=n, lang=language, pause=pause)] #default pause is 2
    return urls

# build link
def link_build(k):
    if 'http'not in k:
        k='http://'+k #we dont need to add www in the url it works without that too
    return k


# google the website url if correction required
def link_corrector(input_url):
    ''' corrects the problems in top level domains by googling'''

    url_found=get_urls(input_url+' uk company website',1,'en')[0] # retrieves the first result of googling
    print('link corrector found this link:',url_found)
    if tldextract.extract(url_found).domain.lower()==tldextract.extract(input_url).domain.lower():
        print('match found on search engine')
        return url_found
    else:
        return input_url # return original if couldnt match domain on googled link

#link_corrector(input_url='datagardener')

# google facebook link (when scraping doesnt work)
def fb_google(url):
    facebook_ggl=''
    facebook_ggl = get_urls(f'{pattern_builder(url)} uk company facebook', 1 , 'en', pause=2.0)[0].lower()
    facebook_ggl = re.sub('\?.*', '', facebook_ggl)
    if 'facebook' == tldextract.extract(facebook_ggl).domain.lower():
        print('googled facebook link result: ',facebook_ggl)
        return facebook_ggl
    else:
        return '' 

    #print(facebook_ggl)
    #verify_fb(url,facebook_ggl) # verify the facebook link



def tw_google(url):
    twitter_ggl=''
    twitter_ggl = get_urls(f'{pattern_builder(url)} uk company twitter', 1 , 'en')[0].lower()
    twitter_ggl = re.sub('\?.*', '', twitter_ggl)
    if 'twitter' == tldextract.extract(twitter_ggl).domain.lower():
        print('googled twitter link result: ',twitter_ggl)
        return twitter_ggl

    else:
        return '' 

#tw_google('monzo.com')



def verify_tw(url,tw_url):
    verified=False
    verified_twitter_link=''
    html=''
    followers=''
    likes=''
    print(f'func: verify_tw, url:{url}, tw_url:{tw_url}')


    try:
        html=requests.get('http://webcache.googleusercontent.com/search?q=cache:'+ tw_url, timeout=4).text
        soup=BeautifulSoup(html, 'lxml')
        found_url=soup.findAll('a',{'class':'u-textUserColor', 'rel':'me nofollow noopener'}, href=True)[0]['title'] 
        print('found_url',found_url)       
        
        url_extract = tldextract.extract(url.lower())
        found_url_extract = tldextract.extract(found_url.lower())

        if url_extract.domain + url_extract.suffix == found_url_extract.domain + found_url_extract.suffix:
            verified=True
            verified_twitter_link=tw_url
            #verified_tw_link=tw_url # store the twitter url

            # # LOGO LINK: extract the logo link from the page
            # verified_logo_from_twitter=soup.findAll('img', {'class':'ProfileAvatar-image'})[0]['src'] # logo url 

            #followers
            followers=soup.findAll('span',{'class':'ProfileNav-value'})[2]['data-count'] # followers on twitter

            #likes
            likes=soup.findAll('span',{'class':'ProfileNav-value'})[3]['data-count'] # likes on twitter



            print('twitter link has been verified')
        else:
            verified_twitter_link=''
            print('domains didnt match for verification to be successful')
    except Exception as e:
        print('func: verify_tw, link not found:',e)
        pass
    

    return {
            'verified':verified,
            'twitter':verified_twitter_link,
            'html':html,
            'origin':'twitter',
            'followers':followers,
            'likes':likes

            }

#verify_tw(url='https://vector.ai/',tw_url='https://twitter.com/vectoraitrade')



# build the facebook about page
def about_page(fb_url):

    if '/pages/' not in fb_url:
        fb_url=re.sub('facebook.com\/','facebook.com/pg/',fb_url) #trying to add 'pg' as it is present in the about page url 
    
    fb_url=re.sub('\/$','',fb_url) #removes the '/' at the end if present
    fb_url=fb_url+'/about/?ref=page_internal' #final link for the about page
    #print(f'fb about page link generated: {fb_url}')
    return fb_url



# verify the facebook link by checking if the website link is attached in the About page
def verify_fb(url,page_url): # STATIC SRAPING IS SUFFICIENT FOR FB MOST OF THE TIMES
    #page_url=about_page(fb_url)
    #global logo_is_downloaded
    verified=False
    verified_facebook_link=''
    html=''
    try:
        html = requests.get(page_url, timeout=4).text # added a timeout of 4 seconds to avoid unnecessary waiting
        soup=BeautifulSoup(html,"lxml")
        lines = soup.findAll('a',{'rel':'nofollow'},href=True)
        #print(lines)
        for line in lines:
            print('checking line for website link in verify_fb: ',line.text)
            if '.' in line.text: # just a way to find which line might be a link, links usually have a slash '/'
                print('possible link for website checking in verify_fb',line.text)
                try:
                    #if 'http' not in line.text:
                    try: # here we try to capture any redirection but some companies dont let you get response from website
                        # so in except we still maintain the line retrieved and move on to check the doamin
                        finding_url=requests.get(link_build(line.text),timeout=4).url # HANDLES ANY REDIRECTS, CAPTURES THE LATEST URL
                    except:
                        finding_url=link_build(line.text)
                    #else: 
                    #    finding_url=line.text
                    print('printing url and finding_url: ',url,finding_url)
                    if tldextract.extract(url).domain.lower()+tldextract.extract(url).suffix.lower()==tldextract.extract(finding_url).domain.lower()+tldextract.extract(finding_url).suffix.lower():
                        print('found')
                        verified= True # domain matches!
                        verified_facebook_link=page_url
                        # download the logo as the page is verified
                        #logo_downloader(html) # downloads logo
                        #logo_is_downloaded=True
                        break

                    else:
                        verified=False
                        html=''
                        verified_facebook_link=''
                        print('domain did not match for verification')
                except Exception as e:
                    print(e,'link not found')
                    pass
        print('verify_fb loop ended')
    except Exception as e:
        print(e,'! couldnt reach the facebook about page !')
    
    return {
            'verified':verified,
            'facebook':verified_facebook_link,
            'html':html,
            'origin':'facebook'
            }

#verify_fb(url='https://monzo.com/',page_url='https://www.facebook.com/monzobank')


def simple_static_front(url): #url
    #global executed_the_url
    #global url
    html=''
    facebook=''
    twitter=''

    try:
        if '.' not in url: # Avoiding executing the url if the TLD is not provided as the url wont work
            raise Exception(' TLD seems to be missing in the provided url, skipping link_build, googling now')

        else :
            url=link_build(url)

        page=requests.get(url, timeout=4)
        html=page.text
        url=page.url # capture any redirected link of website
        executed_the_url=True

    except Exception as e:
        print(e)
        try:
            # now try with googled url
            print('using google link corrector')
            new_url=link_corrector(url)
            if new_url.lower()!=url.lower(): # avoid scraping if new link is not found after googling 
                url=new_url # save the googled url as the new url as the domain was verified 
                # and some websites wont let you run and get reponse back like tescoplc.com, so the below line might not run


                page=requests.get(new_url, timeout=4) 
                html=page.text
                url=page.url # SAVE THIS URL AS IT GOT EXECUTED
        except Exception as e:
            print('could not scrape:',e)
            html=''

    soup = BeautifulSoup(html,'lxml')
    for link in soup.find_all('a', href=True):
        if 'facebook' in link['href'] and not facebook:
            facebook=link['href'] # focussing on storing only 1 facebook related link from website
            print('facebook link found from simple_static_front: ',facebook)

        elif 'twitter' in link['href'] and not twitter:
            twitter=link['href']
            print('twitter link found from simple_static_front: ',twitter)

    return {
            'url':url, # this url contains any redirection occured in website link
            'twitter':twitter,
            'facebook':facebook
            }

#simple_static_front('https://www.multiverse.io/en-GB')


# download logo image
def logo_downloader(url,html,origin):
    #print('html: ',html)
    print('origin received: ',origin)

    logo_is_downloaded=False
    pattern=''
    local_logo_path=''

    try:

        if url:
            pattern=pattern_builder(url)
            print('input url or executed url  used for logo name: ',pattern)

            soup=BeautifulSoup(html,'lxml')
            print('Beautiful souped inside logo_downloader')

            if origin=='facebook':
                response=requests.get(soup.findAll('meta',{'property':'og:image'})[0]['content']) # gets facebook logo

            elif origin=='twitter':
                response=requests.get(soup.findAll('img', {'class':'ProfileAvatar-image'})[0]['src']) # gets twitter logo 

            print('logo was retrieved from internet')
            print('response in logo_downloader: ',response)
            local_logo_path='/tmp/'+pattern
            #local_logo_path='/content/'+pattern

            file = open(local_logo_path,"wb")
            file.write(response.content)
            file.close()
            print('Logo saved')
            logo_is_downloaded=True
        else:
            print('Url/Name to be used to save the logo is not found')


    except Exception as e:
        print('error in logo_downloader: ',e)
        path=''
 

    return {
            'logo_is_downloaded':logo_is_downloaded,
            'local_logo_path':local_logo_path
            }


# #testing code
# html=requests.get('http://webcache.googleusercontent.com/search?q=cache:https://twitter.com/monzo').text
# logo_downloader(url='https://monzo.com/',html=html,origin='twitter')



# this name/pattern will be used to save images for s3 objects, for eg: "example.com" 
def pattern_builder(input_received):

    extracted=tldextract.extract(input_received)

    if '.' in input_received:

        extracted=tldextract.extract(input_received)

        if extracted.suffix:
            pattern=extracted.domain+'.'+extracted.suffix
        else:
            pattern=extracted.domain
    else:
        pattern=input_received


    return pattern




# find s3 objects matching to a pattern
def searching_logos_with_pattern(input_received, bucket_name, my_region):
    #collector=[] # collects all the dictionaries of details for the objects found in the bucket
    s3client=boto3.client('s3') # EXPERIMENTING WITH METADATA OF S3 OBJECTS # DELETE IF UNSUCCESSFUL 

    list_of_logos=[]
    pattern=pattern_builder(input_received)
    print('pattern received: ',pattern)


    s3 = boto3.resource("s3")
    bucket=s3.Bucket(bucket_name)
    for obj in bucket.objects.filter(Prefix=pattern):
        
        print('printing obj:',obj)
        metadata=s3client.head_object(Bucket=bucket_name, Key=obj.key)
        print(metadata['Metadata'])
        metadata['Metadata']['object_link']='https://'+bucket.name+'.s3.'+my_region+'.amazonaws.com/'+obj.key
        list_of_logos.append(metadata['Metadata'])

 
    print('printing all the logo names found according to the prefix given', list_of_logos)
    return list_of_logos




def social_link_finder(url):
    ''' we here call the respective functions for twitter and facebook both (currently sequentially)
    the returned values from these two functions will be dictionaries
    then we after the values are recieved from both theses functions we 
    check which logo links are available and download one of them
    '''
    downloader_dict={'logo_is_downloaded':False, 'local_logo_path':''}
    ssf_dict={'url':'', 'facebook':'','twitter':''}
    vtw_dict={'twitter':'','verified':False,'html':''}
    vfb_dict={'facebook':'','verified':False,'html':''}

    url=url.lower() #this is the only input, just convert it into lower here itself

    # call simple_static_front only once and get the possible links
    ssf_dict=simple_static_front(url)# try static scraping

    if not tldextract.extract(ssf_dict['url']).suffix=='':
         
    

        # Facebook verification trials
        if ssf_dict['facebook']: # if facebook link is present from static scraping
            vfb_dict=verify_fb(ssf_dict['url'],ssf_dict['facebook']) # verify facebook received
            print('vfb_dict inside social_link_finder, decide to Google or not, value in dict: ',vfb_dict['verified'] )
        if not vfb_dict['verified']: # if facebook link not present yet OR if failed to be verified
            print('googling for facebook link')
            ssf_dict['facebook']=fb_google(ssf_dict['url']) #google facebook link
            vfb_dict=verify_fb(ssf_dict['url'],ssf_dict['facebook']) # verify facebook received

        print('vfb_dict ',vfb_dict['facebook'])

        # Twitter verificaion trials
        if ssf_dict['twitter']: # if twitter link is present from static scraping
            vtw_dict=verify_tw(ssf_dict['url'],ssf_dict['twitter']) # verify twitter received
            print('vtw_dict inside social_link_finder, decide to Google or not, value in dict: ',vtw_dict['verified'])
        if not vtw_dict['verified']: # if facebook link not present yet OR if failed to be verified
            print('googling for twitter link')
            ssf_dict['twitter']=tw_google(ssf_dict['url']) #google twitter link
            vtw_dict=verify_tw(ssf_dict['url'],ssf_dict['twitter']) # verify facebook received


        print('vtw_dict ',vtw_dict['twitter'])

        # which logo to download ?
        # try twitter logo, fall back to facebook logo
        if vtw_dict['verified']:
            downloader_dict=logo_downloader(url=ssf_dict['url'],html=vtw_dict['html'],origin='twitter')
        
        elif vfb_dict['verified'] and not downloader_dict['logo_is_downloaded']:
            downloader_dict=logo_downloader(url=ssf_dict['url'],html=vfb_dict['html'],origin='facebook')
        
        else:
            print('no logo possible from twitter or facebook, either no social links found or no logo attached on profile')
    
    
    else:
        print('Top Level Domain(TLD) was not resolved, aborting link finder. TLD is needed to be able to find the social media links with accuracy')

    return {
        'url': ssf_dict['url'],
        'twitter': vtw_dict['twitter'],
        'facebook': vfb_dict['facebook'],
        'logo_is_downloaded': downloader_dict['logo_is_downloaded'],
        'local_logo_path': downloader_dict['local_logo_path']
         }


#social_link_finder(url='whitehallfinance')

# HANDLER FUNCTION BELOW
def hello(event, context):
    s3 = boto3.resource('s3')

    list_of_logos=[]

    global lambda_counter
    lambda_counter+=1 # INCREMENT THE COUNT    

    logo_bucket_link=''
    origin=''
    logo_is_downloaded=False
    finder_dict={'url':'','facebook':'','twitter':'','logo_is_downloaded':''}

    start=time.time()
    bucket_name='' # provide here the name of the s3 bucket where logos are stored
    # get the region
    my_session = boto3.session.Session()
    my_region = my_session.region_name

    # print the PUBLIC IP ADDRESS !!
    public_ip_address=requests.get('https://checkip.amazonaws.com/').text
    print(public_ip_address)

    url=event['queryStringParameters']['url'].lower() # input url

    if 'social' not in event['queryStringParameters']:
   

        try: 
            list_of_logos=searching_logos_with_pattern(input_received=url, bucket_name=bucket_name, my_region=my_region) # SEARCH OBJECTS IN S3 BUCKET WITH PATTERN

            if not list_of_logos:
                raise Exception ('list of logos was returned empty, logo doesnt seem to exist, scraping logo now')

        except Exception as e:
            print('Error in Loading the data from s3 ',e)
            
            try:
                # MAIN FUNCTION which calls all other functions, downloads the logo
                finder_dict = social_link_finder(url) #url
            except Exception as e:
                print('error in social_link_finder: ',e)
                pass

    else:
        social=event['queryStringParameters']['social'].lower()
        print('social media link received: ',social)
        finder_dict['url']=url # save the url

        origin=tldextract.extract(social).domain
        finder_dict[origin]=social #save the social media link

        if origin=='twitter':
            social='http://webcache.googleusercontent.com/search?q=cache:'+social
        elif origin=='facebook':
            pass
        print('social media modified: ',social)
        html=requests.get(social,timeout=4).text
        finder_dict={**finder_dict, **logo_downloader(url=url,html=html,origin=origin)} # merging dictioanries, second dict has precedence over values
        #finder_dict[origin]=social #save the social media link


    # SAVE the logo with metadata in s3 bucket
    if finder_dict['logo_is_downloaded']: # execute this block of code only if logo has been downloaded
        # try:
        pattern=pattern_builder(finder_dict['url'])

        s3.Bucket(bucket_name).upload_file(finder_dict['local_logo_path'], pattern+'.logo', ExtraArgs={"Metadata": {"url":finder_dict['url'],"twitter":finder_dict['twitter'],"facebook":finder_dict['facebook'] }} )
        logo_bucket_link='https://'+bucket_name+'.s3.'+my_region+'.amazonaws.com/'+pattern+'.logo'  
        print('image stored')



    # CHECK COUNTER AND DISCARD THE INSTANCE WHEN REACHED 5 EXECUTIONS
    if lambda_counter>=5:
        # Change the code so that we force cold start every time, this provides us with new IP address each time 
        # (confirmed for one active function at a time)
        n = random.randrange(100, 200)
        client = boto3.client('lambda')
        client.update_function_configuration( # response = 
        FunctionName='explambda-dev-hello',
        Timeout=n)

    total_time=time.time()-start # total time taken to perform the operation

        

    body = {
        "public_ip_address": public_ip_address,
        # "url": finder_dict['url'],
        # "facebook": finder_dict['facebook'],
        # "twitter": finder_dict['twitter'],
        "time_taken_seconds": total_time,
        "lambda_counter": lambda_counter,
        "list_of_logos":[]
    }

 

    if finder_dict['logo_is_downloaded']:
        body['list_of_logos'].append({'object_link':logo_bucket_link, "url": finder_dict['url'], "twitter": finder_dict['twitter'], "facebook": finder_dict['facebook'] })

    if list_of_logos:
        body['list_of_logos'].extend(list_of_logos)

    response = {
        "statusCode": 200,
        "body": json.dumps(body)
    }


    print('----------reached the end of the funtion, returning result now ----------------')
    return response



