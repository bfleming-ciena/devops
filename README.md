# scripts

##gatherlogs.py

Example
    
    python gatherlogs.py --hosts 199.71.143.62,199.71.143.63 --src "/var/tmp" --local /tmp/bucket --filter ".*user-action.*" --days 5

Store the credentials in a yaml file: ~/.gatherlogs.credentials

    {password: 'mypassword', username: myuser}


