# Helper script 

This script takes a posts.py with 
an array of post ids which contain the posts to be pinned in Mattermost and then runs 
httpie to send the request to mark those posts.

## Requirements
httpie and bash
posts.py with Mattermost postids in an array (`['id1', 'id2', ...]`)

## Instructions
`./pin.sh`
