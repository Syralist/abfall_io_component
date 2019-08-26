# abfall_io_component
Custom Home Assistant Component for accessing abfall.io API.

If you found this repository, chances are you already know your waste collection company uses the abfall.io API.

Be aware that this not a plug and play component. Some fiddeling is required to get it to work for different waste companies and adresses.

## How to install and use
Copy the files from the custom_components folder to your Home Assistant config-folder.

Change the values in the payload to match your adress.
To find the correct values I used the development tools in Chrome to look at the sourcecode on the waste collection website.

You might also need to change the names of the different waste types. For example _Hausmüll_ might be called _Restmüll_ in your case.

## Acknowledgements
I found this code on [Tom Beyers Blog](https://beyer-tom.de/blog/2018/11/home-assistant-integration-abfall-io-waste-collection-dates/).
There is also a thread on the [Home Assiantant Forum](https://community.home-assistant.io/t/home-assistant-integration-of-abfall-io-waste-collection-dates-schedule/80160).