import json

# The service account key content (extracted from the broken file)
# We'll write it fresh as proper JSON
creds = {
    "type": "service_account",
    "project_id": "jarvis-be47a",
    "private_key_id": "c87a300e12455cae5af392e84ad5fbcb720864e1",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQD/AAbH/uF90rko
Zjcv1McBVbHBdv8zKfSAZ5493XbehmDI5wynGwt+S3tlQyEvQ0RcD7+fUsUJan7t
8u9bQ17WkGVoknmf3O3zsNOJURDkuXmzV3ZDXSTkDb6uR4GJqfToGho2Tax4R4pc
yGGILuV4GDH7/3SQcOAaNLxXumg/ibTjh5ivDx5DB2+goDeC5Wqef3hY5JGsk3cT
TrDHD8PzQPu3L9GKLIF78ngJE8BfDMhdcHt6Zd0ZVcg0NHR2nu8Fvv0K1GwXBBuI
1jHOiKMUUG5l484H7EBOK3V5LljPuX82o5xbkgdJu5s/s4H6uhZLzkmMvoUXa7vm
PJVDkPTpAgMBAAECggEAY1zeR5YQxZeT4KMbw/6UYPfEYQ9+V7B0fohhx9eBFyqj
kgU+D+tg6iB9f7LNvn3mqDzWvT1iW83skcnE7PnufYsciMfyrpFHA1sWwn4dKBMB
0hk1kwA7fMXCVGS2nC7mqH5rUlen6eJujsLiBk/HyKkc6QXcpN/m4y9DaKfRMVgv
TvxHZGUIdHDHFykieCwugLM/k7RV1Pi4pBmV4DUS7kFsfhnakxviUeQdTHUkSZVX
IjUvaQlsikNeAlI9uPCzTUALBCiXyrcXTSe2eGuktG9dzbZBH5sBU7+SQK3Piv6V
wMJtPKSgHAWmGj53EM0meJvKVc3CibhzRKB0KzPF1QKBgQD/y5Kw9Vi1jcXIPT//
LPc17s7PHsZktEom2LVhxUYYhpvnRNVzhHAVt2XdNwa+n9Ac2XK79kQ0zNK+OZ5j
91j1lxRLgGiuszmUAltKa8a/gjOIp/hqoyU5j5uut/jcVjJZp6mlEBaW1/iJnJRz
OsPsvSy9zrxD+aHtnFnXQXxJ9wKBgQD/NEpfKaI7Gd8qiqPmeyz2p6H7bgbIYRa5
B1IF/9fu7+80bh5+QIlAMVpHbfhZOZyjlKEDguFLEpSKETMHwPsWbyT96BhlK2xw
C4mS3c8eySM4eYVEwnoMLiMhBjz48WbR1sqW5Zzk39r3aeo0VvYE7e7WLfF9XBye
po56FZwAHwKBgEpudCrl2YBK1qhjmkGoVe7tpGQEcnpPM9yF5pGik7kDQk5Ta0EH
4o2PJibuohnJ6wbaB1bGXCZ5C0GrBnnUOaCM66zkmpFrOW/mF6ZaIiULv+8d4V02
R9it/wEiK1oCAvivnt+XBNuz0HBKja/SA7zZdzFr/MBS3VmEy2eleIMVAoGBALOZ
70UtnbiOKppb26EWyrwDmWHDOw7GFSG+XyFNvn+vZ960KM2dSXpdwTVH1WGlw/Dz
ZqV79GXK+7J3DDzGuW4+ZgAy2QhKGRR5aiZr55m44AqcqweK/i2YQqy5ISvpZ/0B
dq3fhh0k1YsNhP+0u4sYj983kh4xNwsIGHkewBztAoGBAI/1ve9X8LETwlbGEW7f
gcpJdZNfXKeBb/ql/+9yJuw9djBqwpTUCPtLGTPfqeyOWz+/r3NL6QJ4sxIvLpnh
Zy0BU4VoKgG14h2TfIS2k3Qhk05sZh2c4WkRKOeJbQdIkoJYT6HutZtNk31G+xag
iC2YTM3MAgGL1lyQRaJlItQm
-----END PRIVATE KEY-----
""",
    "client_email": "firebase-adminsdk-fbsvc@jarvis-be47a.iam.gserviceaccount.com",
    "client_id": "115850011912399794688",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40jarvis-be47a.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

# Write proper JSON
with open('serviceAccountKey.json', 'w', encoding='utf-8') as f:
    json.dump(creds, f, indent=2, ensure_ascii=False)

print("Fixed serviceAccountKey.json")
print(f"Project: {creds['project_id']}")
print(f"Client: {creds['client_email']}")
