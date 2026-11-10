with open('kodi_guisettings.xml', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('<setting id="services.webserver" default="true">false</setting>', '<setting id="services.webserver">true</setting>')
text = text.replace('<setting id="services.webserverauthentication" default="true">true</setting>', '<setting id="services.webserverauthentication">false</setting>')
text = text.replace('<setting id="addons.unknownsources" default="true">false</setting>', '<setting id="addons.unknownsources">true</setting>')

with open('kodi_guisettings.xml', 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated kodi_guisettings.xml!")
