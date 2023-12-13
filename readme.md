# Synapse broadcast module

> [!IMPORTANT]  
> 🚧 This repo hosts a POC and is not meant to be used

## Use case 📖

- a user is part of a private federation in which, for some reason, has several accounts on different homeserver
- there's a 3rd party service linking the user and its MXID
- the user wants all the conversations of all his/her MXIDs to be synchronized
- if a message is read (or sent) with a MXID it should be marked read for every MXID

## Idea 💡

These requirements could be met with a Synapse module :

- when a user is invited to or creates a room, all its MXID are invited
- when a message is read, it should be marked as read for all the MXID

## Limitations 🚧

- The receipts part should not be modified like this, but it's just a POC 🤷🏻

## Directory

TODO ...

## Run the POC 🚜

### Prerequisites

- docker / docker compose installed
- traefik and domain name configured

### Start the stack

- fill the .env file

  ```.env
  TRAEFIK_NETWORK=
  DOMAIN=
  USER=("admin_matrix" "alice" "bob")
  SUB_DOMAIN_1=kiwi
  SUB_DOMAIN_2=litchi
  DIRECTORY_URL=https://something-that-returns-an-array-of-mxid?mxid=
  ```

__DIRECTORY_URL :__ an url that, concatenated with a MXID, should return a json array of linked mxid.

- start the stack
  
  ```bash
  chmod +x *.sh  
  ./init.sh
  docker-compose up -d
  ```

- register users (configure in.env) in both servers (password=username, all admin : YOLO!)

  ```bash
  ./register-users.sh
  ```

- if you want to reset the stack (erase database)

  ```bash
  ./reset-stack.sh
  ```

docker-compose logs etc... and go to your domain, login, create room, invite user and try it out!
