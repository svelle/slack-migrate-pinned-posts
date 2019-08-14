#!/bin/bash

while getopts h:t:f: option
do
case "${option}"
in
h) HOST=${OPTARG};;
t) TOKEN=${OPTARG};;
f) FILE=${OPTARG};;
esac
done

sed 's/, /\n/g' $FILE > posts.txt
sed "s/\[/ /g" -i posts.txt
sed "s/]/ /g" -i posts.txt
sed "s/'/ /g" -i posts.txt

for i in $(cat posts.txt); do 
    http -v POST $HOST/api/v4/posts/$i/pin "Authorization:Bearer $TOKEN"
done