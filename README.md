# Social RSS

Social RSS is a web server that allows you to receive updates from your social network accounts via RSS.

For now it supports [VK](https://vk.com/) and [Twitter](https://twitter.com/) social networks.


## How to use

*Note: social-rss requires Python 3*

```sh
# Clone the source code
$ git clone https://github.com/KonishchevDmitry/social-rss.git
$ cd social-rss

# Install all requirements
$ sudo pip3 install -r requirements.txt

# Run the server
$ ./social-rss 8888
```

### VK RSS

*Attention: by using VK RSS you violate VK Terms of Service, so do this on your own risk!*

#### Obtaining access token

* Go to https://vk.com/editapp?act=create and create a standalone VK application.

* Go to https://oauth.vk.com/authorize?client_id=YOUR_APP_ID&scope=wall,friends,offline&response_type=code&redirect_uri=http://oauth.vk.com/blank.html and grant the requested permissions. You will be redirected to https://oauth.vk.com/blank.html#code=CODE.

* Go to https://oauth.vk.com/access_token?client_id=YOUR_APP_ID&client_secret=SECRET_KEY_OF_YOUR_APP&redirect_uri=http://oauth.vk.com/blank.html&code=CODE_OBTAINED_FROM_PREVIOUS_URL and save access_token from its response.

#### Getting RSS

Just type in browser ``http://:YOUR_ACCESS_TOKEN@localhost:8888/vk.rss`` or pass this URL to your favourite RSS reader (it must support [HTTP Basic Access Authentication](http://en.wikipedia.org/wiki/Basic_access_authentication)).


### Twitter RSS

#### Obtaining access token

Go to https://dev.twitter.com/apps/new and create an application (fill only required fields). You will be redirected to your application's page. Press "Create my access token" button on it.

#### Getting RSS

Just type in browser ``http://${CONSUMER_KEY}_${CONSUMER_SECRET}:${ACCESS_TOKEN}_${ACCESS_TOKEN_SECRET}@localhost:8888/twitter.rss`` or pass this URL to your favourite RSS reader (it must support [HTTP Basic Access Authentication](http://en.wikipedia.org/wiki/Basic_access_authentication)).
