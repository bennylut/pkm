from pkm.api.pkm import pkm

http = pkm.httpclient
with http.get('https://download.pytorch.org/whl/torch/', headers={'server':'download.pytorch.org'}) as resonse:
    print(resonse)