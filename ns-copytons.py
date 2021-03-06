#!/usr/bin/env python
#Automates the certificate renewal process for Netscaler via REST API and dehydrated (https://github.com/lukas2511/dehydrated)
#USE AT OWN RISK

#Imports
import json, requests, base64, sys, os, re
requests.packages.urllib3.disable_warnings()
#imports variables used for script
from mynsconfig import *

__author__ = "Ryan Butler (techdrabble.com)"
__license__ = "GPL"
__version__ = "2.1.1"
__maintainer__ = "Philip Cruz"

#what to perform
whattodo = sys.argv[1]

def getAuthCookie(connectiontype,nitroNSIP,nitroUser,nitroPass):
   url = '%s://%s/nitro/v1/config/login' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/vnd.com.citrix.netscaler.login+json'}
   json_string = {
       "login":{
       "username":nitroUser,
       "password":nitroPass,
       }
   }
   payload = json.dumps(json_string)
   try:
     response = requests.post(url, data=payload, headers=headers, verify=False, timeout=1.0)
     response.raise_for_status()      
   except requests.exceptions.RequestException as e:
     print e
     sys.exit(1)
   except requests.exceptions.HTTPError as err:
     print err
     sys.exit(1)
    
   cookie = response.cookies['NITRO_AUTH_TOKEN']
   nitroCookie = 'NITRO_AUTH_TOKEN=%s' % cookie
   return nitroCookie 
   
def logOut(connectiontype,nitroNSIP,authToken):
   url = '%s://%s/nitro/v1/config/logout' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/vnd.com.citrix.netscaler.logout+json','Cookie': authToken}
   json_string = {
       "logout":{}
   }
   payload = json.dumps(json_string)
   response = requests.post(url, data=payload, headers=headers, verify=False)
   print "LOGOUT: %s" % response.reason
   
def SaveNSConfig(connectiontype,nitroNSIP,authToken):
   url = '%s://%s/nitro/v1/config/nsconfig?action=save' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/json','Cookie': authToken}
   json_string = {
       "nsconfig":{}
   }
   payload = json.dumps(json_string)
   response = requests.post(url, data=payload, headers=headers, verify=False)
   print "SAVE NS: %s" % response.reason

def sendFile(connectiontype,nitroNSIP,authToken,nscert,localcert,nscertpath):
   url = '%s://%s/nitro/v1/config/systemfile' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/vnd.com.citrix.netscaler.systemfile+json','Cookie': authToken}
   f = open(localcert, 'r')
   filecontent = base64.b64encode(f.read())
   json_string = {
   "systemfile": {
       "filename": nscert,
       "filelocation": nscertpath,
       "filecontent":filecontent,
       "fileencoding": "BASE64",}
   }
   payload = json.dumps(json_string)
   response = requests.post(url, data=payload, headers=headers, verify=False)
   print "CREATING %s: %s" % (nscert, response.reason)

def EditrespPol(connectiontype,nitroNSIP,authToken,nsresppol,token_filename):
   url = '%s://%s/nitro/v1/config/responderpolicy' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/json','Cookie': authToken}
   buildrule = 'HTTP.REQ.URL.CONTAINS(\"well-known/acme-challenge/%s\")' % token_filename
   print buildrule
   json_string = {
   "responderpolicy": {
       "name": nsresppol,
       "rule": buildrule,}
   }
   payload = json.dumps(json_string)
   response = requests.put(url, data=payload, headers=headers, verify=False)
   print "EDIT RESPONDER POLICY: %s" % response.reason

def EditrespAct(connectiontype,nitroNSIP,authToken,nsrespact,token_value):
   url = '%s://%s/nitro/v1/config/responderaction' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/json','Cookie': authToken}
   buildtarget = "\"HTTP/1.0 200 OK\" +\"\\r\\n\\r\\n\" + \"%s\"" % token_value
   json_string = {
   "responderaction": {
       "name": nsrespact,
       "target": buildtarget,}
   }
   payload = json.dumps(json_string)
   response = requests.put(url, data=payload, headers=headers, verify=False)
   print "EDIT RESPONDER ACTION: %s" % response.reason

def removeFile(connectiontype,nitroNSIP,authToken,nscert,nscertpath):
   url = '%s://%s/nitro/v1/config/systemfile/%s?args=filelocation:%%2Fnsconfig%%2Fssl' % (connectiontype, nitroNSIP, nscert)
   headers = {'Content-type': 'application/vnd.com.citrix.netscaler.systemfile+json','Cookie': authToken}
   response = requests.delete(url, headers=headers, verify=False)
   print "DELETE NETSCALER CERTIFICATE: %s" % response.reason
   return response

def updateSSL(connectiontype,nitroNSIP,authToken, nscert, nspairname):
   url = '%s://%s/nitro/v1/config/sslcertkey?action=update' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/json','Cookie': authToken}
   json_string = {
   "sslcertkey": {
       "certkey": nspairname,
       "cert": nscert,
       "nodomaincheck": True,}
   }
   payload = json.dumps(json_string)
   response = requests.post(url, data=payload, headers=headers, verify=False)
   print "Update Netscaler CERT: %s" % response.reason

def createSSL(connectiontype,nitroNSIP,authToken, nscert, nspairname, nskey):
   url = '%s://%s/nitro/v1/config/sslcertkey' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/json','Cookie': authToken}
   json_string = {
   "sslcertkey": {
       "certkey": nspairname,
       "cert": nscert,
       "key": nskey,}
   }
   payload = json.dumps(json_string)
   response = requests.post(url, data=payload, headers=headers, verify=False)
   print "Create Netscaler CERT: %s" % response.reason

def GetSSL(connectiontype,nitroNSIP,authToken, nspairname):
   url = '%s://%s/nitro/v1/config/sslcertkey/%s' % (connectiontype, nitroNSIP, nspairname)
   headers = {'Cookie': authToken}
   response = requests.get(url,headers=headers, verify=False)
   return response.status_code

def createSSLCA(connectiontype,nitroNSIP,authToken,nscert,nspairname):
   url = '%s://%s/nitro/v1/config/sslcertkey' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/json','Cookie': authToken}
   json_string = {
   "sslcertkey": {
       "certkey": nspairname,
       "cert": nscert,}
   }
   payload = json.dumps(json_string)
   response = requests.post(url, data=payload, headers=headers, verify=False)
   print "Create Netscaler CA CERT: %s" % response.reason

def linkSSL(connectiontype,nitroNSIP,authToken, nschainname, nspairname):
   url = '%s://%s/nitro/v1/config/sslcertkey?action=link' % (connectiontype, nitroNSIP)
   headers = {'Content-type': 'application/json','Cookie': authToken}
   json_string = {
   "sslcertkey": {
       "certkey": nspairname,
       "linkcertkeyname": nschainname,}
   }
   payload = json.dumps(json_string)
   response = requests.post(url, data=payload, headers=headers, verify=False)
   print "Link Netscaler CERTS: %s" % response.reason

authToken = getAuthCookie(connectiontype,nitroNSIP,nitroUser,nitroPass)
if whattodo == "save":
   localcert = sys.argv[2]
   localkey = sys.argv[3]
   localchain = sys.argv[4]
   domain = sys.argv[5]
   m = re.search('(.+?)(?=\.)', domain[:23])
   nspairname = '%s-%s-pair' % (nspairname, m.group(0))
   nscert = '%s-%s-cert.pem' % (nscert, domain)
   nskey = '%s-%s-key.pem' % (nskey, domain)
   existcode = GetSSL(connectiontype,nitroNSIP,authToken, nspairname)
   if existcode == 200:
       print "Using existing cert"
       removeFile(connectiontype,nitroNSIP,authToken,nscert,nscertpath)
       sendFile(connectiontype,nitroNSIP,authToken,nscert,localcert,nscertpath)
       updateSSL(connectiontype,nitroNSIP,authToken, nscert, nspairname)
   else:
       print "Creating Netscaler Certificate"
       sendFile(connectiontype,nitroNSIP,authToken,nscert,localcert,nscertpath)
       sendFile(connectiontype,nitroNSIP,authToken,nskey,localkey,nscertpath)
       createSSL(connectiontype,nitroNSIP,authToken, nscert, nspairname, nskey)
       existchaincode = GetSSL(connectiontype,nitroNSIP,authToken, nschainname)
       if existchaincode == 200:
           print "Using existing CA"
       else:
           print "Creating CA"
           sendFile(connectiontype,nitroNSIP,authToken,nschain,localchain,nscertpath)
           createSSLCA(connectiontype,nitroNSIP,authToken, nschain, nschainname)
       linkSSL(connectiontype,nitroNSIP,authToken, nschainname, nspairname)
elif whattodo == "test":
   print "Connectivity To Netscaler OK"
elif whattodo == "challenge":
   token_filename = sys.argv[2]
   token_value = sys.argv[3]
   challenge_domain = sys.argv[4]
   domaincount = int(sys.argv[5])
   polname = '%s-%s' % (nsresppol, challenge_domain)
   actname = '%s-%s' % (nsrespact, challenge_domain)
   print "Creating Challenge Policy for %s" % challenge_domain
   EditrespPol(connectiontype,nitroNSIP,authToken,nsresppol,token_filename)
   EditrespAct(connectiontype,nitroNSIP,authToken,nsrespact,token_value)
elif whattodo == "saveconfig":
    print "Saving Netscaler Configuration"
    SaveNSConfig(connectiontype,nitroNSIP,authToken)
   
logOut(connectiontype,nitroNSIP,authToken)
