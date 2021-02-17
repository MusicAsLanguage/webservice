# webservice
Web service code for the MusicAsLanguage project.


## Development
- Local development
    1. Install Python 3.7 or higher.
    2. Install MongoDB community edition from https://www.mongodb.com/try/download/community, choose the right bits for your OS. 
       Run following commands to create the local db and user:
          ```
          mongo --port 27017
          use admin
          use MusicAsLanguage
          db.createUser(
            {
                user: "maluser",
                pwd: "Mal123!",
                roles: [ { role: "readWrite", db: "MusicAsLanguage" } ]
            }
           )
          ```
    3. Set up python virtual envirnment, run following commands in the repo root.
        - Linux Bash
            ```
            python3 -m venv .venv
            source .venv/bin/activate
            pip install -r requirements.txt
            ```

        - Windows CMD
            ```
            py -3 -m venv .venv
            .venv\scripts\activate
            pip install -r requirements.txt
            ```
    4. Run the development server.
        ```
        flask run
        ``` 
    5. Following APIs are live:
       - GET: http://127.0.0.1:5000/api/lesson/getLessons

       - POST: http://127.0.0.1:5000/api/auth/signup
         - example body: {"email":"shengyfu@microsoft.com", "password":"xxxxx"}
         - example response: {"id": "602cc4a466b4a9edb913f9c2"}

       - POST: http://127.0.0.1:5000/api/auth/login
         - example body: {"email":"shengyfu@microsoft.com", "password":"xxxxx"}
         - example response: {"token": "xxx"}

       