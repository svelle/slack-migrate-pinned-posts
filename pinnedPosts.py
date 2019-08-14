#!/bin/python3

import json
import zipfile
import psycopg2
import mysql.connector
import requests
import argparse
import yaml

channelTypes = ["dms.json", "groups.json", "mpims.json", "channels.json"]


parser = argparse.ArgumentParser(
    prog='Mark posts as pinned', description='Tries to mark all pinned posts from a slack export file in the import MM instance as pinned post as well.\n Modify args.yaml to fit your env.')
parser.add_argument('--configfile', type=bool,
                    help='load arguments from args.yaml file (Default: True !)', default=True)
parser.add_argument('--dbdriver', type=str,
                    help='Name of the Database driver. Valid values: psql or mysql (default: mysql)', default="mysql")
parser.add_argument('--dbport', type=str,
                    help='port for the db (default: 3306)', default="3306")
parser.add_argument('--dbhost', type=str,
                    help='Host of the Mattermost Database (default: localhost)', default="localhost")
parser.add_argument('--dbpass', type=str,
                    help='Name of the Mattermost Database pass (default: mostest)', default="mostest")
parser.add_argument('--dbuser', type=str,
                    help='Name of the Mattermost Database user (default: mmuser)', default="mmuser")
parser.add_argument('--dbname', type=str,
                    help='Name of the Mattermost Database (default: mattermost_test)', default="mattermost_test")
parser.add_argument('--zipfile', type=str,
                    help='Name of the slack export zipfile')
parser.add_argument('--mmurl', type=str,
                    help='URL of the Mattermost Server (default: http://localhost:8065)', default="http://localhost:8065")
parser.add_argument('--token', type=str,
                    help='Authentication token for the admin user to pin the posts')
parser.add_argument('--dry-run', type=bool,
                    help='Get all posts without running the api calls')
args = parser.parse_args()

if args.configfile:
    f = open("args.yaml", "r")
    yaml = yaml.load(f.read(), Loader=yaml.FullLoader)


def loadZip(zipName):
    archive = zipfile.ZipFile(zipName, 'r')
    jsonFiles = {}
    for channelType in channelTypes:
        try:
            jsonFiles[channelType] = archive.open(channelType)
            print("Found " + channelType + " in archive. Adding.")
        except:
            print("Warning: Couldn't find " + channelType + " in archive. Skipping.")
    return jsonFiles


def getPostTimestamps(channelType):
    postIds = []
    channelData = json.load(channelType)
    for channel in channelData:
        if "pins" in channel:
            for pinnedPost in channel["pins"]:
                postIds.append(pinnedPost["id"])
    return postIds


def truncTimestamps(postIds):
    for i in range(0, len(postIds)):
        postIds[i] = str(int(postIds[i].split('.')[0]) * 1000)
    return postIds


def getAllPostTimestamps():
    if yaml:
        files = loadZip(yaml["zipfile"])
    else:
        files = loadZip(args.zipfile)
    allPostTimestamps = {}
    for channelType in channelTypes:
        if channelType in files:
            allPostTimestamps[channelType] = getPostTimestamps(
                files[channelType])
            allPostTimestamps[channelType] = truncTimestamps(
                allPostTimestamps[channelType])
    return allPostTimestamps


def getPostsFromDatabase(ids, driver="mysql", dbhost="localhost", dbport="3306", dbuser="mmuser", dbpass="mostest", dbname="mattermost_test"):
    returnIds = []
    if (driver != "psql"):
        try:
            connection = mysql.connector.connect(
                host=dbhost,
                port=dbport,
                user=dbuser,
                passwd=dbpass,
                database=dbname
            )
            cursor = connection.cursor()
            cursor.execute(
                "SELECT Id FROM Posts WHERE CreateAt = UpdateAt AND CreateAt in ('%s')" % "','".join(ids))
            returnIds = cursor.fetchall()
            cursor.close()
            connection.close()
        except (Exception, psycopg2.Error) as error:
            print("Error while connecting to PostgreSQL", error)
    else:
        try:
            connection = psycopg2.connect(user=dbuser,
                                          password=dbpass,
                                          host=dbhost,
                                          port=dbport,
                                          database=dbname)
            cursor = connection.cursor()
            cursor.execute(
                "SELECT Id FROM Posts WHERE CreateAt = UpdateAt AND CreateAt in ('%s')" % "','".join(ids))
            returnIds = cursor.fetchall()
            cursor.close()
            connection.close()
        except (Exception, psycopg2.Error) as error:
            print("Error while connecting to PostgreSQL", error)
    if returnIds != []:
        for i in range(0, len(returnIds)):
            returnIds[i] = returnIds[i][0]
    return returnIds


def pinPosts(allPostIds, mmurl, access_token):
    token = ""
    url = mmurl + "/api/v4/posts/"
    req = "/pin"
    headers = {
        "Authorization": "Bearer %s" % (access_token),
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    for post in allPostIds:
        requrl = url + post + req
        r = requests.post(requrl, headers=headers)
        response = json.loads(r.text)
        if (r.status_code != 200):
            print("Error: " + response[""] + response["message"])
            return 1
        else: 
            print("Pinned " + str(len(allPostIds)) + "post(s).")
            return 0


def main():
    allPostTimestamps = getAllPostTimestamps()
    allPostIds = []
    for channelType in channelTypes:
        if channelType in allPostTimestamps:
            print( "Found " + str(len(allPostTimestamps[channelType])) + " pinned posts in " + channelType)
            if yaml:
                allPostIds += (getPostsFromDatabase(allPostTimestamps[channelType], yaml["dbdriver"], dbhost=yaml["dbhost"],
                                                    dbport=yaml["dbport"], dbuser=yaml["dbuser"], dbpass=yaml["dbpass"], dbname=yaml["dbname"]))
            else:
                allPostIds += (getPostsFromDatabase(allPostTimestamps[channelType], args.dbdriver, dbhost=args.dbhost,
                                                    dbport=args.dbport, dbuser=args.dbuser, dbpass=args.dbpass, dbname=args.dbname))
    if len(allPostIds) > 0:
        if yaml:
            if yaml["dry-run"]:
                print(allPostIds)
                print("Dry run, no posts pinned.")
                exit = 0
            else:
                exit = pinPosts(allPostIds, yaml["mmurl"], yaml["token"])
        else:
            if args.dry_run:
                print(allPostIds)
                print("Dry run, no posts pinned.")
                exit = 0
            else:
                exit = pinPosts(allPostIds, mmurl=args.mmurl, access_token=args.token)
        if exit != 0:
            print("Error occured while pinning, check logs!")
    else:
        print("Warning: No posts to pin found in DB. Exiting.")

main()
