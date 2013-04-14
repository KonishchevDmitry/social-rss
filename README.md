# Social RSS

Social RSS is a web server that allows you to receive updates from your social network accounts via RSS.

For now it supports only [VK](https://vk.com/) social network.


## How to use

```sh
# Clone the source code
$ git clone git@github.com:KonishchevDmitry/social-rss.git
$ git submodule init
$ git submodule update

# Run the server (requires Python 3 and Tornado web framework)
$ social-rss/social-rss 8888
```


### VK RSS

*Attention: by using VK RSS you violate VK Terms of Service, so do this on your own risk!*

#### Obtaining access_token

* Go to https://vk.com/editapp?act=create and create a standalone VK application.

* Go to https://oauth.vk.com/authorize?client_id=YOUR_APP_ID&scope=wall,friends,offline&response_type=code&redirect_uri=http://oauth.vk.com/blank.html and grant the requested permissions. You will be redirected to https://oauth.vk.com/blank.html#code=CODE.

* Go to https://oauth.vk.com/access_token?client_id=YOUR_APP_ID&client_secret=SECRET_KEY_OF_YOUR_APP&redirect_uri=http://oauth.vk.com/blank.html&code=CODE_OBTAINED_FROM_PREVIOUS_URL and save access_token from its response.

#### Getting RSS

Just type in browser ``http://:YOUR_ACCESS_TOKEN@localhost:8888/vk.rss`` or pass this URL to your favourite RSS reader (it must support [HTTP Basic Access Authentication](http://en.wikipedia.org/wiki/Basic_access_authentication)).
