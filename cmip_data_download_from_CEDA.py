#!/usr/bin/env python
# Qun Liu, contact via <liuqunxyz@gmail.com>
# Date: 2016-01-05
# Modified: 2016-03-20

from bs4 import BeautifulSoup
import urllib, urllib2
import os, sys

def loginCEDA(username,password):
    '''
    Login the CEDA website, use cookies and fillin the forms
    Return opener.
    Input Parameters:
        usrename: Your username for the account in the CEDA website, and you have to apply before.
        password: Your password for the account in the CEDA website.
    Output Value:
        opener: An opener that contains the cookies information to login the website
    '''
    loginURL = 'https://services.ceda.ac.uk/dj_security/account/signin/'
    cookieHandler = urllib2.HTTPCookieProcessor()
    opener = urllib2.build_opener( urllib2.HTTPSHandler(), cookieHandler )
    opener.addheaders = [('Referer', loginURL)]
    urllib2.install_opener(opener)
    loginPage = opener.open(loginURL)
    csrf_cookie = None
    for cookie in cookieHandler.cookiejar:
        if cookie.name == 'csrftoken':
            csrf_cookie = cookie
            break
    if not cookie:
        raise IOError("No csrf cookie found!")
    load = {'csrfmiddlewaretoken':csrf_cookie.value,
            'username':username,
            'password':password,
            'blogin':'Sign in'
            }
    postdata = urllib.urlencode(load)
    req = urllib2.Request(loginURL, postdata)
    try:
        resp = urllib2.urlopen(req)
    except urllib2.HTTPError, e:
        print e.fp.read()
    return opener

def getCMIPInstituteModelsDict(baseURL,cmipType):
    '''
    Get all the Institute and Models for CMIP5 or CMIP3 output, and the results are stored in a dictionary, where the key is the name of institute, and the value is a list of tuples of models belong to that institute and its url. 

    For example:
    {u'CCCma': [(u'CanAM4', u'http://browse.ceda.ac.uk/browse/badc/cmip5/data/cmip5/output1/CCCma/CanAM4'), (u'CanCM4', u'http://browse.ceda.ac.uk/browse/badc/cmip5/data/cmip5/output1/CCCma/CanCM4'), (u'CanESM2', u'http://browse.ceda.ac.uk/browse/badc/cmip5/data/cmip5/output1/CCCma/CanESM2')]}

    Input Parameters:
        baseURL:    the base URL to get the full path of the URL.
        cmipType:   'cmip3' or 'cmip5' to indicate which CMIP dataset to download 
    '''
    if cmipType == 'cmip5':
        url = 'http://browse.ceda.ac.uk/browse/badc/cmip5/data/cmip5/output1/'
    if cmipType == 'cmip3':
        url =  'http://browse.ceda.ac.uk/browse/badc/cmip3_drs/data/cmip3/output/'
    page = urllib2.urlopen(url).read()
    soup = BeautifulSoup(page, "html5lib")
    inst = [(a.string, baseURL+a['href']) for a in soup.find_all('table')[-1].find_all('a')]
    InstModelsDict = {}
    for item in inst:
        page = urllib2.urlopen(item[1]).read()
        soup = BeautifulSoup(page, "html5lib")
        models = [(a.string, baseURL+a['href']) for a in soup.find_all('table')[-1].find_all('a')]
        InstModelsDict[item[0]] = models
    return InstModelsDict

def getVarFileUrlsList(baseURL,varURL):
    try:
        page = urllib2.urlopen(varURL).read()
        soup = BeautifulSoup(page, "html5lib")
        td = soup.find_all('table')
        memberFileUrlsList = []
        if td != []:
            for td_i in td:
                memberFileUrlsList.extend([(a.string, baseURL+a['href']) for a in td_i.find_all('a') if '.nc' in a.string ])
            return memberFileUrlsList
        else:
            return None
    except urllib2.HTTPError, e:
        print e.fp.read()
        return None

def getCIMPModelFilesUrlsDict(baseURL, InstModelsDict, experimentType, memberType, varName):
    '''
    Get models and files dict.
    Note: Here we just support for the download of the monthly data, and the atmosphere ones. If you want to download other data such as the data in ocean or data in daily format, please modify the code by hand.
    Input Parameters:
        experiment: 'historical' or '20c3m' for historical run, cmip5 or cmip3; 'piControl' for pre-industrial control run
        memberType: rxiypz type for cmip5, such as 'r1i1p1', 'r2i1p1'; rx type for cmip3, such as 'r1', 'r2'
        varName: the variable to be download, such as 'ts' 'psl' and 'pr'
    '''
    modelFileUrlDict = {}
    for (inst, models) in InstModelsDict.items():
        for model in models:
            if 'cmip5' in model[1]:
                varURL = model[1]+'/'+experimentType+'/mon/atmos/Amon/'+memberType+'/'+varName+'/latest/'
            if 'cmip3' in model[1]:
                varURL = model[1]+'/'+experimentType+'/mon/atmos/'+varName+'/'+memberType+'/v1/'
            if len(model[0])<6 and 'CCSM' not in model[0]:
                modelKey = inst+'-'+model[0]
            else:
                modelKey = model[0]
            modelFileUrlDict[modelKey] = getVarFileUrlsList(baseURL,varURL)
    return modelFileUrlDict

def downloadVarFiles(opener, modelFileUrlDict, outDir):
    for (model, file_urls) in modelFileUrlDict.items():
        '''
         key of the dict is model name, and value of the dict is a list of the netCDF file names and the urls if it is not None.
         Example:
         {u'ACCESS1-0': None, u'ACCESS1-3': [(u'ts_Amon_ACCESS1-3_historical_r2i1p1_185001-200512.nc', 
         u'http://browse.ceda.ac.uk/browse/badc/cmip5/data/cmip5/output1/CSIRO-BOM/ACCESS1-3/historical/mon/atmos/Amon/r2i1p1/ ...
         latest/ts/ts_Amon_ACCESS1-3_historical_r2i1p1_185001-200512.nc')]}
        '''
        if file_urls != None:
            for item in file_urls:
                data = opener.open(item[1]).read()
                # Change name for cmip3
                tempName = item[0].split('_')
                tempName[2] = model
                temp = '_'.join(x for x in tempName) 
                with open(outDir+'/'+temp, "wb") as code:
                        code.write(data)

if __name__ == '__main__':
    if (len(sys.argv) != 6):
        print "Check your parameters!"
        print "Usage:"+sys.argv[0]+" cmipType experimentType varName memberType outDir"
        print "Example: "+sys.argv[0]+" 'cmip5' 'historical' 'ts' 'r1i1p1' './'"
        print "or Example: "+sys.argv[0]+" 'cmip3' '20c3m' 'ts' 'r1' './'"
        sys.exit()

    cmipType = sys.argv[1]
    experimentType = sys.argv[2]
    varName = sys.argv[3]
    memberType = sys.argv[4]
    outDir = sys.argv[5]

    opener = loginCEDA(username='<yourusername>',password='<yourpassword>') # change to your own username and password

    baseURL = 'http://browse.ceda.ac.uk'

    print 'Get institute and models dictionary...'
    InstModelsDict = getCMIPInstituteModelsDict(baseURL,cmipType)
    print 'Get files and their URLs dictionary...'
    modelFileUrlDict = getCIMPModelFilesUrlsDict(baseURL, InstModelsDict, experimentType, memberType, varName)
    f = file(varName+'_'+memberType+'.txt', 'w')
    f.write(str(modelFileUrlDict)) 
    f.close()
    print 'Begin download...'
    outDirectory = outDir + cmipType+'_'+experimentType+'_'+varName+'_'+memberType
    os.system('[[ ! -d '+outDirectory +' ]] && mkdir -p '+outDirectory)
    downloadVarFiles(opener, modelFileUrlDict, outDirectory) 
    print 'Download finished!'
