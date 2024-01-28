# webservice
Web service code for the MusicAsLanguage project.


## Development
- Local development
    1. Install Python 3.11 or higher.
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
          use testdb
          db.createUser(
            {
                user: "maluser",
                pwd: "Mal123!",
                roles: [ { role: "readWrite", db: "testdb" } ]
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
    4. Run all unit tests at the repo root directory:
        - Linux Bash
           ```
           export APP_ENV=test
           pytest tests
           pytest tests/test_signup.py::TestUserSignup::test_creating_already_existing_user
           ```
        - Windows CMD
           ```
           set APP_ENV=test
           pytest tests
           pytest tests/test_signup.py::TestUserSignup::test_creating_already_existing_user
           ```
    5. Run the development server.
        - Linux Bash
            ```
            export APP_ENV=dev
            python app.py
            ``` 
        - Windows CMD
            ```
            set APP_ENV=dev
            python app.py
            ``` 
    6. Build/run a docker container for local development:
        - Install docker engine from https://docs.docker.com/engine/install/
        - Linux Bash
            ```
            docker_build_dev.sh
            docker_run_dev.sh
            ``` 
        - Windows CMD
            ```
            docker_build_dev.bat
            docker_run_dev.bat
            ``` 
    6. Following APIs are live:
       - GET: http://127.0.0.1:8000/api/lesson/getLessons

       - POST: http://127.0.0.1:8000/api/auth/signup
         - example body: {"email":"xxxxx@microsoft.com", "password":"xxxxx"}
         - example response: {"id": "602cc4a466b4a9edb913f9c2"}

       - POST: http://127.0.0.1:8000/api/auth/login
         - example body: {"email":"xxxxx@microsoft.com", "password":"xxxxx"}
         - example response: {"token": "xxx"}
       - If you are accessing the APIs above from android/iphone emulator, replace 127.0.0.1 with the emulator ip.
       