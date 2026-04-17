from app import create_app
import os
from dotenv import load_dotenv

load_dotenv('config.env')

app = create_app()

if __name__ == '__main__':
    app.run(app, debug=True, host='0.0.0.0', port=5003) 